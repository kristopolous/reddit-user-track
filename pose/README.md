Pose search: find images in the archive with a similar human pose. See `../pose-search.md` for the spec.

Each image gets two kinds of vector:

- **Pose:** RTMPose (via rtmlib) finds people and their joints, which become bone-direction vectors.
- **Image:** a DINOv2 embedding of the whole picture.

A query searches by pose when its skeleton is trustworthy. Otherwise it searches by image: midsections, extreme close-ups, odd crops. Everything runs on onnxruntime, with no torch and no mmcv.

## Install

Nothing to do. Run `./pose-search` from the repo root. The first run sets up `pose/.venv`, using CUDA if `nvidia-smi` exists and CPU otherwise; set `POSE_EXTRA=cpu|cuda` to force one. To reinstall, delete `pose/.venv`.

The device is detected automatically (cuda, then rocm, then coreml, falling back to cpu); `--device` overrides it. The models download on first run: about 140MB into `~/.cache/rtmlib`, plus about 90MB of DINOv2 into `~/.cache/huggingface`.

## Use

    ./pose-search index data/ --limit 2000 --shuffle   # try a random sample first
    ./pose-search index data/                          # the rest; resumable, ctrl-c is safe
    ./pose-search serve                                # web page at http://127.0.0.1:8765/
    ./pose-search smoke                                # -> pose-smoke.html
    ./pose-search smoke --route both --only somefolder/  # pose vs image search, side by side
    ./pose-search search some/image.jpg                # -> results/query.jpg, results/results.jpg
    ./pose-search show some/image.jpg                  # skeleton overlay + the pose vector
    ./pose-search stats

The index lives in `./pose-index`, or wherever `--index-dir` / `$POSE_INDEX` points. Qdrant is embedded by default. For the full corpus, run a server and pass `--qdrant-url http://localhost:6333`, because embedded mode loads every point into RAM when it starts.

`smoke` is the "does it work at all" check. It picks random indexed images and shows each one with its 4 nearest matches (`-n`, `-k`). Each row says which route the query took. Pose results are cropped to the matched person, with the skeleton drawn on top. Image results show the whole frame. It reuses the stored vectors, so it doesn't need a GPU. The image links are relative to the HTML file, so keep it next to the archive or serve both from the same place.

`serve` is the interactive version. Drop any photo anywhere on the page to search by it. It doesn't need to be in the index, and phone photos (HEIC) work. You can also paste one, pick a file, or drag one straight from another browser tab. To search from your phone, start it with `--host 0.0.0.0` and open the page there; "pick one" offers the camera. Click any result to search by that result, and use back/forward to retrace. The route menu switches between auto, pose, image, and both. Models load once at startup, so searches after the first are quick. The server only serves images that are in the index. It listens on localhost unless you pass `--host 0.0.0.0`.

Indexes built by an older version are redone automatically the next time you run `index`.

## When the pose is trusted

The person detector misses most close-ups. When it finds nobody, the pose model runs on the whole frame instead, which often still finds shoulders, hips and arms in a torso crop. On an empty picture, though, it invents joints. So every pose gets two numbers:

- `n_bones`: how many of the 16 bones are visible.
- `visible_conf`: the mean score of the joints it claims to see. This one doesn't penalize a crop for what's out of frame.

A pose is trusted when `n_bones >= --min-bones` (5) and `visible_conf >= --min-conf` (0.6). A trusted query searches by pose, and only against other trusted poses. Anything else searches by image. `show` prints both numbers and which route an image would take.

Those defaults are guesses. On test crops, some untrusted torsos at 0.5 to 0.6 still found the right pose. To tune them, run `smoke --route both` on real images and adjust `--min-conf` / `--min-bones`. Changing them doesn't require re-indexing.

## How pose similarity works

The pose vector holds 16 bones, each stored as a unit direction (x, y). A bone that isn't confidently visible is stored as (0, 0). The store uses a dot product, so the score is the sum of cosines over the bones both poses share. Missing bones add nothing instead of acting as a penalty. That lets a head-and-shoulders crop match on what it has.

`--metric` re-ranks the top 200 candidates:

- `bones` (default) is the dot product described above.
- `bones_mean` is the average agreement over shared bones. It ignores how many bones overlap.
- `joints` is the distance between normalized joint positions, using only joints visible in both poses.

To add another metric, add a function to `METRICS` in `retrieve.py`.

Image search is plain cosine similarity on DINOv2-small (`--embed-model base` is bigger, but needs its own index). It matches on orientation and framing, and also on clothing and background, so expect reposts and near-duplicates to rank first.
