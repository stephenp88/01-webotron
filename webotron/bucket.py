# -*- coding: utf-8 -*-

"""Classes for s3 Buckets."""

import mimetypes
from pathlib import Path
from botocore.exceptions import ClientError


class BucketManager:
    """Manage an S3 Bucket."""

    def __init__(self, session):
        """Create a BucketManager object."""
        self.session = session
        self.s3 = self.session.resource('s3')

    def all_buckets(self):
        """Get and iterator for all buckets."""
        return self.s3.buckets.all()

    def all_objects(self, bucket):
        """Get an iterator for all objects in bucket."""
        return self.s3.Bucket(bucket).objects.all()

    def init_bucket(self, bucket):
        """Create new bucket, or return existing bucket."""
        s3_bucket = None
        try:
            s3_bucket = self.s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={'LocationConstraint': self.session.region_name}
                    )
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = self.s3.Bucket(bucket)
                print("S3 bucket already exists. Proceeding with script")
            else:
                raise e

        return s3_bucket

    def set_policy(self, bucket):
        """Set bucket policy for website."""
        policy = """
        {
            "Version": "2012-10-17",
            "Statement": [
                    {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": [
                                    "s3:GetObject"
                            ],
                            "Resource": [
                                    "arn:aws:s3:::%s/*"
                            ]
                    }
            ]
        }
        """ % bucket.name
        policy = policy.strip()
        pol = bucket.Policy()
        print(policy)
        pol.put(Policy=policy)

    def configure_website(self, bucket):
        """Configure s3 website properties."""
        bucket.Website().put(WebsiteConfiguration={
            'ErrorDocument': {
                'Key': 'error.html'
            },
            'IndexDocument': {
                'Suffix': 'index.html'
            }
        })

    def upload_file(self, bucket, path, key):
        """Upload a file to S3."""
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'
        bucket.upload_file(
            path,
            key,
            ExtraArgs={
                'ContentType': content_type
            })

    def sync(self, pathname, bucket_name):
        bucket = self.s3.Bucket(bucket_name)
        root = Path(pathname).expanduser().resolve()

        def handle_directory(target):
            """Sync directory tree to S3."""
            for p in target.iterdir():
                if p.is_dir():
                    handle_directory(p)
                if p.is_file():
                    self.upload_file(bucket, str(p), str(p.relative_to(root)))

        handle_directory(root)
