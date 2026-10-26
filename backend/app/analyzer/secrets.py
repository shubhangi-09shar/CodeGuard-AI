import re


def check_secrets(code: str):
    issues = []

    pattern = r"(api[_-]?key|password|secret)\s*=\s*['\"][^'\"]+['\"]"

    for i, line in enumerate(code.splitlines()):
        if re.search(pattern, line, re.IGNORECASE):
            issues.append({
                "type": "secret",
                "severity": "Critical",
                "line": i + 1,
                "message": "Possible hardcoded secret detected."
            })

    return issues