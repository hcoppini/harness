/**
 * HARNESS // High-End Editorial Mobile Companion JavaScript Controller
 * Connects directly to the Harness REST & RPC APIs for two-way synchronization.
 */

const MobileApp = {
  activeTab: "cockpit",
  todayData: null,
  dashboardData: null,
  tumData: null,
  metroData: null,
  projectsData: null,
  bodyData: null,
  killListData: null,
  selectedWorkoutType: "Gym",
  captureMode: "task",
  completedBlocks: new Set(),
  completedExercises: new Set(),
  saveDebounceTimer: null,

  getLocalDateStr(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  },

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
    // Quick capture backdrop dismissal
    const overlay = document.getElementById("quickCaptureOverlay");
    if (overlay) {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) this.closeQuickCapture();
      });
    }
  },

  async refreshAll() {
    try {
      this.setSyncStatus("SYNCING...");
      await Promise.allSettled([
        this.loadDashboard(),
        this.loadToday(),
        this.loadKillList(),
        this.loadTUM(),
        this.loadMetro(),
        this.loadProjects(),
        this.loadBody(),
      ]);
      this.setSyncStatus("SYNCED");
    } catch (err) {
      console.error("Sync error:", err);
      this.setSyncStatus("OFFLINE");
    }
  },

  async syncNow() {
    const dot = document.getElementById("mSyncDot");
    if (dot) dot.style.animation = "syncPulse 0.6s infinite ease-in-out";
    this.showToast("Synchronizing with Executive Cloud...");
    await this.refreshAll();
    if (dot) dot.style.animation = "syncPulse 2.4s infinite ease-in-out";
    this.showToast("All Modules Up-to-Date ✓");
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
    setTimeout(() => toast.classList.remove("show"), 2200);
  },

  switchTab(tabName) {
    this.activeTab = tabName;
    document.querySelectorAll(".mobile-view").forEach((el) => el.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));

    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) targetView.classList.add("active");

    const targetNav = document.querySelector(`.nav-item[data-view="${tabName}"]`);
    if (targetNav) targetNav.classList.add("active");

    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  // --------------------------------------------------------------------------
  // Layer 0: Cockpit & Execution Pulse
  // --------------------------------------------------------------------------
  async loadDashboard() {
    try {
      const res = await fetch(`/api/dashboard?date=${this.getLocalDateStr()}`);
      if (!res.ok) return;
      this.dashboardData = await res.json();
      this.renderCockpit();
    } catch (err) {
      console.error("Dashboard load failed:", err);
    }
  },

  renderCockpit() {
    if (!this.dashboardData) return;
    const { metrics, today_velocity, heatmap, upcoming } = this.dashboardData;

    // Streak & Velocity
    const streakEl = document.getElementById("mStreakPill");
    if (streakEl) streakEl.textContent = `${metrics?.current_streak || 0}d Streak`;

    const velPct = today_velocity?.percentage || 0;
    const velPctEl = document.getElementById("mVelocityPct");
    const velBarEl = document.getElementById("mVelocityBar");
    const routineNameEl = document.getElementById("mRoutineName");

    if (velPctEl) velPctEl.textContent = `${velPct}%`;
    if (velBarEl) velBarEl.style.width = `${velPct}%`;
    if (routineNameEl) routineNameEl.textContent = today_velocity?.schedule_name || "Daily Routine";

    // Kill List mini counter in cockpit
    const killPill = document.getElementById("mCockpitKillPill");
    if (killPill && this.killListData) {
      const completedCount = this.killListData.filter((k) => k.completed).length;
      killPill.textContent = `${completedCount}/3 Killed`;
    }

    // Lavender Execution Heatmap Pulse (Recent 22 weeks)
    const gridEl = document.getElementById("mHeatmapGrid");
    const totalEl = document.getElementById("mHeatmapTotal");
    if (gridEl && heatmap?.weeks) {
      if (totalEl) totalEl.textContent = `${heatmap.total_contributions || 0} boxes`;
      const recentWeeks = heatmap.weeks.slice(-22);

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

    // Tomorrow's Upcoming Forecast
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
  // Layer 1: Today Routine, Tasks, Kill List & Reflections
  // --------------------------------------------------------------------------
  async loadToday(dateStr = null) {
    try {
      const targetDate = dateStr || this.getLocalDateStr();
      const res = await fetch(`/api/today?date=${targetDate}`);
      if (!res.ok) return;
      this.todayData = await res.json();
      this.renderToday();
    } catch (err) {
      console.error("Today load failed:", err);
    }
  },

  renderToday() {
    if (!this.todayData) return;
    const log = this.todayData.log || this.todayData.daily_log;
    const { schedule, tasks } = this.todayData;

    // Completed sets
    this.completedBlocks = new Set(
      (log?.completed_blocks || "").split(",").map((s) => s.trim()).filter(Boolean)
    );
    this.completedExercises = new Set(
      (log?.completed_exercises || "").split(",").map((s) => s.trim()).filter(Boolean)
    );

    // Schedule Header & Routine List
    const schedHeader = document.getElementById("mScheduleHeader");
    const schedProg = document.getElementById("mScheduleProgress");
    if (schedHeader) schedHeader.textContent = schedule?.name || "Daily Routine";

    const blocks = schedule?.blocks || [];
    const checkedBlocksCount = Array.from(this.completedBlocks).length;
    if (schedProg) schedProg.textContent = `${checkedBlocksCount}/${blocks.length}`;

    const routineList = document.getElementById("mRoutineList");
    if (routineList) {
      routineList.innerHTML = blocks
        .map((b, idx) => {
          const isDone = this.completedBlocks.has(String(idx));
          return `
            <div class="execution-row ${isDone ? "completed" : ""}" onclick="MobileApp.toggleBlock(${idx})">
              <div class="check-circle ${isDone ? "checked" : ""}"></div>
              <div class="row-content">
                <div class="row-meta">
                  <span class="row-tag" style="color: var(--accent-lavender);">${this.escapeHtml(b.time)}</span>
                </div>
                <div class="row-title">${this.escapeHtml(b.activity || b.focus)}</div>
              </div>
            </div>
          `;
        })
        .join("");
    }

    // Active Tasks Checklist
    const taskList = document.getElementById("mTaskList");
    if (taskList) {
      if (!tasks || tasks.length === 0) {
        taskList.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 10px 0;">No active tasks. Use + above to add one.</div>`;
      } else {
        taskList.innerHTML = tasks
          .map((t) => {
            const isDone = t.completed;
            const cat = t.category || "General";
            return `
              <div class="execution-row ${isDone ? "completed" : ""}">
                <div class="check-circle ${isDone ? "checked" : ""}" onclick="MobileApp.toggleTask(${t.id})"></div>
                <div class="row-content" onclick="MobileApp.toggleTask(${t.id})">
                  <div class="row-meta">
                    <span class="row-tag">${this.escapeHtml(cat)}</span>
                    ${t.rollover_count ? `<span class="row-tag" style="color: var(--accent-gold);">Rolled ${t.rollover_count}x</span>` : ""}
                  </div>
                  <div class="row-title">${this.escapeHtml(t.title)}</div>
                </div>
                <button class="btn-icon-subtle" onclick="MobileApp.deleteTask(${t.id})" title="Delete Task">✕</button>
              </div>
            `;
          })
          .join("");
      }
    }

    // Reflection & Sleep Fields (only populate if not actively typing)
    const wakeInput = document.getElementById("mWakeTime");
    const sleepInput = document.getElementById("mSleepTime");
    const workedInput = document.getElementById("mReflectionWorked");
    const slippedInput = document.getElementById("mReflectionSlipped");
    const tomorrowInput = document.getElementById("mReflectionTomorrow");
    const pad = document.getElementById("mScratchpad");

    if (log) {
      if (wakeInput && document.activeElement !== wakeInput) wakeInput.value = log.wake_time || "";
      if (sleepInput && document.activeElement !== sleepInput) sleepInput.value = log.sleep_time || "";
      if (workedInput && document.activeElement !== workedInput) workedInput.value = log.reflection_worked || "";
      if (slippedInput && document.activeElement !== slippedInput) slippedInput.value = log.reflection_slipped || "";
      if (tomorrowInput && document.activeElement !== tomorrowInput) tomorrowInput.value = log.reflection_tomorrow || "";
      if (pad && document.activeElement !== pad) pad.value = log.scratchpad || "";
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

  async handleAddTask(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("mTaskInput");
    const catSelect = document.getElementById("mTaskCategory");
    const title = input?.value.trim();
    if (!title) return;

    const category = catSelect?.value || "General";
    try {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, category }),
      });
      if (input) input.value = "";
      await this.loadToday();
      this.showToast("Task added");
    } catch (err) {
      console.error("Add task failed:", err);
    }
  },

  async toggleTask(taskId) {
    try {
      await fetch(`/api/tasks/${taskId}/toggle`, { method: "POST" });
      await this.loadToday();
    } catch (err) {
      console.error("Toggle task failed:", err);
    }
  },

  async deleteTask(taskId) {
    try {
      await fetch(`/api/tasks/${taskId}/delete`, { method: "POST" });
      await this.loadToday();
      this.showToast("Task deleted");
    } catch (err) {
      console.error("Delete task failed:", err);
    }
  },

  async rolloverTasks() {
    try {
      const res = await fetch("/api/tasks/rollover", { method: "POST" });
      const data = await res.json();
      await this.loadToday();
      this.showToast(`Rolled over ${data.rolled_over_count || 0} tasks`);
    } catch (err) {
      console.error("Rollover failed:", err);
    }
  },

  debouncedSaveDailyLog() {
    clearTimeout(this.saveDebounceTimer);
    this.saveDebounceTimer = setTimeout(() => this.saveDailyLog(), 500);
  },

  async saveDailyLog() {
    const pad = document.getElementById("mScratchpad");
    const wake = document.getElementById("mWakeTime");
    const sleep = document.getElementById("mSleepTime");
    const worked = document.getElementById("mReflectionWorked");
    const slipped = document.getElementById("mReflectionSlipped");
    const tomorrow = document.getElementById("mReflectionTomorrow");

    const blocksStr = Array.from(this.completedBlocks).join(",");
    const exStr = Array.from(this.completedExercises).join(",");

    const log = this.todayData?.log || this.todayData?.daily_log;
    const dateStr = log?.date || this.getLocalDateStr();

    try {
      await fetch("/api/today/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: dateStr,
          scratchpad: pad ? pad.value : (log?.scratchpad || ""),
          wake_time: wake ? wake.value : (log?.wake_time || ""),
          sleep_time: sleep ? sleep.value : (log?.sleep_time || ""),
          reflection_worked: worked ? worked.value : (log?.reflection_worked || ""),
          reflection_slipped: slipped ? slipped.value : (log?.reflection_slipped || ""),
          reflection_tomorrow: tomorrow ? tomorrow.value : (log?.reflection_tomorrow || ""),
          completed_blocks: blocksStr,
          completed_exercises: exStr,
        }),
      });

      if (this.todayData) {
        if (!this.todayData.log) this.todayData.log = {};
        this.todayData.log.date = dateStr;
        this.todayData.log.completed_blocks = blocksStr;
        this.todayData.log.completed_exercises = exStr;
        if (pad) this.todayData.log.scratchpad = pad.value;
        if (wake) this.todayData.log.wake_time = wake.value;
        if (sleep) this.todayData.log.sleep_time = sleep.value;
        if (worked) this.todayData.log.reflection_worked = worked.value;
        if (slipped) this.todayData.log.reflection_slipped = slipped.value;
        if (tomorrow) this.todayData.log.reflection_tomorrow = tomorrow.value;
      }
      this.showToast("Reflection saved");
    } catch (err) {
      console.error("Save daily log failed:", err);
    }
  },

  // --------------------------------------------------------------------------
  // Kill List (Rule of 3) Engine
  // --------------------------------------------------------------------------
  async loadKillList() {
    try {
      const res = await fetch("/api/kill-list");
      if (!res.ok) return;
      const data = await res.json();
      this.killListData = data.items || [];
      this.renderKillList();

      // Update cockpit pill
      const killPill = document.getElementById("mCockpitKillPill");
      if (killPill) {
        const completedCount = this.killListData.filter((k) => k.completed).length;
        killPill.textContent = `${completedCount}/3 Killed`;
      }
    } catch (err) {
      console.error("Kill list load failed:", err);
    }
  },

  renderKillList() {
    const container = document.getElementById("mKillList");
    if (!container) return;

    if (!this.killListData || this.killListData.length === 0) {
      container.innerHTML = `
        <div style="font-size: 11px; color: var(--text-tertiary); padding: 10px 0; text-align: center;">
          No kill items locked for today. Tap <b style="color: var(--accent-lavender);">+ Kill Item</b> above to set your 3 non-negotiables.
        </div>
      `;
      return;
    }

    container.innerHTML = this.killListData
      .map((item) => {
        const isDone = item.completed;
        const category = item.category || "General";
        const targetPath = item.target_path || "";
        const deliverableId = item.station_deliverable_id || "";

        return `
          <div class="execution-row ${isDone ? "completed" : ""}">
            <div class="check-circle ${isDone ? "checked" : ""}" onclick="MobileApp.toggleKillItem('${item.id}')"></div>
            <div class="row-content" onclick="MobileApp.toggleKillItem('${item.id}')">
              <div class="row-meta">
                <span class="row-tag" style="color: var(--accent-lavender);">${this.escapeHtml(category)}</span>
                ${deliverableId ? `<span class="deliverable-link-chip">◎ ${this.escapeHtml(deliverableId)}</span>` : ""}
              </div>
              <div class="row-title">${this.escapeHtml(item.title)}</div>
            </div>
            ${targetPath ? `
              <a href="${this.escapeHtml(targetPath)}" target="_blank" rel="noopener noreferrer" class="btn-icon-subtle" title="Open Link" onclick="event.stopPropagation()">
                ↗
              </a>
            ` : ""}
            <button class="btn-icon-subtle" onclick="MobileApp.deleteKillItem('${item.id}')" title="Delete Item">✕</button>
          </div>
        `;
      })
      .join("");
  },

  async toggleKillItem(itemId) {
    try {
      await fetch(`/api/kill-list/${itemId}/toggle`, { method: "POST" });
      await Promise.all([this.loadKillList(), this.loadDashboard()]);
    } catch (err) {
      console.error("Toggle kill item failed:", err);
    }
  },

  async deleteKillItem(itemId) {
    try {
      await fetch(`/api/kill-list/${itemId}`, { method: "DELETE" });
      await Promise.all([this.loadKillList(), this.loadDashboard()]);
      this.showToast("Kill item removed");
    } catch (err) {
      console.error("Delete kill item failed:", err);
    }
  },

  // --------------------------------------------------------------------------
  // Layer 2: TUM Metro Hub & Aptitude Calculator
  // --------------------------------------------------------------------------
  async loadTUM() {
    try {
      const res = await fetch("/api/tum/overview");
      if (!res.ok) return;
      this.tumData = await res.json();
      this.renderTUM();
    } catch (err) {
      console.error("TUM overview load failed:", err);
    }
  },

  renderTUM() {
    if (!this.tumData) return;
    const { aptitude, profile } = this.tumData;

    // Aptitude Hero Score
    const scoreValEl = document.getElementById("mTumScoreVal");
    const scoreBarEl = document.getElementById("mTumScoreBar");
    const badgeEl = document.getElementById("mTumAptitudeBadge");
    const gradeValEl = document.getElementById("mBavarianGradeVal");

    const cockpitScore = document.getElementById("mCockpitTumScore");
    const cockpitStatus = document.getElementById("mCockpitTumStatus");

    const score = aptitude?.total_score || 0;
    const bavGrade = aptitude?.bavarian_grade?.toFixed(2) || profile?.bavarian_grade?.toFixed(2) || "1.00";
    const statusText = aptitude?.status || "Direct Admission";

    if (scoreValEl) scoreValEl.textContent = `${score} / 100`;
    if (scoreBarEl) scoreBarEl.style.width = `${Math.min(100, Math.max(0, score))}%`;
    if (badgeEl) badgeEl.textContent = statusText;
    if (gradeValEl) gradeValEl.textContent = bavGrade;

    if (cockpitScore) cockpitScore.textContent = `${score} / 100`;
    if (cockpitStatus) cockpitStatus.textContent = statusText;
  },

  async loadMetro() {
    try {
      const res = await fetch("/api/metro");
      if (!res.ok) return;
      this.metroData = await res.json();
      this.renderMetro();
    } catch (err) {
      console.error("Metro load failed:", err);
    }
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
          <div class="station-card ${isMajor ? "major" : ""} ${isCompleted ? "completed" : ""}">
            <div class="card-title-row">
              <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: ${isMajor ? "var(--accent-lavender)" : "var(--text-secondary)"};">
                ${st.month_label} • ${st.phase.split(":")[0]}
              </span>
              <span class="mono-chip ${isCompleted ? "green" : "lavender"}">
                ${isCompleted ? "COMPLETED ✓" : `${completedDelivs.length}/${delivs.length} DELIVERABLES`}
              </span>
            </div>
            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">${this.escapeHtml(st.name)}</div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 10px;">${this.escapeHtml(st.objective || "")}</div>

            <!-- Deliverables Checklist -->
            <div>
              ${delivs
                .map(([key, val]) => {
                  const isChecked = completedDelivs.includes(key);
                  return `
                    <div class="deliverable-subitem ${isChecked ? "completed" : ""}" onclick="MobileApp.toggleMetroDeliverable('${st.id}', '${this.escapeHtml(key)}')">
                      <div class="check-circle ${isChecked ? "checked" : ""}" style="width: 18px; height: 18px; margin-top: 2px;"></div>
                      <div class="row-content">
                        <div class="row-tag" style="color: var(--accent-lavender-dim); font-size: 8px;">${key} STREAM</div>
                        <div class="row-title" style="font-size: 12px; ${isChecked ? "text-decoration: line-through; color: var(--text-tertiary);" : ""}">${this.escapeHtml(val)}</div>
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
    try {
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
    } catch (err) {
      console.error("Toggle deliverable failed:", err);
    }
  },

  // --------------------------------------------------------------------------
  // Layer 3: Projects & Ventures
  // --------------------------------------------------------------------------
  async loadProjects() {
    try {
      const res = await fetch("/api/projects");
      if (!res.ok) return;
      this.projectsData = await res.json();
      this.renderProjects();
    } catch (err) {
      console.error("Projects load failed:", err);
    }
  },

  renderProjects() {
    if (!this.projectsData) return;
    const countEl = document.getElementById("mProjectsCount");
    const listEl = document.getElementById("mProjectsList");
    if (!listEl) return;

    const projects = Array.isArray(this.projectsData) ? this.projectsData : this.projectsData.projects || [];
    if (countEl) countEl.textContent = `${projects.length} Active`;

    if (projects.length === 0) {
      listEl.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 12px 0;">No active ventures registered.</div>`;
      return;
    }

    listEl.innerHTML = projects
      .map((p) => {
        const milestone = p.current_milestone || "Initial execution";
        const nextAction = p.next_action || "Define immediate next physical step";
        const gh = p.github_url || "";

        return `
          <div class="project-card">
            <div class="card-title-row">
              <span class="card-title" style="color: var(--text-primary); font-size: 13px;">${this.escapeHtml(p.name)}</span>
              <span class="mono-chip lavender">${this.escapeHtml(p.status || "Active")}</span>
            </div>
            ${p.description ? `<div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">${this.escapeHtml(p.description)}</div>` : ""}
            
            <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">
              Milestone: <b style="color: var(--text-secondary);">${this.escapeHtml(milestone)}</b>
            </div>

            <!-- Next Physical Action Highlight Box -->
            <div class="next-action-box" onclick="MobileApp.editProjectNextAction(${p.id}, '${this.escapeHtml(nextAction)}', '${this.escapeHtml(milestone)}')">
              <div class="next-action-label">Next Physical Action ✎</div>
              <div class="next-action-text">${this.escapeHtml(nextAction)}</div>
            </div>

            ${gh ? `
              <div style="margin-top: 8px; text-align: right;">
                <a href="${this.escapeHtml(gh)}" target="_blank" rel="noopener noreferrer" style="font-family: var(--font-mono); font-size: 10px; color: var(--accent-lavender); text-decoration: none;">
                  GitHub Repository ↗
                </a>
              </div>
            ` : ""}
          </div>
        `;
      })
      .join("");
  },

  async editProjectNextAction(projectId, currentAction, currentMilestone) {
    const updated = prompt("Update Next Immediate Action:", currentAction);
    if (updated === null || updated.trim() === "") return;

    try {
      await fetch(`/api/projects/${projectId}/next_action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          next_action: updated.trim(),
          current_milestone: currentMilestone,
        }),
      });
      await this.loadProjects();
      this.showToast("Next action updated");
    } catch (err) {
      console.error("Update project failed:", err);
    }
  },

  // --------------------------------------------------------------------------
  // Layer 4: Body & Health
  // --------------------------------------------------------------------------
  async loadBody() {
    try {
      const res = await fetch("/api/body");
      if (!res.ok) return;
      this.bodyData = await res.json();
      this.renderBody();
    } catch (err) {
      console.error("Body load failed:", err);
    }
  },

  renderBody() {
    this.renderGymExercises();
    this.renderRecentWorkouts();
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
      if (tagEl) tagEl.textContent = "Recovery";
      return;
    }

    if (headerEl) headerEl.textContent = todayGym.name || "Gym Protocol";
    if (tagEl) tagEl.textContent = `${todayGym.focus || "Hypertrophy"} (${todayGym.exercises.length} sets)`;

    listEl.innerHTML = todayGym.exercises
      .map((ex, idx) => {
        const isDone = this.completedExercises.has(String(idx));
        return `
          <div class="execution-row ${isDone ? "completed" : ""}" onclick="MobileApp.toggleExercise(${idx})">
            <div class="check-circle ${isDone ? "checked" : ""}"></div>
            <div class="row-content">
              <div class="row-meta">
                <span class="row-tag" style="color: var(--accent-lavender);">${this.escapeHtml(ex.sets_reps || "")}</span>
                ${ex.rest ? `<span class="row-tag">• Rest: ${this.escapeHtml(ex.rest)}</span>` : ""}
              </div>
              <div class="row-title">${this.escapeHtml(ex.name)}</div>
            </div>
          </div>
        `;
      })
      .join("");
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

  renderRecentWorkouts() {
    const listEl = document.getElementById("mRecentWorkoutsList");
    if (!listEl) return;

    const history = this.bodyData?.history || [];
    const workouts = history.filter((h) => h.workouts && h.workouts.length > 0).flatMap((h) => h.workouts);

    if (workouts.length === 0) {
      listEl.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 6px 0;">No sessions logged yet this week.</div>`;
      return;
    }

    listEl.innerHTML = workouts
      .slice(-5)
      .reverse()
      .map((w) => {
        return `
          <div class="execution-row" style="cursor: default;">
            <div class="mono-chip lavender" style="padding: 2px 6px;">${this.escapeHtml(w.workout_type || "Gym")}</div>
            <div class="row-content">
              <div class="row-title" style="font-size: 12px;">${this.escapeHtml(w.details || "Training Session")}</div>
            </div>
            <span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">RPE ${w.intensity || 7}</span>
          </div>
        `;
      })
      .join("");
  },

  selectWorkoutType(type) {
    this.selectedWorkoutType = type;
    document.querySelectorAll(".workout-pill").forEach((el) => el.classList.remove("active"));
    const target = document.getElementById(`mPill${type}`);
    if (target) target.classList.add("active");
  },

  async logSelectedWorkout() {
    const detailsInput = document.getElementById("mWorkoutDetails");
    const details = detailsInput?.value.trim() || `${this.selectedWorkoutType} session logged from companion`;

    try {
      await fetch("/api/body/workout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workout_type: this.selectedWorkoutType,
          details,
        }),
      });
      if (detailsInput) detailsInput.value = "";
      await this.loadBody();
      this.showToast(`Logged ${this.selectedWorkoutType} session`);
    } catch (err) {
      console.error("Log workout failed:", err);
    }
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

    try {
      await fetch("/api/body/metric", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          weight_kg: weight,
          calories_met: cal ? cal.checked : false,
          protein_met: prot ? prot.checked : false,
          notes: "Logged from Mobile Companion",
        }),
      });

      this.showToast(`Logged: ${weight.toFixed(1)} kg`);
      if (input) input.value = "";
      await this.loadBody();
    } catch (err) {
      console.error("Save weight failed:", err);
    }
  },

  // --------------------------------------------------------------------------
  // Quick Capture Bottom Sheet
  // --------------------------------------------------------------------------
  openQuickCapture(mode = "task") {
    this.captureMode = mode;
    const overlay = document.getElementById("quickCaptureOverlay");
    const title = document.getElementById("sheetTitle");
    const label = document.getElementById("captureInputLabel");
    const textInput = document.getElementById("captureInputText");
    const catWrap = document.getElementById("captureCategoryWrap");

    if (overlay) overlay.classList.add("active");

    if (mode === "kill") {
      if (title) title.textContent = "New Kill List Priority";
      if (label) label.textContent = "Priority Objective (Rule of 3)";
      if (textInput) {
        textInput.placeholder = "e.g. Complete 5 Bavarian Math R integrals...";
        textInput.value = "";
        textInput.focus();
      }
      if (catWrap) catWrap.style.display = "flex";
    } else {
      if (title) title.textContent = "New Active Task";
      if (label) label.textContent = "Task Title";
      if (textInput) {
        textInput.placeholder = "e.g. Review Anki flashcards before bed...";
        textInput.value = "";
        textInput.focus();
      }
      if (catWrap) catWrap.style.display = "flex";
    }
  },

  closeQuickCapture(e) {
    if (e && e.target && e.target.closest(".sheet-container") && !e.target.classList.contains("btn-icon-subtle")) {
      return;
    }
    const overlay = document.getElementById("quickCaptureOverlay");
    if (overlay) overlay.classList.remove("active");
  },

  async handleQuickCaptureSubmit(e) {
    e.preventDefault();
    const textInput = document.getElementById("captureInputText");
    const catSelect = document.getElementById("captureCategory");
    const title = textInput?.value.trim();
    if (!title) return;

    const category = catSelect?.value || "General";

    try {
      if (this.captureMode === "kill") {
        await fetch("/api/kill-list", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            category,
            action_type: "url",
            quantity: 1,
          }),
        });
        this.showToast("Locked into Kill List ✓");
        await Promise.all([this.loadKillList(), this.loadDashboard()]);
      } else {
        await fetch("/api/tasks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, category }),
        });
        this.showToast("Task added ✓");
        await this.loadToday();
      }
      this.closeQuickCapture();
    } catch (err) {
      console.error("Quick capture failed:", err);
    }
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
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

