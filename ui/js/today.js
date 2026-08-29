/**
 * Section 1: TODAY (Zero-Friction Daily Execution Engine)
 * Automatically loads Schedule A/B/C, pre-loads structured gym routines,
 * persists block & exercise checkmarks, handles quick tasks, scratchpad, and sleep times.
 */

const Today = {
  tasks: [],
  schedule: null,
  gymRoutine: null,
  completedBlocks: new Set(),
  completedExercises: new Set(),
  debounceTimer: null,

  async init() {
    this.bindEvents();
    await this.load();
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

    // Rollover button
    const btnRollover = document.getElementById("btnRollover");
    if (btnRollover) {
      btnRollover.addEventListener("click", async () => {
        await this.handleRollover();
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

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      const data = await window.pywebview.api.get_today();
      this.tasks = data.tasks || [];
      this.schedule = data.schedule || null;
      this.gymRoutine = data.gym_routine || null;

      // Parse persisted completed blocks & exercises
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
              title="Click to check off routine block"
            ></div>
            <div class="routine-time">${block.time}</div>
            <div class="routine-info">
              <div class="routine-focus" style="${isChecked ? "text-decoration: line-through; color: var(--text-tertiary);" : ""}">${this.escapeHtml(block.focus)}</div>
              <div class="routine-activity">${this.escapeHtml(block.activity)}</div>
            </div>
            ${isDeepWork ? '<span class="key-pill" style="color: #ffffff; border-color: rgba(255,255,255,0.3);">TUM Focus</span>' : ""}
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
        await window.pywebview.api.update_daily_log(
          null, null, null, null, null, null, null,
          strVal,
          null
        );
      }
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
    if (titleEl) titleEl.textContent = `LIFT TODAY • ${this.gymRoutine.name}`;

    const exercises = this.gymRoutine.exercises || [];
    exercisesContainer.innerHTML = exercises
      .map((ex, idx) => {
        const isChecked = this.completedExercises.has(String(idx));
        return `
          <div class="lift-exercise-row">
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
        await window.pywebview.api.update_daily_log(
          null, null, null, null, null, null, null,
          null,
          strVal
        );
      }
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
            <button class="btn-ghost-icon" style="padding: 2px 6px;" onclick="Today.deleteTask(${t.id})">&times;</button>
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
      const newTask = await window.pywebview.api.add_task(title, "personal", false);
      this.tasks.unshift(newTask);
      this.renderTasks();
      input.value = "";
      window.HarnessApp.showToast("Task added");
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
    } catch (err) {
      console.error("Error deleting task:", err);
    }
  },

  async handleRollover() {
    try {
      const count = await window.pywebview.api.rollover_tasks();
      await this.load();
      window.HarnessApp.showToast(count > 0 ? `Carried forward ${count} pending item(s)` : "No pending items to carry forward");
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
          null,
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

window.Today = Today;
