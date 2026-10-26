from app.models import GitHubRepository
from app.tasks import analyze_pull_request_task
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import hashlib
import secrets
from datetime import datetime
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.tasks import analyze_pull_request_task
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import SessionLocal
from app.models import Review, User
from app.services.ai_review import review_code
from app.analyzer.secrets import check_secrets
from app.analyzer.security import check_security
from app.analyzer.complexity import check_complexity
import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.github import (
    get_pull_request,
    get_pull_request_files,
)

router = APIRouter(prefix="/api", tags=["analysis"])


class AnalysisRequest(BaseModel):
    """JSON fields accepted by POST /api/analyze."""

    repository: str = Field(min_length=1, max_length=200)
    pull_request: int = Field(gt=0)
    user_id: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/analyze")
async def analyze_pull_request(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:   
    """Fetch real pull request information from GitHub."""

    repository = request.repository.strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        repository,
    ):
        raise HTTPException(
            status_code=422,
            detail="Repository must use the format owner/repository.",
        )

    owner, repo = repository.split("/", 1)

    try:
        pull_request = await get_pull_request(
            owner,
            repo,
            request.pull_request,
        )

        files = await get_pull_request_files(
            owner,
            repo,
            request.pull_request,
        )

    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code

        if status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Repository or pull request was not found.",
            )

        if status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="GitHub denied access to this repository or pull request.",
            )

        raise HTTPException(
            status_code=502,
            detail="GitHub API returned an unexpected error.",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to GitHub.",
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

        review = await review_code(code)

        ai_reviews.append({
            "filename": file["filename"],
            "review": review,
        })

    for file in changed_files:
        if file["patch"]:
            issues = check_security(file["patch"])
            security_issues.extend(issues)

    for file in changed_files:
        if file["patch"]:
            issues = check_secrets(file["patch"])
            secret_issues.extend(issues)

    for file in changed_files:
        if file["patch"]:
            issues = check_complexity(file["patch"])
            complexity_issues.extend(issues)
    review_record = Review(
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
        "success": True,
        "message": "Pull request fetched successfully",
        "repository": repository,
        "pull_request": pull_request["number"],
        "title": pull_request["title"],
        "state": pull_request["state"],
        "author": pull_request["user"]["login"],
        "html_url": pull_request["html_url"],
        "additions": pull_request["additions"],
        "deletions": pull_request["deletions"],
        "changed_files": pull_request["changed_files"],
        "files": changed_files,
        "complexity_issues": complexity_issues,
        "security_issues": security_issues,
        "secret_issues": secret_issues,
        "ai_reviews": ai_reviews,
        "review_id": review_record.id
    }
@router.get("/reviews")
def get_reviews(
    user_id: int,
    db: Session = Depends(get_db)
):
    reviews = (
        db.query(Review)
        .filter(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    return {
        "reviews": [
            {
                "id": review.id,
                "repository": review.repository,
                "pull_request": review.pull_request,
                "title": review.title,
                "author": review.author,
                "additions": review.additions,
                "deletions": review.deletions,
                "created_at": review.created_at,
            }
            for review in reviews
        ]
    }
@router.get("/reviews/{review_id}")
def get_review(
    review_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    review = (
        db.query(Review)
        .filter(
            Review.id == review_id,
            Review.user_id == user_id
        )
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found.",
        )

    return {
        "id": review.id,
        "repository": review.repository,
        "pull_request": review.pull_request,
        "title": review.title,
        "author": review.author,
        "additions": review.additions,
        "deletions": review.deletions,
        "complexity_issues": review.complexity_issues,
        "security_issues": review.security_issues,
        "secret_issues": review.secret_issues,
        "ai_review": review.ai_review,
        "created_at": review.created_at,
    }
@router.post("/analyze-background")
def analyze_background(request: AnalysisRequest):
    repository = request.repository.strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        repository,
    ):
        raise HTTPException(
            status_code=422,
            detail="Repository must use the format owner/repository.",
        )

    task = analyze_pull_request_task.delay(
        repository,
        request.pull_request,
        request.user_id,
    )

    return {
        "success": True,
        "message": "Analysis queued successfully",
        "task_id": task.id,
        "repository": repository,
        "pull_request": request.pull_request,
    }
@router.get("/analysis-status/{task_id}")
def get_analysis_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task.status,
    }

    if task.successful():
        response["result"] = task.result

    if task.failed():
        response["error"] = str(task.result)

    return response
@router.get("/dashboard-stats")
def get_dashboard_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    reviews = (
        db.query(Review)
        .filter(Review.user_id == user_id)
        .all()
    )
    reviews = db.query(Review).all()

    total_reviews = len(reviews)

    total_issues = 0
    critical_issues = 0
    reviews_today = 0

    today = datetime.utcnow().date()

    for review in reviews:
        complexity = review.complexity_issues or []
        security = review.security_issues or []
        secrets = review.secret_issues or []

        all_static_issues = complexity + security + secrets

        total_issues += len(all_static_issues)

        for issue in all_static_issues:
            if issue.get("severity") == "Critical":
                critical_issues += 1

        if review.created_at and review.created_at.date() == today:
            reviews_today += 1

    return {
        "total_reviews": total_reviews,
        "total_issues": total_issues,
        "critical_issues": critical_issues,
        "reviews_today": reviews_today,
    }
class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=100)


@router.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):

    email = request.email.strip().lower()

    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        request.password.encode(),
        salt.encode(),
        100000,
    ).hex()

    stored_password = f"{salt}${password_hash}"

    user = User(
        name=request.name.strip(),
        email=email,
        password_hash=stored_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Account created successfully.",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }
class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=100)


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):

    email = request.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    salt, stored_hash = user.password_hash.split("$")

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        request.password.encode(),
        salt.encode(),
        100000,
    ).hex()

    if password_hash != stored_hash:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    return {
        "success": True,
        "message": "Login successful.",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }
@router.post("/github-webhook")
async def github_webhook(
    payload: dict,
    db: Session = Depends(get_db)
):

    action = payload.get("action")
    pull_request = payload.get("pull_request")
    repository = payload.get("repository")

    if not pull_request or not repository:
        return {
            "success": False,
            "message": "Invalid GitHub webhook payload."
        }

    if action not in ["opened", "synchronize", "reopened"]:
        return {
            "success": True,
            "message": "Event ignored."
        }

    repo_name = repository.get("full_name")
    pr_number = pull_request.get("number")

    repository_mapping = (
    db.query(GitHubRepository)
    .filter(GitHubRepository.repository == repo_name)
    .first()
    )

    if not repository_mapping:
        return {
            "success": False,
            "message": "Repository is not connected to a CodeGuard user."
    }

    task = analyze_pull_request_task.delay(
    repo_name,
    pr_number,
    repository_mapping.user_id  
    )
    return {
    "success": True,
    "message": "Webhook received and analysis queued.",
    "repository": repo_name,
    "pull_request": pr_number,
    "task_id": task.id
}
