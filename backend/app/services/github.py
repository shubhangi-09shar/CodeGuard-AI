import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


# Load the .env file from the backend folder
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GITHUB_API_URL = "https://api.github.com"


def get_headers():
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2026-03-10",
    }


async def get_pull_request(owner, repo, pull_number):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pull_number}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=get_headers())

    response.raise_for_status()

    return response.json()


async def get_pull_request_files(owner, repo, pull_number):
    url = (
        f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/files"
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=get_headers())

    response.raise_for_status()

    return response.json()