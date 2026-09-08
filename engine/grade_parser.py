"""Polish School Grade Parser and Running GPA Calculator.

Supports standard Polish 1-6 grades with +/- modifiers, percentages, points/fractions (e.g. 17/17),
and non-ordinary informational markers (np = nieprzygotowanie, bz = brak zadania).
"""

import re
from typing import Dict, Any, Optional, List, Tuple


def percentage_to_polish_grade(pct: float) -> Tuple[float, str]:
    """
    Converts a percentage score (0-100) to Polish school grade (1.0 to 6.0).
    Standard Polish Liceum grade thresholds:
      - 98% - 100%: 6.0 (celujący)
      - 95% - 97%: 5.5 (bardzo dobry+)
      - 90% - 94%: 5.0 (bardzo dobry)
      - 83% - 89%: 4.5 (dobry+)
      - 75% - 82%: 4.0 (dobry)
      - 67% - 74%: 3.5 (dostateczny+)
      - 60% - 66%: 3.0 (dostateczny)
      - 55% - 59%: 2.5 (dopuszczający+)
      - 50% - 54%: 2.0 (dopuszczający)
      - < 50%: 1.0 (niedostateczny)
    """
    pct = max(0.0, min(100.0, pct))
    if pct >= 98.0:
        return 6.0, "6"
    elif pct >= 95.0:
        return 5.5, "5+"
    elif pct >= 90.0:
        return 5.0, "5"
    elif pct >= 83.0:
        return 4.5, "4+"
    elif pct >= 75.0:
        return 4.0, "4"
    elif pct >= 67.0:
        return 3.5, "3+"
    elif pct >= 60.0:
        return 3.0, "3"
    elif pct >= 55.0:
        return 2.5, "2+"
    elif pct >= 50.0:
        return 2.0, "2"
    else:
        return 1.0, "1"


def parse_polish_grade(raw_input: str) -> Dict[str, Any]:
    """
    Parses a user input grade string and returns a structured record with:
      - valid: bool
      - raw_input: original text
      - numeric_value: float or None (if non-numeric like np/bz)
      - display_label: formatted display string
      - counts_in_average: bool
      - percentage: Optional[float]
      - grade_type: 'standard', 'points', 'percentage', 'special'
      - badge_color: theme color for badges
    """
    cleaned = (raw_input or "").strip()
    if not cleaned:
        return {
            "valid": False,
            "raw_input": raw_input,
            "numeric_value": None,
            "display_label": "--",
            "counts_in_average": False,
            "percentage": None,
            "grade_type": "invalid",
            "badge_color": "var(--text-tertiary)",
        }

    lower = cleaned.lower()

    # 1. Check Non-Ordinary Informational Markers: NP, BZ, plus, minus
    if lower in ["np", "nieprzygotowanie"]:
        return {
            "valid": True,
            "raw_input": cleaned,
            "numeric_value": None,
            "display_label": "NP",
            "counts_in_average": False,
            "percentage": None,
            "grade_type": "special",
            "badge_color": "#a1a1aa",  # Muted grey
        }
    if lower in ["bz", "brak zadania", "brak zad"]:
        return {
            "valid": True,
            "raw_input": cleaned,
            "numeric_value": None,
            "display_label": "BZ",
            "counts_in_average": False,
            "percentage": None,
            "grade_type": "special",
            "badge_color": "#f87171",  # Reddish
        }
    if cleaned == "+":
        return {
            "valid": True,
            "raw_input": "+",
            "numeric_value": None,
            "display_label": "+",
            "counts_in_average": False,
            "percentage": None,
            "grade_type": "special",
            "badge_color": "#6ee7b7",
        }
    if cleaned == "-":
        return {
            "valid": True,
            "raw_input": "-",
            "numeric_value": None,
            "display_label": "-",
            "counts_in_average": False,
            "percentage": None,
            "grade_type": "special",
            "badge_color": "#fda4af",
        }

    # 2. Points / Fractions format: e.g. "17/17", "14 / 20", "28.5/30"
    fraction_match = re.match(r"^(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)$", cleaned)
    if fraction_match:
        try:
            score = float(fraction_match.group(1).replace(",", "."))
            max_score = float(fraction_match.group(2).replace(",", "."))
            if max_score > 0:
                pct = round((score / max_score) * 100.0, 1)
                num_val, grade_str = percentage_to_polish_grade(pct)
                return {
                    "valid": True,
                    "raw_input": cleaned,
                    "numeric_value": num_val,
                    "display_label": f"{cleaned} ({pct:.0f}%)",
                    "counts_in_average": True,
                    "percentage": pct,
                    "grade_type": "points",
                    "badge_color": get_grade_badge_color(num_val),
                }
        except ValueError:
            pass

    # 3. Percentages: e.g. "85%", "92.5 %"
    percent_match = re.match(r"^(\d+(?:[.,]\d+)?)\s*%$", cleaned)
    if percent_match:
        try:
            pct = float(percent_match.group(1).replace(",", "."))
            num_val, grade_str = percentage_to_polish_grade(pct)
            return {
                "valid": True,
                "raw_input": cleaned,
                "numeric_value": num_val,
                "display_label": f"{pct:.0f}% ({grade_str})",
                "counts_in_average": True,
                "percentage": pct,
                "grade_type": "percentage",
                "badge_color": get_grade_badge_color(num_val),
            }
        except ValueError:
            pass

    # 4. Standard Grades with Pluses and Minuses
    # Examples: "4+", "+4", "5-", "-5", "4,5", "4.5", "3"
    mod_match = re.match(r"^([+-])?([1-6])([+-])?$", cleaned)
    if mod_match:
        prefix, num_str, suffix = mod_match.groups()
        base = float(num_str)
        is_plus = (prefix == "+" or suffix == "+")
        is_minus = (prefix == "-" or suffix == "-")

        if is_plus:
            val = min(6.0, base + 0.5)
            label = f"{int(base)}+"
        elif is_minus:
            val = max(1.0, base - 0.25)
            label = f"{int(base)}-"
        else:
            val = base
            label = str(int(base))

        return {
            "valid": True,
            "raw_input": cleaned,
            "numeric_value": val,
            "display_label": label,
            "counts_in_average": True,
            "percentage": None,
            "grade_type": "standard",
            "badge_color": get_grade_badge_color(val),
        }

    # Decimal grade like 4.5 or 3,75
    dec_clean = cleaned.replace(",", ".")
    try:
        dec_val = float(dec_clean)
        if 1.0 <= dec_val <= 6.0:
            return {
                "valid": True,
                "raw_input": cleaned,
                "numeric_value": dec_val,
                "display_label": f"{dec_val:g}",
                "counts_in_average": True,
                "percentage": None,
                "grade_type": "standard",
                "badge_color": get_grade_badge_color(dec_val),
            }
    except ValueError:
        pass

    return {
        "valid": False,
        "raw_input": raw_input,
        "numeric_value": None,
        "display_label": cleaned,
        "counts_in_average": False,
        "percentage": None,
        "grade_type": "unknown",
        "badge_color": "var(--text-tertiary)",
    }


def get_grade_badge_color(val: Optional[float]) -> str:
    """Returns aesthetic color hex for grade badge according to Polish scale."""
    if val is None:
        return "#a1a1aa"
    if val >= 5.0:
        return "#6ee7b7"  # Emerald / Celujący / Bdb
    if val >= 4.0:
        return "#7dd3fc"  # Sky Blue / Dobry
    if val >= 3.0:
        return "#c4b5fd"  # Lavender / Dostateczny
    if val >= 2.0:
        return "#f59e0b"  # Amber / Dopuszczający
    return "#f87171"      # Red / Niedostateczny


def calculate_subject_average(entries: List[Dict[str, Any]]) -> Optional[float]:
    """Calculates weighted average from a list of grade entries."""
    total_weighted = 0.0
    total_weights = 0.0

    for e in entries:
        val = e.get("numeric_value")
        counts = e.get("counts_in_average", True)
        weight = float(e.get("weight", 1.0))
        if val is not None and counts and weight > 0:
            total_weighted += float(val) * weight
            total_weights += weight

    if total_weights > 0:
        return round(total_weighted / total_weights, 2)
    return None
