def check_complexity(code: str):
    issues = []

    lines = code.splitlines()

    for i, line in enumerate(lines):
        if "for " in line or "while " in line:
            for next_line in lines[i + 1:]:
                if "for " in next_line or "while " in next_line:
                    issues.append({
                        "type": "complexity",
                        "severity": "Medium",
                        "line": i + 1,
                        "message": "Nested loop detected. This may result in O(n²) time complexity."
                    })
                    break

    return issues