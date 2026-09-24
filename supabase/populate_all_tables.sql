-- ==========================================================================
-- HARNESS // Executive OS - Supabase Database Population Script
-- Generated: 2026-09-24T20:52:28.586733
-- Run this in Supabase Dashboard -> SQL Editor -> New Query -> Run
-- ==========================================================================

-- 1. TUM Curriculum Target & Actual Grades
INSERT INTO public.tum_grades (id, subject, semester, target_grade, actual_grade, percentage, notes)
VALUES
  (1, 'Matematyka', 1, 6.0, NULL, NULL, ''),
  (2, 'Informatyka', 1, 6.0, 3.0, NULL, ''),
  (3, 'Język Angielski', 1, 5.5, 5.0, NULL, ''),
  (4, 'Język Polski', 1, 4.5, NULL, NULL, ''),
  (5, 'Fizyka', 1, 4.5, NULL, NULL, ''),
  (6, 'Historia', 1, 4.0, 4.0, NULL, ''),
  (7, 'Geografia', 1, 4.0, NULL, NULL, ''),
  (8, 'Biologia / Chemia', 1, 4.0, NULL, NULL, ''),
  (9, 'Język Niemiecki', 1, 5.0, NULL, NULL, ''),
  (10, 'Matematyka', 2, 6.0, NULL, NULL, ''),
  (11, 'Informatyka', 2, 6.0, NULL, NULL, ''),
  (12, 'Język Angielski', 2, 5.5, NULL, NULL, ''),
  (13, 'Język Polski', 2, 4.5, NULL, NULL, ''),
  (14, 'Fizyka', 2, 4.5, NULL, NULL, ''),
  (15, 'Historia', 2, 4.0, NULL, NULL, ''),
  (16, 'Geografia', 2, 4.0, NULL, NULL, ''),
  (17, 'Biologia / Chemia', 2, 4.0, NULL, NULL, ''),
  (18, 'Język Niemiecki', 2, 5.0, NULL, NULL, ''),
  (19, 'Matematyka', 3, 6.0, NULL, NULL, ''),
  (20, 'Informatyka', 3, 6.0, NULL, NULL, ''),
  (21, 'Język Angielski', 3, 5.5, NULL, NULL, ''),
  (22, 'Język Polski', 3, 4.5, NULL, NULL, ''),
  (23, 'Fizyka', 3, 4.5, NULL, NULL, ''),
  (24, 'Historia', 3, 4.0, NULL, NULL, ''),
  (25, 'Geografia', 3, 4.0, NULL, NULL, ''),
  (26, 'Biologia / Chemia', 3, 4.0, NULL, NULL, ''),
  (27, 'Język Niemiecki', 3, 5.0, NULL, NULL, ''),
  (28, 'Matematyka', 4, 6.0, NULL, NULL, ''),
  (29, 'Informatyka', 4, 6.0, NULL, NULL, ''),
  (30, 'Język Angielski', 4, 5.5, NULL, NULL, ''),
  (31, 'Język Polski', 4, 4.5, NULL, NULL, ''),
  (32, 'Fizyka', 4, 4.5, NULL, NULL, ''),
  (33, 'Historia', 4, 4.0, NULL, NULL, ''),
  (34, 'Geografia', 4, 4.0, NULL, NULL, ''),
  (35, 'Biologia / Chemia', 4, 4.0, NULL, NULL, ''),
  (36, 'Język Niemiecki', 4, 5.0, NULL, NULL, '')
ON CONFLICT (id) DO UPDATE SET
  subject = EXCLUDED.subject, semester = EXCLUDED.semester, target_grade = EXCLUDED.target_grade, actual_grade = EXCLUDED.actual_grade, percentage = EXCLUDED.percentage, notes = EXCLUDED.notes;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.tum_grades', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.tum_grades', 'id'), COALESCE(MAX(id), 1)) FROM public.tum_grades;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 2. TUM Grade Ledger Entries (Clean Vulcan & Manual Grades)
INSERT INTO public.tum_grade_entries (id, subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average, created_at)
VALUES
  (1, 'Historia', 1, '+', NULL, 1.0, 'Aktywność', '', '2026-09-10', FALSE, '2026-09-10 04:56:13'),
  (4, 'Historia', 1, '+', NULL, 0.0, 'Bieżące', 'Praca na lekcji', '2026-09-03', FALSE, '2026-09-13 20:48:50'),
  (5, 'Historia', 1, '4', 4.0, 1.0, 'Bieżące', 'Kartkówka 1  - bitwy Powstania listopadowego.', '2026-09-10', TRUE, '2026-09-13 20:48:50'),
  (6, 'Informatyka', 1, '14', NULL, 0.0, 'Aktywność', 'Stanowisko komputerowe', '2026-09-04', FALSE, '2026-09-13 20:48:50'),
  (7, 'Język angielski', 1, '14.0/15.0', 5.0, 1.0, 'Bieżące', 'Matura - listening', '2026-09-15', TRUE, '2026-09-15 15:23:32'),
  (8, 'Język angielski', 1, '17.0/18.0', 5.0, 1.0, 'Bieżące', 'Matura - reading', '2026-09-15', TRUE, '2026-09-15 15:23:32'),
  (9, 'Język angielski', 1, '11.0/14.0', 4.0, 1.0, 'Bieżące', 'Matura - use of English', '2026-09-15', TRUE, '2026-09-15 15:23:32'),
  (12, 'Matematyka', 1, 'NP (21.09)', NULL, 0.0, 'Nieprzygotowanie', 'nieprzygotowanie', '2026-09-21', FALSE, '2026-09-21 20:06:41'),
  (13, 'Język angielski', 1, '10.0/10.0', 6.0, 1.0, 'Bieżące', 'Wypowiedź ustna', '2026-09-24', TRUE, '2026-09-24 18:18:03'),
  (14, 'Historia', 1, '+', NULL, 0.0, 'Bieżące', 'zadanie dodatkowe', '2026-09-23', FALSE, '2026-09-24 18:18:03'),
  (15, 'Informatyka', 1, '3', 3.0, 1.0, 'Bieżące', 'Podstawy programowania w c++', '2026-09-23', TRUE, '2026-09-24 18:18:03')
ON CONFLICT (id) DO UPDATE SET
  subject = EXCLUDED.subject, semester = EXCLUDED.semester, raw_input = EXCLUDED.raw_input, numeric_value = EXCLUDED.numeric_value, weight = EXCLUDED.weight, category = EXCLUDED.category, description = EXCLUDED.description, date = EXCLUDED.date, counts_in_average = EXCLUDED.counts_in_average;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.tum_grade_entries', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.tum_grade_entries', 'id'), COALESCE(MAX(id), 1)) FROM public.tum_grade_entries;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 3. TUM Matura Benchmarks
INSERT INTO public.tum_matura (id, subject, target_percentage, current_mock_percentage, notes)
VALUES
  (1, 'Matematyka Rozszerzona', 90.0, 0.0, 'Przedmiot kluczowy na TUM'),
  (2, 'Informatyka Rozszerzona', 90.0, 0.0, 'Algorytmika, Python/C++, CKE arkusze'),
  (3, 'Język Angielski Dwujęzyczny / R', 95.0, 0.0, 'Język wykładowy TUM Heilbronn'),
  (4, 'Matematyka Podstawowa', 100.0, 0.0, 'Fundament punktowy'),
  (5, 'Język Polski Podstawowy', 75.0, 0.0, 'Wymóg zdawalności')
ON CONFLICT (subject) DO UPDATE SET
  target_percentage = EXCLUDED.target_percentage, current_mock_percentage = EXCLUDED.current_mock_percentage, notes = EXCLUDED.notes;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.tum_matura', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.tum_matura', 'id'), COALESCE(MAX(id), 1)) FROM public.tum_matura;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 4. TUM German Language Roadmap
INSERT INTO public.tum_language (id, level, target_date, status, milestone_description)
VALUES
  (1, 'A1', '2025-06-01', 'completed', 'Podstawy gramatyki, czasowniki regularne/nieregularne'),
  (2, 'A2', '2025-11-01', 'in_progress', 'Konwersacje codzienne, czas przeszły Perfekt/Präteritum'),
  (3, 'B1', '2026-06-01', 'pending', 'Certyfikat Goethe B1: czytanie artykułów, pisanie maili'),
  (4, 'B2', '2027-02-01', 'pending', 'Goethe B2 / TestDaF: niemiecki akademicki i biznesowy')
ON CONFLICT (level) DO UPDATE SET
  target_date = EXCLUDED.target_date, status = EXCLUDED.status, milestone_description = EXCLUDED.milestone_description;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.tum_language', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.tum_language', 'id'), COALESCE(MAX(id), 1)) FROM public.tum_language;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 5. School Exams (Live Vulcan & Manual Tests)
INSERT INTO public.school_exams (id, subject, title, exam_date, scope, completed, result_percentage, created_at)
VALUES
  (5, 'Geografia', 'Sprawdzian: Sprawdzian wiadomości - "Mapa fizyczna P', '2026-10-02', 'Sprawdzian wiadomości - "Mapa fizyczna Polski."', FALSE, NULL, '2026-09-13 20:48:50'),
  (6, 'Język polski', 'Sprawdzian: Rozprawka (romantyzm) - wstęp, teza, arg', '2026-10-06', 'Rozprawka (romantyzm) - wstęp, teza, argument, przykład, kontekst.', FALSE, NULL, '2026-09-13 20:48:50'),
  (7, 'Informatyka', 'Sprawdzian: Podstawy programowania - pojęcia (algory', '2026-09-21', 'Podstawy programowania - pojęcia (algorytm, sposoby przedstawiania algorytmu, języki programowania, środowisko programistyczne, kompilacja, interpretacja, kod źródłowy), język c++ - struktura programu, cout, cin , instrukcja if', FALSE, NULL, '2026-09-14 15:08:01'),
  (13, 'Chemia', 'Kartkówka: Alkany - szereg homologiczny, izomeria,', '2026-09-29', 'Alkany - szereg homologiczny, izomeria, reakcje spalania.', FALSE, NULL, '2026-09-21 20:06:41'),
  (14, 'Matematyka', 'Sprawdzian: Okręgi i koła rozdz. 4', '2026-10-07', 'Okręgi i koła rozdz. 4', FALSE, NULL, '2026-09-24 18:18:03'),
  (15, 'Fizyka', 'Sprawdzian: Termodynamika', '2026-10-05', 'Termodynamika', FALSE, NULL, '2026-09-24 18:18:03'),
  (16, 'Fizyka', 'Sprawdzian: Termodynamika', '2026-10-01', 'Termodynamika', FALSE, NULL, '2026-09-24 18:18:03')
ON CONFLICT (id) DO UPDATE SET
  subject = EXCLUDED.subject, title = EXCLUDED.title, exam_date = EXCLUDED.exam_date, scope = EXCLUDED.scope, completed = EXCLUDED.completed, result_percentage = EXCLUDED.result_percentage;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.school_exams', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.school_exams', 'id'), COALESCE(MAX(id), 1)) FROM public.school_exams;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 6. Homework Deliverables (Live Vulcan & Manual Homework)
INSERT INTO public.homework_items (id, subject, title, due_date, completed, source, priority, notes, created_at)
VALUES
  (9, 'Język polski', 'Proszę o przeczytanie ,,Lalki" Bolesława Prusa', '2026-10-09', FALSE, 'vulcan', 1, 'Proszę o przeczytanie ,,Lalki" Bolesława Prusa', '2026-09-13 20:48:50'),
  (26, 'Matematyka', '4.114
4.117', '2026-09-24', FALSE, 'vulcan', 1, '4.114
4.117', '2026-09-24 18:18:03'),
  (27, 'Matematyka', '4.125
4.126', '2026-09-25', FALSE, 'vulcan', 1, '4.125
4.126', '2026-09-24 18:18:03')
ON CONFLICT (id) DO UPDATE SET
  subject = EXCLUDED.subject, title = EXCLUDED.title, due_date = EXCLUDED.due_date, completed = EXCLUDED.completed, source = EXCLUDED.source, priority = EXCLUDED.priority, notes = EXCLUDED.notes;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.homework_items', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.homework_items', 'id'), COALESCE(MAX(id), 1)) FROM public.homework_items;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 7. SGH Library Kill List (Daily 3-Item Execution Engine)
INSERT INTO public.kill_list_items (id, date, category, title, action_type, target_path, target_spec, station_deliverable_id, quantity, completed, created_at)
VALUES
  ('kill_2df9f21e', '2026-09-16', 'Math R', 'Math R Diagnostic: Algebra & Functions', 'pdf', 'arkusze/matura_math_diag.pdf', 'Sets 1–5 (Zero-AI)', 'sep26_math_diag', 1, TRUE, '2026-09-04 14:23:38'),
  ('kill_951b31ff', '2026-09-15', 'Algorithms', 'LeetCode: Problem #5 (Unassisted)', 'url', 'https://leetcode.com/problemset/all/', '1 Problem Unassisted', 'sep26_leetcode_15', 1, TRUE, '2026-09-04 14:23:38'),
  ('kill_9a0940cf', '2026-09-14', 'German', 'German Vocabulary: Words 1–20', 'url', 'https://learngerman.dw.com/en/nicos-weg/c-36519789', 'Words 1–20 (Nicos Weg A2)', 'sep26_german_anki', 20, TRUE, '2026-09-15 15:24:12'),
  ('kill_334f1065', '2026-09-14', 'Algorithms', 'LeetCode: Problem #5 (Unassisted)', 'url', 'https://leetcode.com/problemset/all/', 'Problem #5 (Zero-AI, trace by hand)', 'sep26_leetcode_15', 1, TRUE, '2026-09-15 15:24:19'),
  ('kill_4232cffc', '2026-09-14', 'Math R', 'Math R Diagnostic: Zadania 1–5', 'pdf', 'https://cke.gov.pl', 'Zadania 1–5 (Zero-AI, pen & paper)', 'sep26_math_diag', 5, TRUE, '2026-09-15 15:24:36'),
  ('kill_a9a3437d', '2026-09-16', 'Math R', 'Math R Diagnostic: Zadania 11–15', 'pdf', 'https://cke.gov.pl', 'Zadania 11–15 (Zero-AI, pen & paper)', 'sep26_math_diag', 5, TRUE, '2026-09-16 15:00:09'),
  ('kill_e5cbe433', '2026-09-17', 'Physical', 'Nutrition: 140g Daily Protein Floor', 'url', 'https://www.myfitnesspal.com', 'Log 140g high-protein meals', 'sep26_phys_protein', 1, TRUE, '2026-09-17 13:50:57')
ON CONFLICT (id) DO UPDATE SET
  completed = EXCLUDED.completed, date = EXCLUDED.date, quantity = EXCLUDED.quantity;

-- 8. Station Deliverable Progress
INSERT INTO public.station_deliverable_progress (deliverable_id, station_id, stream, title, total_required, completed_count, unit_label, is_completed)
VALUES
  ('sep26_math_diag', 'sep-2026', 'academics', 'Math R Diagnostic Problem Sets', 40, 16, 'problems', FALSE),
  ('sep26_sigg_setup', 'sep-2026', 'sigg', 'Team registered & Gra Testowa access', 1, 0, 'gate', FALSE),
  ('sep26_german_anki', 'sep-2026', 'german', 'A2 Nicos Weg Vocabulary Units', 100, 20, 'words', FALSE),
  ('sep26_phys_protein', 'sep-2026', 'physical', 'Daily Protein Floor Met (140g)', 30, 16, 'days', FALSE),
  ('sep26_leetcode_15', 'sep-2026', 'code', 'LeetCode Easy/Medium without AI', 15, 6, 'exercises', FALSE)
ON CONFLICT (deliverable_id) DO UPDATE SET
  completed_count = EXCLUDED.completed_count, is_completed = EXCLUDED.is_completed;

-- 9. Daily Logs & Historical Velocity (25+ Days of Tracked Performance)
INSERT INTO public.daily_logs (date, wake_time, sleep_time, scratchpad, reflection_worked, reflection_slipped, reflection_tomorrow, completed_blocks, completed_exercises, updated_at)
VALUES
  ('2026-08-30', '', '', '', 'Locked 60m pure syntax problem solving with 0% AI', 'Phone on desk during morning math', 'Phone outside room before 16:15 deep sprint', '0,1,2', '', '2026-08-30 15:46:56'::timestamp with time zone),
  ('2026-08-31', '', '', '', '', '', '', '0,1,2,3,5,6', '', '2026-08-31 21:48:58'::timestamp with time zone),
  ('2026-09-01', '', '', '', '', '', '', '0,2,3,6,7', '', '2026-09-03 17:21:20'::timestamp with time zone),
  ('2026-09-02', '', '', '', '', '', '', '0,1,2,3,4,5,6,7', '', '2026-09-08 19:06:35'::timestamp with time zone),
  ('2026-09-03', '', '', '', '', '', '', '0,1,2,3,4,5', '0,1,2,3,4,5', '2026-09-03 19:38:19'::timestamp with time zone),
  ('2026-09-04', '07:01', '00:00', '', '', '', '', '0,1', '', '2026-09-04 13:21:34'::timestamp with time zone),
  ('2026-09-05', '', '', '', '', '', '', '2', '', '2026-09-07 18:41:05'::timestamp with time zone),
  ('2026-09-12', '06:45', '22:30', '', '', '', '', '0,1,2', '', '2026-09-01 04:55:42'::timestamp with time zone),
  ('2026-09-30', '', '', '', '', '', '', '', '', '2026-09-01 04:55:43'::timestamp with time zone),
  ('2026-09-07', '', '', '', '', '', '', '0,1,2,3,4,5', '', '2026-09-07 18:40:47'::timestamp with time zone),
  ('2026-09-11', '06:35', '23:00', '', '', '', '', '0,1,2,3,4,5,6,7', '', '2026-09-11 23:15:00'::timestamp with time zone),
  ('2026-09-06', '', '', '', '', '', '', '0,1,2', '', '2026-09-07 18:40:58'::timestamp with time zone),
  ('2026-09-13', '06:45', '22:30', '', '', '', '', '0,1,2', '', '2026-09-13 15:34:13'::timestamp with time zone),
  ('2026-09-08', '', '', '', '', '', '', '0,1,2,3,5,6,7', '', '2026-09-10 04:52:21'::timestamp with time zone),
  ('2026-09-09', '', '', '', '', '', '', '0,1,2,3,5,6,7', '', '2026-09-09 21:00:54'::timestamp with time zone),
  ('2026-09-10', '', '', '', '', '', '', '0,1,2,3,5,6,7', '0,1,2,3,4,5', '2026-09-15 16:12:14'::timestamp with time zone),
  ('2026-09-16', '', '', '', '', '', '', '0,1,2,3,4,5,6', '', '2026-09-17 13:03:28'::timestamp with time zone),
  ('2026-09-25', '06:45', '22:30', '', '', '', '', '', '', '2026-09-12 20:41:45'::timestamp with time zone),
  ('2026-09-14', '', '', '', '', '', '', '0,1,2,3,4,5,6,7', '', '2026-09-15 15:24:07'::timestamp with time zone),
  ('2026-10-02', '', '', '', '', '', '', '', '', '2026-09-13 21:00:06'::timestamp with time zone),
  ('2026-09-15', '', '', '', '', '', '', '0,1,2,3,5,6,7', '', '2026-09-15 19:14:41'::timestamp with time zone),
  ('2026-09-17', '', '', '', '', '', '', '0,1,3', '', '2026-09-17 13:50:39'::timestamp with time zone),
  ('2026-09-19', '', '', '', '', '', '', '2', '', '2026-09-19 18:34:25'::timestamp with time zone),
  ('2026-09-18', '', '', '', '', '', '', '0,1,2,3,5,6,7', '', '2026-09-19 18:34:21'::timestamp with time zone),
  ('2026-09-20', '', '', '', '', '', '', '', '', '2026-09-19 22:30:40'::timestamp with time zone)
ON CONFLICT (date) DO UPDATE SET
  wake_time = EXCLUDED.wake_time, sleep_time = EXCLUDED.sleep_time, scratchpad = EXCLUDED.scratchpad, reflection_worked = EXCLUDED.reflection_worked, reflection_slipped = EXCLUDED.reflection_slipped, reflection_tomorrow = EXCLUDED.reflection_tomorrow, completed_blocks = EXCLUDED.completed_blocks, completed_exercises = EXCLUDED.completed_exercises, updated_at = EXCLUDED.updated_at;

-- 10. Body Metrics
INSERT INTO public.body_metrics (id, date, weight_kg, calories_met, protein_met, notes)
VALUES
  (1, '2026-08-30', 68.5, TRUE, TRUE, '')
ON CONFLICT (id) DO UPDATE SET
  weight_kg = EXCLUDED.weight_kg, protein_met = EXCLUDED.protein_met, calories_met = EXCLUDED.calories_met;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.body_metrics', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.body_metrics', 'id'), COALESCE(MAX(id), 1)) FROM public.body_metrics;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 11. Workouts
INSERT INTO public.workouts (id, date, workout_type, details, intensity, created_at)
VALUES
  (1, '2026-08-30', 'boxing', '6 rounds technical sparring + bag work', 8, '2026-08-29 22:38:14'),
  (2, '2026-08-30', 'boxing', '6 rounds technical sparring + bag work', 8, '2026-08-29 22:38:36')
ON CONFLICT (id) DO UPDATE SET
  workout_type = EXCLUDED.workout_type, details = EXCLUDED.details, intensity = EXCLUDED.intensity;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.workouts', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.workouts', 'id'), COALESCE(MAX(id), 1)) FROM public.workouts;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 12. Projects
INSERT INTO public.projects (id, name, description, local_path, github_url, current_milestone, next_action, deadline, notes, status, created_at)
VALUES
  (1, 'SIGG 2025/2026 (GPW Contest)', 'Annual inter-school trading competition on Warsaw Stock Exchange. Goal: GPW Trading Floor Finals.', 'c:/Users/heito/Desktop/polish_stocks_day_trade-main', '', 'Stage 1 Prep (WIG20, mWIG40, sWIG80 momentum scanner)', 'Update Scanner', '2025-10-13 (Test Game) / 2025-11-17 (Stage 1 Start)', 'Rules: Max 1 order / 10s. No bots during live execution. Top 12 to finals. Educational module bonus = +2 PLN per point.', 'active', '2026-08-29 22:36:44'),
  (2, 'Code Independence & Matura CS', 'Break AI dependency. Develop raw algorithmic problem solving for Matura Rozszerzona & software engineering.', 'c:/Users/heito/Desktop/harness', '', 'Algorithmic thinking & raw data structures (Python / C++)', 'Deconstruct and solve 2 HackerRank exercises unassisted; write algorithm in plain English first', 'Daily Repetition', 'Crucial: Understand every line. If AI writes code, rewrite it from scratch with comments explaining memory & complexity.', 'active', '2026-08-29 22:36:44'),
  (3, 'Harness — Personal Life Hub', 'Personal desktop execution hub. 5 layers connecting daily action to TUM Heilbronn.', 'c:/Users/heito/Desktop/harness', '', 'V1 Desktop Hub Build & Testing', 'Package standalone Harness.exe and add to Windows Startup', '2026-08-29', 'Philosophy: Turn intention into execution without productivity bloat.', 'active', '2026-08-29 22:36:44'),
  (4, 'Financial Agency / Polish SME Outreach', 'Web dev and automation for Polish small businesses to hit 2,000 PLN/month financial independence.', 'c:/Users/heito/Desktop/grodt_v1', '', 'Outreach pipeline revamp', 'Audit scraped business list and refine high-converting offer script', '2,000 PLN / month target', 'Persistence over perfection. Focus on 10 high-signal calls instead of burning out on 1,000 cold leads.', 'paused', '2026-08-29 22:36:44')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, current_milestone = EXCLUDED.current_milestone, next_action = EXCLUDED.next_action, status = EXCLUDED.status;

DO $$
BEGIN
  IF pg_get_serial_sequence('public.projects', 'id') IS NOT NULL THEN
    PERFORM setval(pg_get_serial_sequence('public.projects', 'id'), COALESCE(MAX(id), 1)) FROM public.projects;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 13. Metro Stations & Milestones
INSERT INTO public.metro_stations (id, name, phase, month_label, year_month, is_major, status, objective, deliverables, completed_deliverables, order_idx)
VALUES
  ('kickoff-2026', 'Class 3 Kickoff', 'Phase 1: Year 3 Liceum', 'SEP 1', '2026-09-01', FALSE, 'completed', 'Class 3 Liceum kickoff, school timetable setup & baseline diagnostics.', '{"Academics": "Set up TM1 school timetable & semester targets.", "Code": "Harness OS activated & unassisted coding rule established.", "Physical": "Establish 68.0 kg baseline bodyweight."}'::jsonb, '["Physical", "Academics", "Code"]'::jsonb, 0),
  ('sep-2026', 'Pure Syntax', 'Phase 1: Year 3 Liceum', 'SEP ''26', '2026-09', TRUE, 'active', 'Diagnostic benchmarking & pure unassisted algorithmic habit building.', '{"Academics": "Benchmark diagnostic test in Math Rozszerzona. Target first-month grade average >= 4.75.", "Code": "Zero AI copilot rule activated. Complete 15 foundational LeetCode Easy problems writing pure algorithms by hand (4/15 solved).", "SIGG": "Team registered with teacher-guardian; test environment accounts setup.", "German": "20 min/day active input (Nicos Weg A2 module). Target: 100 new vocabulary items in Anki.", "Physical": "Weight 68.5 kg, daily protein floor at 140g."}'::jsonb, '[]'::jsonb, 1),
  ('oct-2026', 'Gra Testowa', 'Phase 1: Year 3 Liceum', 'OCT ''26', '2026-10', FALSE, 'upcoming', 'Max out educational bonus capital (+2 PLN/point) & first major school exams.', '{"Academics": "First major sprawdziany in Math & CS. Maintain grade 5.0 in both.", "Code": "Solve 20 past CKE Matura task 1s (computational thinking/math logic on paper).", "SIGG": "Gra Testowa (Oct 13 - Nov 16). Complete all individual educational e-learning modules to max out bonus multiplier.", "German": "Finish A2.1 vocabulary deck."}'::jsonb, '[]'::jsonb, 2),
  ('nov-2026', 'Stage 1 Deployment', 'Phase 1: Year 3 Liceum', 'NOV ''26', '2026-11', TRUE, 'upcoming', 'Launch real trading in Stage 1 & CKE data parsing tasks.', '{"Academics": "Mid-semester review. All subjects > 4.0, Math and CS locked at 5.0+.", "SIGG": "Stage 1 begins (Nov 17). Execute first transaction within mandatory 14 days. Focus strictly on WIG20/mWIG40 momentum setups (respect 1 order/10s throttle).", "Code": "Transition to CKE Matura programming tasks in Python/C++ (file operations, data parsing).", "Physical": "Weight 69.5 kg; 5k run pace under 4:40."}'::jsonb, '[]'::jsonb, 3),
  ('dec-2026', 'Semester 1 Lock', 'Phase 1: Year 3 Liceum', 'DEC ''26', '2026-12', TRUE, 'upcoming', 'Lock in high grades on Sem 1 transcript & audit stock scanner.', '{"Academics": "Finalize Semester 1 proposed grades. No grade below 4; Math, CS, English at 5 or 6.", "SIGG": "Mid-Stage 1 portfolio review. Rebalance positions before holiday low-liquidity periods.", "German": "A2 certification test (self-assessment or mock). Begin transition to B1 materials.", "Code": "Audit desktop/polish_stocks_day_trade-main and understand every function without AI explanation."}'::jsonb, '[]'::jsonb, 4),
  ('jan-2027', 'Stage 1 Finish', 'Phase 1: Year 3 Liceum', 'JAN ''27', '2027-01', FALSE, 'upcoming', 'Stage 1 competition conclusion & dynamic programming drills.', '{"Academics": "Formal Semester 1 grades locked onto official transcript.", "SIGG": "Stage 1 closes (Jan 16). Review rank. If top 12: secure direct Finals spot; if not: prepare for Stage 2.", "Code": "Solve 10 dynamic programming and recursion problems from previous Matura sheets."}'::jsonb, '[]'::jsonb, 5),
  ('feb-2027', 'Winter Intensive', 'Phase 1: Year 3 Liceum', 'FEB ''27', '2027-02', FALSE, 'upcoming', 'Winter break math acceleration & futures simulation.', '{"Academics": "Complete 5 full Math Rozszerzona past sheets (CKE 2020-2024).", "SIGG": "Futures simulation prep: paper-trade WIG20 futures (FW20) leverage and short mechanics.", "German": "B1 grammar foundations (Subjunctive II, passive voice, subordinate clauses).", "Physical": "Weight 71.0 kg; bench/squat/deadlift baseline increase of 5%."}'::jsonb, '[]'::jsonb, 6),
  ('mar-2027', 'Stage 2 Derivatives', 'Phase 1: Year 3 Liceum', 'MAR ''27', '2027-03', TRUE, 'upcoming', 'Stage 2 live futures trading & Matura SQL database mastery.', '{"SIGG": "Stage 2 live (Mar 2 - Mar 27) with 10,000 PLN capital. Execute trade in first 7 days. Apply strict stop-losses on short positions.", "Academics": "Q3 school grades checkup. Ensure Polish, History, and Biology stay >= 4.0.", "Code": "Master SQL databases and Access/Excel data processing modules required for Matura Informatyka."}'::jsonb, '[]'::jsonb, 7),
  ('apr-2027', 'Regional Play-offs & Finals', 'Phase 1: Year 3 Liceum', 'APR ''27', '2027-04', FALSE, 'upcoming', 'GPW Warsaw Trading Floor finals sprint.', '{"SIGG": "Dogrywka (Apr 13-17) or live Finals at GPW Warsaw Trading Floor (Apr 23).", "Academics": "End-of-year sprint begins. Target 5.0+ in all core STEM subjects.", "German": "B1 intermediate listening comprehension (DW Langsam gesprochene Nachrichten)."}'::jsonb, '[]'::jsonb, 8),
  ('may-2027', 'Trial Matura Audit', 'Phase 1: Year 3 Liceum', 'MAY ''27', '2027-05', FALSE, 'upcoming', 'Write official 2027 Matura 1 year early under timed exam conditions.', '{"Academics": "Sit down with 2027 official Matura papers written by 4th-graders. Score yourself under real exam timing (aim for >70% raw score on Math R 1 year early).", "Physical": "Body weight 72.5 kg at 14-15% body fat."}'::jsonb, '[]'::jsonb, 9),
  ('jun-2027', 'Year 3 Final Report', 'Phase 1: Year 3 Liceum', 'JUN ''27', '2027-06', TRUE, 'upcoming', 'Milepost 1 for TUM: 3rd Class Liceum Final Transcript (GPA >= 4.8).', '{"Academics": "Milepost 1 for TUM: 3rd Class Liceum Final Transcript completed with GPA >= 4.8.", "Code": "Complete a standalone, production-ready project for your portfolio without AI-generated scaffolding.", "Harness": "Update portfolio database with SIGG credentials and year-end metrics."}'::jsonb, '[]'::jsonb, 10),
  ('jul-aug-2027', 'Summer Build', 'Phase 2: Year 4 Liceum', 'JUL ''27', '2027-07', FALSE, 'upcoming', 'Goethe B1 certification, Math Calculus sprint, and 74kg mass check.', '{"German": "Target Goethe-Zertifikat B1 exam or verify B1 competence. Start B2 reading.", "Academics": "Math Rozszerzona topical review (Calculus, Stereometry, Combinatorics).", "Physical": "Peak summer check: 73.5-74 kg, 13-14% body fat, 5k run maintained at sub-4:40 pace."}'::jsonb, '[]'::jsonb, 11),
  ('sep-2027', 'Class 4 Kickoff', 'Phase 2: Year 4 Liceum', 'SEP ''27', '2027-09', TRUE, 'upcoming', 'Official Matura declarations locked & daily timed algorithm speed drills.', '{"Academics": "Lock in official Matura declarations: Matematyka Podstawowa + Rozszerzona, Informatyka Rozszerzona, Język Angielski Dwujęzyczny / C1.", "Code": "Daily timed Matura algorithm speed-drills (45 min/day)."}'::jsonb, '[]'::jsonb, 12),
  ('oct-2027', 'TUM Portfolio Prep', 'Phase 2: Year 4 Liceum', 'OCT ''27', '2027-10', FALSE, 'upcoming', 'Draft English Letter of Motivation highlighting SIGG, coding, and startups.', '{"TUM Heilbronn": "Draft English Letter of Motivation (emphasizing data science projects, SIGG trading algorithms, startup initiatives).", "German": "B2 technical business/math vocabulary immersion."}'::jsonb, '[]'::jsonb, 13),
  ('nov-2027', 'Mock Exam Wave 1', 'Phase 2: Year 4 Liceum', 'NOV ''27', '2027-11', TRUE, 'upcoming', 'School mock exams (Próbne). Targets: Math R >= 80%, CS >= 75%, English >= 90%.', '{"Academics": "School mock exams (Nowa Era / Operon / CKE). Target scores: Math R >= 80%, Informatyka >= 75%, English Bilingual >= 90%."}'::jsonb, '[]'::jsonb, 14),
  ('dec-2027', 'Semester 3 Final Report', 'Phase 2: Year 4 Liceum', 'DEC ''27', '2027-12', FALSE, 'upcoming', 'Milepost 2 for TUM: First-semester grades of 4th liceum finalized.', '{"Academics": "Milepost 2 for TUM: First-semester grades of 4th liceum finalized. All semi-annual grades on transcript reflect high distinction."}'::jsonb, '[]'::jsonb, 15),
  ('jan-2028', 'Uni-Assist Setup', 'Phase 2: Year 4 Liceum', 'JAN ''28', '2028-01', TRUE, 'upcoming', 'Set up uni-assist.de for VPD processing & address weakest 3 math topics.', '{"TUM Pipeline": "Set up account on uni-assist.de for VPD (Vorprüfungsdokumentation) processing.", "Academics": "Identify weakest 3 math topics from mock results and solve 100 dedicated drill problems."}'::jsonb, '[]'::jsonb, 16),
  ('feb-2028', 'Winter Lock-in', 'Phase 2: Year 4 Liceum', 'FEB ''28', '2028-02', FALSE, 'upcoming', '10 full past-paper simulations under timed conditions. Zero external assistance.', '{"Academics": "10 full past-paper simulations under timed conditions. Zero external assistance.", "German": "B2 conversational practice (prepares for potential TUM aptitude assessment interview)."}'::jsonb, '[]'::jsonb, 17),
  ('mar-2028', 'Formal Clearance', 'Phase 2: Year 4 Liceum', 'MAR ''28', '2028-03', FALSE, 'upcoming', 'Order certified sworn translations (German/English) of transcripts.', '{"Academics": "Final school grades for 4th year locked in.", "TUM Pipeline": "Order sworn certified translations (German or English) of your 3rd and 4th-year semester reports (Halbjahresnoten)."}'::jsonb, '[]'::jsonb, 18),
  ('apr-2028', 'Graduation', 'Phase 2: Year 4 Liceum', 'APR ''28', '2028-04', TRUE, 'upcoming', 'Receive Świadectwo Ukończenia Liceum & assemble TUMonline package.', '{"Academics": "Receive high school graduation diploma (Świadectwo ukończenia liceum ogólnokształcącego).", "TUMonline": "Portal opens May 15. Prepare upload packages (Passport, CV, Motivation Letter, Transcripts)."}'::jsonb, '[]'::jsonb, 19),
  ('may-2028', 'Egzaminy Maturalne', 'Phase 2: Year 4 Liceum', 'MAY ''28', '2028-05', TRUE, 'upcoming', 'Write official CKE Matura & submit application via TUMonline.', '{"Execution": "Write official CKE Matura: Matematyka Podstawa & Rozszerzenie, Język Angielski Dwujęzyczny, Informatyka Rozszerzenie.", "TUM Application": "Submit application via TUMonline as soon as the window opens."}'::jsonb, '[]'::jsonb, 20),
  ('jun-2028', 'VPD & Matura Results', 'Phase 2: Year 4 Liceum', 'JUN ''28', '2028-06', FALSE, 'upcoming', 'Submit graduation certificate to Uni-Assist for expedited VPD generation.', '{"TUM Pipeline": "Submit graduation certificate and preliminary grades to Uni-Assist for expedited VPD generation.", "Physical": "Transition back to full boxing schedule (3-4x/week) and gym hypertrophy blocks."}'::jsonb, '[]'::jsonb, 21),
  ('jul-2028', 'TUM Direct Offer', 'Phase 2: Year 4 Liceum', 'JUL ''28', '2028-07', TRUE, 'upcoming', 'Stage 1 Aptitude score >= 88 pts triggers Direct Admission to TUM Heilbronn!', '{"July 8-9": "Official CKE Matura results published.", "Action": "Immediately forward official Matura certificate to Uni-Assist / TUMonline before July 15 deadline.", "Outcome": "Stage 1 Aptitude score >= 88 points triggers Direct Admission without an assessment interview.", "Station Arrived": "Acceptance letter confirmed for B.Sc. Management and Data Science at TUM Campus Heilbronn."}'::jsonb, '[]'::jsonb, 22)
ON CONFLICT (id) DO UPDATE SET
  status = EXCLUDED.status, deliverables = EXCLUDED.deliverables, completed_deliverables = EXCLUDED.completed_deliverables;

-- 14. App Settings
INSERT INTO public.app_settings (key, value) VALUES ('vulcan_config', '{"enabled": true, "service_url": "https://uonetplus.vulcan.net.pl", "student_symbol": "warszawamokotow", "student_name": "Heitor Coppini", "username": "", "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiXHVEODNFXHVEREQyIEhlaXRvciBDdXBpbmkgKFpTTGlUIG5yIDEpIiwidWlkIjoiMzE1N2YyMWQtNzczMC00M2FlLWFkN2YtYmY3MWM5YmY1MjQzIiwidGVuYW50Ijoid2Fyc3phd2Ftb2tvdG93IiwidW5pdHVpZCI6IjE0MjBiODQxLWM0YWEtNDM2OS1hOTEwLWZjOWIwNTU4YTUwNyIsInVyaSI6Imh0dHBzOi8vdWN6ZW4uZWR1dnVsY2FuLnBsL3dhcnN6YXdhbW9rb3Rvdy9zdGFydD9wcm9maWw9MzE1N2YyMWQtNzczMC00M2FlLWFkN2YtYmY3MWM5YmY1MjQzIiwic2VydmljZSI6IkZhbHNlIiwiY2FwcyI6IltdIiwibmJmIjoxNzg5MzMxOTU4LCJleHAiOjE3ODkzMzU1NTgsImlhdCI6MTc4OTMzMTk1OH0.F4xLfmw2Rz8_pqrPOCJ8_fyHg7xzoQjMO6G35ChQOGLJTV6yBBeSgFRqf6RZtLZknL7zIFeSuX0AYrAypYKfNhCycFVgJMfOyJtvgoOYmhQ-22YbKPeda3IsBurQuMEB5reRp-DyBx6R4iOQ9Dga4LOibLPTPPS1f0xtvH09e6Oq4p1Pqo9Gl5YmO0F3KwQAFIW-MFmtfsRtnzX7rVHdEvG4mdLTvmE5U8zg_EcmYdt4Wim_SgS6dEfp5zzrgOOHEu0pLmHO6VtYtDYptrQrXJVsnz6Rz7Ek71qrsW5p5Wk8nqJC5kVA0TzZJU3veFOqu5GaIZpkVpwQWTKm5zPmMQ", "registered_device": {"certificate": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxqD891NOFUwRajSxLbeMisvWwzCJJzvG9zDNcGAm2OumldYuXYUWaSwM6McziPikfYR0tZuH57p0X4sEw945+wdDScieKkMK9SDdb4v5rSWL73bVvFnpo4SoYrXwpwAkbCbS+ylnk+Y1OSjDfPRvkhaVfL+KfgYZUxVw8wwvJPJi1kT5AFNiHYKhdzTv8+3U1JRyh086GcJh6uHgH3pDBCPu7q/yxQqu88mlKd4UFnlMkco2yMH2Em2ADZs+Wq6V6s/6xfPrbDgTgzN3kFJl3VfTkWI3bSRiVmYR2pwfnMV+qhPYsR8UMl602ocm1jUGRpjxrqu3R9Hy2w0py31ZcQIDAQAB", "fingerprint": "bf24d7ea6a9820687854f3d97c6f769c", "private_key": "MIIEpAIBAAKCAQEAxqD891NOFUwRajSxLbeMisvWwzCJJzvG9zDNcGAm2OumldYuXYUWaSwM6McziPikfYR0tZuH57p0X4sEw945+wdDScieKkMK9SDdb4v5rSWL73bVvFnpo4SoYrXwpwAkbCbS+ylnk+Y1OSjDfPRvkhaVfL+KfgYZUxVw8wwvJPJi1kT5AFNiHYKhdzTv8+3U1JRyh086GcJh6uHgH3pDBCPu7q/yxQqu88mlKd4UFnlMkco2yMH2Em2ADZs+Wq6V6s/6xfPrbDgTgzN3kFJl3VfTkWI3bSRiVmYR2pwfnMV+qhPYsR8UMl602ocm1jUGRpjxrqu3R9Hy2w0py31ZcQIDAQABAoIBABcyNsiVYHGJRCFgjO53WIDfBDIgSWwdBYPZnaxJdk/v2TD3ZcvDHpZisBFBLioJS4BjBxQsWSc9NZjwzbooCiJgO0HzHVF3KeDtmR6NPLe1Qk3RVW2dHHVdqSJ59+Qw1pAQyqPNNozlngKSWZ4Ol7b6TzPV1JEaGjwDLYEcw6avOQuenxFWzn/1lHigNeZZ0AKHzkajnafCH7vLHDcfhZ0kpDobwf0S7NY5XXAYXwp9rpxov5OjUePb7e51hNt2AAJr8+majInyFb0PU73fYs2p4Yvxb/o8aCtZOE7lVl8rw9T4Z9DBBqOFlaq0raH3G6StXfkONsYuLsN6SFL0jIcCgYEA71Nx89EN7hS+zPn598oQJxGTv3hwMFOmkVu6XMYR9KelnuGQ5mmc9aleuS2Bo4K9LSJtmyb1vIk6C8N6pb5VLFZgel0eC4/IvT1ehdeDms6iCGnS7g7BlM645V7rtMFZP28R9d/7CfabZ9yGNlVRJ2DxRpUitidtKdaZZGiVencCgYEA1HeuJ0l3Q4qX9t4by1cU37S57amCKGrIwv+dQJx22S9P9QMamKneamWWiJga15qVmmgB+qFZguZYVqhe7xwg1bjlXSLLiLXl1vqNnxSA1cJoSSlu8b5wGhXrxJIclOssMUqNl4S7f98AhbpxP8Fnmt6Yz+Vdl/eauSP+K//I3VcCgYEAwY4ALAtYM8PNaCOHuZJPK/m4P3NdcIhGv2qrN1rtrKtldDDDqsWhrsDTHfqizSXwb69Xa9K/jUKCkn7/E0rywY/+KRhkMz+PPxWB+8cH5czWGO3VLLj8cKgbu03gXWi+EGJ46RzDgBRVLVOZrBmmL63klIwK7bzHOb4Ygq9erRMCgYBJI2mv3HpRpcPqF0s6FB/7Yhse1NsZTqkNdzCKrVG8Ma00inz9UHxf49iN7M5QqcYWAPetbx2BEgoWyp7jcKtc5ukNxoyJ4xPbjSRzPnubGfEMPlcSoJu2XxVp9WIhYVM1JJTZM7fXrMxhPGz/pXQku7ue1TYCuhlo4hr8ynA6wQKBgQCn1TyUjTFdF5jkx7xJd6oeLf4hRjQcB9WOzstN/fARlN/QWnMB5JWymxHww8h7iFPF+s0bFPYoxVZEaftyLVNAWDcGTVg0TcHi5DemO8kc5alMWPt14RdHZec+Q6JrBW8XwMeuKXCvOzy79daVdyBYWN2tPU9Sbr015fKKz8uiGA==", "device_id": "7945c4bf-8f47-44c2-a030-4e3cc910b975", "rest_url": "https://lekcjaplus.vulcan.net.pl/warszawamokotow/008899/api", "pupil_id": 27533, "unit_id": 8, "period_id": 9079, "school_name": "Zespół Szkół Licealnych i Technicznych nr 1"}, "last_synced_at": "2026-09-24T20:44:44.373069", "last_daily_sync_date": "2026-09-24", "sync_time_daily": "15:00", "demo_mode": false}'::jsonb) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();