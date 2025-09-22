import re

def read_prefix(qe_in: str) -> str:
    with open(qe_in) as f:
        for line in f:
            if "prefix" in line.lower():
                m = re.search(r"prefix\s*=\s*['\"]([^'\"]+)['\"]", line, re.IGNORECASE)
                if m:
                    return m.group(1)
    return ""

def read_nspin(qe_in: str) -> int:
    with open(qe_in) as f:
        text = f.read().lower()
    match = re.search(r"nspin\s*=\s*(\d+)", text)
    return int(match.group(1)) if match else 1