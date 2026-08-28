/**
 * TUM Layer: Direction, dependency roadmap, grade tracker, Matura benchmarks, German ladder.
 */

const Tum = {
  data: null,
  activeSemester: 1,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    const semButtons = document.querySelectorAll("#semesterFilterButtons button");
    semButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        semButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeSemester = parseInt(btn.getAttribute("data-sem"), 10);
        this.renderGradesTable();
      });
    });
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.data = await window.pywebview.api.get_tum_overview();
      this.renderSummary();
      this.renderMaturaTable();
      this.renderLanguageLadder();
      this.renderGradesTable();
    } catch (err) {
      console.error("Error loading TUM data:", err);
    }
  },

  renderSummary() {
    if (!this.data) return;

    const gpaEl = document.getElementById("tumGpaVal");
    const riskEl = document.getElementById("tumRiskVal");
    const germanEl = document.getElementById("tumGermanVal");

    if (gpaEl) {
      gpaEl.textContent = this.data.overall_gpa > 0 ? this.data.overall_gpa.toFixed(2) : "5.00 (Est)";
    }

    if (riskEl) {
      riskEl.textContent = this.data.grades_under_four;
      riskEl.style.color = this.data.grades_under_four > 0 ? "var(--accent-red)" : "var(--accent-green)";
    }

    if (germanEl && this.data.language) {
      const active = this.data.language.find((l) => l.status === "in_progress");
      germanEl.textContent = active ? active.level + " (Active)" : "B1 Target";
    }
  },

  renderMaturaTable() {
    const tbody = document.getElementById("maturaTableBody");
    if (!tbody || !this.data || !this.data.matura) return;

    tbody.innerHTML = this.data.matura
      .map((item) => {
        const isReady = item.current_mock_percentage >= item.target_percentage;
        const color = item.current_mock_percentage > 0 ? (isReady ? "var(--accent-green)" : "var(--accent-gold)") : "var(--text-dim)";

        return `
          <tr>
            <td style="font-weight: 600; color: var(--text-main);">
              ${item.subject}
              <div style="font-size: 11px; color: var(--text-dim); font-weight: normal;">${item.notes || ""}</div>
            </td>
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-cyan);">
              &ge; ${item.target_percentage}%
            </td>
            <td>
              <div style="display: flex; align-items: center; gap: 8px;">
                <input 
                  type="number" 
                  min="0" 
                  max="100" 
                  value="${item.current_mock_percentage || ""}" 
                  placeholder="0"
                  class="text-input" 
                  style="width: 70px; font-weight: 700; color: ${color};"
                  onchange="Tum.updateMaturaScore(${item.id}, this.value)"
                />
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--text-dim);">%</span>
              </div>
            </td>
            <td>
              <span class="badge" style="background: ${isReady ? "var(--accent-green-bg)" : "var(--bg-tertiary)"}; color: ${isReady ? "var(--accent-green)" : "var(--text-muted)"};">
                ${isReady ? "Target Met" : "In Prep"}
              </span>
            </td>
          </tr>
        `;
      })
      .join("");
  },

  renderLanguageLadder() {
    const tbody = document.getElementById("languageTableBody");
    if (!tbody || !this.data || !this.data.language) return;

    tbody.innerHTML = this.data.language
      .map((item) => {
        const statusBadges = {
          completed: `<span class="badge" style="background: var(--accent-green-bg); color: var(--accent-green);">Completed</span>`,
          in_progress: `<span class="badge badge-tum">Active Focus</span>`,
          pending: `<span class="badge badge-cat">Pending</span>`,
        };

        return `
          <tr>
            <td style="font-family: var(--font-mono); font-weight: 800; font-size: 14px; color: var(--accent-gold);">
              ${item.level}
            </td>
            <td style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
              ${item.target_date || "--"}
            </td>
            <td style="color: var(--text-main);">
              ${item.milestone_description}
            </td>
            <td>
              <select 
                class="category-select" 
                onchange="Tum.updateLanguageStatus('${item.level}', this.value)"
                style="font-family: var(--font-mono);"
              >
                <option value="pending" ${item.status === "pending" ? "selected" : ""}>Pending</option>
                <option value="in_progress" ${item.status === "in_progress" ? "selected" : ""}>In Progress</option>
                <option value="completed" ${item.status === "completed" ? "selected" : ""}>Completed</option>
              </select>
            </td>
          </tr>
        `;
      })
      .join("");
  },

  renderGradesTable() {
    const tbody = document.getElementById("gradesTableBody");
    if (!tbody || !this.data || !this.data.semesters) return;

    const list = this.data.semesters[this.activeSemester] || [];
    tbody.innerHTML = list
      .map((grade) => {
        const actual = grade.actual_grade;
        const isUnderFour = actual !== null && actual < 4.0;
        const statusColor = actual === null ? "var(--text-dim)" : isUnderFour ? "var(--accent-red)" : "var(--accent-green)";

        return `
          <tr>
            <td style="font-weight: 600; color: var(--text-main);">
              ${grade.subject}
            </td>
            <td style="font-family: var(--font-mono); color: var(--text-muted);">
              ${grade.target_grade.toFixed(1)}
            </td>
            <td>
              <input 
                type="number" 
                step="0.5" 
                min="1" 
                max="6" 
                value="${actual !== null ? actual : ""}" 
                placeholder="--" 
                class="text-input" 
                style="width: 70px; font-weight: 700; color: ${statusColor};"
                onchange="Tum.updateGradeScore(${grade.id}, this.value)"
              />
            </td>
            <td style="font-family: var(--font-mono); color: var(--text-dim);">
              ${actual !== null ? Math.round((actual / 6.0) * 100) + "%" : "--"}
            </td>
            <td>
              ${
                isUnderFour
                  ? '<span class="badge" style="background: var(--accent-red-bg); color: var(--accent-red);">Below Target (&lt;4)</span>'
                  : actual !== null
                  ? '<span class="badge" style="background: var(--accent-green-bg); color: var(--accent-green);">On Track</span>'
                  : '<span class="badge badge-cat">Pending</span>'
              }
            </td>
          </tr>
        `;
      })
      .join("");
  },

  async updateGradeScore(gradeId, value) {
    try {
      const num = value === "" ? null : parseFloat(value);
      await window.pywebview.api.update_grade(gradeId, num);
      await this.load();
      window.HarnessApp.showToast("Grade updated");
    } catch (err) {
      console.error("Error updating grade:", err);
    }
  },

  async updateMaturaScore(maturaId, value) {
    try {
      const num = parseFloat(value) || 0.0;
      await window.pywebview.api.update_matura(maturaId, num);
      await this.load();
      window.HarnessApp.showToast("Matura mock score updated");
    } catch (err) {
      console.error("Error updating matura score:", err);
    }
  },

  async updateLanguageStatus(level, status) {
    try {
      await window.pywebview.api.update_language_status(level, status);
      await this.load();
      window.HarnessApp.showToast(`German ${level} status: ${status}`);
    } catch (err) {
      console.error("Error updating language status:", err);
    }
  },
};
