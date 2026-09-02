# HARNESS // Executive OS (Version 2.0)

> **"Harness exists to turn intention into execution. Long-term goals are meaningless if they never influence today's actions."**

Harness is an executive desktop OS designed for **Heitor** (16, Liceum Class 3 in Poland). It bridges your long-term ambitions—entering **TUM Campus Heilbronn (B.Sc. Management and Data Science)**, scoring 90%+ on Rozszerzona Matura (Maths, Computer Science, Bilingual English), climbing the German ladder ($A2 \to B1 \to B2$), winning the **SIGG 2025/2026 GPW contest**, building to 80kg mass, and gaining 100% code independence—directly into daily, frictionless execution.

---

## 6 Core Layers

```
┌─────────────────────────────────────────────────────────────┐
│                       HARNESS 2.0                           │
├─────────────────────────────────────────────────────────────┤
│ 0. DASHBOARD  │ GitHub-style daily execution heatmap,       │
│ (Home Page)   │ upcoming 7-day schedule forecast & pulse.   │
├───────────────┼─────────────────────────────────────────────┤
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

### Layer 0: DASHBOARD (Home Page & Execution Pulse)
- **GitHub Contribution Heatmap**: Full 52-week activity matrix compiling tasks checked, routine blocks completed, boxing/gym workouts logged, body metrics recorded, and evening audits. Glowing brightness levels (0 to 4) visualize daily consistency and track execution streaks without guilt.
- **Upcoming 7-Day Schedule Forecast**: Immediate forward visibility into tomorrow and the entire week. Displays Schedule A (Boxing cutoff 17:15), Schedule B (TUM 2h Sprint + Gym), Schedule C (Saturday 5k + 2h Exam paper / Sunday CNS Reset), and embedded gym workout protocols.
- **Tri-Pillar Command Center**: At-a-glance KPI widgets spanning TUM Heilbronn (current station + next action, GPA, German stage), Body (weight bar to 80kg, weekly session counts), and Active Projects.


### Layer 1: TODAY (Zero-Friction Automated Execution)
- **Executive Palette**: High-contrast, solid monochrome Obsidian Black (`#08090a`), Clean White (`#fafafa`), and solid Electric/Royal Purple (`#9333ea`) accents with zero noisy neon gradients.
- **Interactive Mini-Calendar**: Click any date in the calendar to inspect that exact day's routines, completed tasks, and reflection logs. Instant 1-click jump back to "Today".
- **TM1 School Timetable Bridge**: Live parser for Technikum Mechatroniczne nr 1 / LXXX LO (Optivum 3lb) pulling daily lesson numbers, subjects, teachers, and rooms directly into the daily execution ledger.
- **Homework & Exam Radar**: Track daily homework due dates with priority tags and upcoming sprawdziany/kartkówki with real-time countdown days.
- **Quick Links Hub**: 1-click launchpad for essential portals (TM1, Vulcan UONET+, SIGG Platform, TUM Heilbronn, CKE Matura).
- **Focus Mode & Deep Work Timer HUD**: Embedded sprint timer in the top header (`T`) with presets for **60m Math R**, **60m CS Code**, **25m Sprint**, and **50m Lift** with auto-completion log and synthesized Web Audio chime.
- **Zero Input Fatigue**: Pre-calibrated schedules automatically adapt by weekday:
  - **Mon, Wed, Fri (Schedule A)**: Boxing Days (Hard cognitive work cutoff at 17:15).
  - **Tue, Thu (Schedule B)**: TUM Deep Work Sprint (60m Math R + 60m CS raw coding + 50m lift).
  - **Saturday (Schedule C)**: 5k Recovery Run + 2h timed exam paper + afternoon free.
  - **Sunday (Schedule C)**: Full CNS Reset.
- **Embedded Workout Card**: On Tuesdays and Thursdays, the exact 6-exercise gym routine is pre-loaded with checkable sets.
- **Quick One-Off Task Bar**: Hit `N` to focus, type, and press `Enter` to add ad-hoc items.


### Layer 2: TUM METRO ROADMAP (Horizontal Draggable Subway Line)
- **Hold & Drag Timeline**: Interactive horizontal canvas spanning 24 stations from **Sep '26 ("Pure Syntax")** to **Jul '28 ("TUM Heilbronn Direct Offer")**.
- **Clickable Station Nodes**: Click any station to inspect deliverables across all streams: Academics, Code, SIGG, German, Physical, and TUM Admissions.


### Layer 3: PROJECTS (Dev Launchpad & Competition Engine)
- **1-Click Workspace Launchers**: Open any repository directly in **VS Code** (`code .`), **Terminal** (PowerShell/Windows Terminal), or **File Explorer**.
- **Live Git Status & Badges**: Branch indicator, uncommitted changes counter, and recent commit history for each project.
- **Immediate Next Actions**: Every build maintains an active milestone and an immediate next action.


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

---

## Global Shortcuts (Fluidity First)

| Key | Action |
| :--- | :--- |
| `Ctrl + K` / `Cmd + K` | Summon **Global Command Palette** (search projects, workspaces, and actions) |
| `0` / ``` ` ``` | Switch to **Dashboard** Layer (Home Page & Heatmap) |
| `1` | Switch to **Today** Layer |
| `2` | Switch to **TUM** Layer |
| `3` | Switch to **Projects** Layer |
| `4` | Switch to **Body / Life** Layer |
| `5` | Switch to **Knowledge** Layer |
| `T` | Open **Focus Deep Work Timer HUD** |
| `N` / `n` | Focus on **New Task** input |
| `R` / `r` | Trigger **Carry Over / Rollover** |
| `Esc` | Blur active input / dismiss modal |


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
