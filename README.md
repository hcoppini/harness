# HARNESS // Executive OS (Version 2.0)

> **"Harness exists to turn intention into execution. Long-term goals are meaningless if they never influence today's actions."**

Harness is an executive desktop OS designed for **Heitor** (16, Liceum Class 3 in Poland). It bridges your long-term ambitions—entering **TUM Campus Heilbronn (B.Sc. Management and Data Science)**, scoring 90%+ on Rozszerzona Matura (Maths, Computer Science, Bilingual English), climbing the German ladder ($A2 \to B1 \to B2$), winning the **SIGG 2025/2026 GPW contest**, building to 80kg mass, and gaining 100% code independence—directly into daily, frictionless execution.

---

## 5 Core Layers

```
┌─────────────────────────────────────────────────────────────┐
│                       HARNESS 2.0                           │
├─────────────────────────────────────────────────────────────┤
│ 1. TODAY      │ Automated day routines (Sched A/B/C),       │
│               │ embedded gym protocols, zero input fatigue. │
├───────────────┼─────────────────────────────────────────────┤
│ 2. TUM METRO  │ Horizontal draggable subway timeline        │
│               │ (24 stations: Sep '26 -> Jul '28 direct).   │
├───────────────┼─────────────────────────────────────────────┤
│ 3. PROJECTS   │ Active builds (SIGG Scanner, Harness, etc.) │
│               │ Milestones, immediate next actions.         │
├───────────────┼─────────────────────────────────────────────┤
│ 4. BODY       │ Machine maintenance: Boxing, Gym (80kg goal)│
│               │ Running, Sleep. Informs, never guilt-trips. │
├───────────────┼─────────────────────────────────────────────┤
│ 5. KNOWLEDGE  │ Intellectual ledger: unassisted algorithms, │
│               │ daily reflection audit, and JSON data hub.  │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: TODAY (Zero-Friction Automated Execution)
- **Zero Input Fatigue**: You don't type out 10 tasks each morning. The app detects the day of the week and loads your pre-calibrated schedule:
  - **Mon, Wed, Fri (Schedule A)**: Boxing Days (Hard cognitive work cutoff at 17:15).
  - **Tue, Thu (Schedule B)**: TUM Deep Work Sprint (60m Math R + 60m CS raw coding + 50m lift).
  - **Saturday (Schedule C)**: 5k Recovery Run + 2h timed exam paper + afternoon free.
  - **Sunday (Schedule C)**: Full CNS Reset.
- **Embedded Workout Card**: On Tuesdays and Thursdays, the exact 6-exercise gym routine is pre-loaded with checkable sets.
- **Quick One-Off Task Bar**: Hit `N` to focus, type, and press `Enter` to add ad-hoc items.

### Layer 2: TUM METRO ROADMAP (Horizontal Draggable Subway Line)
- **Hold & Drag Timeline**: Interactive horizontal canvas spanning 24 stations from **Sep '26 ("Pure Syntax")** to **Jul '28 ("TUM Heilbronn Direct Offer")**.
- **Clickable Station Nodes**: Click any station to inspect deliverables across all streams: Academics, Code, SIGG, German, Physical, and TUM Admissions.

### Layer 4: BODY / LIFE (Structured Gym Protocols)
- **Tuesday**: *Posterior Chain & Horizontal Power* (Trap Bar Deadlift, Neutral DB Bench, DB Rows, RDL, Face Pulls, Leg Raises).
- **Thursday**: *Unilateral Balance & Vertical Pull* (Bulgarian Split Squats, Pull-Ups, Incline Press, Single-Arm Row, Lateral Raises, Pallof Press).
- **Mass Goal**: Linear progress gauge from 68.0 kg to 80.0 kg.

### Layer 5: KNOWLEDGE & STANDARDIZED JSON HUB
- Standardized second-brain data models in `data/`:
  - `schedules.json`: Routines A, B, and C.
  - `gym_routines.json`: Workout protocols.
  - `metro_roadmap.json`: The 24-station 2-year timeline.
- Accessible via the **JSON Hub** button in the header.

### Layer 4: BODY / LIFE (Machine Maintenance)
- **Hypertrophy Progress**: Visual progress bar tracking transition from 68.0 kg (17% BF) $\to$ 80.0 kg (11–13% BF).
- **Weekly Discipline Counts**:
  - Boxing: 2–3 sessions/week target
  - Gym: 3–4 hypertrophy sessions/week target
  - Running: 1–2 sessions/week (5k PB 4:45 pace)
- **Daily Weigh-in & Nutrition**: Log morning weight, calorie surplus adherence, and 150–160g protein target.

### Layer 5: KNOWLEDGE / LOG (Memory & Deep Intellect)
- **First-Principles Algorithm Ledger**: Deconstruct algorithm mechanics in plain English before typing code. Includes the *4-Step Independence Protocol*.
- **Tactical Playbooks**: Built-in summaries of SIGG 24 contest rules and TUM admission criteria.
- **Evening Reflection Audit**: 3 brutal daily questions:
  1. *What worked today?*
  2. *Where did I slip / lose focus?*
  3. *What single adjustment will I make tomorrow?*

---

## Keyboard Shortcuts (Fluidity First)

| Key | Action |
| :--- | :--- |
| `1` | Switch to **Today** Layer |
| `2` | Switch to **TUM** Layer |
| `3` | Switch to **Projects** Layer |
| `4` | Switch to **Body / Life** Layer |
| `5` | Switch to **Knowledge** Layer |
| `N` / `n` | Focus on **New Task** input |
| `R` / `r` | Trigger **Carry Over / Rollover** |
| `Esc` | Blur active input / clear focus |

---

## How to Run & Develop

### 1. Instant Launch
Double click `run.bat` or run:
```powershell
python main.py
```

### 2. Run Test Suite
```powershell
python -m pytest tests/ -v
```

### 3. Build Standalone Executable
Double click `build.bat` or run:
```powershell
python -m PyInstaller --name "Harness" --windowed --noconsole --add-data "ui;ui" --clean -y main.py
```
The resulting `Harness.exe` will be generated inside `dist/Harness/Harness.exe`. You can right-click it and create a desktop shortcut.

---

## Database & Data Durability
All data is stored locally in `data/harness.db` (SQLite in WAL mode). Zero cloud dependencies, 100% offline, private, and durable.
