"""Landing layer: write normalized postings to the data lake.

  * MinIO (S3-compatible)  -> bronze/<source>/<job_id>.json   (raw, immutable)
  * MongoDB                -> raw_postings collection           (schema-on-read)

Both are written so the project demonstrates a distributed object store AND a
NoSQL document store, each used where it fits.
"""
from __future__ import annotations

import json
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from pymongo import MongoClient

from . import settings
from .base import Posting

log = logging.getLogger("lake")


class LakeWriter:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

        self.mongo = MongoClient(settings.MONGO_URI)
        self.coll = self.mongo[settings.MONGO_DB][settings.MONGO_COLLECTION]
        # idempotent upserts keyed by (source, job_id)
        self.coll.create_index([("source", 1), ("job_id", 1)], unique=True)

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            log.info("Creating bucket %s", self.bucket)
            self.s3.create_bucket(Bucket=self.bucket)

    def write(self, posting: Posting) -> None:
        doc = posting.to_dict()
        body = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")

        # bronze object (immutable raw landing)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=f"bronze/{posting.key}.json",
            Body=body,
            ContentType="application/json",
        )
        # mongo upsert (schema-on-read view)
        self.coll.update_one(
            {"source": posting.source, "job_id": posting.job_id},
            {"$set": doc},
            upsert=True,
        )

    def write_many(self, postings) -> int:
        n = 0
        for p in postings:
            self.write(p)
            n += 1
        log.info("Wrote %d postings to lake (bronze + mongo)", n)
        return n

    def close(self):
        self.mongo.close()
