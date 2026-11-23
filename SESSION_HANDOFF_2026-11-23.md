# Harness — Session Handoff & Operational Baseline (`2026-11-23`)

> **Branch**: `main` (canonical; local `master` retired)  
> **Leveling Baseline**: `2026-11-24` (Tuesday)  
> **Verification**: `198 passed, 0 failed` (`pytest tests/ -q`), CI guardrails green, Supabase Cloud reconciled (`42` ghost rows purged)  
> **Master Debt Ledger**: [`TECH_DEBT.md`](TECH_DEBT.md)

Use this file to resume seamlessly on **any device or AI session** without re-explaining context.

---

## 1. Ground-Truth Life & Schedule Baseline (Effective Tue Nov 24)

- **School (`3lb`)**: Live timetable refreshed from `https://planlekcji.staff.edu.pl/plany/o6.html` (effective Nov 16, 2026). **No Religia on Tuesday** (school ends `14:15` Mon/Tue/Thu/Fri, `15:05` Wed).
- **Two New Online Math Classes (1h each, online, at home)**:
  - **Monday `15:00 – 16:00`**: Online Matura Math Class #1 (Home, protected `type="class"`) — direct commute home from `14:15` school, meal/prep `16:00–17:15`, **Boxing `17:20` untouched**.
  - **Tuesday `19:00 – 20:00`**: Online Math Class #2 (Home, protected `type="class"`).
- **Weekly Math Homework Commitment (`40 exercises/week` = 20 Mon + 20 Tue)** split across `Tue–Sat` in `data/schedules.json`:
  - **Tue `18:15 – 18:55`**: 5 exercises
  - **Wed `15:15 – 16:15`**: 8 exercises
  - **Thu `14:30 – 16:00`**: 9 exercises
  - **Fri `14:30 – 16:00`**: 9 exercises
  - **Sat `11:00 – 12:30`**: 9 exercises → **40/40 closed before Monday**
- **Training Cadence (4x/wk)**:
  - **Boxing (2x)**: Mon `17:20`, Wed `17:20`
  - **Gym (2x)**: Tue `15:30 – 16:40` (Day 1: Posterior Chain), Thu `17:45 – 18:45` (Day 2: Unilateral & Pull)
  - **Optional Run**: Sat `09:30 – 10:15` | **Full Rest**: Sun
- **Grades Policy**: All **32** existing Semester 1 grades in `tum_grade_entries` / `tum_grades` are **locked as fixed baseline** (no retroactive grade chasing).
- **Upcoming Exams (Clean Slate)**:
  1. `2026-11-24` — **Język niemiecki**: Sprawdzian: Kapitel 1
  2. `2026-11-27` — **Matematyka**: Sprawdzian: trygonometria
  3. `2026-12-11` — **Geografia**: Praca klasowa — Geografia fizyczna Polski *(moved from Dec 4; old `id=1009` deleted)*
- **Active Station (`nov-2026`, Nov 24–30 — 7-Day Clean Slate)**:
  - `nov2026_acad`: `0 / 40 exercises` (Week 1 Math Homework + Tue Niemiecki & Fri Trygonometria defense)
  - `nov2026_phys`: `0 / 7 days` (140g protein floor + Tue/Thu Gym resumption + Wed Boxing)
  - Pace velocity anchored to `baseline_date = 2026-11-24` (`0.0` deficit / `Optimal` starting tomorrow).
- **School Material Deficit Ledger (`material_deficit` table — 7 finite concept units)**:
  - `[P1 | active]` **Matematyka**: Trygonometria — wzory redukcyjne, miara łukowa, tożsamości i równania *(exam Nov 27)*
  - `[P1 | open]` **Matematyka**: Geometria płaska — okręgi i koła (okrąg wpisany i opisany)
  - `[P1 | open]` **Matematyka**: Tożsamości trygonometryczne — przekształcenia i dowody
  - `[P2 | open]` **Informatyka**: C++ Podstawy i instrukcje iteracyjne (pętle `for`/`while`, ręczne śledzenie)
  - `[P2 | open]` **Informatyka**: Funkcje w C++, algorytm Euklidesa (NWD/NWW) i zadania tekstowe
  - `[P3 | open]` **Fizyka**: Termodynamika — bilans cieplny i przemiany fazowe
  - `[P3 | open]` **Fizyka**: Elektrostatyka — prawo Coulomba, pole elektryczne i potencjał

---

## 2. Engineering Changes Shipped Today

| Area | What Changed | Key Files |
| :--- | :--- | :--- |
| **Single UI Tree** | Deleted duplicated `ui/` (32 files, 1.2 MB), dead `js/web_bridge.js`, and deprecated Expo `client/`. Unified Desktop + Web PWA onto canonical root assets. | `server.py`, `main.py`, `build.bat` |
| **Security Hardening** | Locked `/data/*` & `/mobile/data/*` behind strict `PUBLIC_DATA_FILES` allowlist (blocks `.db` & `*config*.json` with `403`); added `X-Harness-Key` / Bearer auth (`HARNESS_API_KEY`); blocked desktop OS RPCs in headless/Vercel mode; shipped Supabase RLS migration. | `server.py`, `supabase/harden_rls.sql` |
| **Self-Leveling Engine** | Built reusable `rebase_to_today()`, baseline-aware `get_station_pace_velocity()`, Material Deficit CRUD (`material_deficit` table), protected `class` blocks, dynamic `travel_windows` lookup, and `/api/leveling/*` routes. | `app/services/leveling_service.py`, `app/db.py`, `app/api.py`, `engine/kill_list_controller.py`, `engine/workload_governor.py` |
| **Cloud Sync & Ghost Fix** | Stopped `sync_all()` from resurrecting purged `'Cross-sync test'` rows, expired homework, deleted exams, or old `nov-2026` deliverables; purged 42 ghost rows from Supabase Cloud; synced all 4 `travel_windows`; moved write sync to debounced background thread. | `app/services/sync_service.py`, `app/services/leveling_service.py`, `server.py` |
| **Vulcan & Timetable** | Canonical Unicode-safe deduplication on Vulcan exams/homework; automatic 7-day staleness refresh on `school_timetable.json`; removed duplicate `toggle_station_sidequest`. | `app/services/vulcan_service.py`, `app/services/school_service.py`, `app/services/tum_service.py` |
| **Observability & CI** | Added centralized structured logging + `/api/health/diagnostics` endpoint; added GitHub Actions CI (`pytest` + AST duplicate-def + JSON + single-tree guardrails); added 8 new security/leveling tests (`198/198` passing). | `app/diagnostics.py`, `.github/workflows/ci.yml`, `tests/test_security_and_routes.py`, `tests/test_leveling_and_schedule.py` |

---

## 3. Exact Next Steps (Pick Up From Any Device)

### Immediate Manual Cloud Steps (5 mins in Supabase SQL Editor)
1. Run `supabase/create_remaining_tables.sql` to create the 6 missing cloud tables currently returning HTTP 404 (`tasks`, `daily_logs`, `metro_stations`, `body_metrics`, `workouts`, `projects` — `TD-18`).
2. Run `supabase/harden_rls.sql` and set `HARNESS_API_KEY` on hosted server env vars (`TD-04`).

### Next Engineering Sprints (Ordered by Leverage — Full Details in `TECH_DEBT.md`)
1. **Execute for 1–2 weeks first**: Live in the Nov 24 baseline daily (check boxes, hit 40/40 math exercises, attend Tue/Thu Gym & Mon/Wed Boxing) before doing any major UI rewrite so the redesign serves real usage.
2. **Sprint A — API & Bridge Cleanup (`TD-13`, `TD-10`)**:
   - Slim 2,868-line `js/api_bridge.js` into a thin `/api/rpc/*` client + read-only offline cache.
   - Sweep remaining legacy `except Exception: pass` blocks in `gcalendar_service.py`, `sync_service.py`, `kill_list_controller.py`, and `vulcan_service.py` into `app.diagnostics.record_error()`.
3. **Sprint B — Structural UI Redesign (`TD-19`)**:
   - Replace the monolithic 123 KB `index.html` + 135 KB `css/app.css` + 18 modals with a stripped-down, execution-first interface built around the real daily loop:
     - **Daily Execution**: Routine checkboxes + live `X/40` Weekly Math Homework tracker + Protected Online Class pills
     - **Academic Defense & Deficit**: Upcoming exams + interactive **Material Deficit Ledger** (currently backend/API-ready, needs UI panel)
     - **System Health & 1-Click Rebase**: Surface `/api/health/diagnostics` + 1-click "Level Baseline" button
   - Automate static asset cache-busting instead of manual `?v=7.0` edits.
4. **Sprint C — Backend Modularization (`TD-15`)**:
   - Split `sync_service.py` (2,774L), `workload_governor.py` (2,305L), and `gcalendar_service.py` (2,043L) into focused submodules.

---

## 4. Quick Start Commands on Any Device

```bash
git checkout main && git pull
pytest tests/ -q                      # Verify 198/198 passing
python server.py                      # Web/PWA server on http://localhost:5000
python main.py                        # Native Desktop window (PyWebView)
curl http://localhost:5000/api/health/diagnostics
```
