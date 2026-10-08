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

POSES, IMAGES = "poses", "images"
PROCESSED, FAILED, NO_PERSON = "processed", "failed", "no_person"


def point_id(image_path, person_id=None):
  # deterministic, so re-indexing an image overwrites rather than duplicates
  key = image_path if person_id is None else f"{image_path}#{person_id}"
  return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _is(key, value):
  return models.FieldCondition(key=key, match=models.MatchValue(value=value))


class VectorStore:
  """Two collections: "poses" has one point per detected person (bone
  vector, dot product); "images" has one per image (DINOv2, cosine)."""

  def __init__(self, index_dir, url=None, image_dim=None):
    os.makedirs(index_dir, exist_ok=True)
    if url:
      self.client = QdrantClient(url=url)
    else:
      self.client = QdrantClient(path=os.path.join(index_dir, "qdrant"))
    self._ensure(POSES, vectorize.DIM, models.Distance.DOT, url)
    if image_dim:
      self._ensure(IMAGES, image_dim, models.Distance.COSINE, url)

  def _ensure(self, name, dim, distance, url):
    if self.client.collection_exists(name):
      have = self.client.get_collection(name).config.params.vectors.size
      if have != dim:
        raise SystemExit(f"collection {name!r} has {have}-dim vectors, expected {dim}; "
                         f"use a fresh --index-dir or the embedding model it was built with")
      return
    self.client.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=distance))
    if url:
      # embedded mode has no payload indexes (and warns if asked)
      self.client.create_payload_index(name, "image_path", models.PayloadSchemaType.KEYWORD)

  def upsert(self, poses, images=()):
    """poses: [(image_path, person_id, vector, payload)]; images: [(image_path, vector, payload)]"""
    if poses:
      self.client.upsert(POSES, [
        models.PointStruct(id=point_id(p, i), vector=v.tolist(), payload=pl) for p, i, v, pl in poses
      ])
    if images:
      self.client.upsert(IMAGES, [
        models.PointStruct(id=point_id(p), vector=v.tolist(), payload=pl) for p, v, pl in images
      ])

  def delete_poses(self, image_path, person_ids):
    if person_ids:
      self.client.delete(POSES, [point_id(image_path, i) for i in person_ids])

  def get(self, image_path):
    """All stored poses for an image, with vectors, most confident first."""
    points, _ = self.client.scroll(
      POSES, scroll_filter=models.Filter(must=[_is("image_path", image_path)]),
      with_vectors=True, limit=100,
    )
    return sorted(points, key=lambda p: p.payload["person_id"])

  def get_image(self, image_path):
    found = self.client.retrieve(IMAGES, [point_id(image_path)], with_vectors=True)
    return found[0] if found else None

  def search(self, vector, limit=50, exclude_image=None, with_vectors=False, min_bones=0, min_conf=0.0):
    must = []
    if min_bones:
      must.append(models.FieldCondition(key="n_bones", range=models.Range(gte=min_bones)))
    if min_conf:
      must.append(models.FieldCondition(key="visible_conf", range=models.Range(gte=min_conf)))
    return self._query(POSES, vector, limit, exclude_image, must, with_vectors)

  def search_images(self, vector, limit=50, exclude_image=None):
    return self._query(IMAGES, vector, limit, exclude_image, [], False)

  def _query(self, collection, vector, limit, exclude_image, must, with_vectors):
    must_not = [_is("image_path", exclude_image)] if exclude_image else []
    flt = models.Filter(must=must, must_not=must_not) if must or must_not else None
    return self.client.query_points(
      collection, query=list(map(float, vector)), query_filter=flt, limit=limit,
      with_vectors=with_vectors,
    ).points

  def count(self, collection=POSES):
    if not self.client.collection_exists(collection):
      return 0
    return self.client.count(collection).count


class Status:
  def __init__(self, index_dir):
    # the web UI uses it from request threads (always under its own lock)
    self.db = sqlite3.connect(os.path.join(index_dir, "status.db"), check_same_thread=False)
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

  def load(self):
    """path -> (status, representation_version, n_persons)"""
    return {row[0]: row[1:] for row in self.db.execute(
      "select path, status, representation_version, n_persons from images")}

  def set(self, path, status, n_persons=0, error=None, estimator=None, representation_version=None):
    self.db.execute(
      "insert or replace into images values (?, ?, ?, ?, ?, ?, ?)",
      (path, status, n_persons, error, estimator, representation_version, time.time()),
    )

  def commit(self):
    self.db.commit()

  def counts(self):
    return dict(self.db.execute("select status, count(*) from images group by status"))

  def has(self, path):
    return self.db.execute(
      "select 1 from images where path = ? and status in (?, ?)", (path, PROCESSED, NO_PERSON)
    ).fetchone() is not None

  def random_indexed(self, n, only=None):
    return [row[0] for row in self.db.execute(
      "select path from images where status in (?, ?) and instr(path, ?) > 0 order by random() limit ?",
      (PROCESSED, NO_PERSON, only or "", n)
    )]
