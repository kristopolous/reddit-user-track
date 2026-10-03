"""Search: route each query to pose search or generic image search.

A query whose pose is trustworthy (enough bones, confident joints) is matched
by pose against other trustworthy poses. Anything else - a midsection, an
extreme close-up, no person at all - is matched by its DINOv2 image vector.

For pose search, Qdrant does the first pass (bone-direction dot product);
other metrics re-rank a larger candidate pool from that pass, so trying a new
metric is just a new function in METRICS.
"""
from dataclasses import dataclass

import numpy as np

from . import vectorize
from .estimator import PersonPose


@dataclass
class Match:
  score: float
  payload: dict


def pose_from_payload(pl):
  return PersonPose(
    keypoints=np.array(pl["keypoints"], dtype=np.float32),
    confidence=np.array(pl["scores"], dtype=np.float32),
    bounding_box=tuple(pl["bbox"]),
    person_confidence=pl["confidence"],
  )


def bones(query_vec, query_pose, point):
  """Sum of cosines over bones both poses have. Rewards more shared evidence."""
  return point.score


def bones_mean(query_vec, query_pose, point):
  """Mean cosine over shared bones. Pure agreement; ignores how much is shared,
  so tiny overlaps (one forearm) can win. Needs at least 3 shared bones."""
  cand = np.asarray(point.vector, dtype=np.float32)
  shared = np.count_nonzero((query_vec.reshape(-1, 2) != 0).any(1) & (cand.reshape(-1, 2) != 0).any(1))
  return point.score / shared if shared >= 3 else -1.0


def joints(query_vec, query_pose, point):
  """Negative mean distance between normalized joints visible in both."""
  q, qmask = vectorize.normalize(query_pose)
  c, cmask = vectorize.normalize(pose_from_payload(point.payload))
  both = qmask & cmask
  if both.sum() < 4:
    return -1e9
  return -float(np.linalg.norm(q[both] - c[both], axis=1).mean())


METRICS = {"bones": bones, "bones_mean": bones_mean, "joints": joints}


# A pose is trusted only with this many bones and this mean score over the
# joints it claims to see. Starting guesses: tune them with the smoke page.
MIN_BONES = 5
MIN_CONF = 0.6


def trusted(payload, min_bones=MIN_BONES, min_conf=MIN_CONF):
  return payload["n_bones"] >= min_bones and payload["visible_conf"] >= min_conf


def route(poses, min_bones=MIN_BONES, min_conf=MIN_CONF):
  """poses: payload dicts for one image. Returns the trusted pose with the
  most bones, or None meaning "use the image vector"."""
  good = [p for p in poses if trusted(p, min_bones, min_conf)]
  return max(good, key=lambda p: (p["n_bones"], p["visible_conf"])) if good else None


def search(store, query_vec, query_pose=None, limit=20, exclude_image=None,
           metric="bones", pool=200, one_per_image=True, min_bones=MIN_BONES, min_conf=MIN_CONF):
  fn = METRICS[metric]
  if fn is not bones and query_pose is None:
    raise ValueError(f"metric {metric} needs the query pose")

  # untrusted poses are left out of results too; those images are still
  # reachable through image search
  points = store.search(query_vec, limit=max(pool, limit * 3), exclude_image=exclude_image,
                        with_vectors=fn is bones_mean, min_bones=min_bones, min_conf=min_conf)
  scored = sorted(((fn(query_vec, query_pose, p), p) for p in points), key=lambda t: -t[0])

  out, seen = [], set()
  for score, p in scored:
    if one_per_image:
      if p.payload["image_path"] in seen:
        continue
      seen.add(p.payload["image_path"])
    out.append(Match(float(score), p.payload))
    if len(out) == limit:
      break
  return out


def search_images(store, image_vec, limit=20, exclude_image=None):
  return [Match(float(p.score), p.payload)
          for p in store.search_images(image_vec, limit=limit, exclude_image=exclude_image)]
