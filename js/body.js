/**
 * Body Layer: Machine maintenance, mass progress, structured gym protocols, and weigh-in logging.
 */

const Body = {
  summary: null,
  gymConfigs: null,
  activeGymTab: "tuesday",

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    // Weigh-in form
    const bodyForm = document.getElementById("bodyMetricForm");
    if (bodyForm) {
      bodyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleLogMetric();
      });
    }

    // Workout form
    const workoutForm = document.getElementById("workoutLogForm");
    if (workoutForm) {
      workoutForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleLogWorkout();
      });
    }

    // Gym tabs
    const tabTue = document.getElementById("tabGymTuesday");
    const tabThu = document.getElementById("tabGymThursday");
    if (tabTue) {
      tabTue.addEventListener("click", () => {
        tabTue.classList.add("active");
        tabThu?.classList.remove("active");
        this.activeGymTab = "tuesday";
        this.renderGymProtocol();
      });
    }
    if (tabThu) {
      tabThu.addEventListener("click", () => {
        tabThu.classList.add("active");
        tabTue?.classList.remove("active");
        this.activeGymTab = "thursday";
        this.renderGymProtocol();
      });
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.summary = await window.pywebview.api.get_body_summary();
      const configs = await window.pywebview.api.get_all_configs();
      this.gymConfigs = configs.gym_routines?.routines || null;

      this.renderSummary();
      this.renderGymProtocol();
    } catch (err) {
      console.error("Error loading Body data:", err);
    }
  },

  renderSummary() {
    if (!this.summary) return;

    const weightEl = document.getElementById("currentWeightDisplay");
    const barFill = document.getElementById("weightProgressBar");

    if (weightEl) weightEl.textContent = this.summary.current_weight.toFixed(1);
    if (barFill) {
      const pct = Math.min(100, Math.max(3, this.summary.progress_percentage));
      barFill.style.width = `${pct}%`;
    }
  },

  renderGymProtocol() {
    const container = document.getElementById("gymRoutineDisplay");
    if (!container || !this.gymConfigs) return;

    const routine = this.gymConfigs[this.activeGymTab];
    if (!routine) {
      container.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary);">No routine configured.</div>`;
      return;
    }

    const exercises = routine.exercises || [];
    container.innerHTML = `
      <div style="margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(routine.name)}</div>
        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(routine.focus)}</div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${exercises
          .map((ex, idx) => {
            return `
              <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-hairline); border-radius: 4px; padding: 8px 10px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                  <span style="font-weight: 500; font-size: 12px; color: var(--text-primary);">
                    ${idx + 1}. ${this.escapeHtml(ex.name)}
                  </span>
                  <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">
                    ${ex.sets} &times; ${ex.reps} (${ex.rest} rest)
                  </span>
                </div>
                ${
                  ex.notes
                    ? `<div style="font-size: 10px; color: var(--text-tertiary); margin-top: 4px; line-height: 1.3;">
                         ${this.escapeHtml(ex.notes)}
                       </div>`
                    : ""
                }
              </div>
            `;
          })
          .join("")}
      </div>
    `;
  },

  async handleLogMetric() {
    const input = document.getElementById("logWeightInput");
    const calories = document.getElementById("logCaloriesMet")?.checked || false;
    const protein = document.getElementById("logProteinMet")?.checked || false;

    const val = parseFloat(input?.value);
    if (!val || val <= 0) return;

    try {
      await window.pywebview.api.log_body_metric(val, calories, protein);
      if (input) input.value = "";
      await this.load();
      window.HarnessApp.showToast("Weigh-in recorded");
    } catch (err) {
      console.error("Error logging weigh-in:", err);
    }
  },

  async handleLogWorkout() {
    const typeSelect = document.getElementById("logWorkoutType");
    const detailsInput = document.getElementById("logWorkoutDetails");

    const wType = typeSelect?.value || "gym";
    const details = detailsInput?.value.trim() || "";
    if (!details) return;

    try {
      await window.pywebview.api.log_workout(wType, details, 8);
      if (detailsInput) detailsInput.value = "";
      await this.load();
      window.HarnessApp.showToast("Training session logged");
    } catch (err) {
      console.error("Error logging workout:", err);
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

window.Body = Body;
