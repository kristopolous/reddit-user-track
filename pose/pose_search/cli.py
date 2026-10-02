import argparse
import os
import sys

import numpy as np

from . import vectorize


def _store(args):
  from .store import Status, VectorStore
  return VectorStore(args.index_dir, url=args.qdrant_url), Status(args.index_dir)


def _estimator(args):
  from .estimator import RTMPoseEstimator
  return RTMPoseEstimator(mode=args.mode, device=args.device)


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


def cmd_index(args):
  from . import indexer
  store, status = _store(args)
  indexer.run(args.archive, _estimator(args), store, status, limit=args.limit,
              workers=args.workers, retry_failed=args.retry_failed, shuffle=args.shuffle)


def cmd_show(args):
  """Phase 1/2: one image -> skeleton overlay + the vector it produces."""
  from .output import draw_pose, open_with_pose
  poses = _query_pose(args, _estimator(args), args.image)
  im = open_with_pose(args.image)
  for i, pose in enumerate(poses):
    draw_pose(im, pose)
    vec, n = vectorize.encode(pose)
    norm, mask = vectorize.normalize(pose)
    print(f"person {i}: confidence {pose.person_confidence:.3f}, "
          f"{vectorize.pose_type(mask)}, {n} bones, bbox {[round(v) for v in pose.bounding_box]}")
    for name, xy, ok in zip(vectorize.KEYPOINTS, norm, mask):
      print(f"  {name:11s} {'%6.2f %6.2f' % tuple(xy) if ok else '     -      -'}")
    print("  bones:", ", ".join(vectorize.visible_bones(vec)))
  out = args.out or os.path.splitext(os.path.basename(args.image))[0] + "-pose.jpg"
  im.save(out, quality=90)
  print(f"wrote {out}")


def cmd_search(args):
  from . import retrieve
  from .output import contact_sheet, open_with_pose

  store, _ = _store(args)
  pose = _query_pose(args, _estimator(args), args.image)[args.person]
  vec, _ = vectorize.encode(pose)
  matches = retrieve.search(store, vec, pose, limit=args.limit, metric=args.metric,
                            exclude_image=os.path.abspath(args.image))

  os.makedirs(args.out, exist_ok=True)
  open_with_pose(args.image, pose).save(os.path.join(args.out, "query.jpg"), quality=90)
  contact_sheet(matches, os.path.join(args.out, "results.jpg"))
  for m in matches:
    print(f"{m.score:8.3f}  {m.payload['pose_type']:14s} person {m.payload['person_id']}  {m.payload['image_path']}")
  print(f"wrote {args.out}/query.jpg and {args.out}/results.jpg", file=sys.stderr)


def cmd_smoke(args):
  """Random indexed images -> their nearest neighbours, as one HTML page.

  Uses the stored poses, so it needs no estimator or GPU.
  """
  from . import retrieve
  from .output import smoke_page

  store, status = _store(args)
  total = store.count()
  if not total:
    sys.exit(f"nothing indexed in {args.index_dir}; run `pose-search index` first")

  rows = []
  for path in status.random_processed(args.n):
    points = store.get(path)
    if not points:
      continue
    query = points[0]  # most confident person
    vec = np.asarray(query.vector, dtype=np.float32)
    matches = retrieve.search(store, vec, retrieve.pose_from_payload(query.payload),
                              limit=args.k, metric=args.metric, exclude_image=path)
    rows.append((query.payload, matches))

  smoke_page(rows, args.out, f"{len(rows)} random queries · metric={args.metric} · "
                             f"{total} poses indexed · {status.counts()}")
  print(f"wrote {args.out}")


def cmd_stats(args):
  store, status = _store(args)
  print(f"poses: {store.count()}")
  for k, v in sorted(status.counts().items()):
    print(f"{k}: {v}")


def main():
  from .retrieve import METRICS

  p = argparse.ArgumentParser(prog="pose-search")
  p.add_argument("--index-dir", default=os.environ.get("POSE_INDEX", "pose-index"),
                 help="where vectors + indexing status live (default ./pose-index, or $POSE_INDEX)")
  p.add_argument("--qdrant-url", default=os.environ.get("QDRANT_URL"),
                 help="use a Qdrant server instead of the embedded store")
  sub = p.add_subparsers(dest="cmd", required=True)

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
  estimator_args(sp)
  sp.set_defaults(fn=cmd_show)

  sp = sub.add_parser("search", help="find similar poses to an image, write a contact sheet")
  sp.add_argument("image")
  sp.add_argument("--limit", type=int, default=20)
  sp.add_argument("--person", type=int, default=0, help="which detected person (0 = most confident)")
  sp.add_argument("--metric", default="bones", choices=METRICS)
  sp.add_argument("--out", default="results")
  estimator_args(sp)
  sp.set_defaults(fn=cmd_search)

  sp = sub.add_parser("smoke", help="HTML page of random indexed images and their nearest poses")
  sp.add_argument("-n", type=int, default=12, help="number of query images")
  sp.add_argument("-k", type=int, default=4, help="results per query")
  sp.add_argument("--metric", default="bones", choices=METRICS)
  sp.add_argument("--out", default="pose-smoke.html",
                  help="image links are relative to this file's directory")
  sp.set_defaults(fn=cmd_smoke)

  sp = sub.add_parser("stats")
  sp.set_defaults(fn=cmd_stats)

  args = p.parse_args()
  args.fn(args)


if __name__ == "__main__":
  main()
