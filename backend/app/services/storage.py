import httpx
import boto3
from dataclasses import dataclass
from botocore.config import Config


@dataclass
class R2StorageClient:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str

    def _s3(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def upload_from_url(self, url: str, key: str) -> str:
        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        return self.upload_bytes(resp.content, key, content_type)

    def upload_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        self._s3().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{self.endpoint}/{self.bucket}/{key}"
