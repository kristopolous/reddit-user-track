Pose search: find images in the archive with a similar human pose. See `../pose-search.md` for the spec.

RTMPose (via rtmlib/onnxruntime) → bone-direction vectors → Qdrant. There's no torch and no mmcv.

## Install

Pick one onnxruntime:

    pip install -e './pose[cuda]'   # nvidia
    pip install -e './pose[cpu]'    # anything else

The device is detected automatically (cuda, then rocm, then coreml, falling back to cpu); `--device` overrides it. The models (~140MB) download to `~/.cache/rtmlib` on first run.

## Use

    pose-search index data/ --limit 2000 --shuffle   # try a random sample first
    pose-search index data/                          # the rest; resumable, ctrl-c is safe
    pose-search smoke                                # -> pose-smoke.html
    pose-search search some/image.jpg                # -> results/query.jpg, results/results.jpg
    pose-search show some/image.jpg                  # skeleton overlay + the pose vector
    pose-search stats

The index lives in `./pose-index`, or wherever `--index-dir` / `$POSE_INDEX` points. Qdrant is embedded by default. For the full corpus, run a server and pass `--qdrant-url http://localhost:6333`, because embedded mode loads every point into RAM when it starts.

`smoke` is the "does it work at all" check. It picks random indexed images and shows each one with its 4 nearest poses (`-n`, `-k`). Each thumbnail is cropped to the matched person, with the skeleton drawn on top. It reuses the stored poses, so it doesn't need a GPU. The image links are relative to the HTML file, so keep it next to the archive or serve both from the same place.

## How similarity works

The vector holds 16 bones, each stored as a unit direction (x, y). A bone that isn't confidently visible is stored as (0, 0). The store uses a dot product, so the score is the sum of cosines over the bones both poses share. Missing bones add nothing instead of acting as a penalty. That lets a head-and-shoulders crop match on what it has.

`--metric` re-ranks the top 200 candidates:

- `bones` (default) is the dot product described above.
- `bones_mean` is the average agreement over shared bones. It ignores how many bones overlap.
- `joints` is the distance between normalized joint positions, using only joints visible in both poses.

To add another metric, add a function to `METRICS` in `retrieve.py`.
