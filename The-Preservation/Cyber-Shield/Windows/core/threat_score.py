"""威胁评分原子。

对每次攻击进行评分：轻度/中度/重度/组织化。
评分驱动后续动作强度。
"""

THREAT_LEVELS = ["mild", "moderate", "severe", "organized"]


def score(freq_count: int, is_attack: bool, is_report_chain: bool,
          has_personal_info: bool = False, custom_weight: float = 1.0) -> dict:
    score_val = 0
    if is_attack:
        score_val += 3
    if is_report_chain:
        score_val += 4
    if freq_count > 10:
        score_val += 2
    if freq_count > 50:
        score_val += 3
    if has_personal_info:
        score_val += 2

    score_val = int(score_val * custom_weight)
    score_val = max(1, min(10, score_val))

    if score_val <= 3:
        level = "mild"
    elif score_val <= 6:
        level = "moderate"
    elif score_val <= 8:
        level = "severe"
    else:
        level = "organized"

    return {
        "score": score_val,
        "level": level,
        "actions": _actions_for(level),
    }


def _actions_for(level: str) -> list:
    return {
        "mild": ["forensics", "lockdown"],
        "moderate": ["forensics", "lockdown", "counterstrike_single"],
        "severe": ["forensics", "lockdown", "counterstrike_multi"],
        "organized": [
            "forensics", "lockdown", "counterstrike_multi",
            "notify_nihility", "notify_hunt",
        ],
    }.get(level, ["forensics"])
