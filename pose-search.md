# Pose Search MVP

## 1. Overview

Build a local pose-search system for a large image archive of approximately 400,000 images.

The core use case is:

1. Select an existing image from the archive.
2. Extract the visible human pose.
3. Search the archive for other images containing a similar pose.
4. Display the nearest matches as a contact sheet / thumbnail grid.

The first goal is **not** to build a sophisticated AI image search system. The first goal is to establish that explicit human-pose representations can produce useful nearest-neighbor search results on this particular, noisy image corpus.

The archive contains substantially messier imagery than professional fashion photography. Images may contain:

* Full-body people
* Upper-body crops
* Head/shoulder crops
* Individual arms or legs
* Partial occlusion
* Poor framing
* Selfies
* Multiple people
* Unusual camera angles
* People near the edge of the frame
* Low-quality or ambiguous pose detections

The system must therefore tolerate incomplete pose observations.

---

# 2. MVP Success Criterion

The primary success criterion is qualitative:

> Given a random image from the corpus, "Find Similar Poses" should return a contact sheet in which the majority of high-ranked results have visibly similar body poses.

Do not optimize for benchmark scores initially.

Do not build a sophisticated learned pose embedding unless the simple explicit-keypoint approach demonstrably fails.

The first milestone should be a working experiment on a representative subset of the corpus.

---

# 3. Initial Architecture

```text
                    Image Archive
                         |
                         v
                Person Detection
                         |
                         v
                  Pose Estimation
                         |
                         v
             Keypoints + Confidence
                         |
                         v
               Pose Normalization
                         |
                         v
                 Pose Vector
                         |
                         v
                      Qdrant
                         |
              +----------+----------+
              |                     |
              v                     v
       Existing Image         Query Image
              |                     |
              +----------+----------+
                         |
                         v
                  Pose Extraction
                         |
                         v
                  Vector Search
                         |
                         v
                  Nearest Images
                         |
                         v
                  Contact Sheet
```

Keep the architecture modular so pose-estimation models can be swapped later.

---

# 4. Pose Estimation

Start with an existing, production-quality human pose estimator rather than implementing pose estimation.

Candidate starting point:

* RTMPose

Other candidates may be evaluated later:

* ViTPose / ViTPose++
* Sapiens
* Other current high-quality human pose estimators

The implementation should isolate the pose-estimation backend behind a simple interface so another estimator can be substituted without changing the indexing/search layer.

The estimator should return, at minimum:

```python
PersonPose(
    keypoints,
    confidence,
    bounding_box,
    person_confidence,
)
```

where `keypoints` contains normalized or raw `(x, y)` coordinates for each detected joint.

Support multiple detected people per image.

Do not assume there is exactly one person.

---

# 5. Pose Representation

For the first implementation, use explicit pose geometry rather than a learned image embedding.

A pose consists of:

* joint coordinates
* joint confidence
* visibility / availability
* person bounding box

Normalize the pose so that irrelevant image properties do not dominate similarity.

At minimum:

1. Translate the skeleton relative to a body reference point.
2. Scale according to body size.
3. Preserve relative joint geometry.
4. Do not encode absolute image position.

For example, hip-center or torso-center can be used as the origin when those joints are available.

Use a sensible fallback when those joints are unavailable.

The representation should preserve enough information to distinguish:

* standing vs crouching
* arms raised vs lowered
* left/right limb configuration
* torso rotation / leaning
* leg configuration
* relative limb positions

---

# 6. Missing / Low-Confidence Joints

This is critical.

Do **not** treat missing joints as ordinary zero-valued coordinates.

Each joint should have an associated confidence/visibility value.

Similarity must be able to compare partial observations.

For example:

```text
Image A:
head
shoulders
left arm
right arm
```

can still be compared against:

```text
Image B:
head
shoulders
left arm
right arm
hips
legs
```

The comparison should primarily use the joints available in both observations.

A candidate with missing information should not automatically receive a huge distance penalty merely because the query contains joints that are not visible in the candidate.

---

# 7. Similarity

Implement an explicit pose-distance function first.

Start with:

* cosine similarity on the normalized pose vector

Also make it easy to experiment with:

* Euclidean distance
* confidence-weighted distance
* joint-wise distance
* angle-based distance

Do not assume cosine similarity is optimal.

The system should retain enough metadata to inspect why two poses were considered similar.

---

# 8. Multiple People

If an image contains multiple people:

* Extract a pose for each person.
* Store each person pose independently.
* Associate each pose with the source image and bounding box.

Conceptually:

```text
image_123
    person_0 -> pose vector
    person_1 -> pose vector
    person_2 -> pose vector
```

A search result should identify which person in the image generated the match.

The UI can initially simply display the original image, optionally with the matched person's bounding box highlighted.

---

# 9. Qdrant

Use Qdrant as the initial vector database.

Store one vector per detected person/pose rather than one vector per image.

Payload should contain enough information to locate and display the source:

```json
{
  "image_id": "...",
  "image_path": "...",
  "person_id": 0,
  "bbox": [x1, y1, x2, y2],
  "pose_type": "...",
  "confidence": 0.94
}
```

Do not put image binaries into Qdrant.

The image archive remains the source of truth.

Use a collection configuration appropriate for the chosen vector dimensionality and similarity metric.

---

# 10. Initial Indexing Strategy

Do not immediately process all 400,000 images.

First support:

```bash
pose-index /path/to/images --limit 10000
```

Then:

```bash
pose-index /path/to/images
```

for the full corpus.

Indexing must be resumable.

If the process stops after 237,000 images, restarting should continue rather than recomputing everything.

Store an indexing status per image.

At minimum:

```text
pending
processed
failed
no_person
```

Failures should be recorded rather than terminating the entire indexing job.

---

# 11. Image Discovery

The archive may contain many different image formats.

Support common formats:

* JPEG
* PNG
* WebP

Ignore unsupported files.

The indexing system should recursively walk the configured archive directory.

Do not copy or reorganize the original archive.

---

# 12. Prototype CLI

Implement a minimal CLI.

### Index

```bash
pose-search index /path/to/archive
```

Optional:

```bash
pose-search index /path/to/archive --limit 10000
pose-search index /path/to/archive --workers 8
pose-search index /path/to/archive --resume
```

### Search

```bash
pose-search search /path/to/image.jpg
```

Expected behavior:

1. Run pose detection.
2. Extract pose(s).
3. Search Qdrant.
4. Return the nearest results.
5. Generate a contact sheet.

Example:

```bash
pose-search search /path/to/query.jpg --limit 50
```

---

# 13. Contact Sheet

The initial output should be deliberately simple.

Given a query image:

```text
query.jpg
```

produce something like:

```text
results/
    query.jpg
    results.jpg
```

`results.jpg` should contain a thumbnail grid of the nearest matches.

Each thumbnail should display:

* similarity score
* source image ID/path
* optionally the detected-person bounding box

This contact sheet is the primary evaluation mechanism.

Do not build a web application before the retrieval quality has been demonstrated.

---

# 14. Evaluation Dataset

Create a small manually inspectable evaluation set.

Randomly select approximately 100 images from the real corpus.

For each:

1. Run pose search.
2. Save the top 20 results.
3. Generate contact sheets.

Review results manually.

Specifically include difficult examples:

* full-body
* upper-body
* head-only
* arm-only
* partially occluded
* unusual framing
* multiple people
* sitting
* crouching
* lying down
* extreme perspective
* low-confidence detections

The purpose is to determine whether explicit pose retrieval works on the actual corpus.

---

# 15. Do Not Build Yet

Do NOT initially implement:

* text-to-pose search
* image generation
* Qwen Image
* ControlNet generation
* semantic image search
* sophisticated learned pose embeddings
* elaborate web UI
* automatic natural-language descriptions
* facial recognition
* identity matching
* clothing classification
* aesthetic ranking

These may become useful later but are not part of the MVP.

The first question is simply:

> Does explicit pose geometry produce useful nearest neighbors?

---

# 16. Possible Second Stage: Visibility Classification

If the initial experiment shows that full-body pose representation performs poorly on partial images, introduce a lightweight classification stage.

The classifier should determine what anatomical information is meaningfully available.

Possible categories:

```text
HEAD
HEAD_SHOULDERS
UPPER_BODY
TORSO
ARM
HAND
LEG
FULL_BODY
MULTIPLE_PEOPLE
NO_USABLE_POSE
```

Classification should not necessarily be mutually exclusive.

For example:

```text
image_123:
    UPPER_BODY = 0.98
    ARM = 0.94
    HAND = 0.72
```

The classifier can then route the image to an appropriate pose representation.

Example:

```text
upper body -> upper-body keypoints
arm        -> arm keypoints
hand       -> hand landmarks
full body  -> full-body pose
```

Do not implement this until testing demonstrates that it is necessary.

---

# 17. Possible Specialized Representations

If required, maintain separate vector representations for different anatomical scopes:

```text
full_body_vector
upper_body_vector
arm_vector
hand_vector
```

This permits partial-image retrieval.

For example, an image containing only an arm should not be forced into a full-body representation.

Qdrant collections or payload filtering can be used to keep incompatible representations from being compared.

---

# 18. Performance

The archive contains approximately 400,000 images, so preprocessing speed matters.

The system should:

* batch inference where practical
* use GPU acceleration when available
* avoid loading the entire archive into RAM
* persist indexing progress
* avoid recomputing poses unnecessarily
* cache pose-estimation results locally

The implementation should make it possible to run indexing overnight on a local GPU.

Do not prematurely optimize the vector search layer. 400,000 vectors is a modest retrieval problem.

---

# 19. Reproducibility

Store the pose-estimator name/version and representation version with indexed records.

For example:

```text
estimator = rtmpose
estimator_version = ...
representation_version = 1
```

Changing the pose representation should make it possible to rebuild or migrate the index without ambiguity.

---

# 20. Architecture Requirements

Keep these components independently replaceable:

```text
ImageScanner
PersonDetector
PoseEstimator
PoseNormalizer
PoseVectorizer
VectorStore
Retriever
ContactSheetGenerator
```

The important interface is approximately:

```python
poses = pose_estimator.extract(image)

vectors = [
    vectorizer.encode(pose)
    for pose in poses
]

results = vector_store.search(vector)
```

Do not tightly couple Qdrant to the pose-estimation implementation.

---

# 21. Development Order

Implement in this order:

### Phase 1

Single image:

```text
image -> pose estimator -> visualize skeleton
```

Verify the estimator works on representative real images.

### Phase 2

Single image:

```text
image -> pose -> normalized vector
```

Visualize/print the representation.

### Phase 3

Small corpus:

```text
1,000 images -> vectors -> Qdrant
```

### Phase 4

Query:

```text
query image -> vector -> nearest neighbors
```

Generate contact sheet.

### Phase 5

Test on 10,000 real images.

### Phase 6

Evaluate difficult/partial images.

### Phase 7

Only if necessary, add anatomical visibility classification and specialized pose representations.

### Phase 8

Scale to the full ~400,000-image corpus.

---

# 22. Guiding Principle

The system should initially be **boring**.

The first useful result should require only:

```text
pose estimation
+
normalization
+
vector search
+
contact sheet
```

If this produces good results, build on it.

If it produces bad results, inspect the actual nearest-neighbor failures before adding more AI.

The project is successful when selecting an arbitrary image and asking:

**"Find similar poses."**

produces a set of real images that a human would recognize as having similar poses.

