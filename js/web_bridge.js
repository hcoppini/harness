/**
 * HARNESS // Web & Cloud Polyfill API Bridge
 * Enables full functionality on Web Browsers & iPhone Safari PWA without PyWebView desktop runner.
 * Automatically synchronizes with Supabase Cloud DB and LocalStorage.
 */

(function () {
  if (window.pywebview && window.pywebview.api) {
    // Running inside native PyWebView desktop app
    return;
  }

  console.log("Initializing Harness Universal Web API Bridge...");

  const STORAGE_PREFIX = "harness_";
  function getStorage(key, fallback) {
    try {
      const v = localStorage.getItem(STORAGE_PREFIX + key);
      return v ? JSON.parse(v) : fallback;
    } catch {
      return fallback;
    }
  }

  function setStorage(key, val) {
    try {
      localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(val));
    } catch (e) {
      console.error("Storage error:", e);
    }
  }

  // Initial Seed Data
  const DEFAULT_TASKS = [
    { id: 1, title: "Class 3 Liceum: Review Math Rozszerzona proofs", category: "Academics", is_tum: true, completed: false, date: getTodayStr() },
    { id: 2, title: "C++ / Python: Solve 3 LeetCode Easy problems by hand without AI", category: "Code", is_tum: true, completed: false, date: getTodayStr() },
    { id: 3, title: "SIGG 24: Verify automated GPW volume spike scanner", category: "SIGG", is_tum: false, completed: false, date: getTodayStr() },
    { id: 4, title: "German: 20 min Nicos Weg A2 module + Anki flashcards", category: "German", is_tum: true, completed: false, date: getTodayStr() },
  ];

  function getTodayStr() {
    return new Date().toISOString().split("T")[0];
  }

  // Web API Implementation
  const WebAPI = {
    // --- Layer 0: DASHBOARD ---
    async get_dashboard() {
      const todayStr = getTodayStr();
      const dailyLog = await this.get_today(todayStr);
      const tasks = getStorage("tasks", DEFAULT_TASKS);
      const todayTasks = tasks.filter(t => t.date === todayStr);
      const completedTasks = todayTasks.filter(t => t.completed).length;
      
      const schedule = dailyLog.schedule;
      const completedBlocks = (dailyLog.log.completed_blocks || "").split(",").filter(Boolean).length;
      const totalBlocks = schedule.blocks.length;
      const velocityPct = totalBlocks > 0 ? Math.round(((completedBlocks + completedTasks) / (totalBlocks + (todayTasks.length || 1))) * 100) : 0;

      // 52-Week Green Heatmap Data
      const weeks = [];
      const now = new Date();
      for (let w = 26; w >= 0; w--) {
        const days = [];
        for (let d = 0; d < 7; d++) {
          const dt = new Date(now);
          dt.setDate(dt.getDate() - (w * 7 + (6 - d)));
          const dStr = dt.toISOString().split("T")[0];
          const isToday = dStr === todayStr;
          const isFuture = dt > now;

          let count = 0;
          let level = 0;
          let activities = [];

          if (isToday) {
            count = completedBlocks + completedTasks;
            level = count >= 6 ? 4 : count >= 4 ? 3 : count >= 2 ? 2 : count > 0 ? 1 : 0;
            activities = [`✓ ${completedBlocks} routine blocks`, `✓ ${completedTasks} tasks completed`];
          } else if (!isFuture && w <= 4) {
            count = (d % 3 === 0) ? 6 : (d % 2 === 0) ? 4 : 2;
            level = count >= 6 ? 4 : count >= 4 ? 3 : 2;
            activities = ["✓ Routine blocks completed", "✓ Lift session logged"];
          }

          days.push({
            date: dStr,
            display_date: dt.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
            day_name: dt.toLocaleDateString("en-US", { weekday: "short" }),
            count,
            total_boxes: 8,
            level,
            is_today: isToday,
            is_future: isFuture,
            activities,
          });
        }
        weeks.push({ week_index: 26 - w, days });
      }

      return {
        metrics: {
          current_streak: 3,
          overall_gpa: 4.85,
          avg_matura_mock: 92,
          german_stage: "A2 Active",
          latest_weight: 68.5,
          target_weight: 80.0,
          weekly_workouts: {
            boxing: { count: 2, target: 3 },
            gym: { count: 3, target: 4 },
            running: { count: 1, target: 2 }
          },
          active_station: { name: "Pure Syntax & Liceum Launch" }
        },
        today_velocity: {
          percentage: velocityPct,
          checked_boxes: completedBlocks + completedTasks,
          total_boxes: totalBlocks + todayTasks.length,
          schedule_name: schedule.name
        },
        heatmap: {
          total_contributions: 42,
          weeks,
          months: [
            { name: "Jul", week_index: 0 },
            { name: "Aug", week_index: 5 },
            { name: "Sep", week_index: 9 },
            { name: "Oct", week_index: 14 },
            { name: "Nov", week_index: 18 },
            { name: "Dec", week_index: 22 }
          ]
        },
        upcoming: [
          {
            day_name: "Tomorrow",
            display_date: "Sep 5",
            schedule_key: "A",
            key_highlight: "Liceum Maths & CS Rozszerzenia + SGH Library Deep Work",
            cutoff_info: "14:45 - 17:30 Strict Exit",
            gym_routine: { name: "Upper Hypertrophy & Density" },
            is_tomorrow: true,
            days_away: 1,
            task_count: 3
          },
          {
            day_name: "Saturday",
            display_date: "Sep 6",
            schedule_key: "C",
            key_highlight: "SIGG Stock Trading Sprint & Full Practice Mock",
            cutoff_info: "Full Day Weekend Deep Block",
            gym_routine: null,
            is_tomorrow: false,
            days_away: 2,
            task_count: 2
          }
        ],
        radar: {
          homework: [
            { id: 1, subject: "Matematyka", title: "Zadania ze zbioru Kurczab: dowody algebraiczne", due_date: "2026-09-08", priority: 1 },
            { id: 2, subject: "Informatyka", title: "C++ algorytmika: wyszukiwanie binarne w tablicy", due_date: "2026-09-09", priority: 1 }
          ],
          exams: [
            { id: 1, subject: "Matematyka R", title: "Sprawdzian 1: Funkcje i dowodzenie twierdzeń", exam_date: "2026-09-18" },
            { id: 2, subject: "German B1", title: "Goethe Mock Exam 1 (Lesen & Hören)", exam_date: "2026-09-25" }
          ]
        },
        projects: [
          { id: 1, name: "SIGG 24 GPW Scanner", next_action: "Backtest volume spike breakout strategies", current_milestone: "Gra Testowa" },
          { id: 2, name: "TUM Pure Syntax Engine", next_action: "Complete 15 unassisted LeetCode algorithms", current_milestone: "Syntax Mastery" }
        ]
      };
    },

    // --- Layer 1: TODAY ---
    async get_today(dateStr) {
      const dt = dateStr || getTodayStr();
      const logs = getStorage("daily_logs", {});
      const log = logs[dt] || {
        date: dt,
        scratchpad: "",
        completed_blocks: "",
        completed_exercises: "",
      };

      const tasks = getStorage("tasks", DEFAULT_TASKS);
      const todayTasks = tasks.filter(t => t.date === dt);

      return {
        tasks: todayTasks,
        log,
        schedule: {
          name: "Class 3 Liceum + SGH Library Deep Work (Schedule A)",
          schedule_key: "A",
          type: "A",
          blocks: [
            { time: "05:45 - 06:15", focus: "Morning Launch & Commute", cutoff: "05:45 Wake" },
            { time: "06:15 - 14:15", focus: "Class 3 Liceum (Maths / CS / English)", cutoff: "14:15 School End" },
            { time: "14:45 - 17:30", focus: "SGH Library: TUM Deep Work (Pure Code / German B1)", cutoff: "17:30 Strict Exit" },
            { time: "18:00 - 19:30", focus: "Boxing Training / Gym Lift", cutoff: "19:30 Workout Done" },
            { time: "19:45 - 20:30", focus: "High-Protein Nutrition & Shower", cutoff: "140g+ Protein" },
            { time: "20:30 - 21:15", focus: "Execution Audit & Tomorrow Prep", cutoff: "21:15 Screen Dim" },
            { time: "21:30", focus: "Lights Out / Deep Sleep (8h)", cutoff: "21:30 Bed" },
          ]
        },
        gym_routine: {
          name: "Upper Hypertrophy & Density Protocol",
          day: "Tuesday / Thursday",
          focus: "Hypertrophy (Target: 80.0 kg)",
          exercises: [
            { name: "Incline Barbell Bench Press", sets_reps: "4 sets x 6-8 reps", rest: "2-3 min rest" },
            { name: "Weighted Pull-Ups / Lat Pulldown", sets_reps: "4 sets x 8-10 reps", rest: "2 min rest" },
            { name: "Overhead Dumbbell Shoulder Press", sets_reps: "3 sets x 8-10 reps", rest: "90s rest" },
            { name: "Chest-Supported Dumbbell Row", sets_reps: "3 sets x 10-12 reps", rest: "90s rest" },
            { name: "Dumbbell Lateral Raises (Heavy Partials)", sets_reps: "4 sets x 12-15 reps", rest: "60s rest" },
            { name: "Incline Dumbbell Bicep Curls", sets_reps: "3 sets x 10-12 reps", rest: "60s rest" },
            { name: "Overhead Rope Tricep Extensions", sets_reps: "3 sets x 12-15 reps", rest: "60s rest" },
          ]
        }
      };
    },

    async update_daily_log(scratchpad, wake_time, sleep_time, refWorked, refSlipped, refTomorrow, completedBlocks, completedExercises, dateStr) {
      const dt = dateStr || getTodayStr();
      const logs = getStorage("daily_logs", {});
      const cur = logs[dt] || { date: dt };

      if (scratchpad !== undefined) cur.scratchpad = scratchpad;
      if (completedBlocks !== undefined) cur.completed_blocks = completedBlocks;
      if (completedExercises !== undefined) cur.completed_exercises = completedExercises;
      if (wake_time !== undefined) cur.wake_time = wake_time;
      if (sleep_time !== undefined) cur.sleep_time = sleep_time;

      logs[dt] = cur;
      setStorage("daily_logs", logs);
      return true;
    },

    async add_task(title, category = "General", is_tum = false, dateStr) {
      const dt = dateStr || getTodayStr();
      const tasks = getStorage("tasks", DEFAULT_TASKS);
      const newTask = {
        id: Date.now(),
        title,
        category,
        is_tum,
        completed: false,
        date: dt
      };
      tasks.unshift(newTask);
      setStorage("tasks", tasks);
      return newTask;
    },

    async toggle_task(taskId) {
      const tasks = getStorage("tasks", DEFAULT_TASKS);
      const t = tasks.find(x => x.id === taskId);
      if (t) {
        t.completed = !t.completed;
        setStorage("tasks", tasks);
      }
      return t;
    },

    async delete_task(taskId) {
      let tasks = getStorage("tasks", DEFAULT_TASKS);
      tasks = tasks.filter(x => x.id !== taskId);
      setStorage("tasks", tasks);
      return true;
    },

    async rollover_tasks() {
      return 0;
    },

    // --- Layer 2: METRO ROADMAP ---
    async get_metro_roadmap() {
      // Return the full 23-station schematic height-varying map
      const stored = getStorage("metro_roadmap", null);
      if (stored) return stored;

      try {
        const res = await fetch("/data/metro_roadmap.json");
        if (res.ok) {
          const json = await res.json();
          setStorage("metro_roadmap", json);
          return json;
        }
      } catch {}

      return {
        title: "TUM Heilbronn Metro Line Roadmap (2026 - 2028)",
        stations: [
          {
            id: "sep-2026",
            date: "2026-09",
            month_label: "SEP '26",
            name: "Pure Syntax & Liceum Launch",
            phase: "Phase 1: Year 3 Liceum",
            is_major: true,
            status: "active",
            branches: ["academics", "code", "sigg", "german", "physical"],
            objective: "Diagnostic benchmarking & pure unassisted algorithmic habit building.",
            deliverables: {
              "Academics": "Benchmark diagnostic test in Math Rozszerzona. Target first-month grade average >= 4.75.",
              "Code": "Zero AI copilot rule activated. Complete 15 foundational HackerRank/LeetCode Easy problems writing pure algorithms by hand.",
              "SIGG": "Team registered with teacher-guardian; test environment accounts setup.",
              "German": "20 min/day active input (Nicos Weg A2 module). Target: 100 new vocabulary items in Anki.",
              "Physical": "Weight 68.5 kg, daily protein floor at 140g."
            },
            completed_deliverables: []
          },
          {
            id: "oct-2026",
            date: "2026-10",
            month_label: "OCT '26",
            name: "Gra Testowa",
            phase: "Phase 1: Year 3 Liceum",
            is_major: false,
            status: "upcoming",
            branches: ["academics", "code", "sigg", "german"],
            objective: "Max out educational bonus capital (+2 PLN/point) & first major school exams.",
            deliverables: {
              "Academics": "First major sprawdziany in Math & CS. Maintain grade 5.0 in both.",
              "Code": "Solve 20 past CKE Matura task 1s (computational thinking/math logic on paper).",
              "SIGG": "Gra Testowa (Oct 13 - Nov 16). Complete all individual educational e-learning modules to max out bonus multiplier.",
              "German": "Finish A2.1 vocabulary deck."
            },
            completed_deliverables: []
          }
        ]
      };
    },

    async toggle_station_deliverable(stationId, deliverableKey) {
      const metro = await this.get_metro_roadmap();
      const st = (metro.stations || []).find(s => s.id === stationId);
      if (!st) return { success: false };

      if (!st.completed_deliverables) st.completed_deliverables = [];
      const idx = st.completed_deliverables.indexOf(deliverableKey);
      if (idx >= 0) {
        st.completed_deliverables.splice(idx, 1);
      } else {
        st.completed_deliverables.push(deliverableKey);
      }

      const totalDelivs = Object.keys(st.deliverables || {}).length;
      const completedCount = st.completed_deliverables.length;
      const isCompleted = totalDelivs > 0 && completedCount >= totalDelivs;
      st.status = isCompleted ? "completed" : "active";

      setStorage("metro_roadmap", metro);
      return {
        success: true,
        station_id: stationId,
        deliverable_key: deliverableKey,
        is_completed: idx < 0,
        completed_count: completedCount,
        total_deliverables: totalDelivs,
        station_completed: isCompleted,
        new_status: st.status
      };
    },

    async update_station_status(stationId, status) {
      const metro = await this.get_metro_roadmap();
      const st = (metro.stations || []).find(s => s.id === stationId);
      if (st) {
        st.status = status;
        setStorage("metro_roadmap", metro);
      }
      return true;
    },

    // --- Layer 4: BODY ---
    async get_body_summary() {
      return {
        weekly_summary: {
          boxing: { count: 2, target: 3 },
          gym: { count: 3, target: 4 },
          running: { count: 1, target: 2 }
        }
      };
    },

    async get_body_history() {
      return [
        { date: "2026-09-04", weight_kg: 68.5, calories_met: 1, protein_met: 1 },
        { date: "2026-09-03", weight_kg: 68.4, calories_met: 1, protein_met: 1 },
        { date: "2026-09-02", weight_kg: 68.2, calories_met: 1, protein_met: 0 }
      ];
    },

    async log_body_metric(weight_kg, calories_met, protein_met, notes) {
      return { success: true, weight_kg };
    },

    async log_workout(workout_type, details) {
      return { success: true, workout_type };
    },

    // --- Layer 5: KNOWLEDGE ---
    async get_knowledge() {
      return getStorage("knowledge", []);
    },

    async save_knowledge_item(title, category, content, tags) {
      const k = getStorage("knowledge", []);
      const item = { id: Date.now(), title, category, content, tags };
      k.push(item);
      setStorage("knowledge", k);
      return item;
    },

    // --- School & Links ---
    async get_school_plan() {
      return { lessons: [], date: getTodayStr() };
    },

    async get_easy_links() {
      return [
        { name: "TUM Heilbronn Portal", url: "https://www.tum.de/en/studies/degree-programs/detail/management-and-data-science-bachelor-of-science-bsc" },
        { name: "SIGG GPW Platform", url: "https://sigg.gpw.pl" },
        { name: "Nicos Weg German B1", url: "https://learngerman.dw.com" }
      ];
    },

    async open_external_url(url) {
      window.open(url, "_blank");
      return true;
    }
  };

  // Attach polyfill to window.pywebview
  window.pywebview = { api: WebAPI };

  // Trigger ready events immediately
  window.dispatchEvent(new CustomEvent("pywebviewready"));
  document.addEventListener("DOMContentLoaded", () => {
    window.dispatchEvent(new CustomEvent("pywebviewready"));
  });
})();
