"""Tests that infrastructure config files are valid and contain required structure."""

import os
import sys
import tomllib
import yaml

# Project root is two levels up from this file (backend/tests/test_config_files.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "GOOGLE_PLACES_API_KEY",
    "YELP_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLOUDFLARE_R2_ENDPOINT",
    "CLOUDFLARE_R2_ACCESS_KEY",
    "CLOUDFLARE_R2_SECRET_KEY",
    "CLOUDFLARE_R2_BUCKET",
    "VERCEL_TOKEN",
    "VERCEL_TEAM_ID",
    "AGENCY_DOMAIN",
    "RESEND_API_KEY",
    "HUNTER_API_KEY",
    "OUTREACH_DAILY_CAP",
    "REVIEW_MODE",
]


def test_docker_compose_valid_yaml():
    """docker-compose.yml must be valid YAML."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"
    with open(compose_path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "docker-compose.yml must be a YAML mapping"


def test_docker_compose_has_required_services():
    """docker-compose.yml must declare postgres, redis, api, and worker services."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    for required in ("postgres", "redis", "api", "worker"):
        assert required in services, f"Missing service '{required}' in docker-compose.yml"


def test_docker_compose_no_version_key():
    """docker-compose.yml must not have a deprecated 'version' key."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        data = yaml.safe_load(f)
    assert "version" not in data, "docker-compose.yml must not contain a 'version' key (deprecated)"


def test_railway_toml_valid_toml():
    """railway.toml must be valid TOML."""
    toml_path = os.path.join(PROJECT_ROOT, "railway.toml")
    assert os.path.exists(toml_path), f"railway.toml not found at {toml_path}"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    assert isinstance(data, dict), "railway.toml must be a TOML mapping"


def test_railway_toml_has_deploy_section():
    """railway.toml must have a [deploy] section."""
    toml_path = os.path.join(PROJECT_ROOT, "railway.toml")
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    assert "deploy" in data, "railway.toml must have a [deploy] section"


def test_railway_toml_has_build_section():
    """railway.toml must have a [build] section with dockerfile builder."""
    toml_path = os.path.join(PROJECT_ROOT, "railway.toml")
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    assert "build" in data, "railway.toml must have a [build] section"
    assert data["build"].get("builder") == "dockerfile"


def test_env_example_exists_and_contains_all_vars():
    """.env.example must exist and list every required environment variable."""
    env_path = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.exists(env_path), f".env.example not found at {env_path}"
    with open(env_path) as f:
        content = f.read()
    for var in REQUIRED_ENV_VARS:
        assert var in content, f"Missing env var '{var}' in .env.example"


def test_dockerfile_exists():
    """backend/Dockerfile must exist."""
    dockerfile_path = os.path.join(BACKEND_DIR, "Dockerfile")
    assert os.path.exists(dockerfile_path), f"Dockerfile not found at {dockerfile_path}"


def test_dockerfile_uses_python_312():
    """Dockerfile must use Python 3.12."""
    dockerfile_path = os.path.join(BACKEND_DIR, "Dockerfile")
    with open(dockerfile_path) as f:
        content = f.read()
    assert "python:3.12" in content, "Dockerfile must use Python 3.12 base image"


def test_dockerfile_has_expose_8000():
    """Dockerfile must expose port 8000."""
    dockerfile_path = os.path.join(BACKEND_DIR, "Dockerfile")
    with open(dockerfile_path) as f:
        content = f.read()
    assert "EXPOSE 8000" in content, "Dockerfile must contain 'EXPOSE 8000'"


def test_dockerfile_has_uvicorn_cmd():
    """Dockerfile CMD must start uvicorn on 0.0.0.0:8000."""
    dockerfile_path = os.path.join(BACKEND_DIR, "Dockerfile")
    with open(dockerfile_path) as f:
        content = f.read()
    assert "uvicorn" in content, "Dockerfile CMD must reference uvicorn"
    assert "0.0.0.0" in content, "Dockerfile CMD must bind to 0.0.0.0"
    assert "8000" in content, "Dockerfile CMD must use port 8000"
