import asyncio

from app.services.github import get_pull_request_files
from app.services.ai_review import review_code


async def main():
    files = await get_pull_request_files(
        "shubhangi-09shar",
        "repo-demo",
        2
    )

    for file in files:
        code = file.get("patch", "")

        if not code:
            continue

        print(f"\n===== {file['filename']} =====\n")

        result = await review_code(code)

        print(result)


asyncio.run(main())