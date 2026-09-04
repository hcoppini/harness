/**
 * TUM Layer Controller: Metro Map coordinator and Grade Ledger.
 */

const Tum = {
  data: null,
  activeSemester: 1,
  showingGradesTable: false,

  async init() {
    this.bindEvents();
    if (window.MetroMap) {
      await window.MetroMap.init();
    }
    await this.load();
  },

  bindEvents() {
    // Toggle between Metro Map and Grades Ledger table
    const btnToggle = document.getElementById("btnToggleGradesView");
    if (btnToggle) {
      btnToggle.addEventListener("click", () => {
        this.showingGradesTable = !this.showingGradesTable;
        const drawer = document.getElementById("gradesTableDrawer");
        if (drawer) {
          drawer.style.display = this.showingGradesTable ? "block" : "none";
          btnToggle.textContent = this.showingGradesTable ? "Hide Grades Table" : "View Grades Table";
        }
      });
    }

    // Semester filter buttons
    const semButtons = document.querySelectorAll("#semesterFilterButtons button");
    semButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
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
      this.renderGradesTable();
    } catch (err) {
      console.error("Error loading TUM overview:", err);
    }
  },

  renderGradesTable() {
    const tbody = document.getElementById("gradesTableBody");
    if (!tbody || !this.data || !this.data.semesters) return;

    const list = this.data.semesters[this.activeSemester] || [];
    tbody.innerHTML = list
      .map((grade) => {
        const actual = grade.actual_grade;
        const isUnderFour = actual !== null && actual < 4.0;
        const statusColor = actual === null ? "var(--text-tertiary)" : isUnderFour ? "#e06c75" : "var(--text-primary)";

        return `
          <tr style="border-bottom: 1px solid var(--border-hairline);">
            <td style="padding: 8px 0; font-weight: 500; color: var(--text-primary);">
              ${grade.subject}
            </td>
            <td style="font-family: var(--font-mono); color: var(--text-secondary);">
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
                class="btn-ghost-icon" 
                style="width: 60px; font-family: var(--font-mono); color: ${statusColor};"
                onchange="Tum.updateGradeScore(${grade.id}, this.value)"
              />
            </td>
            <td>
              ${
                isUnderFour
                  ? '<span class="key-pill" style="color: #e06c75; border-color: rgba(224, 108, 117, 0.3);">&lt; 4.0 (Risk)</span>'
                  : actual !== null
                  ? '<span class="key-pill" style="color: var(--text-primary);">On Track</span>'
                  : '<span class="key-pill">Pending</span>'
              }
            </td>
          </tr>
        `;
      })
      .join("");

    this.renderBavarianAssessment();
  },

  renderBavarianAssessment() {
    if (!this.data || !this.data.bavarian_assessment) return;
    const b = this.data.bavarian_assessment;

    const badgeEl = document.getElementById("tumAdmissionBadge");
    const gpaEl = document.getElementById("tumGermanGpaVal");
    const plGpaEl = document.getElementById("tumPolishGpaVal");
    const totalEl = document.getElementById("tumTotalScoreVal");
    const subjEl = document.getElementById("tumSubjectScoreVal");
    const verdictEl = document.getElementById("tumVerdictText");

    if (gpaEl) gpaEl.textContent = Number(b.german_gpa).toFixed(2);
    if (plGpaEl) plGpaEl.textContent = `Polish: ${b.gpa_pl !== undefined ? Number(b.gpa_pl).toFixed(2) : "--"}`;
    if (totalEl) totalEl.textContent = `${Number(b.total_tum_points).toFixed(1)} / 100`;
    if (subjEl) subjEl.textContent = `${b.pts_subject !== undefined ? Number(b.pts_subject).toFixed(1) : "--"} pts`;
    if (verdictEl) verdictEl.textContent = b.verdict;

    if (badgeEl) {
      if (b.total_tum_points >= 88.0) {
        badgeEl.innerHTML = `<span class="mono-chip done" style="background: rgba(110, 231, 183, 0.15); border-color: rgba(110, 231, 183, 0.4); color: #6ee7b7; font-size: 11px; padding: 4px 10px; font-weight: 700;">DIRECT ADMISSION SAFE (Level 1)</span>`;
      } else if (b.total_tum_points >= 70.0) {
        badgeEl.innerHTML = `<span class="mono-chip amber" style="background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.4); color: #f59e0b; font-size: 11px; padding: 4px 10px; font-weight: 700;">INTERVIEW THRESHOLD (Level 2)</span>`;
      } else {
        badgeEl.innerHTML = `<span class="mono-chip" style="background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #f87171; font-size: 11px; padding: 4px 10px; font-weight: 700;">DEFICIT: MATH/CS RECOVERY NEEDED</span>`;
      }
    }
  },

  async updateGradeScore(gradeId, value) {
    try {
      const num = value === "" ? null : parseFloat(value);
      await window.pywebview.api.update_grade(gradeId, num);
      await this.load();
      window.HarnessApp.showToast("Grade record updated");
    } catch (err) {
      console.error("Error updating grade:", err);
    }
  },
};

window.Tum = Tum;
