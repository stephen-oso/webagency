"""Publisher interface and Vercel implementation for deploying Next.js sites."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import subprocess


class Publisher(ABC):
    @abstractmethod
    def deploy(self, build_path: str, slug: str) -> str:
        """Deploy a Next.js project directory. Returns the public URL."""


@dataclass
class VercelPublisher(Publisher):
    token: str
    team_id: str | None
    agency_domain: str

    def deploy(self, build_path: str, slug: str) -> str:
        cmd = ["vercel", "deploy", "--yes", "--token", self.token]
        if self.team_id:
            cmd += ["--scope", self.team_id]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=build_path,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Vercel deploy failed: {result.stderr}")

        vercel_url = result.stdout.strip().split("\n")[-1].strip()
        return vercel_url
