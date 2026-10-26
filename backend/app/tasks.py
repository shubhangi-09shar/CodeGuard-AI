import asyncio
from app.services.ai_review import review_code_sync
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Review

from app.services.github import (
    get_pull_request,
    get_pull_request_files,
)

from app.analyzer.secrets import check_secrets
from app.analyzer.security import check_security
from app.analyzer.complexity import check_complexity


async def run_analysis(
    repository: str,
    pull_request_number: int,
    user_id: int,
):
    owner, repo = repository.split("/", 1)

    pull_request = await get_pull_request(
        owner,
        repo,
        pull_request_number,
    )

    files = await get_pull_request_files(
        owner,
        repo,
        pull_request_number,
    )

    changed_files = [
        {
            "filename": file.get("filename"),
            "status": file.get("status"),
            "additions": file.get("additions"),
            "deletions": file.get("deletions"),
            "changes": file.get("changes"),
            "patch": file.get("patch"),
        }
        for file in files
    ]

    complexity_issues = []
    security_issues = []
    secret_issues = []
    ai_reviews = []

    for file in changed_files:
        code = file.get("patch") or ""

        if not code:
            continue

        ai_result = review_code_sync(code)

        ai_reviews.append({
            "filename": file["filename"],
            "review": ai_result,
        })

        security_issues.extend(check_security(code))
        secret_issues.extend(check_secrets(code))
        complexity_issues.extend(check_complexity(code))

    db = SessionLocal()

    try:
        review_record = Review(
            user_id=user_id,
            repository=repository,
            pull_request=pull_request["number"],
            title=pull_request["title"],
            author=pull_request["user"]["login"],
            additions=pull_request["additions"],
            deletions=pull_request["deletions"],
            complexity_issues=complexity_issues,
            security_issues=security_issues,
            secret_issues=secret_issues,
            ai_review=ai_reviews,
        )

        db.add(review_record)
        db.commit()
        db.refresh(review_record)

        return {
            "review_id": review_record.id,
            "repository": repository,
            "pull_request": pull_request["number"],
            "title": pull_request["title"],
            "state": pull_request["state"],
            "html_url": pull_request["html_url"],
            "changed_files": pull_request["changed_files"],
            "files": changed_files,
            "status": "completed",
        }   

    finally:
        db.close()


@celery_app.task
def analyze_pull_request_task(
    repository: str,
    pull_request_number: int,
    user_id: int,
):
    print(
        f"Starting CodeGuard analysis for "
        f"{repository} PR #{pull_request_number}"
    )

    return asyncio.run(
    run_analysis(
        repository,
        pull_request_number,
        user_id,
    )
)