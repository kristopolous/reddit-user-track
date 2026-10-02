"""Contact sheets (JPEG) and the smoke-test HTML page."""
import html
import os
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageOps

from . import vectorize
from .retrieve import pose_from_payload

LIMB_COLORS = {"l_": (60, 160, 255), "r_": (255, 110, 60)}


def _bone_color(a, b):
  for prefix, color in LIMB_COLORS.items():
    if a.startswith(prefix) and b.startswith(prefix):
      return color
  return (80, 230, 80)


def skeleton_lines(pose):
  """[(x1, y1, x2, y2, (r, g, b)), ...] for each visible bone."""
  pts = vectorize.visible_joints(pose)
  return [
    (*map(float, pts[a]), *map(float, pts[b]), _bone_color(a, b))
    for a, b in vectorize.BONES if a in pts and b in pts
  ]


def draw_pose(im, pose, width=None):
  width = width or max(2, round(max(im.size) / 250))
  d = ImageDraw.Draw(im)
  d.rectangle(pose.bounding_box, outline=(255, 255, 0), width=max(1, width // 2))
  for x1, y1, x2, y2, color in skeleton_lines(pose):
    d.line((x1, y1, x2, y2), fill=color, width=width)
  return im


def open_with_pose(path, pose=None):
  im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
  return draw_pose(im, pose) if pose else im


def contact_sheet(matches, out_path, cell=256, cols=5):
  """matches: list of retrieve.Match"""
  label_h = 34
  rows = max(1, (len(matches) + cols - 1) // cols)
  sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), (24, 24, 24))
  d = ImageDraw.Draw(sheet)

  for i, m in enumerate(matches):
    x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
    try:
      im = open_with_pose(m.payload["image_path"], pose_from_payload(m.payload))
      im.thumbnail((cell, cell))
      sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
    except Exception as ex:
      d.text((x + 4, y + 4), f"unreadable: {ex}"[:40], fill=(255, 80, 80))
    d.text((x + 4, y + cell + 2), f"{i + 1}. {m.score:.3f} {m.payload['pose_type']}", fill=(255, 255, 255))
    d.text((x + 4, y + cell + 17), _tail(m.payload["image_path"], 40), fill=(170, 170, 170))

  sheet.save(out_path, quality=90)


def _tail(path, n):
  path = "/".join(path.split("/")[-2:])
  return path if len(path) <= n else "…" + path[-(n - 1):]


# ---- smoke test page -------------------------------------------------------

PAGE = """<!doctype html>
<meta charset=utf-8>
<title>pose-search smoke test</title>
<style>
  body {{ background:#181818; color:#ddd; font:13px system-ui, sans-serif; margin:16px }}
  .row {{ display:flex; gap:8px; margin-bottom:18px; align-items:center; overflow-x:auto }}
  .row > div {{ flex:none }}
  .cell {{ width:{s}px; height:{s}px; background:#000; display:block }}
  .query .cell {{ outline:3px solid #fc0 }}
  .cap {{ font-size:12px; color:#aaa; width:{s}px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis }}
  .cap b {{ color:#fff }}
  .arrow {{ font-size:28px; color:#666 }}
  label {{ user-select:none; margin-left:1em }}
  body.noskel .skel {{ display:none }}
</style>
<p>{summary}
  <label><input type=checkbox checked
    onchange="document.body.classList.toggle('noskel', !this.checked)"> skeletons</label>
  <label><input type=checkbox
    onchange="for (const s of document.querySelectorAll('svg.cell'))
                s.setAttribute('viewBox', s.dataset[this.checked ? 'full' : 'crop'])"> full frame</label></p>
{rows}
"""


def _svg(payload, base_dir):
  """The image, zoomed to the matched person, with the skeleton drawn over it."""
  pose = pose_from_payload(payload)
  w, h = payload["width"], payload["height"]
  x1, y1, x2, y2 = pose.bounding_box
  side = max(x2 - x1, y2 - y1) * 1.15
  cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
  crop = f"{cx - side / 2:.0f} {cy - side / 2:.0f} {side:.0f} {side:.0f}"
  sw = side / 90

  src = html.escape(quote(os.path.relpath(payload["image_path"], base_dir)))
  parts = [f'<image href="{src}" width="{w}" height="{h}"/><g class=skel>',
           f'<rect x="{x1:.0f}" y="{y1:.0f}" width="{x2 - x1:.0f}" height="{y2 - y1:.0f}" '
           f'fill="none" stroke="#ff0" stroke-width="{sw / 2:.1f}" opacity=".5"/>']
  for ax, ay, bx, by, (r, g, b) in skeleton_lines(pose):
    parts.append(f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{bx:.0f}" y2="{by:.0f}" '
                 f'stroke="rgb({r},{g},{b})" stroke-width="{sw:.1f}" stroke-linecap="round"/>')
  return (f'<svg class=cell viewBox="{crop}" data-crop="{crop}" data-full="0 0 {w} {h}">'
          f'{"".join(parts)}</g></svg>')


def _cell(payload, caption, base_dir, cls=""):
  path = html.escape(payload["image_path"])
  return (f'<div class="{cls}" title="{path}">{_svg(payload, base_dir)}'
          f'<div class=cap>{caption}</div></div>')


def smoke_page(rows, out_path, summary, size=240):
  """rows: [(query_payload, [Match, ...]), ...]"""
  base = os.path.dirname(os.path.abspath(out_path))
  out = []
  for query, matches in rows:
    cells = [_cell(query, f"<b>query</b> {query['pose_type']} · {query['n_bones']} bones · "
                          f"{html.escape(_tail(query['image_path'], 60))}", base, "query"),
             '<div class=arrow>→</div>']
    for m in matches:
      pl = m.payload
      cells.append(_cell(pl, f"<b>{m.score:.2f}</b> {pl['pose_type']} · "
                             f"{html.escape(_tail(pl['image_path'], 60))}", base))
    out.append(f'<div class=row>{"".join(cells)}</div>')

  with open(out_path, "w") as fp:
    fp.write(PAGE.format(s=size, summary=html.escape(summary), rows="\n".join(out)))
