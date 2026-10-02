"""Vector store (Qdrant) and per-image indexing status (sqlite).

Both live under one index directory. Qdrant runs embedded (a directory on
disk) unless a server URL is given; for the full ~400k corpus a server is
the better choice since embedded mode loads everything into RAM at startup.
"""
import os
import sqlite3
import time
import uuid

from qdrant_client import QdrantClient, models

from . import vectorize

COLLECTION = "poses"
PROCESSED, FAILED, NO_PERSON = "processed", "failed", "no_person"


def point_id(image_path, person_id):
  # deterministic, so re-indexing an image overwrites rather than duplicates
  return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{image_path}#{person_id}"))


class VectorStore:
  def __init__(self, index_dir, url=None):
    os.makedirs(index_dir, exist_ok=True)
    if url:
      self.client = QdrantClient(url=url)
    else:
      self.client = QdrantClient(path=os.path.join(index_dir, "qdrant"))

    if not self.client.collection_exists(COLLECTION):
      self.client.create_collection(
        COLLECTION,
        vectors_config=models.VectorParams(size=vectorize.DIM, distance=models.Distance.DOT),
      )
      if url:
        # embedded mode has no payload indexes (and warns if asked)
        self.client.create_payload_index(COLLECTION, "image_path", models.PayloadSchemaType.KEYWORD)

  def upsert(self, points):
    """points: list of (image_path, person_id, vector, payload)"""
    if points:
      self.client.upsert(COLLECTION, [
        models.PointStruct(id=point_id(p, i), vector=v.tolist(), payload=pl)
        for p, i, v, pl in points
      ])

  def delete_image(self, image_path):
    self.client.delete(COLLECTION, models.Filter(must=[
      models.FieldCondition(key="image_path", match=models.MatchValue(value=image_path))
    ]))

  def get(self, image_path):
    """All stored poses for an image, with vectors."""
    points, _ = self.client.scroll(
      COLLECTION,
      scroll_filter=models.Filter(must=[
        models.FieldCondition(key="image_path", match=models.MatchValue(value=image_path))
      ]),
      with_vectors=True, limit=100,
    )
    return sorted(points, key=lambda p: p.payload["person_id"])

  def search(self, vector, limit=50, exclude_image=None, with_vectors=False):
    flt = None
    if exclude_image:
      flt = models.Filter(must_not=[
        models.FieldCondition(key="image_path", match=models.MatchValue(value=exclude_image))
      ])
    return self.client.query_points(
      COLLECTION, query=list(map(float, vector)), query_filter=flt, limit=limit,
      with_vectors=with_vectors,
    ).points

  def count(self):
    return self.client.count(COLLECTION).count


class Status:
  def __init__(self, index_dir):
    self.db = sqlite3.connect(os.path.join(index_dir, "status.db"))
    self.db.execute("""
      create table if not exists images (
        path text primary key,
        status text not null,
        n_persons integer,
        error text,
        estimator text,
        representation_version integer,
        updated real
      )""")
    self.db.commit()

  def done(self, retry_failed=False):
    skip = (PROCESSED, NO_PERSON) if retry_failed else (PROCESSED, NO_PERSON, FAILED)
    q = f"select path from images where status in ({','.join('?' * len(skip))})"
    return {row[0] for row in self.db.execute(q, skip)}

  def set(self, path, status, n_persons=0, error=None, estimator=None, representation_version=None):
    self.db.execute(
      "insert or replace into images values (?, ?, ?, ?, ?, ?, ?)",
      (path, status, n_persons, error, estimator, representation_version, time.time()),
    )

  def commit(self):
    self.db.commit()

  def counts(self):
    return dict(self.db.execute("select status, count(*) from images group by status"))

  def random_processed(self, n):
    return [row[0] for row in self.db.execute(
      "select path from images where status = ? order by random() limit ?", (PROCESSED, n)
    )]
