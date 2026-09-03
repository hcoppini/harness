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

  // Calendar Navigation (defaults to today)
  currentDateStr: new Date().toISOString().split("T")[0],
  selectedDateStr: new Date().toISOString().split("T")[0],
  calDisplayYear: new Date().getFullYear(),
  calDisplayMonth: new Date().getMonth(), // 0-indexed

  async init() {
    this.bindEvents();
    this.renderMiniCalendar();
    await this.load(this.selectedDateStr);
    await this.loadSchoolPlan();
    await this.loadEasyLinks();
    await this.loadHomeworkAndExams();
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
        const todayStr = new Date().toISOString().split("T")[0];
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
          await window.pywebview.api.open_external_url("http://planlekcji2.staff.edu.pl/plany/o6.html");
        }
      });
    }

    // Scratchpad auto-save
    const scratchpad = document.getElementById("scratchpadTextarea");
    if (scratchpad) {
      scratchpad.addEventListener("input", () => this.debounceSaveDailyLog());
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

    const todayStr = new Date().toISOString().split("T")[0];

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
    } catch (err) {
      console.error("Error loading Today data:", err);
    }
  },

  renderSchedule() {
    const badgeEl = document.getElementById("scheduleBadge");
    const dayNameEl = document.getElementById("scheduleDayName");
    const descEl = document.getElementById("scheduleDescription");
    const blocksContainer = document.getElementById("routineBlocksContainer");

    if (!this.schedule || !blocksContainer) return;

    if (badgeEl) badgeEl.textContent = this.schedule.key ? `SCHEDULE ${this.schedule.key.replace("C_", "")}` : "DAILY";
    if (dayNameEl) dayNameEl.textContent = `${this.schedule.weekday || ""} • ${this.schedule.name || ""}`;
    if (descEl) descEl.textContent = this.schedule.description || "";

    const blocks = this.schedule.blocks || [];
    blocksContainer.innerHTML = blocks
      .map((block, idx) => {
        const isDeepWork = block.type === "deep_work";
        const isChecked = this.completedBlocks.has(String(idx));
        return `
          <div class="routine-block ${isDeepWork ? "deep-work" : ""}">
            <div 
              class="check-dot ${isChecked ? "checked" : ""}" 
              onclick="Today.toggleRoutineBlock(${idx})"
              title="Check off routine block"
            ></div>
            <div class="routine-time">${block.time}</div>
            <div class="routine-info">
              <div class="routine-focus" style="${isChecked ? "text-decoration: line-through; color: var(--text-tertiary);" : ""}">${this.escapeHtml(block.focus)}</div>
              <div class="routine-activity">${this.escapeHtml(block.activity)}</div>
            </div>
            ${isDeepWork ? '<span class="key-pill" style="color: var(--accent-purple-light); border-color: var(--accent-purple-glow);">TUM Focus</span>' : ""}
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
    if (titleEl) titleEl.textContent = `STRUCTURED LIFT • ${this.gymRoutine.name}`;

    const exercises = this.gymRoutine.exercises || [];
    exercisesContainer.innerHTML = exercises
      .map((ex, idx) => {
        const isChecked = this.completedExercises.has(String(idx));
        return `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div 
                class="check-dot ${isChecked ? "checked" : ""}" 
                onclick="Today.toggleGymExercise(${idx})"
                title="Mark exercise complete"
              ></div>
              <span style="font-weight: 500; color: ${isChecked ? "var(--text-tertiary); text-decoration: line-through;" : "var(--text-primary);"}">
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
      const target = this.tasks.find((t) => t.id === taskId);
      if (target) target.completed = res.completed;
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
    if (pill) pill.textContent = "Saving...";

    this.debounceTimer = setTimeout(async () => {
      await this.saveDailyLog();
      if (pill) pill.textContent = "Saved";
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
  async loadHomeworkAndExams() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      if (window.pywebview.api.get_upcoming_homework) {
        this.homeworkList = await window.pywebview.api.get_upcoming_homework();
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

    if (hwContainer) {
      if (this.homeworkList.length === 0) {
        hwContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary);">No pending homework due.</div>`;
      } else {
        hwContainer.innerHTML = this.homeworkList
          .map((h) => {
            let dueBadge = `${h.due_date}`;
            if (h.days_left === 0) dueBadge = "Today";
            else if (h.days_left === 1) dueBadge = "Tomorrow";
            else if (h.days_left < 0) dueBadge = `${Math.abs(h.days_left)}d overdue`;
            else dueBadge = `in ${h.days_left}d`;

            const isOverdue = h.days_left < 0;

            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px;">
                <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 72%;">
                  <div class="check-dot ${h.completed ? "checked" : ""}" onclick="Today.toggleHomeworkItem(${h.id})"></div>
                  <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 600;">[${this.escapeHtml(h.subject)}]</span>
                  <span style="font-size: 12px; color: var(--text-primary);">${this.escapeHtml(h.title)}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                  <span class="key-pill" style="font-size: 9px; ${isOverdue ? "border-color: #ef4444; color: #ef4444;" : ""}">${dueBadge}</span>
                  <button class="btn-ghost-icon" style="padding: 1px 4px; font-size: 10px;" onclick="Today.deleteHomeworkItem(${h.id})">&times;</button>
                </div>
              </div>
            `;
          })
          .join("");
      }
    }

    if (examContainer) {
      if (this.examsList.length === 0) {
        examContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary);">No upcoming tests scheduled.</div>`;
      } else {
        examContainer.innerHTML = this.examsList
          .map((e) => {
            let countdown = `${e.days_left}d left`;
            if (e.days_left === 0) countdown = "TODAY";
            else if (e.days_left === 1) countdown = "TOMORROW";

            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px;">
                <div>
                  <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 600;">[${this.escapeHtml(e.subject)}]</span>
                  <span style="font-size: 12px; color: var(--text-primary); margin-left: 4px; font-weight: 500;">${this.escapeHtml(e.title)}</span>
                  ${e.scope ? `<div style="font-size: 10px; color: var(--text-tertiary); margin-top: 2px;">Scope: ${this.escapeHtml(e.scope)}</div>` : ""}
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                  <span class="key-pill" style="font-size: 9px; color: var(--accent-purple-light);">${countdown}</span>
                  <button class="btn-ghost-icon" style="padding: 1px 4px; font-size: 10px;" onclick="Today.deleteExamItem(${e.id})">&times;</button>
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

window.Today = Today;
