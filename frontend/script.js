const API_URL = "http://127.0.0.1:8000/api/analyze-background";
const form = document.querySelector("#analysis-form");
const repositoryInput = document.querySelector("#repository");
const pullRequestInput = document.querySelector("#pull-request");
const analyzeButton = document.querySelector("#analyze-button");
const result = document.querySelector("#result");

function showResult(message, state = "") {
  result.className = `result ${state}`.trim();
  result.querySelector("p").textContent = message;
  result.querySelector(".result-mark").textContent = state === "success" ? "✓" : state === "error" ? "!" : "i";
}

function showPullRequestDetails(data) {
  const secretIssues = data.secret_issues || [];
  const aiReviews = data.ai_reviews || [];
  const securityIssues = data.security_issues || [];
  const complexityIssues = data.complexity_issues || [];
  const files = data.files || [];

  const filesHtml = files
    .map((file) => {
      const patch = file.patch
        ? `<pre>${file.patch}</pre>`
        : `<p>No patch available for this file.</p>`;

      return `
        <div class="file-review">
          <strong>${file.filename}</strong>
          <div>
            Status: ${file.status}
            | +${file.additions}
            | -${file.deletions}
          </div>
          ${patch}
        </div>
      `;
    })
    .join("");

  result.className = "result success";

  result.innerHTML = `
    <div class="pr-details">
      <h3>${data.title}</h3>

      <p>
        <strong>PR #${data.pull_request}</strong>
        · ${data.state}
      </p>

      <p>Author: ${data.author}</p>

      <p>
        ${data.changed_files} file(s) changed
        · +${data.additions} additions
        · -${data.deletions} deletions
      </p>

      <a href="${data.html_url}" target="_blank" rel="noopener noreferrer">
        View on GitHub
      </a>
      <h4>Complexity Issues</h4>

${
  complexityIssues.length
    ? complexityIssues.map(issue => `
        <div class="file-review">
          <strong>${issue.severity}</strong>
          <p>${issue.message}</p>
          <p>Line: ${issue.line}</p>
        </div>
      `).join("")
    : "<p>No complexity issues found.</p>"
}
    <h4>Security Issues</h4>

${
  securityIssues.length
    ? securityIssues.map(issue => `
        <div class="file-review">
          <strong>${issue.severity}</strong>
          <p>${issue.message}</p>
          <p>Line: ${issue.line}</p>
        </div>
      `).join("")
    : "<p>No security issues found.</p>"
}
    <h4>Secret Issues</h4>

${
  secretIssues.length
    ? secretIssues.map(issue => `
        <div class="file-review">
          <strong>${issue.severity}</strong>
          <p>${issue.message}</p>
          <p>Line: ${issue.line}</p>
        </div>
      `).join("")
    : "<p>No hardcoded secrets found.</p>"
}
<h4>AI Code Review</h4>

${
  aiReviews.length
    ? aiReviews.map(item => `
        <div class="file-review ai-review">
          <strong>${item.filename}</strong>

          <p>${item.review.summary}</p>

          ${
            item.review.issues.length
              ? item.review.issues.map(issue => `
                  <div class="ai-issue">
                    <strong>
                      ${issue.severity} · ${issue.category}
                    </strong>

                    <h5>${issue.title}</h5>

                    <p>
                      <strong>Why it matters:</strong>
                      ${issue.explanation}
                    </p>

                    <p>
                      <strong>Suggested fix:</strong>
                      ${issue.suggestion}
                    </p>

                    ${
                      issue.corrected_code
                        ? `
                          <p><strong>Corrected code:</strong></p>
                          <pre>${issue.corrected_code}</pre>
                        `
                        : ""
                    }
                  </div>
                `).join("")
              : "<p>No issues found.</p>"
          }
        </div>
      `).join("")
    : "<p>No AI review available.</p>"
}

    <h4>Changed files</h4>

      ${filesHtml}
    </div>
  `;
}
async function checkAnalysisStatus(taskId) {
  while (true) {
    const response = await fetch(
      `http://127.0.0.1:8000/api/analysis-status/${taskId}`
    );

    if (!response.ok) {
      throw new Error("Could not check analysis status.");
    }

    const data = await response.json();

    if (data.status === "SUCCESS") {
      return data.result;
    }

    if (data.status === "FAILURE") {
      throw new Error(data.error || "Analysis failed.");
    }

    showResult(
      `Analysis is running... (${data.status})`,
      "loading"
    );

    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}


form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const user = JSON.parse(
  sessionStorage.getItem("codeguardUser")
);

if (!user) {
  showResult(
    "Please login before analyzing a pull request.",
    "error"
  );
  return;
}
  const repository = repositoryInput.value.trim();
  const pullRequestText = pullRequestInput.value.trim();

  if (!repository) {
    showResult(
      "Please enter a GitHub repository in owner/repository format.",
      "error"
    );
    repositoryInput.focus();
    return;
  }

  if (!pullRequestText) {
    showResult(
      "Please enter a pull request number.",
      "error"
    );
    pullRequestInput.focus();
    return;
  }

  const pullRequest = Number(pullRequestText);

  if (!Number.isInteger(pullRequest) || pullRequest < 1) {
    showResult(
      "Pull request number must be a positive whole number.",
      "error"
    );
    pullRequestInput.focus();
    return;
  }

  analyzeButton.disabled = true;
  analyzeButton.querySelector("span").textContent = "Analyzing…";

  showResult(
    "Queueing your pull request for analysis…",
    "loading"
  );

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        repository,
        pull_request: pullRequest,
        user_id: user.user_id
      })
    });

    const data = await response.json();

    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(item => item.msg).join("; ")
        : data.detail;

      throw new Error(
        detail || "The backend rejected the request."
      );
    }

    showResult(
      "Analysis started. Reviewing your pull request…",
      "loading"
    );

    const reviewResult = await checkAnalysisStatus(data.task_id);

    showResult(
      "Analysis completed successfully!",
      "success"
    );

    const reviewResponse = await fetch(
      `http://127.0.0.1:8000/api/reviews/${reviewResult.review_id}?user_id=${user.user_id}`
    );

    if (!reviewResponse.ok) {
      throw new Error("Analysis completed, but the review could not be loaded.");
    }

    const review = await reviewResponse.json();

    sessionStorage.setItem(
  "codeguardReview",
  JSON.stringify({
    ...review,
    changed_files: reviewResult.changed_files,
    state: reviewResult.state,
    html_url: reviewResult.html_url,
    files: reviewResult.files
  })
);

window.location.href = "review.html";

  } catch (error) {
    const message = error instanceof TypeError
      ? "Could not reach the backend. Start FastAPI and try again."
      : error.message;

    showResult(message, "error");

  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector("span").textContent = "Analyze PR";
  }
});
  async function loadReviewHistory() {
  const historyContainer = document.querySelector("#review-history");

  try {
    const user = JSON.parse(
  sessionStorage.getItem("codeguardUser")
);

if (!user) {
  window.location.href = "login.html";
  return;
}

const response = await fetch(
  `http://127.0.0.1:8000/api/reviews?user_id=${user.user_id}`
);

    if (!response.ok) {
      throw new Error("Failed to load review history");
    }

    const data = await response.json();
    const reviews = data.reviews || [];

    if (!reviews.length) {
      historyContainer.innerHTML = "<p>No reviews found.</p>";
      return;
    }

    historyContainer.innerHTML = reviews.map(review => `
      <div class="history-item">
        <strong>PR #${review.pull_request}</strong>
        <h3>${review.title}</h3>
        <p>${review.repository}</p>
        <p>Author: ${review.author}</p>
        <p>
          +${review.additions} additions ·
          -${review.deletions} deletions
        </p>
          <button class="view-review" data-id="${review.id}">
             View Review
          </button>
      </div>
    `).join("");

  } catch (error) {
    historyContainer.innerHTML =
      "<p>Could not load review history.</p>";
    console.error(error);
  }
}

loadReviewHistory();
document.addEventListener("click", async (event) => {
  if (!event.target.classList.contains("view-review")) {
    return;
  }

  const reviewId = event.target.dataset.id;

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/reviews/${reviewId}`
    );

    if (!response.ok) {
      throw new Error("Could not load review.");
    }

    const review = await response.json();

const detailsSection = document.querySelector("#review-details");
const detailsContent = document.querySelector("#review-details-content");

detailsSection.hidden = false;

detailsContent.innerHTML = `
  <div class="history-item">
    <strong>PR #${review.pull_request}</strong>
    <h3>${review.title}</h3>
    <p>${review.repository}</p>
    <p>Author: ${review.author}</p>

    <h4>Complexity Issues</h4>
    ${
      review.complexity_issues.length
        ? review.complexity_issues.map(issue => `
            <p>
              <strong>${issue.severity}</strong> —
              ${issue.message}
              (Line ${issue.line})
            </p>
          `).join("")
        : "<p>No complexity issues.</p>"
    }

    <h4>Security Issues</h4>
    <p>
      ${
        review.security_issues.length
          ? review.security_issues.map(issue => issue.message).join("<br>")
          : "No security issues."
      }
    </p>

    <h4>Secret Issues</h4>
    <p>
      ${
        review.secret_issues.length
          ? review.secret_issues.map(issue => issue.message).join("<br>")
          : "No hardcoded secrets detected."
      }
    </p>

    <h4>AI Review</h4>
    ${
      review.ai_review.map(item => `
        <div class="ai-issue">
          <strong>${item.review.issues[0].severity} · ${item.review.issues[0].category}</strong>
          <h5>${item.review.issues[0].title}</h5>
          <p><strong>Why it matters:</strong> ${item.review.issues[0].explanation}</p>
          <p><strong>Suggested fix:</strong> ${item.review.issues[0].suggestion}</p>
          <p><strong>Corrected code:</strong></p>
          <pre>${item.review.issues[0].corrected_code}</pre>
        </div>
      `).join("")
    }
  </div>
`;
  } catch (error) {
    console.error(error);
  }
});