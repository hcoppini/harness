import json
import re
from pathlib import Path

def clean_seed():
    p = Path(__file__).resolve().parent.parent / "app" / "seed_data.py"
    with open(p, "r", encoding="utf-8") as f:
        code = f.read()

    # Find the _SEED_JSON string
    prefix = '_SEED_JSON = '
    start = code.find(prefix)
    if start == -1:
        print("prefix not found")
        return
    
    start_quote = start + len(prefix)
    # The JSON string starts with "
    end = code.rfind("\n\nSEED_DATA =")
    raw_literal = code[start_quote:end].strip()
    
    # decode the python string literal to get actual JSON string
    json_str = json.loads(raw_literal)
    data = json.loads(json_str)

    # Filter school_exams
    before_exams = len(data.get("school_exams", []))
    data["school_exams"] = [
        e for e in data.get("school_exams", [])
        if "Trygonometria" not in e.get("title", "")
        and "Kinematyka" not in e.get("title", "")
        and "Wyszukiwania" not in e.get("title", "")
        and "Powstanie Styczniowe" not in e.get("title", "")
    ]
    after_exams = len(data["school_exams"])

    # Filter homework_items
    before_hw = len(data.get("homework_items", []))
    data["homework_items"] = [
        h for h in data.get("homework_items", [])
        if "plecakowy" not in h.get("title", "")
        and "Trading" not in h.get("title", "")
    ]
    after_hw = len(data["homework_items"])

    print(f"Exams: {before_exams} -> {after_exams}. Homework: {before_hw} -> {after_hw}.")

    clean_json_str = json.dumps(data, indent=2, ensure_ascii=False)
    new_literal = json.dumps(clean_json_str, ensure_ascii=False)
    new_code = f"# Auto-generated embedded database seed\nimport json\n\n_SEED_JSON = {new_literal}\n\nSEED_DATA = json.loads(_SEED_JSON)\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("Cleaned seed_data.py successfully!")

if __name__ == "__main__":
    clean_seed()
