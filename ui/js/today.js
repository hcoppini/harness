/**
 * Section 1: TODAY (Daily Execution Engine)
 * Handles Schedule A/B/C, gym workouts, date navigation, checkbox persistence,
 * quick tasks, homework/exam radar, and link launchpad.
 */

const Today = {
  tasks: [],
  schedule: null,
  gymRoutine: null,
  schoolLessons: [],
  easyLinks: [],
  homeworkList: [],
  examsList: [],
  completedBlocks: new Set(),
  completedExercises: new Set(),
  debounceTimer: null,

  // Calendar Navigation (defaults to today in local timezone)
  getLocalDateStr(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  },
  currentDateStr: (() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  })(),
  selectedDateStr: (() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  })(),
  calDisplayYear: new Date().getFullYear(),
  calDisplayMonth: new Date().getMonth(), // 0-indexed

  async init() {
    this.bindEvents();
    this.renderMiniCalendar();
    await this.load(this.selectedDateStr);
    await this.loadSchoolPlan();
    await this.loadEasyLinks();
    await this.loadHomeworkAndExams();

    // Vulcan UONET+ Silent Auto-Sync on startup & 20-min background interval
    this.silentAutoSyncVulcan();
    if (!this._vulcanSyncInterval) {
      this._vulcanSyncInterval = setInterval(() => this.silentAutoSyncVulcan(), 20 * 60 * 1000);
    }
    this.initDaily3pmVulcanSync();

    // Dynamic "Right Now" Execution Banner
    this.updateNowBanner();
    if (!this._nowBannerInterval) {
      this._nowBannerInterval = setInterval(() => this.updateNowBanner(), 30 * 1000);
    }
  },

  bindEvents() {
    // Quick task form
    const quickForm = document.getElementById("quickTaskForm");
    if (quickForm) {
      quickForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleQuickTask();
      });
    }

    // Homework & Exam buttons -> Open native modals
    const btnAddHw = document.getElementById("btnAddHomeworkBtn");
    if (btnAddHw) {
      btnAddHw.addEventListener("click", () => this.openAddHomeworkModal());
    }

    const btnAddExam = document.getElementById("btnAddExamBtn");
    if (btnAddExam) {
      btnAddExam.addEventListener("click", () => this.openAddExamModal());
    }

    // Modal Forms
    const hwForm = document.getElementById("homeworkModalForm");
    if (hwForm) {
      hwForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleSaveHomework();
      });
    }

    const examForm = document.getElementById("examModalForm");
    if (examForm) {
      examForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleSaveExam();
      });
    }

    // Quick Link Modal Button & Form
    const btnAddLink = document.getElementById("btnAddNewLinkModal");
    if (btnAddLink) {
      btnAddLink.addEventListener("click", () => this.openAddLinkModal());
    }

    const linkForm = document.getElementById("quickLinkForm");
    if (linkForm) {
      linkForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleSaveLink();
      });
    }

    const btnDelLink = document.getElementById("btnDeleteLink");
    if (btnDelLink) {
      btnDelLink.addEventListener("click", async () => {
        await this.handleDeleteLink();
      });
    }

    // Rollover button
    const btnRollover = document.getElementById("btnRollover");
    if (btnRollover) {
      btnRollover.addEventListener("click", async () => {
        await this.handleRollover();
      });
    }

    // Kill List Drawer button
    const btnKillList = document.getElementById("btnOpenKillList");
    if (btnKillList) {
      btnKillList.addEventListener("click", () => {
        if (window.KillListDrawer) window.KillListDrawer.open(this.selectedDateStr);
      });
    }

    // Mini-Calendar Navigation Buttons
    const btnPrevMonth = document.getElementById("btnPrevMonth");
    const btnNextMonth = document.getElementById("btnNextMonth");
    const btnTodayReset = document.getElementById("btnTodayReset");

    if (btnPrevMonth) {
      btnPrevMonth.addEventListener("click", () => {
        this.calDisplayMonth--;
        if (this.calDisplayMonth < 0) {
          this.calDisplayMonth = 11;
          this.calDisplayYear--;
        }
        this.renderMiniCalendar();
      });
    }

    if (btnNextMonth) {
      btnNextMonth.addEventListener("click", () => {
        this.calDisplayMonth++;
        if (this.calDisplayMonth > 11) {
          this.calDisplayMonth = 0;
          this.calDisplayYear++;
        }
        this.renderMiniCalendar();
      });
    }

    if (btnTodayReset) {
      btnTodayReset.addEventListener("click", async () => {
        const todayStr = this.getLocalDateStr();
        const now = new Date();
        this.calDisplayYear = now.getFullYear();
        this.calDisplayMonth = now.getMonth();
        await this.selectDate(todayStr);
      });
    }

    // School Timetable sync & web
    const btnRefreshSchool = document.getElementById("btnRefreshSchoolPlan");
    if (btnRefreshSchool) {
      btnRefreshSchool.addEventListener("click", async () => {
        await this.loadSchoolPlan(true);
      });
    }

    const btnOpenTM1Web = document.getElementById("btnOpenTM1Web");
    if (btnOpenTM1Web) {
      btnOpenTM1Web.addEventListener("click", async () => {
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.open_external_url("https://planlekcji.staff.edu.pl/plany/o6.html");
        }
      });
    }

    // Scratchpad auto-save
    const scratchpad = document.getElementById("scratchpadTextarea");
    if (scratchpad) {
      scratchpad.addEventListener("input", () => this.debounceSaveDailyLog());
    }

    // Evening Honesty Diary auto-save
    const refWorked = document.getElementById("reflectionWorked");
    if (refWorked) {
      refWorked.addEventListener("input", () => this.debounceSaveDailyLog());
    }

    // Sleep inputs
    const wakeInput = document.getElementById("wakeTimeInput");
    const sleepInput = document.getElementById("sleepTimeInput");
    if (wakeInput) wakeInput.addEventListener("change", () => this.saveDailyLog());
    if (sleepInput) sleepInput.addEventListener("change", () => this.saveDailyLog());
  },

  async selectDate(dateStr) {
    this.selectedDateStr = dateStr;
    this.renderMiniCalendar();
    await this.load(dateStr);
    await this.loadSchoolPlan();
    await this.loadHomeworkAndExams();
    if (window.Dashboard) {
      window.Dashboard.load();
    }
  },

  renderMiniCalendar() {
    const grid = document.getElementById("miniCalendarGrid");
    const label = document.getElementById("calMonthYearLabel");
    if (!grid || !label) return;

    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    label.textContent = `${monthNames[this.calDisplayMonth]} ${this.calDisplayYear}`;

    const daysHeader = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
    let html = daysHeader.map((d) => `<div class="mini-cal-header-day">${d}</div>`).join("");

    // Calculate day offset (Monday = 0 ... Sunday = 6)
    const firstDay = new Date(this.calDisplayYear, this.calDisplayMonth, 1);
    let startDay = firstDay.getDay() - 1;
    if (startDay === -1) startDay = 6;

    const daysInMonth = new Date(this.calDisplayYear, this.calDisplayMonth + 1, 0).getDate();

    for (let i = 0; i < startDay; i++) {
      html += `<div class="mini-cal-day empty"></div>`;
    }

    const todayStr = this.getLocalDateStr();

    for (let d = 1; d <= daysInMonth; d++) {
      const monthStr = String(this.calDisplayMonth + 1).padStart(2, "0");
      const dayStr = String(d).padStart(2, "0");
      const cellDateStr = `${this.calDisplayYear}-${monthStr}-${dayStr}`;

      const isToday = cellDateStr === todayStr ? "today" : "";
      const isSelected = cellDateStr === this.selectedDateStr ? "selected" : "";

      html += `
        <div 
          class="mini-cal-day ${isToday} ${isSelected}" 
          onclick="Today.selectDate('${cellDateStr}')"
          title="${cellDateStr}"
        >${d}</div>
      `;
    }

    grid.innerHTML = html;
  },

  async load(dateStr = null) {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      const targetDate = dateStr || this.selectedDateStr;
      const data = await window.pywebview.api.get_today(targetDate);
      this.tasks = data.tasks || [];
      this.schedule = data.schedule || null;
      this.gymRoutine = data.gym_routine || null;

      // Reset and parse completed blocks & exercises for the target date
      this.completedBlocks.clear();
      this.completedExercises.clear();

      if (data.log) {
        const blocksStr = data.log.completed_blocks || "";
        this.completedBlocks = new Set(
          blocksStr
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        );

        const exStr = data.log.completed_exercises || "";
        this.completedExercises = new Set(
          exStr
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        );

        const scratchpad = document.getElementById("scratchpadTextarea");
        const wakeInput = document.getElementById("wakeTimeInput");
        const sleepInput = document.getElementById("sleepTimeInput");
        const refWorked = document.getElementById("reflectionWorked");
        const refSlipped = document.getElementById("reflectionSlipped");
        const refTomorrow = document.getElementById("reflectionTomorrow");

        if (scratchpad) scratchpad.value = data.log.scratchpad || "";
        if (wakeInput) wakeInput.value = data.log.wake_time || "";
        if (sleepInput) sleepInput.value = data.log.sleep_time || "";
        if (refWorked) refWorked.value = data.log.reflection_worked || "";
        if (refSlipped) refSlipped.value = data.log.reflection_slipped || "";
        if (refTomorrow) refTomorrow.value = data.log.reflection_tomorrow || "";
      } else {
        const scratchpad = document.getElementById("scratchpadTextarea");
        const wakeInput = document.getElementById("wakeTimeInput");
        const sleepInput = document.getElementById("sleepTimeInput");
        if (scratchpad) scratchpad.value = "";
        if (wakeInput) wakeInput.value = "";
        if (sleepInput) sleepInput.value = "";
      }

      this.renderSchedule();
      this.renderGymCard();
      this.renderTasks();
      this.renderUnitedStudyCard();
      this.updateNowBanner();

      // Refresh Kill List items and render inline on Today view
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_kill_list) {
        try {
          const klData = await window.pywebview.api.get_kill_list(targetDate);
          const klItems = (klData && klData.items) || [];
          this.renderInlineKillList(klItems);
        } catch (e) {
          console.error("Error loading kill list in Today.load:", e);
        }
      }
    } catch (err) {
      console.error("Error loading Today data:", err);
    }
  },

  renderSchedule() {
    const badgeEl = document.getElementById("scheduleBadge");
    const dayNameEl = document.getElementById("scheduleDayName");
    const descEl = document.getElementById("scheduleDescription");
    const blocksContainer = document.getElementById("routineBlocksContainer");
    const wlBadge = document.getElementById("workloadBadge");
    const inlineKillCard = document.getElementById("todayInlineKillListCard");
    const inlineKillTitle = document.getElementById("todayInlineKillListTitle");

    if (!this.schedule || !blocksContainer) return;

    if (badgeEl) badgeEl.textContent = this.schedule.key ? `SCHEDULE ${this.schedule.key.replace("C_", "")}` : "DAILY";
    if (dayNameEl) dayNameEl.textContent = `${this.schedule.weekday || ""} • ${this.schedule.name || ""}`;
    if (descEl) descEl.textContent = this.schedule.description || "";

    // Harness 3.0: Workload Governor Badge
    if (wlBadge) {
      const wl = this.schedule.workload;
      if (wl && wl.mode) {
        wlBadge.style.display = "inline-block";
        wlBadge.textContent = wl.mode;
        if (wl.mode === "SURGE") {
          wlBadge.className = "mono-chip";
          wlBadge.style.background = "rgba(239, 68, 68, 0.15)";
          wlBadge.style.color = "#f87171";
          wlBadge.style.border = "1px solid rgba(239, 68, 68, 0.35)";
          wlBadge.title = `Surge Protocol: Academic load ${wl.academic_load_score}/100. High test density defense. Commute cutoff 16:30.`;
        } else if (wl.mode === "BALANCED") {
          wlBadge.className = "mono-chip lavender";
          wlBadge.style.background = "";
          wlBadge.style.color = "";
          wlBadge.style.border = "";
          wlBadge.title = `Balanced Mode: Academic load ${wl.academic_load_score}/100. Dual-track TUM Metro & school prep.`;
        } else {
          wlBadge.className = "mono-chip";
          wlBadge.style.background = "rgba(110, 231, 183, 0.12)";
          wlBadge.style.color = "#6ee7b7";
          wlBadge.style.border = "1px solid rgba(110, 231, 183, 0.3)";
          wlBadge.title = `Cruise Mode: Academic load ${wl.academic_load_score}/100. 100% TUM Metro priority focus.`;
        }
      } else {
        wlBadge.style.display = "none";
      }
    }

    const blocks = this.schedule.blocks || [];
    const isSunday = this.schedule.key === "G_REST" || (this.schedule.weekday || "").toLowerCase().includes("sun");
    const hasDeepWork = blocks.some((b) => b.type === "deep_work" || (b.focus && (b.focus.includes("Deep Work") || b.focus.includes("SGH Library"))));

    // Harness 3.0: Kill List Visibility Rule
    // Hide completely on days without SGH Library / deep work sessions (e.g. Sunday rest).
    // On home sprint days (Saturday), label it "TUM DEEP WORK KILL LIST".
    // On weekdays with SGH Library, label it "SGH LIBRARY KILL LIST".
    if (inlineKillCard) {
      if (!hasDeepWork || isSunday) {
        inlineKillCard.style.display = "none";
      } else {
        inlineKillCard.style.display = "block";
        if (inlineKillTitle) {
          const isSgh = blocks.some((b) => (b.focus && b.focus.includes("SGH Library")) || (b.activity && b.activity.includes("SGH")));
          inlineKillTitle.textContent = isSgh ? "SGH LIBRARY KILL LIST" : "TUM DEEP WORK KILL LIST";
        }
      }
    }
    blocksContainer.innerHTML = blocks
      .map((block, idx) => {
        const isDeepWork = block.type === "deep_work" || block.type === "study_block" || (block.focus && (block.focus.includes("Deep Work") || block.focus.includes("SGH Library") || block.focus.includes("Weekend Deep Work") || block.focus.includes("Weekend Focus")));
        const isChecked = this.completedBlocks.has(String(idx));
        const schoolBadge = block.is_school_dedicated ? `<span class="mono-chip" style="font-size: 9px; padding: 1px 5px; margin-left: 6px;">School First</span>` : "";
        return `
          <div 
            class="routine-block ${isDeepWork ? "deep-work clickable" : ""} ${isChecked ? "completed" : ""}"
            ${isDeepWork ? `onclick="if (window.KillListDrawer) window.KillListDrawer.open('${this.selectedDateStr}');"` : ""}
            ${isDeepWork ? 'title="Click to open SGH Library Kill List Drawer"' : ""}
            style="display: flex; align-items: center; gap: 10px; ${isDeepWork ? "cursor: pointer; border-left: 3px solid var(--accent-lavender);" : ""} ${isChecked ? "opacity: 0.65;" : ""}"
          >
            <div 
              class="check-dot ${isChecked ? "checked" : ""}" 
              onclick="event.stopPropagation(); Today.toggleRoutineBlock(${idx})" 
              title="${isChecked ? "Mark incomplete" : "Check off routine block"}"
              style="cursor: pointer; flex-shrink: 0;"
            ></div>
            <div class="routine-time" style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: ${isDeepWork ? "var(--accent-lavender)" : "var(--text-secondary)"}; width: 85px; flex-shrink: 0; text-decoration: ${isChecked ? "line-through" : "none"};">${block.time}</div>
            <div class="routine-info" style="flex: 1; min-width: 0;">
              <div class="routine-focus" style="font-size: 13px; font-weight: 600; color: ${isDeepWork ? "var(--text-primary)" : "var(--text-secondary)"}; text-decoration: ${isChecked ? "line-through" : "none"}; display: flex; align-items: center;">
                <span>${this.escapeHtml(block.focus)}</span>
                ${schoolBadge}
              </div>
              <div class="routine-activity" style="font-size: 11px; color: var(--text-tertiary);">${this.escapeHtml(block.activity)}</div>
            </div>
            ${
              isDeepWork
                ? `<button class="btn-primary" onclick="event.stopPropagation(); if (window.KillListDrawer) window.KillListDrawer.open('${this.selectedDateStr}');" style="font-family: var(--font-mono); font-size: 10px; padding: 3px 8px; letter-spacing: 0.03em;" title="Open Kill List Drawer">[KILL LIST]</button>`
                : ""
            }
          </div>
        `;
      })
      .join("");
  },

  async toggleRoutineBlock(idx) {
    const key = String(idx);
    if (this.completedBlocks.has(key)) {
      this.completedBlocks.delete(key);
    } else {
      this.completedBlocks.add(key);
    }
    this.renderSchedule();

    const strVal = Array.from(this.completedBlocks).join(",");
    try {
      if (window.pywebview && window.pywebview.api) {
        // ALWAYS pass this.selectedDateStr to ensure the current selected day is updated!
        await window.pywebview.api.update_daily_log(
          this.selectedDateStr,
          null, null, null, null, null, null,
          strVal,
          null
        );
      }
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error persisting completed block:", err);
    }
  },

  renderGymCard() {
    const card = document.getElementById("todayLiftCard");
    const titleEl = document.getElementById("todayLiftTitle");
    const exercisesContainer = document.getElementById("todayLiftExercises");

    if (!card) return;

    if (!this.gymRoutine) {
      card.style.display = "none";
      return;
    }

    card.style.display = "block";
    const exercises = this.gymRoutine.exercises || [];
    const allCompleted = exercises.length > 0 && exercises.every((_, idx) => this.completedExercises.has(String(idx)));

    if (titleEl) {
      titleEl.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div 
              class="check-dot ${allCompleted ? "checked" : ""}" 
              onclick="Today.toggleWholeWorkout()"
              title="1-Click: Mark entire workout completed"
              style="cursor: pointer; flex-shrink: 0;"
            ></div>
            <span style="color: var(--accent-lavender); font-weight: 700; cursor: pointer;" onclick="Today.toggleWholeWorkout()">
              STRUCTURED LIFT • ${this.escapeHtml(this.gymRoutine.name)}
            </span>
          </div>
          <button type="button" class="btn-ghost-icon" onclick="Today.toggleWholeWorkout()" style="font-size: 9px; padding: 2px 7px; color: ${allCompleted ? "#6ee7b7" : "var(--accent-lavender)"}; border-color: ${allCompleted ? "rgba(110,231,183,0.3)" : "rgba(196,181,253,0.3)"};">
            ${allCompleted ? "[DONE]" : "1-CLICK COMPLETE"}
          </button>
        </div>
      `;
    }

    exercisesContainer.innerHTML = exercises
      .map((ex, idx) => {
        const isChecked = this.completedExercises.has(String(idx));
        return `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div 
                class="check-dot ${allCompleted || isChecked ? "checked" : ""}" 
                onclick="Today.toggleGymExercise(${idx})" 
                title="Mark exercise complete"
                style="cursor: pointer; flex-shrink: 0;"
              ></div>
              <span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary); width: 16px;">#${idx + 1}</span>
              <span style="font-weight: 500; color: ${allCompleted || isChecked ? "var(--text-tertiary); text-decoration: line-through;" : "var(--text-primary);"} cursor: pointer;" onclick="Today.toggleGymExercise(${idx})">
                ${this.escapeHtml(ex.name)}
              </span>
            </div>
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">
              ${ex.sets} &times; ${ex.reps} (${ex.rest} rest)
            </div>
          </div>
        `;
      })
      .join("");
  },

  async toggleWholeWorkout() {
    if (!this.gymRoutine) return;
    const exercises = this.gymRoutine.exercises || [];
    const allCompleted = exercises.length > 0 && exercises.every((_, idx) => this.completedExercises.has(String(idx)));

    if (allCompleted) {
      this.completedExercises.clear();
    } else {
      exercises.forEach((_, idx) => this.completedExercises.add(String(idx)));
    }
    this.renderGymCard();

    const strVal = Array.from(this.completedExercises).join(",");
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.update_daily_log(
          this.selectedDateStr,
          null, null, null, null, null, null,
          null,
          strVal
        );
      }
      if (window.Dashboard) window.Dashboard.load();
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast(allCompleted ? "Workout reset" : "Workout marked completed");
      }
    } catch (err) {
      console.error("Error toggling whole workout:", err);
    }
  },

  async toggleGymExercise(idx) {
    const key = String(idx);
    if (this.completedExercises.has(key)) {
      this.completedExercises.delete(key);
    } else {
      this.completedExercises.add(key);
    }
    this.renderGymCard();

    const strVal = Array.from(this.completedExercises).join(",");
    try {
      if (window.pywebview && window.pywebview.api) {
        // ALWAYS pass this.selectedDateStr to ensure the current selected day is updated!
        await window.pywebview.api.update_daily_log(
          this.selectedDateStr,
          null, null, null, null, null, null,
          null,
          strVal
        );
      }
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error persisting completed exercise:", err);
    }
  },

  renderTasks() {
    const container = document.getElementById("customTaskList");
    if (!container) return;

    if (this.tasks.length === 0) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = this.tasks
      .map((t) => {
        const isCompleted = t.completed ? "completed" : "";
        const checkedClass = t.completed ? "checked" : "";
        return `
          <div class="task-item ${isCompleted}" data-id="${t.id}">
            <div class="check-dot ${checkedClass}" onclick="Today.toggleTask(${t.id})"></div>
            <span class="task-label">${this.escapeHtml(t.title)}</span>
            ${t.rollover_count > 0 ? `<span class="key-pill">Rolled ${t.rollover_count}x</span>` : ""}
            <button class="btn-ghost-icon" style="padding: 2px 6px; font-size: 10px;" onclick="Today.deleteTask(${t.id})">&times;</button>
          </div>
        `;
      })
      .join("");
  },

  async handleQuickTask() {
    const input = document.getElementById("quickTaskInput");
    if (!input) return;
    const title = input.value.trim();
    if (!title) return;

    try {
      const newTask = await window.pywebview.api.add_task(title, "personal", false, this.selectedDateStr);
      this.tasks.unshift(newTask);
      this.renderTasks();
      input.value = "";
      window.HarnessApp.showToast("Task added");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error adding quick task:", err);
    }
  },

  async toggleTask(taskId) {
    try {
      const res = await window.pywebview.api.toggle_task(taskId);
      const target = this.tasks.find((t) => t.id == taskId);
      if (target) {
        target.completed = res && res.completed !== undefined ? res.completed : (target.completed ? 0 : 1);
      }
      this.renderTasks();
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error toggling task:", err);
    }
  },

  async deleteTask(taskId) {
    try {
      await window.pywebview.api.delete_task(taskId);
      this.tasks = this.tasks.filter((t) => t.id !== taskId);
      this.renderTasks();
      window.HarnessApp.showToast("Task removed");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error deleting task:", err);
    }
  },

  async handleRollover() {
    try {
      const count = await window.pywebview.api.rollover_tasks(this.selectedDateStr);
      await this.load();
      window.HarnessApp.showToast(count > 0 ? `Carried forward ${count} pending item(s)` : "No pending items to carry forward");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error running rollover:", err);
    }
  },

  debounceSaveDailyLog() {
    clearTimeout(this.debounceTimer);
    const pill = document.getElementById("scratchpadSavePill");
    const diaryPill = document.getElementById("honestyDiarySavePill");
    if (pill) pill.textContent = "Saving...";
    if (diaryPill) diaryPill.textContent = "Saving...";

    this.debounceTimer = setTimeout(async () => {
      await this.saveDailyLog();
      if (pill) pill.textContent = "Saved";
      if (diaryPill) diaryPill.textContent = "Saved";
      setTimeout(() => {
        if (diaryPill) diaryPill.textContent = "Auto-saving";
      }, 1500);
    }, 400);
  },

  async saveDailyLog() {
    const scratchpad = document.getElementById("scratchpadTextarea")?.value;
    const wakeTime = document.getElementById("wakeTimeInput")?.value;
    const sleepTime = document.getElementById("sleepTimeInput")?.value;
    const refWorked = document.getElementById("reflectionWorked")?.value;
    const refSlipped = document.getElementById("reflectionSlipped")?.value;
    const refTomorrow = document.getElementById("reflectionTomorrow")?.value;

    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.update_daily_log(
          this.selectedDateStr,
          scratchpad,
          wakeTime,
          sleepTime,
          refWorked,
          refSlipped,
          refTomorrow
        );
      }
    } catch (err) {
      console.error("Error saving daily log:", err);
    }
  },

  updateNowBanner() {
    const banner = document.getElementById("dynamicNowBanner");
    const clockEl = document.getElementById("nowCurrentClock");
    const titleEl = document.getElementById("nowBlockTitle");
    const focusEl = document.getElementById("nowBlockFocus");
    const remPill = document.getElementById("nowTimeRemainingPill");
    const actionArea = document.getElementById("nowBlockActionArea");

    if (!banner || !clockEl || !titleEl || !focusEl) return;

    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentMins = hours * 60 + minutes;
    const timeStr = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    clockEl.textContent = timeStr;

    const dayOfWeek = now.getDay(); // 0 = Sun, 1 = Mon, ... 6 = Sat
    const isSunday = dayOfWeek === 0;
    const isSaturday = dayOfWeek === 6;

    let period = null;

    if (isSunday) {
      if (currentMins < 9 * 60) {
        period = { name: "Morning Sleep & Reset", focus: "Full recovery & nervous system restoration", endMins: 9 * 60 };
      } else if (currentMins < 14 * 60) {
        period = { name: "Active Rest & Light Walk", focus: "Mental clarity, hydration, and nutritional reset", endMins: 14 * 60 };
      } else if (currentMins < 18 * 60) {
        period = { name: "Weekly Strategic Review", focus: "Review school week ahead, upcoming Vulcan tests & calendar", endMins: 18 * 60 };
      } else {
        period = { name: "Early Evening Wind-down", focus: "Prepare bag, uniform, and 8h sleep floor for Monday", endMins: 22 * 60 };
      }
    } else if (isSaturday) {
      if (currentMins < 9 * 60) {
        period = { name: "Morning Wake & Fuel", focus: "Clean breakfast, hydration, zero-screen wakefulness", endMins: 9 * 60 };
      } else if (currentMins < 13 * 60) {
        period = { name: "TUM Metro Deep Sprint", focus: "Algorithm exercises, code practice & mathematics focus", endMins: 13 * 60, action: "Kill List" };
      } else if (currentMins < 17 * 60) {
        period = { name: "Matura R Problem Solving", focus: "Planimetria & high-weight exam arkusz practice", endMins: 17 * 60 };
      } else {
        period = { name: "Evening Recovery & Reflection", focus: "Honesty diary, recovery walk, wind-down", endMins: 22 * 60 };
      }
    } else {
      if (currentMins < 7 * 60 + 45) {
        period = { name: "Morning Discipline & Commute", focus: "Breakfast, hydration, transit to Technikum Mechatroniczne (TM1)", endMins: 7 * 60 + 45 };
      } else if (currentMins < 14 * 60 + 15) {
        period = { name: "School Instruction @ TM1", focus: "Classroom presence, defense on questions, note capture", endMins: 14 * 60 + 15 };
      } else if (currentMins < 15 * 60) {
        period = { name: "Post-School Transit & Fuel", focus: "Rapid commute to library / workstation & high-energy meal", endMins: 15 * 60 };
      } else if (currentMins < 18 * 60) {
        period = { name: "SGH Library Deep Work Session", focus: "United Study Protocol: School Defense (25m) -> Matura R (35m) -> LeetCode (25m)", endMins: 18 * 60, action: "Kill List" };
      } else if (currentMins < 20 * 60) {
        period = { name: "Physical Training / Boxing", focus: "Boxing workout, hypertrophy progression or evening dinner", endMins: 20 * 60 };
      } else if (currentMins < 22 * 60) {
        period = { name: "Honesty Diary & Tomorrow Lock", focus: "Log honest 60m output, review next day timetable, lock bedtime", endMins: 22 * 60 };
      } else {
        period = { name: "Sleep Floor (8h Recovery)", focus: "Screens off, bedroom cooled, preparing for 06:45 wake", endMins: 24 * 60 };
      }
    }

    titleEl.textContent = period.name;
    focusEl.textContent = period.focus;

    if (period.endMins) {
      const diff = period.endMins - currentMins;
      if (diff > 0) {
        const diffHrs = Math.floor(diff / 60);
        const diffMins = diff % 60;
        remPill.textContent = diffHrs > 0 ? `${diffHrs}h ${diffMins}m left` : `${diffMins}m left`;
      } else {
        remPill.textContent = "Block Ending";
      }
    } else {
      remPill.textContent = "Active";
    }

    if (actionArea) {
      if (period.action === "Kill List") {
        actionArea.innerHTML = `<button type="button" class="btn-primary" onclick="if (window.KillListDrawer) window.KillListDrawer.open('${this.selectedDateStr}');" style="font-size: 10px; padding: 3px 8px; font-family: var(--font-mono);">[KILL LIST]</button>`;
      } else {
        actionArea.innerHTML = "";
      }
    }
  },

  async toggleStudyBlock(blockKey) {
    if (this.completedBlocks.has(blockKey)) {
      this.completedBlocks.delete(blockKey);
    } else {
      this.completedBlocks.add(blockKey);
    }
    this.renderUnitedStudyCard();

    const strVal = Array.from(this.completedBlocks).join(",");
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.update_daily_log(
          this.selectedDateStr,
          null, null, null, null, null, null,
          strVal,
          null
        );
      }
    } catch (err) {
      console.error("[Today] Error persisting study block:", err);
    }
  },

  renderUnitedStudyCard() {
    const schoolDot = document.getElementById("checkStudySchool");
    const maturaDot = document.getElementById("checkStudyMatura");
    const codeDot = document.getElementById("checkStudyCode");
    const badge = document.getElementById("unitedStudyProgressBadge");

    const schoolDone = this.completedBlocks.has("study_school");
    const maturaDone = this.completedBlocks.has("study_matura");
    const codeDone = this.completedBlocks.has("study_code");

    if (schoolDot) {
      if (schoolDone) {
        schoolDot.classList.add("checked");
      } else {
        schoolDot.classList.remove("checked");
      }
    }
    if (maturaDot) {
      if (maturaDone) {
        maturaDot.classList.add("checked");
      } else {
        maturaDot.classList.remove("checked");
      }
    }
    if (codeDot) {
      if (codeDone) {
        codeDot.classList.add("checked");
      } else {
        codeDot.classList.remove("checked");
      }
    }

    const count = (schoolDone ? 1 : 0) + (maturaDone ? 1 : 0) + (codeDone ? 1 : 0);
    if (badge) {
      badge.textContent = `${count}/3 Completed`;
      if (count === 3) {
        badge.style.background = "#ffffff";
        badge.style.color = "#000000";
      } else {
        badge.style.background = "";
        badge.style.color = "";
      }
    }
  },

  async loadSchoolPlan(forceRefresh = false) {
    const container = document.getElementById("schoolLessonsList");
    if (!container) return;

    try {
      if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_school_plan) return;
      const res = await window.pywebview.api.get_school_plan(this.selectedDateStr, forceRefresh);
      const lessons = res.lessons || [];
      this.schoolLessons = lessons;

      if (lessons.length === 0) {
        container.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 4px 0;">No school lessons scheduled for this day.</div>`;
        return;
      }

      container.innerHTML = lessons
        .map(
          (l) => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); font-size: 11px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 10px; width: 14px;">${l.nr}</span>
            <span style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(l.subject)}</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); display: flex; gap: 6px;">
            <span>${l.time}</span>
            ${l.room ? `<span>s.${this.escapeHtml(l.room)}</span>` : ""}
            ${l.teacher ? `<span>(${this.escapeHtml(l.teacher)})</span>` : ""}
          </div>
        </div>
      `
        )
        .join("");
    } catch (err) {
      console.error("Error loading school plan:", err);
    }
  },

  async loadEasyLinks() {
    const container = document.getElementById("easyLinksContainer");
    if (!container) return;

    try {
      if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_easy_links) return;
      this.easyLinks = await window.pywebview.api.get_easy_links() || [];

      container.innerHTML = this.easyLinks
        .map((link, idx) => {
          let tag = "LINK";
          const lowerName = (link.name || "").toLowerCase();
          if (link.category === "school" || lowerName.includes("tm1")) tag = "TM1";
          else if (lowerName.includes("vulcan") || lowerName.includes("uonet")) tag = "VULCAN";
          else if (link.category === "contest" || lowerName.includes("sigg")) tag = "SIGG";
          else if (link.category === "university" || lowerName.includes("tum")) tag = "TUM";
          else if (link.category === "academics" || lowerName.includes("cke")) tag = "CKE";
          else if (link.category === "dev") tag = "DEV";

          return `
            <div 
              class="easy-link-btn" 
              onclick="window.pywebview.api.open_external_url('${link.url}')"
              title="${this.escapeHtml(link.desc || link.url)}"
            >
              <div class="easy-link-content">
                <span class="mono-chip lavender" style="font-size: 8px;">${tag}</span>
                <span class="easy-link-title">${this.escapeHtml(link.name)}</span>
              </div>
              <button 
                class="btn-ghost-icon" 
                style="padding: 1px 4px; font-size: 9px; opacity: 0.6;" 
                onclick="event.stopPropagation(); Today.openEditLinkModal(${idx})"
                title="Edit bookmark"
              >
                &bull;&bull;&bull;
              </button>
            </div>
          `;
        })
        .join("");

    } catch (err) {
      console.error("Error loading easy links:", err);
    }
  },

  // --- Native Modals for Links ---
  openAddLinkModal() {
    document.getElementById("linkModalTitle").textContent = "Add Quick Link";
    document.getElementById("linkFormIndex").value = "";
    document.getElementById("linkFormName").value = "";
    document.getElementById("linkFormUrl").value = "https://";
    document.getElementById("linkFormCategory").value = "custom";
    document.getElementById("linkFormDesc").value = "";
    document.getElementById("btnDeleteLink").style.display = "none";
    document.getElementById("quickLinkModal").classList.add("open");
  },

  openEditLinkModal(index) {
    const link = this.easyLinks[index];
    if (!link) return;
    document.getElementById("linkModalTitle").textContent = "Edit Quick Link";
    document.getElementById("linkFormIndex").value = index;
    document.getElementById("linkFormName").value = link.name;
    document.getElementById("linkFormUrl").value = link.url;
    document.getElementById("linkFormCategory").value = link.category || "custom";
    document.getElementById("linkFormDesc").value = link.desc || "";
    document.getElementById("btnDeleteLink").style.display = "inline-flex";
    document.getElementById("quickLinkModal").classList.add("open");
  },

  closeLinkModal() {
    document.getElementById("quickLinkModal").classList.remove("open");
  },

  async handleSaveLink() {
    const idxVal = document.getElementById("linkFormIndex").value;
    const name = document.getElementById("linkFormName").value.trim();
    const url = document.getElementById("linkFormUrl").value.trim();
    const category = document.getElementById("linkFormCategory").value;
    const desc = document.getElementById("linkFormDesc").value.trim();

    try {
      if (idxVal !== "") {
        await window.pywebview.api.update_easy_link(parseInt(idxVal, 10), name, url, category, desc);
        window.HarnessApp.showToast("Bookmark updated");
      } else {
        await window.pywebview.api.add_easy_link(name, url, category, desc);
        window.HarnessApp.showToast("Bookmark added");
      }
      this.closeLinkModal();
      await this.loadEasyLinks();
    } catch (err) {
      console.error("Error saving link:", err);
    }
  },

  async handleDeleteLink() {
    const idxVal = document.getElementById("linkFormIndex").value;
    if (idxVal === "") return;
    try {
      await window.pywebview.api.delete_easy_link(parseInt(idxVal, 10));
      this.closeLinkModal();
      await this.loadEasyLinks();
      window.HarnessApp.showToast("Bookmark removed");
    } catch (err) {
      console.error("Error deleting link:", err);
    }
  },

  // --- Homework & Exams ---
  async silentAutoSyncVulcan() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      if (window.pywebview.api.auto_sync_vulcan) {
        const res = await window.pywebview.api.auto_sync_vulcan(this.selectedDateStr);
        if (res && res.status !== "fresh") {
          await this.loadHomeworkAndExams();
          if (window.KillListDrawer) await window.KillListDrawer.load();
          if (window.Dashboard) await window.Dashboard.load();
          if (window.Tum) await window.Tum.load();
        }
      }
    } catch (err) {
      console.warn("Silent Vulcan auto-sync check:", err);
    }
  },

  initDaily3pmVulcanSync() {
    const check3pm = async () => {
      const now = new Date();
      const todayStr = now.toISOString().slice(0, 10);
      const isPast3pm = now.getHours() > 15 || (now.getHours() === 15 && now.getMinutes() >= 0);
      const last3pmDate = localStorage.getItem("harness_vulcan_3pm_last_date");

      if (isPast3pm && last3pmDate !== todayStr) {
        try {
          if (window.pywebview && window.pywebview.api) {
            const apiMethod = window.pywebview.api.check_daily_vulcan_sync || window.pywebview.api.auto_sync_vulcan;
            if (apiMethod) {
              const res = await apiMethod();
              if (res && (res.status === "synced" || res.status !== "fresh")) {
                localStorage.setItem("harness_vulcan_3pm_last_date", todayStr);
                await this.loadHomeworkAndExams();
                if (window.Dashboard) await window.Dashboard.load();
                if (window.Tum) await window.Tum.load();
                if (window.KillListDrawer) await window.KillListDrawer.load();
                if (window.HarnessApp && window.HarnessApp.showToast) {
                  window.HarnessApp.showToast("Vulcan 3:00 PM Auto-Sync completed: homework and grades updated.");
                }
              }
            }
          }
        } catch (e) {
          console.warn("Daily 3pm Vulcan sync error:", e);
        }
      }
    };

    check3pm();

    if (!this._daily3pmCheckInterval) {
      this._daily3pmCheckInterval = setInterval(check3pm, 60 * 1000);
    }

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        check3pm();
      }
    });
  },

  async loadHomeworkAndExams() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      if (window.pywebview.api.get_upcoming_homework) {
        this.homeworkList = await window.pywebview.api.get_upcoming_homework(this.selectedDateStr);
      }
      if (window.pywebview.api.get_upcoming_exams) {
        this.examsList = await window.pywebview.api.get_upcoming_exams();
      }
      this.renderHomeworkAndExams();
    } catch (err) {
      console.error("Error loading homework and exams:", err);
    }
  },

  renderHomeworkAndExams() {
    const hwContainer = document.getElementById("homeworkItemsList");
    const examContainer = document.getElementById("upcomingExamsList");
    const hwTotalBadge = document.getElementById("homeworkTotalCountBadge");
    const examTotalBadge = document.getElementById("examsTotalCountBadge");

    if (hwTotalBadge) {
      hwTotalBadge.textContent = `${this.homeworkList.length} Tasks Synced`;
    }
    if (examTotalBadge) {
      examTotalBadge.textContent = `${this.examsList.length}`;
    }

    if (hwContainer) {
      if (this.homeworkList.length === 0) {
        hwContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px 4px;">No pending homework. All caught up!</div>`;
      } else {
        // Active Horizon Radar: Expired homework is automatically deleted when deadline passes.
        // Group remaining active homework into:
        // 1. Due This Week (0 to 7 days)
        // 2. Upcoming Weeks (> 7 days)
        const dueThisWeek = this.homeworkList.filter((h) => h.days_left >= 0 && h.days_left <= 7);
        const dueLater = this.homeworkList.filter((h) => h.days_left > 7);

        const renderItem = (h) => {
          let dueBadge = `${h.due_date}`;
          let isUrgent = false;

          if (h.days_left === 0) {
            dueBadge = "TODAY";
            isUrgent = true;
          } else if (h.days_left === 1) {
            dueBadge = "TOMORROW";
            isUrgent = true;
          } else {
            dueBadge = `in ${h.days_left}d (${h.due_date})`;
          }

          const badgeColor = isUrgent
            ? "border-color: #f59e0b; color: #f59e0b;"
            : "border-color: rgba(196, 181, 253, 0.3); color: var(--accent-lavender);";

          return `
            <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 7px 9px; margin-bottom: 2px;">
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-bottom: 3px;">
                <div style="display: flex; align-items: center; gap: 6px; min-width: 0;">
                  <div class="check-dot ${h.completed ? "checked" : ""}" onclick="Today.toggleHomeworkItem(${h.id})" title="Mark completed"></div>
                  <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 700; white-space: nowrap;">
                    [${this.escapeHtml(h.subject)}]
                  </span>
                </div>
                <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
                  <span class="key-pill" style="font-size: 9px; padding: 1px 5px; ${badgeColor}">${dueBadge}</span>
                  <button class="btn-ghost-icon" style="padding: 1px 4px; font-size: 10px; color: var(--text-tertiary);" onclick="Today.deleteHomeworkItem(${h.id})" title="Delete">&times;</button>
                </div>
              </div>
              <div style="font-size: 11px; color: ${h.completed ? "var(--text-tertiary)" : "var(--text-primary)"}; text-decoration: ${h.completed ? "line-through" : "none"}; line-height: 1.35; white-space: pre-line; word-break: break-word; padding-left: 18px;">
                ${this.escapeHtml(h.title)}
              </div>
            </div>
          `;
        };

        let html = "";
        if (dueThisWeek.length > 0) {
          html += `<div style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--accent-lavender); text-transform: uppercase; letter-spacing: 0.05em; margin: 4px 0 2px 2px;">Due This Week (${dueThisWeek.length})</div>`;
          html += dueThisWeek.map(renderItem).join("");
        }

        if (dueLater.length > 0) {
          html += `<div style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin: 6px 0 2px 2px;">Upcoming Weeks (${dueLater.length})</div>`;
          html += dueLater.map(renderItem).join("");
        }

        hwContainer.innerHTML = html;
      }
    }

    if (examContainer) {
      if (this.examsList.length === 0) {
        examContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 4px 0;">No upcoming tests scheduled.</div>`;
      } else {
        examContainer.innerHTML = this.examsList
          .map((e) => {
            let countdown = `${e.days_left}d left`;
            if (e.days_left === 0) countdown = "TODAY";
            else if (e.days_left === 1) countdown = "TOMORROW";

            return `
              <div style="display: flex; justify-content: space-between; align-items: flex-start; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px; margin-bottom: 2px;">
                <div style="flex: 1; min-width: 0; padding-right: 6px;">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 700;">[${this.escapeHtml(e.subject)}]</span>
                    <span style="font-size: 10px; color: var(--text-tertiary); font-family: var(--font-mono);">${e.exam_date}</span>
                  </div>
                  <div style="font-size: 11px; color: var(--text-primary); margin-top: 2px; font-weight: 500; line-height: 1.3; word-break: break-word;">
                    ${this.escapeHtml(e.title)}
                  </div>
                  ${e.scope ? `<div style="font-size: 10px; color: var(--text-tertiary); margin-top: 2px; line-height: 1.25; word-break: break-word;">Zakres: ${this.escapeHtml(e.scope)}</div>` : ""}
                </div>
                <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
                  <span class="key-pill" style="font-size: 9px; color: var(--accent-purple-light); border-color: rgba(196, 181, 253, 0.3);">${countdown}</span>
                  <button class="btn-ghost-icon" style="padding: 1px 4px; font-size: 10px; color: var(--text-tertiary);" onclick="Today.deleteExamItem(${e.id})" title="Delete">&times;</button>
                </div>
              </div>
            `;
          })
          .join("");
      }
    }
  },

  async toggleHomeworkItem(id) {
    try {
      await window.pywebview.api.toggle_homework(id);
      await this.loadHomeworkAndExams();
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error toggling homework:", err);
    }
  },

  async deleteHomeworkItem(id) {
    try {
      await window.pywebview.api.delete_homework(id);
      await this.loadHomeworkAndExams();
      window.HarnessApp.showToast("Homework removed");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error deleting homework:", err);
    }
  },

  async deleteExamItem(id) {
    try {
      await window.pywebview.api.delete_exam(id);
      await this.loadHomeworkAndExams();
      window.HarnessApp.showToast("Exam removed");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error deleting exam:", err);
    }
  },

  openAddHomeworkModal() {
    document.getElementById("hwFormSubject").value = "Matematyka";
    document.getElementById("hwFormTitle").value = "";
    document.getElementById("hwFormDueDate").value = this.selectedDateStr;
    document.getElementById("addHomeworkModal").classList.add("open");
  },

  closeHomeworkModal() {
    document.getElementById("addHomeworkModal").classList.remove("open");
  },

  async handleSaveHomework() {
    const subject = document.getElementById("hwFormSubject").value.trim();
    const title = document.getElementById("hwFormTitle").value.trim();
    const dueDate = document.getElementById("hwFormDueDate").value;

    try {
      await window.pywebview.api.add_homework(subject, title, dueDate);
      this.closeHomeworkModal();
      await this.loadHomeworkAndExams();
      window.HarnessApp.showToast("Homework added");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error adding homework:", err);
    }
  },

  openAddExamModal() {
    document.getElementById("examFormSubject").value = "Matematyka";
    document.getElementById("examFormTitle").value = "";
    document.getElementById("examFormDate").value = this.selectedDateStr;
    document.getElementById("examFormScope").value = "";
    document.getElementById("addExamModal").classList.add("open");
  },

  closeExamModal() {
    document.getElementById("addExamModal").classList.remove("open");
  },

  async handleSaveExam() {
    const subject = document.getElementById("examFormSubject").value.trim();
    const title = document.getElementById("examFormTitle").value.trim();
    const date = document.getElementById("examFormDate").value;
    const scope = document.getElementById("examFormScope").value.trim();

    try {
      await window.pywebview.api.add_exam(subject, title, date, scope);
      this.closeExamModal();
      await this.loadHomeworkAndExams();
      window.HarnessApp.showToast("Exam scheduled");
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error adding exam:", err);
    }
  },

  renderInlineKillList(items = []) {
    const container = document.getElementById("todayInlineKillListContainer");
    const countBadge = document.getElementById("todayInlineKillCountBadge");
    const headerBadge = document.getElementById("todayKillListBadge");

    const total = items.length;
    const completed = items.filter((i) => i.completed).length;

    if (countBadge) {
      if (total > 0 && total < 3) {
        countBadge.innerHTML = `${completed} / ${total} Done <span onclick="KillListDrawer.autoPopulate()" style="cursor:pointer; color:var(--accent-lavender); font-weight:700; text-decoration:underline; margin-left:4px;" title="Auto-fill remaining slots">[+ Auto-Fill]</span>`;
        countBadge.className = "mono-chip lavender";
      } else {
        countBadge.textContent = `${completed} / ${total} Done`;
        countBadge.className = total >= 3 && completed >= total ? "mono-chip done" : "mono-chip lavender";
      }
    }
    if (headerBadge) {
      headerBadge.textContent = `${completed}/${total}`;
    }

    if (!container) return;

    if (total === 0) {
      container.innerHTML = `
        <div style="padding: 14px 16px; text-align: center; border: 1px dashed rgba(196, 181, 253, 0.25); border-radius: 6px; background: rgba(196, 181, 253, 0.02);">
          <div style="font-weight: 700; color: var(--accent-lavender); font-size: 12px; margin-bottom: 4px;">Zero Decisions Required • Session Ready</div>
          <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 12px;">Auto-populate dynamically balances Exam Defense, Urgent Homework, and TUM Heilbronn milestones based on this week's commitments.</div>
          <button type="button" class="btn-primary" onclick="KillListDrawer.autoPopulate()" style="padding: 8px 18px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; margin: 0 auto;">
            <span>Auto-Populate 3 Deep Work Targets</span>
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = items
      .map((item) => {
        const isDone = item.completed;
        const catLower = (item.category || "").toLowerCase();
        const catColor = catLower.includes("math")
          ? "#c4b5fd"
          : catLower.includes("german")
          ? "#6ee7b7"
          : catLower.includes("sigg")
          ? "#fdba74"
          : "#7dd3fc";

        const qtyBadge = item.quantity && item.quantity > 1
          ? `<span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--accent-lavender); background: rgba(196, 181, 253, 0.12); padding: 1px 4px; border-radius: 2px;">+${item.quantity} reps</span>`
          : "";

        let burndownPill = "";
        if (item.deliverable) {
          burndownPill = `
            <span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); margin-left: 6px;">
              [Burn-down: ${item.deliverable.completed_count}/${item.deliverable.total_required} ${item.deliverable.unit_label}]
            </span>
          `;
        }

        const actionIcon = (item.action_type || "").toLowerCase() === "pdf" ? "PDF" : (item.action_type || "").toLowerCase() === "workspace" ? "CODE" : "URL";

        return `
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 10px; background: rgba(255, 255, 255, 0.02); border: 1px solid ${isDone ? "rgba(255, 255, 255, 0.04)" : "rgba(255, 255, 255, 0.08)"}; border-radius: 4px; transition: all 0.12s ease;">
            <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;">
              <div 
                class="check-dot ${isDone ? "checked" : ""}" 
                onclick="KillListDrawer.toggleItem('${item.id}')"
                style="cursor: pointer; flex-shrink: 0;"
                title="Toggle complete"
              ></div>
              <div style="flex: 1; min-width: 0;">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: ${catColor}; text-transform: uppercase;">
                    ${this.escapeHtml(item.category)}
                  </span>
                  ${qtyBadge}
                  ${burndownPill}
                </div>
                <div style="font-size: 12px; font-weight: 500; color: ${isDone ? "var(--text-tertiary)" : "var(--text-primary)"}; text-decoration: ${isDone ? "line-through" : "none"}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px;">
                  ${this.escapeHtml(item.title)} ${item.target_spec ? `<span style="font-size: 10px; color: var(--text-secondary); font-weight: normal;">— ${this.escapeHtml(item.target_spec)}</span>` : ""}
                </div>
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
              <button 
                class="btn-ghost-icon" 
                onclick="KillListDrawer.launchItem('${item.action_type}', '${this.escapeJs(item.target_path)}')"
                title="Launch ${item.action_type}"
                style="padding: 2px 6px; font-size: 10px;"
              >
                ${actionIcon}
              </button>
              <button 
                class="btn-ghost-icon" 
                onclick="KillListDrawer.deleteItem('${item.id}')"
                title="Delete item"
                style="padding: 2px 6px; font-size: 10px; color: var(--text-tertiary);"
              >
                &times;
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  },

  async syncVulcan(forceRefresh = false) {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.sync_vulcan_data) {
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Connecting to Vulcan / eduVULCAN...");
        }
        const res = await window.pywebview.api.sync_vulcan_data(this.selectedDateStr, forceRefresh);
        await this.load(this.selectedDateStr);
        await this.loadHomeworkAndExams();
        if (window.KillListDrawer && window.KillListDrawer.isOpen) {
          await window.KillListDrawer.load();
        }
        if (window.MetroMap) {
          await window.MetroMap.load();
        }
        if (window.Tum) {
          await window.Tum.load();
        }
        const examsCount = res && res.exams_synced !== undefined ? res.exams_synced : 0;
        const hwCount = res && res.homework_synced !== undefined ? res.homework_synced : 0;
        const gradesCount = res && res.grades_synced !== undefined ? res.grades_synced : 0;
        const mode = res && res.mode === "live" ? "Live Account" : "TM1 Simulator";
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast(`Vulcan Synced [${mode}]: ${examsCount} exams, ${hwCount} homework, ${gradesCount} grades.`);
        }
      }
    } catch (err) {
      console.error("Error syncing Vulcan:", err);
      alert(err.message || "Failed to sync Vulcan data");
    }
  },

  async openVulcanConfig() {
    const modal = document.getElementById("vulcanConfigModal");
    if (!modal) return;
    modal.classList.add("open");

    const dateInput = document.getElementById("manualExamDate");
    if (dateInput && !dateInput.value) {
      dateInput.value = this.selectedDateStr || this.getLocalDateStr();
    }

    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_vulcan_status) {
        const status = await window.pywebview.api.get_vulcan_status();
        this.renderVulcanStatus(status);
      }
    } catch (e) {
      console.warn("Could not load vulcan status:", e);
    }
  },

  closeVulcanConfig() {
    const modal = document.getElementById("vulcanConfigModal");
    if (modal) modal.classList.remove("open");
  },

  renderVulcanStatus(status) {
    if (!status) return;
    const badge = document.getElementById("vulcanStatusModeBadge");
    const nameEl = document.getElementById("vulcanStudentName");
    const infoEl = document.getElementById("vulcanSchoolInfo");
    const syncEl = document.getElementById("vulcanLastSyncTime");

    const isLive = status.is_connected || status.mode === "live";

    if (badge) {
      badge.textContent = isLive ? `LIVE (${(status.student_symbol || "Warszawa").toUpperCase()})` : "DEMO SIMULATOR";
      badge.className = isLive ? "mono-chip emerald" : "mono-chip";
      if (isLive) {
        badge.style.background = "rgba(16, 185, 129, 0.15)";
        badge.style.color = "#34d399";
        badge.style.border = "1px solid rgba(16, 185, 129, 0.35)";
      } else {
        badge.style.background = "";
        badge.style.color = "";
        badge.style.border = "";
      }
    }

    if (nameEl) {
      nameEl.textContent = status.student_name || "Janek Smagieł";
    }

    if (infoEl) {
      const symbolStr = status.student_symbol ? `Symbol: ${status.student_symbol}` : "Symbol: Warszawa";
      const schoolStr = status.school_name ? ` • ${status.school_name}` : " • TM1 Mechatroniczne";
      const liveNotice = isLive ? " [Linked via eduVULCAN JWT]" : " [Realistic TM1 Schedule Simulator]";
      infoEl.textContent = `${symbolStr}${schoolStr}${liveNotice}`;
    }

    if (syncEl) {
      if (status.last_synced_at) {
        try {
          const dt = new Date(status.last_synced_at);
          syncEl.textContent = `Last Sync: ${dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
        } catch (e) {
          syncEl.textContent = `Last Sync: ${status.last_synced_at.slice(11, 16)}`;
        }
      } else {
        syncEl.textContent = "Last Sync: Not yet synced";
      }
    }
  },

  switchVulcanModalTab(tabName) {
    const tabs = ["connect", "manual", "demo"];
    tabs.forEach((t) => {
      const btn = document.getElementById(`vulcanTabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
      const pane = document.getElementById(`vulcanTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
      if (btn) {
        if (t === tabName) {
          btn.style.color = "var(--accent-lavender)";
          btn.style.borderColor = "rgba(196, 181, 253, 0.4)";
        } else {
          btn.style.color = "var(--text-tertiary)";
          btn.style.borderColor = "transparent";
        }
      }
      if (pane) {
        pane.style.display = t === tabName ? "block" : "none";
      }
    });
  },

  openEduVulcanWebTokenPage() {
    const url = "https://eduvulcan.pl/api/ap";
    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_external_url) {
      window.pywebview.api.open_external_url(url);
    } else {
      window.open(url, "_blank");
    }
    if (window.HarnessApp && window.HarnessApp.showToast) {
      window.HarnessApp.showToast("Opening eduvulcan.pl/api/ap. Copy the token and paste it here.");
    }
  },

  async submitVulcanToken() {
    const input = document.getElementById("vulcanTokenInput");
    if (!input) return;
    const tokenVal = input.value.trim();
    if (!tokenVal) {
      alert("Please paste your token string or JSON from https://eduvulcan.pl/api/ap first.");
      return;
    }

    try {
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast("Generating RSA certificate & pairing with eduVULCAN...");
      }
      if (window.pywebview && window.pywebview.api && window.pywebview.api.register_eduvulcan) {
        const res = await window.pywebview.api.register_eduvulcan(tokenVal);
        if (res && res.success) {
          input.value = "";
          if (window.HarnessApp && window.HarnessApp.showToast) {
            window.HarnessApp.showToast(`eduVULCAN Linked: ${res.student_name || "Student"} (${res.school || res.symbol})! Synced ${res.exams_synced || 0} exams.`);
          }
          await this.openVulcanConfig();
          await this.load(this.selectedDateStr);
          if (window.KillListDrawer && window.KillListDrawer.isOpen) {
            await window.KillListDrawer.load();
          }
        } else {
          alert((res && res.error) || "Failed to pair with eduVULCAN. Please check your token.");
        }
      }
    } catch (err) {
      console.error("Error pairing eduVULCAN:", err);
      alert(err.message || "Failed to register eduVULCAN");
    }
  },

  async disconnectVulcan() {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.disconnect_vulcan) {
        await window.pywebview.api.disconnect_vulcan();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Disconnected eduVULCAN. Switched to TM1 Simulator Mode.");
        }
        await this.openVulcanConfig();
        await this.load(this.selectedDateStr);
      }
    } catch (err) {
      console.error("Error disconnecting Vulcan:", err);
    }
  },

  async handleManualExamSubmit(event) {
    if (event) event.preventDefault();
    const subjInput = document.getElementById("manualExamSubject");
    const titleInput = document.getElementById("manualExamTitle");
    const dateInput = document.getElementById("manualExamDate");
    const scopeInput = document.getElementById("manualExamScope");
    const weightInput = document.getElementById("manualExamWeight");

    if (!subjInput || !titleInput || !dateInput) return;

    const subject = subjInput.value.trim();
    const title = titleInput.value.trim();
    const examDate = dateInput.value.trim();
    const scope = scopeInput ? scopeInput.value.trim() : "";
    const weight = weightInput ? parseInt(weightInput.value, 10) || 2 : 2;

    if (!subject || !title || !examDate) {
      alert("Please fill in subject, title, and exam date.");
      return;
    }

    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.add_manual_exam) {
        await window.pywebview.api.add_manual_exam(subject, title, examDate, scope, weight);
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast(`Saved exam: ${title} (${subject}) on ${examDate}`);
        }
        subjInput.value = "";
        titleInput.value = "";
        if (scopeInput) scopeInput.value = "";
        this.closeVulcanConfig();
        await this.load(this.selectedDateStr);
        if (window.KillListDrawer && window.KillListDrawer.isOpen) {
          await window.KillListDrawer.load();
        }
      }
    } catch (err) {
      console.error("Error adding manual exam:", err);
      alert(err.message || "Failed to add manual exam");
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

  escapeJs(str) {
    if (!str) return "";
    return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  },
};

window.Today = Today;
