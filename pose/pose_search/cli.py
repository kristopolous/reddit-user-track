import argparse
import os
import sys

import numpy as np

from . import vectorize


def _store(args):
  from .embedder import MODELS
  from .store import Status, VectorStore
  dim = MODELS[args.embed_model][1] * 2
  return VectorStore(args.index_dir, url=args.qdrant_url, image_dim=dim), Status(args.index_dir)


def _estimator(args):
  from .estimator import RTMPoseEstimator
  return RTMPoseEstimator(mode=args.mode, device=args.device)


def _embedder(args):
  from .embedder import DinoEmbedder
  return DinoEmbedder(args.embed_model, device=args.device)


def _query_pose(args, estimator, path):
  from .estimator import load_image
  image, scale = load_image(path)
  poses = sorted(estimator.extract(image, scale), key=lambda p: -p.person_confidence)
  poses = [p for p in poses if vectorize.encode(p)[1] >= vectorize.MIN_BONES]
  if not poses:
    sys.exit(f"no usable pose found in {path}")
  if args.person >= len(poses):
    sys.exit(f"only {len(poses)} people found in {path}")
  return poses


def _thresholds(args):
  return dict(min_bones=args.min_bones, min_conf=args.min_conf)


def cmd_index(args):
  from . import indexer
  store, status = _store(args)
  indexer.run(args.archive, _estimator(args), _embedder(args), store, status, limit=args.limit,
              workers=args.workers, retry_failed=args.retry_failed, shuffle=args.shuffle)


def cmd_show(args):
  """Phase 1/2: one image -> skeleton overlay + the vector it produces."""
  from . import retrieve
  from .output import draw_pose, open_with_pose
  poses = _query_pose(args, _estimator(args), args.image)
  im = open_with_pose(args.image)
  for i, pose in enumerate(poses):
    draw_pose(im, pose)
    vec, n = vectorize.encode(pose)
    norm, mask = vectorize.normalize(pose)
    conf = vectorize.visible_confidence(pose)
    ok = retrieve.trusted({"n_bones": n, "visible_conf": conf}, **_thresholds(args))
    print(f"person {i}: {vectorize.pose_type(mask)}, {n} bones, visible-joint conf {conf:.3f}, "
          f"{'person box' if pose.detected else 'no person box (whole frame)'}, "
          f"bbox {[round(v) for v in pose.bounding_box]} -> {'pose' if ok else 'image'} search")
    for name, xy, sc in zip(vectorize.KEYPOINTS, norm, pose.confidence):
      xy = '%6.2f %6.2f' % tuple(xy) if sc >= vectorize.KPT_THRESHOLD else '     -      -'
      print(f"  {name:11s} {xy}   score {sc:.2f}")
    print("  bones:", ", ".join(vectorize.visible_bones(vec)))
  out = args.out or os.path.splitext(os.path.basename(args.image))[0] + "-pose.jpg"
  im.save(out, quality=90)
  print(f"wrote {out}")


def _search(store, route, pose_point, image_vec, path, args):
  """pose_point: (vector, payload) of the query pose, or None."""
  from . import retrieve
  if route == "pose":
    vec, payload = pose_point
    return retrieve.search(store, np.asarray(vec, dtype=np.float32), retrieve.pose_from_payload(payload),
                           limit=args.k, metric=args.metric, exclude_image=path, **_thresholds(args))
  return retrieve.search_images(store, image_vec, limit=args.k, exclude_image=path)


def _routes(args, best_pose):
  if args.route == "auto":
    return ["pose" if best_pose else "image"]
  if args.route == "both":
    return (["pose"] if best_pose else []) + ["image"]
  return [args.route]


def cmd_search(args):
  from . import retrieve
  from .estimator import load_image
  from .indexer import poses_to_points
  from .output import contact_sheet, open_with_pose

  store, _ = _store(args)
  estimator, path = _estimator(args), os.path.abspath(args.image)
  image, scale = load_image(path)
  size = (image.shape[1] / scale, image.shape[0] / scale)
  points = poses_to_points(path, estimator.extract(image, scale), estimator, size)

  if args.person is not None:
    if args.person >= len(points):
      sys.exit(f"only {len(points)} people found in {path}")
    chosen = points[args.person]
  else:
    best = retrieve.route([pl for *_, pl in points], **_thresholds(args))
    chosen = next((pt for pt in points if pt[3] is best), None)
    if chosen is None and args.route == "pose" and points:
      chosen = points[0]  # forced: use the most confident one even if untrusted
  # a single search, so "both" behaves like "auto"
  route = "image" if args.route == "image" or chosen is None else "pose"
  if args.route == "pose" and chosen is None:
    sys.exit(f"no pose found in {path}")

  args.k = args.limit
  image_vec = _embedder(args).embed(image) if route == "image" else None
  matches = _search(store, route, chosen and (chosen[2], chosen[3]), image_vec, path, args)

  os.makedirs(args.out, exist_ok=True)
  pose = retrieve.pose_from_payload(chosen[3]) if route == "pose" else None
  open_with_pose(path, pose).save(os.path.join(args.out, "query.jpg"), quality=90)
  contact_sheet(matches, os.path.join(args.out, "results.jpg"))
  print(f"route: {route}", file=sys.stderr)
  for m in matches:
    pl = m.payload
    who = f"{pl['pose_type']:14s} person {pl['person_id']}" if "keypoints" in pl else f"{'image':14s}"
    print(f"{m.score:8.3f}  {who}  {pl['image_path']}")
  print(f"wrote {args.out}/query.jpg and {args.out}/results.jpg", file=sys.stderr)


def cmd_smoke(args):
  """Random indexed images -> their nearest neighbours, as one HTML page.

  Uses the stored vectors, so it needs no models or GPU.
  """
  from . import retrieve
  from .output import smoke_page

  store, status = _store(args)
  if not store.count("images"):
    sys.exit(f"no image vectors in {args.index_dir}; run `pose-search index` "
             f"(indexes from before image search get upgraded automatically)")

  rows = []
  for path in status.random_indexed(args.n, args.only):
    image = store.get_image(path)
    if image is None:
      continue
    poses = store.get(path)
    best = retrieve.route([p.payload for p in poses], **_thresholds(args))
    point = next((p for p in poses if p.payload is best), None)
    if point is None and args.route in ("pose", "both") and poses:
      point = poses[0]  # forced/comparing: most confident, even if untrusted

    for route in _routes(args, point):
      if route == "pose" and point is None:
        continue
      matches = _search(store, route, point and (point.vector, point.payload), image.vector, path, args)
      label = route if route == "image" or best is not None else "pose (untrusted)"
      rows.append((label, point.payload if route == "pose" else image.payload, matches))

  routes = [r.split()[0] for r, *_ in rows]
  smoke_page(rows, args.out,
             f"{args.n} random images · route={args.route} ({routes.count('pose')} pose, "
             f"{routes.count('image')} image) · metric={args.metric} · trust: ≥{args.min_bones} bones, "
             f"conf ≥{args.min_conf} · {store.count()} poses, {store.count('images')} images · "
             f"{status.counts()}")
  print(f"wrote {args.out}")


def cmd_stats(args):
  store, status = _store(args)
  print(f"poses: {store.count()}")
  print(f"images: {store.count('images')}")
  for k, v in sorted(status.counts().items()):
    print(f"{k}: {v}")


def main():
  from .retrieve import METRICS, MIN_BONES, MIN_CONF

  p = argparse.ArgumentParser(prog="pose-search")
  p.add_argument("--index-dir", default=os.environ.get("POSE_INDEX", "pose-index"),
                 help="where vectors + indexing status live (default ./pose-index, or $POSE_INDEX)")
  p.add_argument("--qdrant-url", default=os.environ.get("QDRANT_URL"),
                 help="use a Qdrant server instead of the embedded store")
  p.add_argument("--embed-model", default="small", choices=["small", "base"],
                 help="DINOv2 size for image search; must match what the index was built with")
  sub = p.add_subparsers(dest="cmd", required=True)

  def search_args(sp):
    sp.add_argument("--route", default="auto", choices=["auto", "pose", "image", "both"],
                    help="auto: pose search if the pose is trusted, else image search. "
                         "both: one row of each, to compare")
    sp.add_argument("--metric", default="bones", choices=METRICS, help="pose-search scoring")
    sp.add_argument("--min-bones", type=int, default=MIN_BONES, help="pose trust threshold")
    sp.add_argument("--min-conf", type=float, default=MIN_CONF, help="pose trust threshold")

  def estimator_args(sp):
    sp.add_argument("--device", choices=["cpu", "cuda", "rocm", "mps"],
                    help="default: whatever onnxruntime has, else cpu")
    sp.add_argument("--mode", default="balanced", choices=["lightweight", "balanced", "performance"])

  sp = sub.add_parser("index", help="index an image archive (resumable)")
  sp.add_argument("archive")
  sp.add_argument("--limit", type=int)
  sp.add_argument("--workers", type=int, default=4, help="image decoding threads")
  sp.add_argument("--shuffle", action="store_true", help="process in random order (good with --limit)")
  sp.add_argument("--retry-failed", action="store_true")
  # resuming is always on; the flag is accepted for the spec's sake
  sp.add_argument("--resume", action="store_true", help=argparse.SUPPRESS)
  estimator_args(sp)
  sp.set_defaults(fn=cmd_index)

  sp = sub.add_parser("show", help="draw the detected skeleton(s) and print the pose vector")
  sp.add_argument("image")
  sp.add_argument("--out")
  sp.add_argument("--person", type=int, default=0)
  sp.add_argument("--min-bones", type=int, default=MIN_BONES)
  sp.add_argument("--min-conf", type=float, default=MIN_CONF)
  estimator_args(sp)
  sp.set_defaults(fn=cmd_show)

  sp = sub.add_parser("search", help="find similar poses to an image, write a contact sheet")
  sp.add_argument("image")
  sp.add_argument("--limit", type=int, default=20)
  sp.add_argument("--person", type=int, help="search by this person's pose (0 = most confident)")
  sp.add_argument("--out", default="results")
  search_args(sp)
  estimator_args(sp)
  sp.set_defaults(fn=cmd_search)

  sp = sub.add_parser("smoke", help="HTML page of random indexed images and their nearest poses")
  sp.add_argument("-n", type=int, default=12, help="number of query images")
  sp.add_argument("-k", type=int, default=4, help="results per query")
  sp.add_argument("--only", metavar="TEXT", help="only query images whose path contains TEXT")
  search_args(sp)
  sp.add_argument("--out", default="pose-smoke.html",
                  help="image links are relative to this file's directory")
  sp.set_defaults(fn=cmd_smoke)

  sp = sub.add_parser("stats")
  sp.set_defaults(fn=cmd_stats)

  args = p.parse_args()
  args.fn(args)


if __name__ == "__main__":
  main()
