import os
import random
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from . import ESTIMATOR, REPRESENTATION_VERSION, vectorize
from .estimator import load_image
from .store import FAILED, NO_PERSON, PROCESSED

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# People smaller than this fraction of the frame (on their longer side) are
# background figures whose keypoints are mostly guesswork
MIN_PERSON_FRACTION = 0.1


def scan(root):
  """Recursively yields absolute paths of supported images under root."""
  for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
    dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
    for name in sorted(filenames):
      if os.path.splitext(name)[1].lower() in EXTENSIONS:
        yield os.path.abspath(os.path.join(dirpath, name))


def poses_to_points(path, poses, estimator, size):
  """Turns estimator output into (path, person_id, vector, payload) tuples.
  size: (width, height) of the original image."""
  points = []
  for pose in sorted(poses, key=lambda p: -p.person_confidence):
    x1, y1, x2, y2 = pose.bounding_box
    if max((x2 - x1) / size[0], (y2 - y1) / size[1]) < MIN_PERSON_FRACTION:
      continue
    vec, n_bones = vectorize.encode(pose)
    if n_bones < vectorize.MIN_BONES:
      continue
    norm, mask = vectorize.normalize(pose)
    person_id = len(points)
    points.append((path, person_id, vec, {
      "image_id": os.path.basename(path),
      "image_path": path,
      "person_id": person_id,
      "bbox": [round(v, 1) for v in pose.bounding_box],
      "width": round(size[0]),
      "height": round(size[1]),
      "pose_type": vectorize.pose_type(mask),
      "confidence": round(pose.person_confidence, 4),
      "visible_conf": round(vectorize.visible_confidence(pose), 4),
      "detected": pose.detected,
      "n_bones": n_bones,
      # raw pixel keypoints + scores so results can be re-scored / drawn
      # without re-running the estimator
      "keypoints": [[round(float(x), 1), round(float(y), 1)] for x, y in pose.keypoints],
      "scores": [round(float(s), 3) for s in pose.confidence],
      "estimator": ESTIMATOR,
      "estimator_version": estimator.version,
      "representation_version": REPRESENTATION_VERSION,
    }))
  return points


def _load(path):
  try:
    return path, load_image(path), None
  except Exception as ex:
    return path, None, ex


def image_point(path, image, scale, embedder, n_persons):
  return (path, embedder.embed(image), {
    "image_id": os.path.basename(path),
    "image_path": path,
    "width": round(image.shape[1] / scale),
    "height": round(image.shape[0] / scale),
    "n_persons": n_persons,
    "embedder": embedder.name,
    "representation_version": REPRESENTATION_VERSION,
  })


def run(root, estimator, embedder, store, status, limit=None, workers=4, retry_failed=False, shuffle=False):
  known = status.load()
  # anything indexed under an older representation gets redone
  done = {
    p for p, (st, ver, _) in known.items()
    if ver == REPRESENTATION_VERSION and (st != FAILED or not retry_failed)
  }
  todo = [p for p in scan(root) if p not in done]
  if shuffle:
    # a random --limit sample is more representative than the first N dirs
    random.shuffle(todo)
  if limit:
    todo = todo[:limit]

  print(f"{len(done)} already done, {len(todo)} to process "
        f"(device={estimator.device}, mode={estimator.mode})", file=sys.stderr)

  start = time.time()
  batch, images = [], []
  try:
    for n, (path, loaded, err) in enumerate(_prefetch(todo, workers), 1):
      try:
        if err:
          raise err
        image, scale = loaded
        size = (image.shape[1] / scale, image.shape[0] / scale)
        points = poses_to_points(path, estimator.extract(image, scale), estimator, size)
        batch.extend(points)
        # every readable image gets an embedding, people or not
        images.append(image_point(path, image, scale, embedder, len(points)))
        # an older run may have found more people in this image
        old_n = (known.get(path) or (None, None, 0))[2] or 0
        store.delete_poses(path, range(len(points), old_n))
        status.set(path, PROCESSED if points else NO_PERSON, len(points),
                   estimator=f"{estimator.version}+{embedder.name}",
                   representation_version=REPRESENTATION_VERSION)
      except Exception as ex:
        status.set(path, FAILED, error=f"{type(ex).__name__}: {ex}",
                   representation_version=REPRESENTATION_VERSION)

      if n % 128 == 0:
        _flush(store, status, batch, images)

      if n % 100 == 0 or n == len(todo):
        rate = n / (time.time() - start)
        eta = (len(todo) - n) / rate / 60
        print(f"  {n}/{len(todo)}  {rate:.1f} img/s  eta {eta:.0f}m", file=sys.stderr)
  finally:
    # also on ctrl-c, so an interrupted run keeps what it finished
    _flush(store, status, batch, images)
    print(status.counts(), file=sys.stderr)


def _prefetch(paths, workers):
  """Decodes images in threads, keeping only a few ahead of inference."""
  with ThreadPoolExecutor(workers) as pool:
    pending = deque()
    it = iter(paths)
    for path in it:
      pending.append(pool.submit(_load, path))
      if len(pending) >= workers * 2:
        break
    while pending:
      yield pending.popleft().result()
      path = next(it, None)
      if path is not None:
        pending.append(pool.submit(_load, path))


def _flush(store, status, poses, images):
  # vectors first: if we die in between, the status says "redo it", which is safe
  store.upsert(poses, images)
  status.commit()
  poses.clear()
  images.clear()
