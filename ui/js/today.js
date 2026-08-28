/**
 * Today Layer: Execution, task management, rollover, sleep, and scratchpad.
 */

const Today = {
  tasks: [],
  debounceTimer: null,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    // Form submit
    const taskForm = document.getElementById("taskForm");
    if (taskForm) {
      taskForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleAddTask();
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
      scratchpad.addEventListener("input", () => {
        this.debounceSaveDailyLog();
      });
    }

    // Wake / sleep inputs
    const wakeInput = document.getElementById("wakeTimeInput");
    const sleepInput = document.getElementById("sleepTimeInput");
    if (wakeInput) {
      wakeInput.addEventListener("change", () => this.saveDailyLog());
    }
    if (sleepInput) {
      sleepInput.addEventListener("change", () => this.saveDailyLog());
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      const data = await window.pywebview.api.get_today();
      this.tasks = data.tasks || [];
      this.renderTasks();

      if (data.log) {
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
    } catch (err) {
      console.error("Error loading Today data:", err);
    }
  },

  renderTasks() {
    const listEl = document.getElementById("taskList");
    if (!listEl) return;

    if (this.tasks.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--text-dim); border: 1px dashed var(--border-dim); border-radius: 6px;">
          No tasks scheduled for today. Press 'N' to add your first high-leverage rep.
        </div>
      `;
      return;
    }

    listEl.innerHTML = this.tasks
      .map((task) => {
        const isTumClass = task.is_tum ? "is-tum" : "";
        const completedClass = task.completed ? "completed" : "";
        const checkedAttr = task.completed ? "checked" : "";

        return `
          <div class="task-item ${isTumClass} ${completedClass}" data-id="${task.id}">
            <input 
              type="checkbox" 
              class="task-checkbox" 
              ${checkedAttr}
              onchange="Today.toggleTask(${task.id})"
            />
            <div class="task-content">
              <span class="task-title">${this.escapeHtml(task.title)}</span>
              <div class="task-badges">
                ${task.is_tum ? '<span class="badge badge-tum">TUM Imperative</span>' : ""}
                ${
                  task.rollover_count > 0
                    ? `<span class="badge badge-rollover" title="Rolled over from earlier day">Rolled ${task.rollover_count}x</span>`
                    : ""
                }
                <span class="badge badge-cat">${task.category}</span>
              </div>
            </div>
            <div class="task-actions">
              <button class="btn-icon" title="Delete task" onclick="Today.deleteTask(${task.id})">
                &times;
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  },

  async handleAddTask() {
    const titleInput = document.getElementById("taskTitleInput");
    const categorySelect = document.getElementById("taskCategorySelect");
    const tumCheckbox = document.getElementById("taskIsTumCheckbox");

    const title = titleInput.value.trim();
    if (!title) return;

    const category = categorySelect.value;
    const isTum = tumCheckbox.checked;

    try {
      const newTask = await window.pywebview.api.add_task(title, category, isTum);
      this.tasks.unshift(newTask);
      this.renderTasks();

      // Reset form
      titleInput.value = "";
      tumCheckbox.checked = false;
      window.HarnessApp.showToast("Task added to today's execution");
    } catch (err) {
      console.error("Error adding task:", err);
    }
  },

  async toggleTask(taskId) {
    try {
      const res = await window.pywebview.api.toggle_task(taskId);
      const target = this.tasks.find((t) => t.id === taskId);
      if (target) {
        target.completed = res.completed;
        target.completed_at = res.completed_at;
      }
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
      if (count > 0) {
        window.HarnessApp.showToast(`Carried forward ${count} pending task(s)`);
      } else {
        window.HarnessApp.showToast("No pending tasks to carry forward");
      }
    } catch (err) {
      console.error("Error performing rollover:", err);
    }
  },

  debounceSaveDailyLog() {
    clearTimeout(this.debounceTimer);
    const indicator = document.getElementById("scratchpadSaveIndicator");
    if (indicator) indicator.textContent = "Saving...";

    this.debounceTimer = setTimeout(async () => {
      await this.saveDailyLog();
      if (indicator) indicator.textContent = "Saved";
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
