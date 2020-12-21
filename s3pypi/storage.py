import logging
from typing import Optional

import boto3
import botocore

from s3pypi.index import Index, Package

log = logging.getLogger()


class S3Storage:
    def __init__(
        self,
        bucket: str,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        prefix: Optional[str] = None,
        acl: Optional[str] = None,
        unsafe_s3_website: bool = False,
    ):
        session = boto3.Session(profile_name=profile, region_name=region)
        self.s3 = session.resource("s3")
        self.bucket = bucket
        self.prefix = prefix
        self.acl = acl or "private"
        self.index_name = "index.html" if unsafe_s3_website else ""

    def _object(self, package: Package, filename: str):
        parts = [package.directory, filename]
        if self.prefix:
            parts.insert(0, self.prefix)
        return self.s3.Object(self.bucket, "/".join(parts))

    def get_index(self, package: Package):
        try:
            html = self._object(package, self.index_name).get()["Body"].read()
        except botocore.exceptions.ClientError:
            return Index()
        return Index.parse(html.decode())

    def put_index(self, index: Index):
        package = next(iter(index.packages))
        self._object(package, self.index_name).put(
            Body=index.to_html(),
            ContentType="text/html",
            CacheControl="public, must-revalidate, proxy-revalidate, max-age=0",
            ACL=self.acl,
        )

    def put_package(self, package: Package):
        for path in package.files:
            log.debug("Uploading: %s", path)
            with open(path, mode="rb") as f:
                self._object(package, path.name).put(
                    Body=f,
                    ContentType="application/x-gzip",
                    ACL=self.acl,
                )
