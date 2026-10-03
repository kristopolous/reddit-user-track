"""Generic image embedding (DINOv2), the fallback for when there's no
trustworthy skeleton: midsections, extreme close-ups, odd crops.

DINOv2 is self-supervised, and its features keep a lot of geometry
(orientation, viewpoint, framing), so nearest neighbours tend to share
"turned to the side" even with no joints to go on. They also share clothing
and background more than pose search would, which is the trade-off.
"""
import numpy as np

from .estimator import PROVIDERS, pick_device

MODELS = {
  "small": ("onnx-community/dinov2-small", 384),
  "base": ("onnx-community/dinov2-base", 768),
}

SIZE = 224  # multiple of the 14px patch
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class DinoEmbedder:
  def __init__(self, model="small", device=None):
    import onnxruntime
    from huggingface_hub import hf_hub_download

    repo, width = MODELS[model]
    self.name = f"dinov2-{model}"
    # class token + mean of patch tokens, as in DINOv2's own linear probes
    self.dim = width * 2
    self.device = device or pick_device()
    path = hf_hub_download(repo, "onnx/model.onnx")
    self.session = onnxruntime.InferenceSession(
      path, providers=list(dict.fromkeys([PROVIDERS[self.device], "CPUExecutionProvider"])))

  def embed(self, image):
    """image: BGR array (from estimator.load_image). Returns unit-length vector."""
    from PIL import Image

    # pad to square instead of center-cropping: in a close-up the edges matter
    rgb = Image.fromarray(np.ascontiguousarray(image[:, :, ::-1]))
    side = max(rgb.size)
    square = Image.new("RGB", (side, side), (124, 116, 104))  # ~ImageNet mean
    square.paste(rgb, ((side - rgb.width) // 2, (side - rgb.height) // 2))
    x = np.asarray(square.resize((SIZE, SIZE), Image.BICUBIC), dtype=np.float32) / 255
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None]

    tokens = self.session.run(None, {"pixel_values": x})[0][0]
    unit = lambda v: v / (np.linalg.norm(v) + 1e-9)
    # normalized separately so neither half dominates the cosine
    return unit(np.concatenate([unit(tokens[0]), unit(tokens[1:].mean(0))]))
