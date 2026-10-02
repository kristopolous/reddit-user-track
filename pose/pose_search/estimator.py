"""Person detection + pose estimation.

Anything with an `extract(image) -> list[PersonPose]` method and `name` /
`version` attributes can stand in for RTMPoseEstimator.
"""
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

# COCO-17 ordering, which is what RTMPose (body7) emits
KEYPOINTS = [
  "nose", "l_eye", "r_eye", "l_ear", "r_ear",
  "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist",
  "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle",
]

# Images get shrunk to this before inference; coordinates are mapped back
MAX_SIDE = 1280


@dataclass
class PersonPose:
  keypoints: np.ndarray       # (17, 2) pixel coords in the original image
  confidence: np.ndarray      # (17,) per-joint score
  bounding_box: tuple         # (x1, y1, x2, y2) pixel coords
  person_confidence: float


def load_image(path):
  """Returns (BGR uint8 array, scale) where scale maps original -> array coords."""
  im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
  scale = min(1.0, MAX_SIDE / max(im.size))
  if scale < 1.0:
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.BILINEAR)
  return np.ascontiguousarray(np.asarray(im)[:, :, ::-1]), scale


def pick_device():
  import onnxruntime
  providers = onnxruntime.get_available_providers()
  for provider, device in [
      ("CUDAExecutionProvider", "cuda"),
      ("ROCMExecutionProvider", "rocm"),
      ("CoreMLExecutionProvider", "mps")]:
    if provider in providers:
      return device
  return "cpu"


class RTMPoseEstimator:
  name = "rtmpose"

  def __init__(self, mode="balanced", device=None):
    from rtmlib import Body
    import rtmlib

    self.device = device or pick_device()
    self.mode = mode
    self.version = f"rtmlib-{rtmlib.__version__ if hasattr(rtmlib, '__version__') else '?'}-{mode}"
    body = Body(mode=mode, backend="onnxruntime", device=self.device)
    self.det_model = body.det_model
    self.pose_model = body.pose_model

  def extract(self, image, scale=1.0):
    """image: BGR array (from load_image). scale: as returned by load_image."""
    boxes = self.det_model(image)
    # rtmlib's pose model runs on the whole frame when handed no boxes,
    # which would invent a person for every empty picture
    if len(boxes) == 0:
      return []

    keypoints, scores = self.pose_model(image, bboxes=boxes)
    return [
      PersonPose(
        keypoints=kp / scale,
        confidence=sc,
        bounding_box=tuple(float(v) / scale for v in box),
        # the detector doesn't surface its score, so use the joints'
        person_confidence=float(np.mean(sc)),
      )
      for kp, sc, box in zip(keypoints, scores, boxes)
    ]
