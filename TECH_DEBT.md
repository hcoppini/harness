# Harness — Master Technical & Operational Debt Ledger

> **Established**: 2026-11-23 (Leveling Baseline: `2026-11-24`, Branch: `main`)  
> **Objective**: Turn Harness from a high-spec MVP into a self-healing, single-source-of-truth, production-ready Personal Execution OS that stays operational without recurring post-damage repairs.

---

## Status Legend
- `[ ]` Open / Tracked
- `[~]` Partially Resolved / Action Remaining
- `[x]` Resolved & Verified

---

## P0 — Security, Data Integrity & Single-Source-of-Truth (Critical)

- [x] **`TD-01` Git Branch Split-Brain (`master` vs `origin/main`)**
  - **Resolved**: Unified local workspace onto `main` tracking `origin/main` (`a61318b`) and removed stale local `master`.

- [x] **`TD-02` Public Exposure of `/data/<path:filename>` in `server.py`**
  - **Resolved**: Locked `/data/` and `/mobile/data/` in `server.py` behind strict `PUBLIC_DATA_FILES` allowlist; `.db`, `*config*.json`, `.log`, and traversal paths return `403`. Verified in `tests/test_security_and_routes.py`.

- [x] **`TD-03` Unauthenticated `/api/rpc/<method>` + Wildcard CORS + Remote OS Execution**
  - **Resolved**: Added `X-Harness-Key` / `Bearer` auth middleware (`HARNESS_API_KEY`), configurable `HARNESS_ALLOWED_ORIGINS` CORS, and `DESKTOP_ONLY_RPC_METHODS` `403` guard in headless/Vercel mode. Verified in `tests/test_security_and_routes.py`.

- [~] **`TD-04` World-Writable Supabase RLS Policies + Hardcoded Publishable Key**
  - **Progress**: Shipped [`supabase/harden_rls.sql`](supabase/harden_rls.sql) replacing `using (true)` with `authenticated`-only RLS across all 17 tables.
  - **Remaining**: Execute `supabase/harden_rls.sql` in Supabase SQL Editor and switch hosted deployments to `HARNESS_API_KEY` + server-side `SUPABASE_SERVICE_ROLE_KEY` (removing hardcoded `sb_publishable_*` fallback in `js/api_bridge.js`).

- [x] **`TD-05` Duplicated Frontend & Data Tree (`root` vs `ui/`, 32 files / 1.2 MB)**
  - **Resolved**: Removed `ui/` entirely (eliminating drifted `ui/data/metro_roadmap.json` & `ui/data/schedules.json`). Unified `server.py`, `main.py`, and `build.bat` onto the single canonical root tree. Enforced by CI & `tests/test_mobile_readiness.py`.

- [x] **`TD-06` SQLite Binary Duplication & Ghost/Junk DB State**
  - **Resolved**: Removed `ui/data/harness.db`, executed clean Nov 24 Final Leveling (32 grade entries verified 100% untouched, closed past station deliverables, removed 3 `'Cross-sync test'` rows, pruned expired homework, removed moved Geografia `1009` & duplicate Pogoda `1016`, seeded 7-unit Material Deficit ledger).

---

## P1 — Operational Self-Healing & Resilience ("Never Repair After Damages")

- [x] **`TD-07` Punitive Linear Pace Velocity (No Rebase Anchor)**
  - **Resolved**: Implemented `app/services/leveling_service.py` + baseline-aware `kill_list_controller.get_station_pace_velocity()` + `HarnessAPI.rebase_to_today()` + `/api/leveling/rebase`. Verified `0.0` deficit on baseline day (`2026-11-24`) and preserved `station_baselines` across `set_operating_mode()`.

- [x] **`TD-08` Hardcoded Dates & Local User Paths**
  - **Resolved (Core Engine)**: `workload_governor.is_us_travel_date()` now queries `get_travel_windows()` dynamically instead of hardcoded dates; weekly math classes & 40-exercise splits live in `data/schedules.json` (`weekly_commitments`); `class`/`protected` blocks are never overwritten by governor.
  - **Follow-up**: Clean remaining legacy hardcoded `c:\Users` placeholder examples in `index.html`, `project_service.py`, and `generate_app_icons.py`.

- [x] **`TD-09` Blocking Synchronous `sync_all()` on Every Write RPC**
  - **Resolved**: Replaced blocking inline `sync_service.sync_all()` in `server.py` write RPCs with 1.5s debounced background daemon thread `_schedule_background_sync()` + telemetry tracking.

- [~] **`TD-10` Silent `except Exception: pass` Blocks Across Backend**
  - **Progress**: Added centralized structured logging + bounded error ring buffer in `app/diagnostics.py` and wired into `server.py`, `main.py`, `school_service.py`, and `leveling_service.py`.
  - **Remaining**: Sweep remaining legacy `except Exception: pass` blocks in `gcalendar_service.py` (11), `kill_list_controller.py` (11), `sync_service.py` (14), and `vulcan_service.py` (9) to call `record_error()`.

- [x] **`TD-11` Vulcan Exam/Homework Duplication & Stale School Timetable**
  - **Resolved**: Upgraded `vulcan_service.py` to canonical Unicode-safe deduplication (`re.sub(r"[^\w]+", "", ...)`) on exam & homework ingest; upgraded `school_service.py` with 7-day automatic staleness refresh (`_is_cached_plan_stale`) + refreshed live `3lb` timetable from `o6.html`.

- [~] **`TD-18` Supabase Cloud Schema Drift & Ghost Resurrection (Discovered During Verification)**
  - **Resolved (Ghost Resurrection)**: Fixed `sync_service.py` (`sync_kill_list_items`, `sync_homework_items`, `sync_station_deliverable_progress`) + `leveling_service.rebase_to_today(sync_cloud=True)` so deleted/expired/rebased items are purged on Supabase (42 cloud ghosts deleted) and never resurrect on `sync_all()`.
  - **Remaining (Supabase Schema)**: Live Supabase project returns HTTP 404 (`PGRST205`) for 6 tables (`tasks`, `daily_logs`, `metro_stations`, `body_metrics`, `workouts`, `projects`). Apply `supabase/create_remaining_tables.sql` + `supabase/harden_rls.sql` in Supabase SQL Editor.

---

## P2 — Architecture, Code Hygiene & Maintainability

- [x] **`TD-12` Duplicate Function Definition & Dead Files**
  - **Resolved**: Removed duplicate `def toggle_station_sidequest` in `app/services/tum_service.py`, deleted unused `js/web_bridge.js` and `ui/components/*.js`, and added AST duplicate-def check to CI.

- [ ] **`TD-13` Triple API Surface Drift (`api.py` vs `server.py` vs 2,868-line `js/api_bridge.js`)**
  - **Scope**: Standardize web calls on `/api/rpc/<method>` matching `HarnessAPI` 1:1 and slim `js/api_bridge.js` (2,868 lines) into a thin RPC transport + read-only offline cache.

- [x] **`TD-14` Diverged Expo React Native Client (`client/`)**
  - **Resolved**: Removed `client/` (1,697-line stale `App.tsx` + 548 KB `package-lock.json`); confirmed Desktop + Mobile PWA only. Enforced by CI & `tests/test_mobile_readiness.py`.

- [ ] **`TD-15` Monolithic God-Files & Manual Cache-Busting**
  - **Scope**: Incrementally split `sync_service.py` (2,774L), `workload_governor.py` (2,305L), `gcalendar_service.py` (2,043L), `js/today.js` (135 KB), and `css/app.css` (135 KB) into cohesive submodules; automate `?v=` asset version stamping across `index.html` and `sw.js`.

- [ ] **`TD-19` Structural UI Simplification & Frontend Consolidation (Post-Usage)**
  - **Root cause**: Despite visual refreshes up to v7.0, the frontend remains a monolithic 123 KB `index.html` + 135 KB `css/app.css` + 135 KB `js/today.js` with 8 views and 18+ modals, while lacking native UI panels for the new Material Deficit Ledger, Weekly 40-Exercise Math counter, 1-Click Rebase button, and System Diagnostics.
  - **Scope**: After 1–2 weeks of real daily execution on the leveled Nov 24 baseline (so redesign follows actual daily usage rather than aesthetics), simplify the UI architecture around the core daily loop (Today checklist + 40-ex Math tracker + Material Deficit + Exam Horizon + Health/Rebase), remove unused modals/views, and modularize CSS/JS alongside `TD-13`.

---

## P3 — Automated CI & Operational Observability

- [x] **`TD-16` Automated Test CI Workflow**
  - **Resolved**: Added [`.github/workflows/ci.yml`](.github/workflows/ci.yml) running static guardrails (no `ui/`/`client/`, valid JSON schemas, no duplicate Python top-level defs) + full `pytest tests/` on push/PR to `main`.

- [x] **`TD-17` Unified System Diagnostics Endpoint (`/api/health/diagnostics`)**
  - **Resolved**: Added `app/diagnostics.py`, `HarnessAPI.get_system_diagnostics()`, and `GET /api/health/diagnostics` reporting SQLite integrity/counts, timetable staleness, operating mode/baselines, open material deficit count, background sync telemetry, and recent logged errors.
