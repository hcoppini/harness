# HARNESS // Personal Execution OS

> **"Harness exists to turn intention into execution. Long-term goals are meaningless if they never influence today's actions."**

Harness is a standalone desktop execution system designed for **Heitor** (16, Liceum Class 3 in Poland). It bridges long-term objectives—entering **TUM Campus Heilbronn (B.Sc. Management and Data Science)**, scoring 90%+ on Rozszerzona Matura (Maths, Computer Science, Bilingual English), climbing the German language ladder (A2 $\to$ B1 $\to$ B2), winning the **SIGG 2025/2026 GPW contest**, building to 80kg mass, and gaining 100% code independence—directly into daily, non-negotiable execution reps.

---

## The 5 Core Layers

```
┌─────────────────────────────────────────────────────────────┐
│                           HARNESS                           │
├─────────────────────────────────────────────────────────────┤
│ 1. TODAY      │ Brutally simple: daily checks, 1 TUM action,│
│               │ rollover mechanics, sleep/wake, scratchpad. │
├───────────────┼─────────────────────────────────────────────┤
│ 2. TUM        │ Reactive roadmap: 4-semester grades (>80%), │
│               │ Matura targets, German ladder (A2 -> B2).   │
├───────────────┼─────────────────────────────────────────────┤
│ 3. PROJECTS   │ Active builds (SIGG Scanner, Harness, etc.) │
│               │ Milestones, immediate next actions.         │
├───────────────┼─────────────────────────────────────────────┤
│ 4. BODY       │ Machine maintenance: Boxing, Gym (80kg goal)│
│               │ Running, Sleep. Informs, never guilt-trips. │
├───────────────┼─────────────────────────────────────────────┤
│ 5. KNOWLEDGE  │ Intellectual ledger: unassisted algorithms, │
│               │ mental models, daily reflection audit.      │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: TODAY (Execution)
- **Zero bloat**: No 18 color-coded distraction graphs.
- **The TUM Imperative**: Exactly 1 high-leverage action tied directly to TUM every single day.
- **Rollover Mechanics**: Incomplete tasks carry over cleanly with `Rolled 1x` flags—no guilt trips, no disappearing into the void.
- **Transient Scratchpad**: Auto-saving notes area for rapid thought capture without context switching.

### Layer 2: TUM (Direction & Reactive Dependency Tree)
- **4-Semester Liceum Grade Tracker**: Tracks all subjects across Semesters 1 to 4. Automatically flags any subject dropping below 4.0 (<80%).
- **Matura Benchmarks**: Tracks target vs. actual mock percentages for Rozszerzona Matematyka (target 90%+), Informatyka (target 90%+), and Bilingual English (target 95%+).
- **German Language Ladder**: Step-by-step progression from A1 $\to$ A2 $\to$ B1 (June 2026) $\to$ B2 (Feb 2027).

### Layer 3: PROJECTS (Building & Shipping)
- Pre-seeded with your 4 active fronts:
  1. **SIGG 2025/2026** (`c:\Users\heito\Desktop\polish_stocks_day_trade-main`): Stage 1 prep, momentum filters, 1-click workspace folder launch.
  2. **Code Independence & Matura CS**: Daily deliberate practice without AI assistance.
  3. **Harness**: Self-hosted desktop hub.
  4. **Financial Agency & SME Outreach** (`c:\Users\heito\Desktop\grodt_v1`): Automated client acquisition.
- Direct **"Open Folder &rarr;"** button launches project directories in Windows File Explorer.

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
