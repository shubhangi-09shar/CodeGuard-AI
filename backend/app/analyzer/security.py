def check_security(code: str):
    issues = []

    for i, line in enumerate(code.splitlines()):
        if "eval(" in line:
            issues.append({
                "type": "security",
                "severity": "High",
                "line": i + 1,
                "message": "Use of eval() can execute arbitrary code and may create a security risk."
            })

    return issues