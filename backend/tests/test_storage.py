import pytest
import respx
import httpx
from moto import mock_aws
import boto3
from unittest.mock import patch, MagicMock
from app.services.storage import R2StorageClient


@pytest.fixture
def r2_client():
    return R2StorageClient(
        endpoint="https://test.r2.cloudflarestorage.com",
        access_key="test-access",
        secret_key="test-secret",
        bucket="webagency-test",
    )


@mock_aws
@respx.mock
def test_upload_from_url_stores_and_returns_url(r2_client):
    # Create bucket via normal S3 client for moto setup
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="webagency-test")

    # Mock the HTTP request to download the image
    respx.get("https://example.com/photo.jpg").mock(
        return_value=httpx.Response(200, content=b"fake-image-bytes",
                                    headers={"content-type": "image/jpeg"})
    )

    # Mock boto3.client to bypass custom endpoint and use moto's S3
    original_client = boto3.client
    def mock_boto3_client(service_name, **kwargs):
        if service_name == "s3" and "endpoint_url" in kwargs:
            # Remove custom endpoint to use moto's S3
            kwargs.pop("endpoint_url", None)
        return original_client(service_name, **kwargs)

    with patch("boto3.client", side_effect=mock_boto3_client):
        url = r2_client.upload_from_url("https://example.com/photo.jpg", "businesses/abc/photo1.jpg")

    assert "photo1.jpg" in url


@mock_aws
def test_upload_bytes_stores_and_returns_url():
    r2_client = R2StorageClient(
        endpoint="https://test.r2.cloudflarestorage.com",
        access_key="test-access",
        secret_key="test-secret",
        bucket="webagency-test",
    )

    # Create bucket via normal S3 client
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="webagency-test")

    # Mock boto3.client to bypass custom endpoint
    original_client = boto3.client
    def mock_boto3_client(service_name, **kwargs):
        if service_name == "s3" and "endpoint_url" in kwargs:
            kwargs.pop("endpoint_url", None)
        return original_client(service_name, **kwargs)

    with patch("boto3.client", side_effect=mock_boto3_client):
        url = r2_client.upload_bytes(b"test-data", "test/image.jpg", "image/jpeg")

    assert "test/image.jpg" in url
    assert r2_client.bucket in url
