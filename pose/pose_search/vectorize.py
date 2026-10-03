"""Pose normalization and vectorization.

The search vector is built from bone *directions*: for each bone, the unit
vector from one joint to the other. Directions ignore where the person is in
the frame and how big they are, and they capture what we care about (arms up
vs down, knees bent, torso leaning, head tilt).

A bone whose endpoints aren't both confidently visible is left as (0, 0).
The vector store uses a plain dot product, so the score is

    sum over bones visible in BOTH poses of cos(angle between them)

A bone missing from either side adds 0: it neither helps nor hurts. That's
how partial observations get compared on what they share, rather than being
punished for what's out of frame.
"""
import numpy as np

from .estimator import KEYPOINTS

J = {name: i for i, name in enumerate(KEYPOINTS)}

# Virtual joints are averages of two real ones
VIRTUAL = {
  "neck": ("l_shoulder", "r_shoulder"),
  "pelvis": ("l_hip", "r_hip"),
}

BONES = [
  # arms
  ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"),
  ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"),
  # legs
  ("l_hip", "l_knee"), ("l_knee", "l_ankle"),
  ("r_hip", "r_knee"), ("r_knee", "r_ankle"),
  # torso
  ("l_shoulder", "r_shoulder"), ("l_hip", "r_hip"),
  ("l_shoulder", "l_hip"), ("r_shoulder", "r_hip"),
  ("neck", "pelvis"),
  # head
  ("neck", "nose"), ("l_eye", "r_eye"), ("l_ear", "r_ear"),
]

DIM = len(BONES) * 2

# Joints below this score are treated as not visible
KPT_THRESHOLD = 0.4

# A pose needs this many usable bones to be worth indexing
MIN_BONES = 2


def visible_joints(pose, threshold=KPT_THRESHOLD):
  """name -> (x, y) for every confidently visible joint, virtual ones included."""
  pts = {
    name: pose.keypoints[i]
    for i, name in enumerate(KEYPOINTS)
    if pose.confidence[i] >= threshold
  }
  for name, (a, b) in VIRTUAL.items():
    if a in pts and b in pts:
      pts[name] = (pts[a] + pts[b]) / 2
  return pts


def normalize(pose, threshold=KPT_THRESHOLD):
  """Keypoints relative to a body origin and divided by a body scale.

  Returns ((17, 2) array, (17,) visibility mask). Invisible joints are NaN,
  never 0, so nothing downstream mistakes them for a real position.
  """
  pts = visible_joints(pose, threshold)

  if "pelvis" in pts:
    origin = pts["pelvis"]
  elif "neck" in pts:
    origin = pts["neck"]
  else:
    x1, y1, x2, y2 = pose.bounding_box
    origin = np.array([(x1 + x2) / 2, (y1 + y2) / 2])

  if "pelvis" in pts and "neck" in pts:
    scale = np.linalg.norm(pts["neck"] - pts["pelvis"])
  elif "l_shoulder" in pts and "r_shoulder" in pts:
    # shoulder width is roughly 0.8 torso lengths
    scale = np.linalg.norm(pts["l_shoulder"] - pts["r_shoulder"]) / 0.8
  else:
    x1, y1, x2, y2 = pose.bounding_box
    scale = max(x2 - x1, y2 - y1) / 3

  scale = max(scale, 1e-6)
  mask = pose.confidence >= threshold
  out = np.full((len(KEYPOINTS), 2), np.nan, dtype=np.float32)
  out[mask] = (pose.keypoints[mask] - origin) / scale
  return out, mask


def encode(pose, threshold=KPT_THRESHOLD):
  """Returns (vector, n_bones). Vector is DIM floats; missing bones are 0."""
  pts = visible_joints(pose, threshold)
  vec = np.zeros(DIM, dtype=np.float32)
  n = 0
  for i, (a, b) in enumerate(BONES):
    if a in pts and b in pts:
      d = pts[b] - pts[a]
      length = np.linalg.norm(d)
      if length > 1e-6:
        vec[2 * i:2 * i + 2] = d / length
        n += 1
  return vec, n


def visible_confidence(pose, threshold=KPT_THRESHOLD):
  """Mean score of the joints claimed visible: how sure the model is about
  what it says it sees. Unlike the all-joint mean, a crop isn't penalized
  for what's out of frame."""
  sc = pose.confidence[pose.confidence >= threshold]
  return float(sc.mean()) if len(sc) else 0.0


def visible_bones(vec):
  return [
    f"{a}-{b}" for i, (a, b) in enumerate(BONES)
    if vec[2 * i] != 0 or vec[2 * i + 1] != 0
  ]


def pose_type(mask):
  """Rough label of what's in frame, for inspection and later filtering."""
  either = lambda *names: any(mask[J[n]] for n in names)
  shoulders = either("l_shoulder", "r_shoulder")
  hips = either("l_hip", "r_hip")
  legs = either("l_knee", "r_knee")
  head = either("nose", "l_eye", "r_eye")

  if shoulders and hips and legs:
    return "full_body" if either("l_ankle", "r_ankle") else "three_quarter"
  if shoulders and hips:
    return "upper_body"
  if head and shoulders:
    return "head_shoulders"
  if head:
    return "head"
  if hips or legs:
    return "legs"
  return "partial"
