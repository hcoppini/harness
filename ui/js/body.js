/**
 * Body / Life Layer: Machine maintenance, weigh-in, training, and routine tracking.
 */

const Body = {
  summary: null,

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
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.summary = await window.pywebview.api.get_body_summary();
      this.render();
    } catch (err) {
      console.error("Error loading body data:", err);
    }
  },

  render() {
    if (!this.summary) return;

    // Weight progress
    const weightEl = document.getElementById("currentWeightDisplay");
    const barFill = document.getElementById("weightProgressBar");
    if (weightEl) weightEl.textContent = this.summary.current_weight.toFixed(1);
    if (barFill) barFill.style.width = Math.min(100, Math.max(2, this.summary.progress_percentage)) + "%";

    // Weekly metrics
    const boxingEl = document.getElementById("boxingCountDisplay");
    const gymEl = document.getElementById("gymCountDisplay");
    const runEl = document.getElementById("runCountDisplay");

    if (boxingEl) {
      boxingEl.textContent = `${this.summary.weekly_counts.boxing} / ${this.summary.weekly_targets.boxing}`;
    }
    if (gymEl) {
      gymEl.textContent = `${this.summary.weekly_counts.gym} / ${this.summary.weekly_targets.gym}`;
    }
    if (runEl) {
      runEl.textContent = `${this.summary.weekly_counts.running} / ${this.summary.weekly_targets.running}`;
    }

    // Recent workouts
    const listEl = document.getElementById("recentWorkoutsList");
    if (listEl && this.summary.recent_workouts) {
      if (this.summary.recent_workouts.length === 0) {
        listEl.innerHTML = `<div style="font-size: 12px; color: var(--text-dim); padding: 12px 0;">No workouts logged yet this week.</div>`;
      } else {
        listEl.innerHTML = this.summary.recent_workouts
          .map((w) => {
            const typeColors = {
              boxing: "var(--accent-gold)",
              gym: "var(--accent-cyan)",
              running: "var(--accent-green)",
            };
            const col = typeColors[w.workout_type] || "var(--text-main)";

            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-primary); border: 1px solid var(--border-dim); padding: 8px 12px; border-radius: 4px; font-size: 12px;">
                <div>
                  <span style="font-weight: 700; text-transform: uppercase; color: ${col}; font-family: var(--font-mono); margin-right: 8px;">
                    ${w.workout_type}
                  </span>
                  <span style="color: var(--text-main);">${this.escapeHtml(w.details)}</span>
                </div>
                <div style="font-family: var(--font-mono); color: var(--text-dim); font-size: 11px;">
                  Intensity: ${w.intensity}/10 | ${w.date}
                </div>
              </div>
            `;
          })
          .join("");
      }
    }
  },

  async handleLogMetric() {
    const input = document.getElementById("logWeightInput");
    const calories = document.getElementById("logCaloriesMet")?.checked || false;
    const protein = document.getElementById("logProteinMet")?.checked || false;

    const val = parseFloat(input.value);
    if (!val || val <= 0) return;

    try {
      await window.pywebview.api.log_body_metric(val, calories, protein);
      input.value = "";
      await this.load();
      window.HarnessApp.showToast("Weigh-in recorded");
    } catch (err) {
      console.error("Error saving weigh-in:", err);
    }
  },

  async handleLogWorkout() {
    const typeSelect = document.getElementById("logWorkoutType");
    const detailsInput = document.getElementById("logWorkoutDetails");
    const intensityInput = document.getElementById("logWorkoutIntensity");

    const wType = typeSelect.value;
    const details = detailsInput.value.trim();
    const intensity = parseInt(intensityInput.value, 10) || 7;

    if (!details) return;

    try {
      await window.pywebview.api.log_workout(wType, details, intensity);
      detailsInput.value = "";
      await this.load();
      window.HarnessApp.showToast("Workout session logged");
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
