"""Local web UI: drop (or paste, or pick) an image and see similar poses.

Models load once at startup, so each search after that is quick. Click any
result to search by that image instead. Only images that are in the index
are ever served, so this doesn't expose the rest of the filesystem.
"""
import html
import io
import json
import mimetypes
import sys
import threading
import urllib.request
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from PIL import Image

from . import retrieve
from .estimator import load_image
from .indexer import image_point, poses_to_points
from .output import STYLE, TOGGLES, rows_html

MAX_UPLOAD = 50 << 20
KEEP_UPLOADS = 50

PAGE = """<!doctype html>
<meta charset=utf-8>
<title>pose-search</title>
<style>%(style)s
  #bar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px }
  #drop { border:2px dashed #555; border-radius:8px; padding:18px 24px; color:#999; cursor:pointer }
  body.dragging #drop { border-color:#fc0; color:#fc0; background:#2a2a1a }
  #msg { color:#999 } #msg.err { color:#f66 }
  select, button { background:#222; color:#ddd; border:1px solid #444; border-radius:4px; padding:3px 6px }
  #results .row { flex-wrap:wrap; align-items:flex-start; overflow:visible;
                 padding-bottom:18px; border-bottom:1px solid #333 }
  #results .arrow { display:none }
  [data-path]:not(.query) { cursor:pointer }
  [data-path]:not(.query):hover .cell { outline:2px solid #888 }
</style>
<div id=bar>
  <label id=drop>Drop any photo here, or paste, or click to pick one
    <input type=file accept="image/*,.heic,.heif" hidden></label>
  <button id=random>random from index</button>
  <label>route <select id=route>
    <option value=auto>auto</option><option value=pose>pose</option>
    <option value=image>image</option><option value=both>both</option></select></label>
  <label>results <select id=k><option>4</option><option selected>12</option><option>24</option><option>48</option></select></label>
  %(toggles)s
</div>
<p id=msg>%(info)s</p>
<div id=results></div>
<script>
const $ = s => document.querySelector(s), msg = $('#msg'), results = $('#results');
let last = null;  // repeat the last search when route/k change

async function run(req) {
  last = req;
  msg.className = ''; msg.textContent = 'searching…';
  const q = `route=${$('#route').value}&k=${$('#k').value}`;
  try {
    const r = await fetch(req.url + (req.url.includes('?') ? '&' : '?') + q,
                          {method: req.method || 'GET', body: req.body});
    const data = await r.json();
    if (!r.ok) throw new Error(data.error);
    results.innerHTML = data.html;
    msg.textContent = data.info;
    if ($('#fullframe').checked)
      for (const s of results.querySelectorAll('svg.cell')) s.setAttribute('viewBox', s.dataset.full);
    scrollTo(0, 0);
  } catch (e) { msg.className = 'err'; msg.textContent = e.message; }
}

const searchFile = f => f && (history.replaceState(null, '', location.pathname), run({url: '/search', method: 'POST', body: f}));
$('#drop input').onchange = e => searchFile(e.target.files[0]);
$('#random').onclick = async () => {
  const r = await fetch('/random'), data = await r.json();
  if (!r.ok) { msg.className = 'err'; msg.textContent = data.error; return; }
  location.hash = 'path=' + encodeURIComponent(data.path);
};
$('#route').onchange = $('#k').onchange = () => last && run(last);
// searches of indexed images live in the URL hash, so back/forward and
// bookmarks work; clicking a result just sets the hash
const fromHash = () => {
  const path = new URLSearchParams(location.hash.slice(1)).get('path');
  if (path) run({url: '/similar?path=' + encodeURIComponent(path)});
};
addEventListener('hashchange', fromHash);
fromHash();
results.onclick = e => {
  const cell = e.target.closest('[data-path]:not(.query)');
  if (cell) location.hash = 'path=' + encodeURIComponent(cell.dataset.path);
};
document.onpaste = e => searchFile(e.clipboardData.files[0]);

let depth = 0;
document.ondragenter = e => { e.preventDefault(); depth++; document.body.classList.add('dragging'); };
document.ondragleave = () => { if (--depth <= 0) { depth = 0; document.body.classList.remove('dragging'); } };
document.ondragover = e => e.preventDefault();
document.ondrop = e => {
  e.preventDefault(); depth = 0; document.body.classList.remove('dragging');
  // not filtered by type: browsers often report HEIC as "", so the server decides
  const f = e.dataTransfer.files[0];
  if (f) return searchFile(f);
  // an image dragged from another tab often arrives as just a URL
  const url = e.dataTransfer.getData('text/uri-list').split('\\n')[0].trim();
  if (url) return run({url: '/search?url=' + encodeURIComponent(url), method: 'POST'});
  msg.className = 'err'; msg.textContent = "that drop didn't contain a file or an image link";
};
</script>
"""


class App:
  def __init__(self, store, status, estimator, embedder, metric, min_bones, min_conf):
    self.store, self.status = store, status
    self.estimator, self.embedder = estimator, embedder
    self.opts = dict(metric=metric, min_bones=min_bones, min_conf=min_conf)
    # qdrant's embedded mode and sqlite aren't built for concurrent use
    self.lock = threading.Lock()
    self.uploads = OrderedDict()

  def info(self):
    with self.lock:
      return (f"{self.store.count('images')} images, {self.store.count()} poses indexed · "
              f"trust: ≥{self.opts['min_bones']} bones, conf ≥{self.opts['min_conf']} · "
              f"device {self.estimator.device}")

  def search_upload(self, data, mode, k):
    try:
      image, scale = load_image(io.BytesIO(data))
    except Exception:
      raise ValueError("can't read that as an image")
    uid = uuid.uuid4().hex
    self.uploads[uid] = (_display_copy(image), "image/jpeg")
    while len(self.uploads) > KEEP_UPLOADS:
      self.uploads.popitem(last=False)

    label = f"upload:{uid}"
    with self.lock:
      size = (image.shape[1] / scale, image.shape[0] / scale)
      points = poses_to_points(label, self.estimator.extract(image, scale), self.estimator, size)
      _, image_vec, image_payload = image_point(label, image, scale, self.embedder, len(points))
      rows = retrieve.query_rows(self.store, [(v, pl) for _, _, v, pl in points], image_vec,
                                 image_payload, mode=mode, k=k, **self.opts)
    return rows, f"{len(points)} {'person' if len(points) == 1 else 'people'} found"

  def search_indexed(self, path, mode, k):
    with self.lock:
      image = self.store.get_image(path)
      if image is None:
        raise ValueError(f"not in the index: {path}")
      poses = [(p.vector, p.payload) for p in self.store.get(path)]
      rows = retrieve.query_rows(self.store, poses, image.vector, image.payload,
                                 exclude_image=path, mode=mode, k=k, **self.opts)
    return rows, path

  def random_path(self):
    with self.lock:
      found = self.status.random_indexed(1)
    if not found:
      raise ValueError("the index is empty; run `pose-search index` first")
    return found[0]

  def indexed(self, path):
    with self.lock:
      return self.status.has(path)


def _display_copy(image):
  """JPEG of the (already rotated) upload for the browser to show. Browsers
  can't display HEIC, and this also settles EXIF rotation."""
  out = io.BytesIO()
  Image.fromarray(image[:, :, ::-1]).save(out, "JPEG", quality=88)
  return out.getvalue()


def src_for(path):
  if path.startswith("upload:"):
    return "/upload/" + path.split(":", 1)[1]
  return "/img?path=" + quote(path)


class Handler(BaseHTTPRequestHandler):
  app = None

  def log_message(self, fmt, *args):
    pass  # keep the terminal quiet

  def _send(self, code, body, ctype):
    self.send_response(code)
    self.send_header("Content-Type", ctype)
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _json(self, code, obj):
    self._send(code, json.dumps(obj).encode(), "application/json")

  def _results(self, fn, *args):
    q = self.query
    mode = q.get("route", ["auto"])[0]
    k = min(int(q.get("k", ["12"])[0]), 100)
    if mode not in ("auto", "pose", "image", "both"):
      return self._json(400, {"error": f"unknown route {mode!r}"})
    try:
      rows, what = fn(*args, mode, k)
    except ValueError as ex:
      return self._json(400, {"error": str(ex)})
    except Exception as ex:
      print(f"error: {type(ex).__name__}: {ex}", file=sys.stderr)
      return self._json(500, {"error": f"{type(ex).__name__}: {ex}"})
    routes = ", ".join(r for r, *_ in rows)
    self._json(200, {"html": rows_html(rows, src_for), "info": f"{what} · route: {routes}"})

  def do_GET(self):
    url = urlparse(self.path)
    self.query = parse_qs(url.query)
    app = self.app

    if url.path == "/":
      page = PAGE % {"style": STYLE, "toggles": TOGGLES, "info": html.escape(app.info())}
      return self._send(200, page.encode(), "text/html; charset=utf-8")

    if url.path == "/img":
      path = self.query.get("path", [""])[0]
      if not app.indexed(path):
        return self._send(404, b"not indexed", "text/plain")
      try:
        with open(path, "rb") as fp:
          data = fp.read()
      except OSError:
        return self._send(404, b"missing", "text/plain")
      return self._send(200, data, mimetypes.guess_type(path)[0] or "application/octet-stream")

    if url.path.startswith("/upload/"):
      found = app.uploads.get(url.path.rsplit("/", 1)[1])
      if found is None:
        return self._send(404, b"expired", "text/plain")
      return self._send(200, *found)

    if url.path == "/similar":
      return self._results(app.search_indexed, self.query.get("path", [""])[0])

    if url.path == "/random":
      try:
        return self._json(200, {"path": app.random_path()})
      except ValueError as ex:
        return self._json(400, {"error": str(ex)})

    self._send(404, b"not found", "text/plain")

  def do_POST(self):
    url = urlparse(self.path)
    self.query = parse_qs(url.query)
    if url.path != "/search":
      return self._send(404, b"not found", "text/plain")

    if "url" in self.query:
      try:
        req = urllib.request.Request(self.query["url"][0], headers={"User-Agent": "pose-search"})
        with urllib.request.urlopen(req, timeout=20) as r:
          data = r.read(MAX_UPLOAD + 1)
      except Exception as ex:
        return self._json(400, {"error": f"couldn't fetch that URL ({ex}); save the image and drop the file"})
    else:
      n = int(self.headers.get("Content-Length") or 0)
      if not n:
        return self._json(400, {"error": "empty upload"})
      data = self.rfile.read(min(n, MAX_UPLOAD + 1))
    if len(data) > MAX_UPLOAD:
      return self._json(400, {"error": "image too large"})
    self._results(self.app.search_upload, data)


def serve(app, host, port):
  Handler.app = app
  server = ThreadingHTTPServer((host, port), Handler)
  print(f"pose-search: open http://{host}:{port}/  (ctrl-c to stop)", file=sys.stderr)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
