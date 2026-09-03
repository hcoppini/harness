"""Service for fetching and parsing school timetables from TM1 / Vulcan Optivum & managing educational links."""


import json
import re
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from app.db import DATA_DIR

DEFAULT_PLAN_URL = "https://planlekcji.staff.edu.pl/plany/o6.html"  # 3lb
CACHED_PLAN_FILE = DATA_DIR / "school_timetable.json"

POLISH_WEEKDAYS = {
    0: "Poniedziałek",
    1: "Wtorek",
    2: "Środa",
    3: "Czwartek",
    4: "Piątek",
    5: "Sobota",
    6: "Niedziela",
}

SAFE_SCHEMES = ("http://", "https://")

DEFAULT_EASY_LINKS = [
    {
        "name": "TM1 Official Portal",
        "category": "school",
        "url": "https://tm1.edu.pl",
        "desc": "Official School News & Announcements",
    },
    {
        "name": "TM1 Live Plan (Optivum)",
        "category": "school",
        "url": "https://planlekcji.staff.edu.pl/plany/o6.html",
        "desc": "Liceum 3lb Live Timetable",
    },
    {
        "name": "Vulcan UONET+ E-Dziennik",
        "category": "school",
        "url": "https://uonetplus.vulcan.net.pl",
        "desc": "Grades, attendance, and official teacher notices",
    },
    {
        "name": "SIGG Platform (GPW)",
        "category": "contest",
        "url": "https://sigg.gpw.pl",
        "desc": "Szkolna Internetowa Gra Giełdowa",
    },
    {
        "name": "TUM Heilbronn Portal",
        "category": "university",
        "url": "https://www.tum.de/heilbronn",
        "desc": "B.Sc. Management and Data Science Requirements",
    },
    {
        "name": "CKE Matura Portal",
        "category": "academics",
        "url": "https://cke.gov.pl",
        "desc": "Official Matura Arkusze (Maths & CS Rozszerzona)",
    },
]


def is_safe_url(url: str) -> bool:
    """Validates that a URL begins with http:// or https:// to prevent script execution."""
    if not url or not isinstance(url, str):
        return False
    return url.lower().startswith(SAFE_SCHEMES)


def open_external_url(url: str) -> bool:
    """Safely opens a website in the default Windows browser."""
    if not is_safe_url(url):
        return False
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def get_easy_links() -> List[Dict[str, Any]]:
    """Returns curated high-signal links for daily execution."""
    links_file = DATA_DIR / "easy_links.json"
    if not links_file.exists():
        try:
            with open(links_file, "w", encoding="utf-8") as f:
                json.dump({"links": DEFAULT_EASY_LINKS}, f, indent=2)
        except Exception:
            return DEFAULT_EASY_LINKS

    try:
        with open(links_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("links", DEFAULT_EASY_LINKS)
    except Exception:
        return DEFAULT_EASY_LINKS


def save_easy_links(links: List[Dict[str, Any]]) -> bool:
    """Saves links list to easy_links.json."""
    links_file = DATA_DIR / "easy_links.json"
    try:
        with open(links_file, "w", encoding="utf-8") as f:
            json.dump({"links": links}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def add_easy_link(name: str, url: str, category: str = "custom", desc: str = "") -> Dict[str, Any]:
    """Adds a new quick link bookmark."""
    links = get_easy_links()
    new_link = {
        "name": name.strip(),
        "url": url.strip(),
        "category": category.strip() or "custom",
        "desc": desc.strip(),
    }
    links.append(new_link)
    save_easy_links(links)
    return new_link


def update_easy_link(index: int, name: str, url: str, category: str = "custom", desc: str = "") -> bool:
    """Updates an existing quick link by index."""
    links = get_easy_links()
    if 0 <= index < len(links):
        links[index] = {
            "name": name.strip(),
            "url": url.strip(),
            "category": category.strip() or "custom",
            "desc": desc.strip(),
        }
        return save_easy_links(links)
    return False


def delete_easy_link(index: int) -> bool:
    """Deletes a quick link by index."""
    links = get_easy_links()
    if 0 <= index < len(links):
        links.pop(index)
        return save_easy_links(links)
    return False


def parse_optivum_html(html_content: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parses Vulcan Optivum timetable HTML into a structured dictionary keyed by Polish weekday."""
    if not BeautifulSoup:
        return {}
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", class_="tabela")
    if not table:
        return {}

    days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    schedule: Dict[str, List[Dict[str, Any]]] = {d: [] for d in days}

    rows = table.find_all("tr")
    for row in rows:
        nr_col = row.find("td", class_="nr")
        g_col = row.find("td", class_="g")
        if not nr_col or not g_col:
            continue

        try:
            nr = int(nr_col.get_text(strip=True))
        except ValueError:
            nr = 0
        time_slot = g_col.get_text(strip=True)

        lesson_cols = row.find_all("td", class_="l")
        for day_idx, cell in enumerate(lesson_cols):
            if day_idx >= len(days):
                break
            day_name = days[day_idx]

            raw_text = cell.get_text(separator=" ", strip=True)
            if not raw_text or raw_text == " ":
                continue

            raw_html = cell.decode_contents()
            parts = [p.strip() for p in re.split(r"<br\s*/?>", raw_html, flags=re.I) if p.strip() and p.strip() != "&nbsp;"]
            if not parts:
                continue

            entry_list = []
            for part in parts:
                part_soup = BeautifulSoup(part, "html.parser")
                p_tag = part_soup.find("span", class_="p")
                n_tag = part_soup.find("a", class_="n") or part_soup.find("span", class_="n")
                s_tag = part_soup.find("a", class_="s") or part_soup.find("span", class_="s")

                subj = p_tag.get_text(strip=True) if p_tag else part_soup.get_text(strip=True)
                teacher = n_tag.get_text(strip=True) if n_tag else ""
                room = s_tag.get_text(strip=True) if s_tag else ""

                # Clean internal Optivum hashtag flags (e.g. #a2, #o2, #zd1, #5r)
                subj = re.sub(r"#[a-zA-Z0-9_-]+", "", subj).strip()
                if not subj:
                    continue

                entry_list.append({"subject": subj, "teacher": teacher, "room": room})

            if not entry_list:
                continue

            if len(entry_list) == 1:
                schedule[day_name].append({
                    "nr": nr,
                    "time": time_slot,
                    "subject": entry_list[0]["subject"],
                    "teacher": entry_list[0]["teacher"],
                    "room": entry_list[0]["room"],
                    "entries": entry_list,
                })
            else:
                # Multiple groups in same slot (e.g. informatyka-1/2 vs wf-2/2)
                subjs = " / ".join([e["subject"] for e in entry_list if e["subject"]])
                teachers = " / ".join([e["teacher"] for e in entry_list if e["teacher"]])
                rooms = " / ".join([e["room"] for e in entry_list if e["room"]])
                schedule[day_name].append({
                    "nr": nr,
                    "time": time_slot,
                    "subject": subjs,
                    "teacher": teachers,
                    "room": rooms,
                    "entries": entry_list,
                })

    return schedule


def fetch_school_plan(plan_url: str = DEFAULT_PLAN_URL, force_refresh: bool = False) -> Dict[str, Any]:
    """Fetches and caches the school timetable from TM1 / staff.edu.pl."""
    if not force_refresh and CACHED_PLAN_FILE.exists():
        try:
            with open(CACHED_PLAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Online fetch with fallback
    try:
        req = urllib.request.Request(
            plan_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Harness/2.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="replace")
        
        parsed = parse_optivum_html(html)
        if parsed:
            data = {
                "source_url": plan_url,
                "fetched_at": datetime.now().isoformat(),
                "schedule": parsed,
            }
            try:
                with open(CACHED_PLAN_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return data
    except Exception as e:
        # If offline or network timeout, return cached file if available
        if CACHED_PLAN_FILE.exists():
            try:
                with open(CACHED_PLAN_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"error": str(e), "schedule": {}}

    return {"schedule": {}}


def get_lessons_for_date(date_str: Optional[str] = None, cached_plan: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Returns the school lessons for the given date (defaults to today)."""
    target_dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    weekday_idx = target_dt.weekday() # 0 = Monday, 6 = Sunday
    if weekday_idx >= 5: # Saturday or Sunday
        return []

    weekday_pl = POLISH_WEEKDAYS.get(weekday_idx, "")
    
    if cached_plan and weekday_pl in cached_plan:
        return cached_plan.get(weekday_pl, [])

    full_plan_data = fetch_school_plan()
    schedule = full_plan_data.get("schedule", {})
    return schedule.get(weekday_pl, [])
