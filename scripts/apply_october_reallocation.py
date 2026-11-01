"""
Script to apply the October reality audit and deliverable redistribution across 
metro_roadmap.json and data/harness.db (station_deliverable_progress).
"""

import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
METRO_JSON = ROOT_DIR / "data" / "metro_roadmap.json"
DB_PATH = ROOT_DIR / "data" / "harness.db"


def update_metro_roadmap():
    with open(METRO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    for st in data.get("stations", []):
        s_id = st.get("id")

        if s_id == "sep-2026":
            st["status"] = "completed"
            st["completed_deliverables"] = ["Academics", "Code", "SIGG", "Physical"]
            st["passed_over_deliverables"] = ["German"]

        elif s_id == "oct-2026":
            st["status"] = "completed"
            st["completed_deliverables"] = []
            st["passed_over_deliverables"] = ["Academics", "Code", "SIGG", "German"]
            st["next_action"] = "October audited and reallocated forward into Nov 2026 - Sep 2027 stations."

        elif s_id == "nov-2026":
            st["status"] = "active"
            st["objective"] = "Launch 25. edycja SIGG Etap Główny (20 000 PLN capital) & CKE data parsing tasks. [Includes +2 Math R & +2 Code catch-up]."
            st["deliverables"] = {
                "Academics": "Mid-semester review. All subjects > 4.0, Math and CS locked at 5.0+. Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "SIGG": "Start Etapu Głównego (16 listopada 2026 – 12 marca 2027). Kapitał 20 000 zł na akcje WIG20/mWIG40 i ETF-y. Złożyć obowiązkową pierwszą transakcję. Śledzić 4 premie lotne w trakcie etapu. (Gra Testowa na GPWtr@der 2-13.11).",
                "Code": "Transition to CKE Matura programming tasks in Python/C++. Target: 17 exercises (15 base + 2 Oct catch-up).",
                "Physical": "Weight 69.5 kg; 5k run pace under 4:40."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "Code": {"count": 0, "total": 17, "unit": "exercises"},
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "Physical": {"count": 0, "total": 30, "unit": "days"}
            }
            st["next_action"] = "Gra Testowa na GPWtr@der (start 2.11) & pierwsze zadania Math R (42 zadania)."

        elif s_id == "dec-2026":
            st["deliverables"] = {
                "Academics": "Finalize Semester 1 proposed grades. No grade below 4; Math, CS, English at 5 or 6. Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "SIGG": "Etap Główny (20 000 zł): Przegląd portfela akcji/ETF przed przerwą świąteczną i okresem niskiej płynności. Polowanie na premię lotną.",
                "German": "A2 certification test (self-assessment or mock). Begin transition to B1 materials. Target: 110 words in Anki (100 base + 10 Oct catch-up).",
                "Code": "Audit desktop/polish_stocks_day_trade-main and understand every function without AI explanation. Target: 17 exercises (15 base + 2 Oct catch-up)."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "German": {"count": 0, "total": 110, "unit": "words"},
                "Code": {"count": 0, "total": 17, "unit": "exercises"}
            }

        elif s_id == "jan-2027":
            st["deliverables"] = {
                "Academics": "Formal Semester 1 grades locked onto official transcript. Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "SIGG": "Półmetek Etapu Głównego (trwa do 12 marca). Audyt portfela akcji/ETF, kontrola obsunięcia kapitału (drawdown) i rywalizacja w modułach wiedzy.",
                "Code": "Solve 17 dynamic programming and recursion problems from previous Matura sheets (15 base + 2 Oct catch-up)."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "Code": {"count": 0, "total": 17, "unit": "exercises"}
            }

        elif s_id == "feb-2027":
            st["deliverables"] = {
                "Academics": "Complete 5 full Math Rozszerzona past sheets (CKE 2020-2024). Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "SIGG": "Etap Główny w fazie finałowej (do 12 marca). Przygotowanie do rozgrywki na kontraktach terminowych (start 15 marca): symulacja mechaniki dźwigni FW20 i pozycji krótkich.",
                "German": "B1 grammar foundations (Subjunctive II, passive voice, subordinate clauses). Target: 112 words (100 base + 12 Oct catch-up).",
                "Physical": "Weight 71.0 kg; bench/squat/deadlift baseline increase of 5%."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "German": {"count": 0, "total": 112, "unit": "words"},
                "Physical": {"count": 0, "total": 30, "unit": "days"}
            }

        elif s_id == "mar-2027":
            st["deliverables"] = {
                "SIGG": "12 marca: Zakończenie Etapu Głównego. 15–26 marca: Dedykowana rozgrywka na kontraktach terminowych z osobną pulą 10 000 zł. Ścisły risk management i stop-loss na kontraktach FW20.",
                "Academics": "Q3 school grades checkup. Ensure Polish, History, and Biology stay >= 4.0. Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "Code": "Master SQL databases and Access/Excel data processing modules required for Matura Informatyka. Target: 16 exercises (15 base + 1 Oct catch-up)."
            }
            st["deliverable_counts"] = {
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "Code": {"count": 0, "total": 16, "unit": "exercises"}
            }

        elif s_id == "apr-2027":
            st["deliverables"] = {
                "SIGG": "12 kwietnia: Ogłoszenie rankingu oficjalnego. 22 kwietnia: Wielki Finał 25. edycji w Sali Notowań GPW w Warszawie dla 50 najlepszych zespołów w Polsce (pula nagród >200 tys. zł, laptopy MacBook).",
                "Academics": "End-of-year sprint begins. Target 5.0+ in all core STEM subjects. Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "German": "B1 intermediate listening comprehension (DW Langsam gesprochene Nachrichten). Target: 113 words (100 base + 13 Oct catch-up)."
            }
            st["deliverable_counts"] = {
                "SIGG": {"count": 0, "total": 5, "unit": "modules"},
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "German": {"count": 0, "total": 113, "unit": "words"}
            }

        elif s_id == "may-2027":
            st["deliverables"] = {
                "Academics": "Sit down with 2027 official Matura papers written by 4th-graders. Score yourself under real exam timing (aim for >70% raw score on Math R 1 year early). Target: 42 Math R problems (40 base + 2 Oct catch-up).",
                "Physical": "Body weight 72.5 kg at 14-15% body fat."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 42, "unit": "problems"},
                "Physical": {"count": 0, "total": 30, "unit": "days"}
            }

        elif s_id == "jun-2027":
            st["deliverables"] = {
                "Academics": "Milepost 1 for TUM: 3rd Class Liceum Final Transcript completed with GPA >= 4.8. Target: 46 Math R problems (40 base + 6 summer catch-up).",
                "Code": "Complete a standalone, production-ready project for your portfolio without AI-generated scaffolding. Target: 21 tasks (15 base + 6 summer catch-up).",
                "Harness": "Update portfolio database with SIGG credentials and year-end metrics."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 46, "unit": "problems"},
                "Code": {"count": 0, "total": 21, "unit": "exercises"},
                "Harness": {"count": 0, "total": 10, "unit": "reps"}
            }

        elif s_id == "jul-aug-2027":
            st["deliverables"] = {
                "German": "Target Goethe-Zertifikat B1 exam or verify B1 competence. Start B2 reading. Target: 165 words in Anki (100 base + 65 summer catch-up).",
                "Academics": "Math Rozszerzona topical review (Calculus, Stereometry, Combinatorics). Target: 54 Math R problems (40 base + 14 summer catch-up).",
                "Physical": "Peak summer check: 73.5-74 kg, 13-14% body fat, 5k run maintained at sub-4:40 pace."
            }
            st["deliverable_counts"] = {
                "German": {"count": 0, "total": 165, "unit": "words"},
                "Academics": {"count": 0, "total": 54, "unit": "problems"},
                "Physical": {"count": 0, "total": 30, "unit": "days"}
            }

        elif s_id == "sep-2027":
            st["deliverables"] = {
                "Academics": "Lock in official Matura declarations: Matematyka Podstawowa + Rozszerzona, Informatyka Rozszerzona, Język Angielski Dwujęzyczny / C1. Target: 46 Math R problems (40 base + 6 summer catch-up).",
                "Code": "Daily timed Matura algorithm speed-drills (45 min/day). Target: 22 tasks (15 base + 7 summer catch-up)."
            }
            st["deliverable_counts"] = {
                "Academics": {"count": 0, "total": 46, "unit": "problems"},
                "Code": {"count": 0, "total": 22, "unit": "exercises"}
            }

    with open(METRO_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("metro_roadmap.json updated successfully.")


def update_database_deliverables():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 1. Close October station deliverables (audited & reallocated)
    cursor.execute("""
        UPDATE station_deliverable_progress
        SET is_completed = 1
        WHERE station_id = 'oct-2026'
    """)

    # 2. Update deliverable targets based on redistribution ledger
    updates = [
        # School Year (Nov 2026 - May 2027)
        ("nov2026_acad", 42),
        ("nov2026_code", 17),
        ("dec2026_acad", 42),
        ("dec2026_code", 17),
        ("dec2026_germ", 110),
        ("jan2027_acad", 42),
        ("jan2027_code", 17),
        ("feb2027_acad", 42),
        ("feb2027_germ", 112),
        ("mar2027_acad", 42),
        ("mar2027_code", 16),
        ("apr2027_acad", 42),
        ("apr2027_germ", 113),
        ("may2027_acad", 42),
        # Summer Expansion (Jun 2027 - Sep 2027)
        ("jun2027_acad", 46),
        ("jun2027_code", 21),
        ("julaug2027_acad", 54),
        ("julaug2027_germ", 165),
        ("sep2027_acad", 46),
        ("sep2027_code", 22),
    ]

    for d_id, new_total in updates:
        cursor.execute("""
            UPDATE station_deliverable_progress
            SET total_required = ?
            WHERE deliverable_id = ?
        """, (new_total, d_id))

    conn.commit()
    conn.close()
    print("station_deliverable_progress database rows updated successfully.")


if __name__ == "__main__":
    update_metro_roadmap()
    update_database_deliverables()
