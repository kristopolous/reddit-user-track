"""Nearest-pose search, with optional re-scoring by other distance functions.

Qdrant always does the first pass (bone-direction dot product). Other metrics
re-rank a larger candidate pool from that pass, so trying a new metric is
just a new function in METRICS.
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


def search(store, query_vec, query_pose=None, limit=20, exclude_image=None,
           metric="bones", pool=200, one_per_image=True):
  fn = METRICS[metric]
  if fn is not bones and query_pose is None:
    raise ValueError(f"metric {metric} needs the query pose")

  points = store.search(query_vec, limit=max(pool, limit * 3), exclude_image=exclude_image,
                        with_vectors=fn is bones_mean)
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
