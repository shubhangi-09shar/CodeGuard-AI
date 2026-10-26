import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


async def review_code(code: str):
    prompt = f"""
You are an AI code reviewer for a developer tool.

Analyze the following code for:
- Bugs
- Performance issues
- Security issues
- Code quality issues

Return your response ONLY as valid JSON in this exact structure:

{{
    "summary": "Short overall assessment",
    "issues": [
        {{
            "category": "Performance",
            "severity": "Critical",
            "title": "Short issue title",
            "explanation": "Explain the problem and why it matters",
            "suggestion": "Explain how to fix it",
            "corrected_code": "Corrected code if useful, otherwise empty string"
        }}
    ]
}}

If there are no issues, return an empty issues array.

Code to review:
{code}
"""

    response = await client.aio.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    return json.loads(response.text)
def review_code_sync(code: str):
    prompt = f"""
You are an AI code reviewer for a developer tool.

Analyze the following code for:
- Bugs
- Performance issues
- Security issues
- Code quality issues

Return your response ONLY as valid JSON in this exact structure:

{{
    "summary": "Short overall assessment",
    "issues": [
        {{
            "category": "Performance",
            "severity": "Critical",
            "title": "Short issue title",
            "explanation": "Explain the problem and why it matters",
            "suggestion": "Explain how to fix it",
            "corrected_code": "Corrected code if useful, otherwise empty string"
        }}
    ]
}}

If there are no issues, return an empty issues array.

Code to review:
{code}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    return json.loads(response.text)