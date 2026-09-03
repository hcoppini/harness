/**
 * HARNESS // iPhone Mobile Companion JavaScript Controller
 * Connects directly to the Harness REST API for two-way synchronization.
 */

const MobileApp = {
  activeTab: "cockpit",
  todayData: null,
  dashboardData: null,
  metroData: null,
  bodyData: null,
  completedBlocks: new Set(),
  completedExercises: new Set(),
  saveDebounceTimer: null,

  async init() {
    this.registerServiceWorker();
    this.bindEvents();
    await this.refreshAll();
  },

  registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  },

  bindEvents() {
    // Scratchpad auto-save
    const pad = document.getElementById("mScratchpad");
    if (pad) {
      pad.addEventListener("input", () => {
        clearTimeout(this.saveDebounceTimer);
        this.saveDebounceTimer = setTimeout(() => this.saveDailyLog(), 400);
      });
    }
  },

  async refreshAll() {
    try {
      this.setSyncStatus("SYNCING...");
      await Promise.all([
        this.loadDashboard(),
        this.loadToday(),
        this.loadMetro(),
        this.loadBody(),
      ]);
      this.setSyncStatus("SYNCED");
    } catch (err) {
      console.error("Sync error:", err);
      this.setSyncStatus("OFFLINE");
    }
  },

  setSyncStatus(text) {
    const el = document.getElementById("syncText");
    if (el) el.textContent = text;
  },

  showToast(msg) {
    const toast = document.getElementById("mobileToast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 1800);
  },

  switchTab(tabName) {
    this.activeTab = tabName;
    document.querySelectorAll(".mobile-view").forEach((el) => el.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));

    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) targetView.classList.add("active");

    const targetNav = document.querySelector(`.nav-item[data-view="${tabName}"]`);
    if (targetNav) targetNav.classList.add("active");
  },

  // --------------------------------------------------------------------------
  // Layer 0: Cockpit & Heatmap
  // --------------------------------------------------------------------------
  async loadDashboard() {
    const res = await fetch("/api/dashboard");
    if (!res.ok) return;
    this.dashboardData = await res.json();
    this.renderCockpit();
  },

  renderCockpit() {
    if (!this.dashboardData) return;
    const { metrics, today_velocity, heatmap, upcoming } = this.dashboardData;

    // Velocity & Streak
    const streakEl = document.getElementById("mStreakPill");
    if (streakEl) streakEl.textContent = `${metrics?.current_streak || 0}d Streak`;

    const velPct = today_velocity?.percentage || 0;
    const velPctEl = document.getElementById("mVelocityPct");
    const velBarEl = document.getElementById("mVelocityBar");
    const routineNameEl = document.getElementById("mRoutineName");

    if (velPctEl) velPctEl.textContent = `${velPct}%`;
    if (velBarEl) velBarEl.style.width = `${velPct}%`;
    if (routineNameEl) routineNameEl.textContent = today_velocity?.schedule_name || "Daily routine";

    // Purple Heatmap (Recent 22 weeks for mobile screen width)
    const gridEl = document.getElementById("mHeatmapGrid");
    const totalEl = document.getElementById("mHeatmapTotal");
    if (gridEl && heatmap?.weeks) {
      if (totalEl) totalEl.textContent = `${heatmap.total_contributions || 0} boxes completed`;
      const recentWeeks = heatmap.weeks.slice(-22); // Recent weeks for mobile

      gridEl.innerHTML = recentWeeks
        .map((w) => {
          return `
            <div class="heatmap-col">
              ${w.days
                .map((d) => {
                  if (!d) return `<div class="m-cell" style="opacity: 0;"></div>`;
                  return `<div class="m-cell m-lvl-${d.level || 0}" title="${d.display_date || ""}: ${d.count || 0} checked"></div>`;
                })
                .join("")}
            </div>
          `;
        })
        .join("");
    }

    // Tomorrow Upcoming
    if (upcoming && upcoming.length > 0) {
      const tomorrow = upcoming[0];
      const dateEl = document.getElementById("mTomorrowDate");
      const focusEl = document.getElementById("mTomorrowFocus");
      const detailsEl = document.getElementById("mTomorrowDetails");

      if (dateEl) dateEl.textContent = tomorrow.display_date;
      if (focusEl) focusEl.textContent = `Schedule ${tomorrow.schedule_key}: ${tomorrow.key_highlight}`;
      if (detailsEl) {
        let details = tomorrow.cutoff_info || "";
        if (tomorrow.gym_routine) {
          details += ` • Lift: ${tomorrow.gym_routine.name}`;
        }
        detailsEl.textContent = details;
      }
    }
  },

  // --------------------------------------------------------------------------
  // Layer 1: Today Routine & Tasks
  // --------------------------------------------------------------------------
  async loadToday() {
    const res = await fetch("/api/today");
    if (!res.ok) return;
    this.todayData = await res.json();
    this.renderToday();
  },

  renderToday() {
    if (!this.todayData) return;
    const { daily_log, schedule, tasks } = this.todayData;

    // Completed sets
    this.completedBlocks = new Set(
      (daily_log?.completed_blocks || "").split(",").map((s) => s.trim()).filter(Boolean)
    );
    this.completedExercises = new Set(
      (daily_log?.completed_exercises || "").split(",").map((s) => s.trim()).filter(Boolean)
    );

    // Schedule Header
    const schedHeader = document.getElementById("mScheduleHeader");
    const schedProg = document.getElementById("mScheduleProgress");
    if (schedHeader) schedHeader.textContent = schedule?.name || "Daily Routine";

    const blocks = schedule?.blocks || [];
    const checkedBlocksCount = Array.from(this.completedBlocks).length;
    if (schedProg) schedProg.textContent = `${checkedBlocksCount}/${blocks.length}`;

    // Render Routine Blocks
    const routineList = document.getElementById("mRoutineList");
    if (routineList) {
      routineList.innerHTML = blocks
        .map((b, idx) => {
          const isDone = this.completedBlocks.has(String(idx));
          return `
            <div class="routine-row ${isDone ? "completed" : ""}" onclick="MobileApp.toggleBlock(${idx})">
              <div class="check-circle ${isDone ? "checked" : ""}"></div>
              <div class="routine-info">
                <div class="routine-time">${this.escapeHtml(b.time)}</div>
                <div class="routine-name">${this.escapeHtml(b.activity || b.focus)}</div>
              </div>
            </div>
          `;
        })
        .join("");
    }

    // Render Active Tasks
    const taskList = document.getElementById("mTaskList");
    if (taskList) {
      if (tasks.length === 0) {
        taskList.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px 0;">No active tasks. Tap + above to add one.</div>`;
      } else {
        taskList.innerHTML = tasks
          .map((t) => {
            const isDone = t.completed;
            return `
              <div class="routine-row ${isDone ? "completed" : ""}">
                <div class="check-circle ${isDone ? "checked" : ""}" onclick="MobileApp.toggleTask(${t.id})"></div>
                <div class="routine-info" onclick="MobileApp.toggleTask(${t.id})">
                  <div class="routine-name">${this.escapeHtml(t.title)}</div>
                </div>
                <button style="background: transparent; border: none; color: var(--text-tertiary); font-size: 14px; padding: 4px;" onclick="MobileApp.deleteTask(${t.id})">✕</button>
              </div>
            `;
          })
          .join("");
      }
    }

    // Scratchpad
    const pad = document.getElementById("mScratchpad");
    if (pad && document.activeElement !== pad) {
      pad.value = daily_log?.scratchpad || "";
    }
  },

  async toggleBlock(idx) {
    const key = String(idx);
    if (this.completedBlocks.has(key)) {
      this.completedBlocks.delete(key);
    } else {
      this.completedBlocks.add(key);
    }
    this.renderToday();
    await this.saveDailyLog();
  },

  async toggleExercise(idx) {
    const key = String(idx);
    if (this.completedExercises.has(key)) {
      this.completedExercises.delete(key);
    } else {
      this.completedExercises.add(key);
    }
    this.renderGymExercises();
    await this.saveDailyLog();
  },

  async saveDailyLog() {
    const pad = document.getElementById("mScratchpad");
    const blocksStr = Array.from(this.completedBlocks).join(",");
    const exStr = Array.from(this.completedExercises).join(",");

    await fetch("/api/today/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scratchpad: pad ? pad.value : "",
        completed_blocks: blocksStr,
        completed_exercises: exStr,
      }),
    });
    this.showToast("Saved");
  },

  async handleAddTask(e) {
    e.preventDefault();
    const input = document.getElementById("mTaskInput");
    const title = input?.value.trim();
    if (!title) return;

    await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, category: "General" }),
    });

    if (input) input.value = "";
    await this.loadToday();
    this.showToast("Task added");
  },

  async toggleTask(taskId) {
    await fetch(`/api/tasks/${taskId}/toggle`, { method: "POST" });
    await this.loadToday();
  },

  async deleteTask(taskId) {
    await fetch(`/api/tasks/${taskId}/delete`, { method: "POST" });
    await this.loadToday();
    this.showToast("Task deleted");
  },

  async rolloverTasks() {
    const res = await fetch("/api/tasks/rollover", { method: "POST" });
    const data = await res.json();
    await this.loadToday();
    this.showToast(`Rolled over ${data.rolled_over_count || 0} tasks`);
  },

  // --------------------------------------------------------------------------
  // Layer 2: Metro Roadmap
  // --------------------------------------------------------------------------
  async loadMetro() {
    const res = await fetch("/api/metro");
    if (!res.ok) return;
    this.metroData = await res.json();
    this.renderMetro();
  },

  renderMetro() {
    if (!this.metroData || !this.metroData.stations) return;
    const listEl = document.getElementById("mMetroList");
    if (!listEl) return;

    listEl.innerHTML = this.metroData.stations
      .map((st) => {
        const isCompleted = st.status === "completed";
        const isMajor = st.is_major;
        const delivs = Object.entries(st.deliverables || {});
        const completedDelivs = st.completed_deliverables || [];

        return `
          <div class="mobile-card ${isMajor ? "major" : ""}">
            <div class="card-title-row">
              <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: ${isMajor ? "var(--accent-gold)" : "var(--text-secondary)"};">
                ${st.month_label} • ${st.phase.split(":")[0]}
              </span>
              <span style="font-family: var(--font-mono); font-size: 10px; color: ${isCompleted ? "var(--accent-green)" : "var(--text-tertiary)"};">
                ${isCompleted ? "COMPLETED ✓" : `${completedDelivs.length}/${delivs.length} MET`}
              </span>
            </div>
            <div style="font-size: 13px; font-weight: 600; margin-bottom: 6px;">${this.escapeHtml(st.name)}</div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 10px;">${this.escapeHtml(st.objective || "")}</div>

            <!-- Deliverables Checklist -->
            <div style="border-top: 1px solid var(--border-hairline); padding-top: 8px;">
              ${delivs
                .map(([key, val]) => {
                  const isChecked = completedDelivs.includes(key);
                  return `
                    <div class="routine-row ${isChecked ? "completed" : ""}" onclick="MobileApp.toggleMetroDeliverable('${st.id}', '${this.escapeHtml(key)}')">
                      <div class="check-circle ${isChecked ? "checked" : ""}"></div>
                      <div class="routine-info">
                        <div style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">${key} LINE</div>
                        <div class="routine-name" style="font-size: 11px;">${this.escapeHtml(val)}</div>
                      </div>
                    </div>
                  `;
                })
                .join("")}
            </div>
          </div>
        `;
      })
      .join("");
  },

  async toggleMetroDeliverable(stationId, deliverableKey) {
    const res = await fetch(`/api/metro/${stationId}/deliverable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deliverable_key: deliverableKey }),
    });
    const data = await res.json();
    await this.loadMetro();
    if (data.station_completed) {
      this.showToast("Station Completed! ✓");
    } else {
      this.showToast(`Updated ${deliverableKey}`);
    }
  },

  // --------------------------------------------------------------------------
  // Layer 3: Body & Gym
  // --------------------------------------------------------------------------
  async loadBody() {
    const res = await fetch("/api/body");
    if (!res.ok) return;
    this.bodyData = await res.json();
    this.renderBody();
  },

  renderBody() {
    this.renderGymExercises();
  },

  renderGymExercises() {
    const listEl = document.getElementById("mGymExerciseList");
    const headerEl = document.getElementById("mGymHeader");
    const tagEl = document.getElementById("mGymDayTag");
    if (!listEl) return;

    const todayGym = this.todayData?.gym_routine;
    if (!todayGym || !todayGym.exercises) {
      listEl.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px 0;">Rest / Conditioning Day. No heavy barbell session scheduled today.</div>`;
      if (headerEl) headerEl.textContent = "Recovery / Rest Day";
      return;
    }

    if (headerEl) headerEl.textContent = todayGym.name || "Gym Protocol";
    if (tagEl) tagEl.textContent = `${todayGym.focus || "Hypertrophy"} (${todayGym.exercises.length} sets)`;

    listEl.innerHTML = todayGym.exercises
      .map((ex, idx) => {
        const isDone = this.completedExercises.has(String(idx));
        return `
          <div class="routine-row ${isDone ? "completed" : ""}" onclick="MobileApp.toggleExercise(${idx})">
            <div class="check-circle ${isDone ? "checked" : ""}"></div>
            <div class="routine-info">
              <div class="routine-time">${this.escapeHtml(ex.sets_reps || "")} • ${this.escapeHtml(ex.rest || "")}</div>
              <div class="routine-name">${this.escapeHtml(ex.name)}</div>
            </div>
          </div>
        `;
      })
      .join("");
  },

  async saveWeight() {
    const input = document.getElementById("mWeightInput");
    const cal = document.getElementById("mCalSurplus");
    const prot = document.getElementById("mProteinMet");

    const weight = parseFloat(input?.value);
    if (isNaN(weight) || weight <= 0) {
      alert("Please enter a valid weight in kg");
      return;
    }

    await fetch("/api/body/metric", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weight_kg: weight,
        calories_met: cal ? cal.checked : false,
        protein_met: prot ? prot.checked : false,
        notes: "Logged from iPhone companion",
      }),
    });

    this.showToast(`Logged: ${weight.toFixed(1)} kg`);
    if (input) input.value = "";
  },

  async logWorkout(type) {
    await fetch("/api/body/workout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workout_type: type,
        details: `${type} logged from iPhone companion`,
      }),
    });
    this.showToast(`Logged ${type} session`);
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};

document.addEventListener("DOMContentLoaded", () => {
  MobileApp.init();
});
