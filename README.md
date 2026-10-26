# CodeGuard AI

CodeGuard AI is a learning project for an AI-powered GitHub Pull Request code review system. **Day 1 only establishes communication between a small HTML/CSS/JavaScript frontend and a Python FastAPI backend.** The backend acknowledges a valid request; it does not contact GitHub or perform a review.

## Day 1 architecture

The browser loads the frontend. JavaScript sends the repository and pull request number as JSON in an HTTP `POST` request to FastAPI. FastAPI validates the data and returns a JSON acknowledgement, which JavaScript displays on the page.

```text
Browser (HTML/CSS/JavaScript)
        │ POST /api/analyze with JSON
        ▼
FastAPI (Python, port 8000)
        │ JSON response
        ▼
Browser result section
```

## Technologies used today

- HTML, CSS, and vanilla JavaScript
- Python, FastAPI, and Uvicorn

## Run the backend

From the project root, create and activate a virtual environment, then install the backend requirements:

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API runs at <http://127.0.0.1:8000>. Visit <http://127.0.0.1:8000/> for its health response and <http://127.0.0.1:8000/docs> for FastAPI's interactive API page.

If PowerShell blocks virtual environment activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again.

## Run the frontend

In a second terminal, from the project root:

```powershell
cd frontend
py -m http.server 5500
```

Open <http://127.0.0.1:5500>. Enter `octocat/Hello-World` and `12`, then select **Analyze PR**. The page should show the backend's acknowledgement and the values it received.

The form reports missing fields and non-positive or non-whole PR numbers before sending. The backend also validates the `owner/repository` format and requires a positive PR number. To see the connection error, stop the backend and submit a valid form; the page will ask you to start FastAPI.

## Project files

- `backend/app/main.py` creates the FastAPI app, enables local CORS, registers routes, and provides the health endpoint.
- `backend/app/routes/analysis.py` validates `POST /api/analyze` input and returns the acknowledgement.
- `backend/requirements.txt` lists the Python packages needed for the backend.
- `frontend/index.html` defines the page and form.
- `frontend/style.css` styles the responsive interface.
- `frontend/script.js` validates form values, sends JSON with `fetch()`, and displays the result or an error.
- `.gitignore` excludes Python caches, virtual environments, and local environment files.

## Planned future features

GitHub integration, webhooks, static code analysis, AI review, PostgreSQL, Redis, background workers, and posting reviews back to GitHub are **future features and are not implemented yet**. Day 1 does not include authentication, Docker, cloud deployment, or an LLM API.
