/**
 * Harness Executive OS - Study & Academic Radar (Version 3.5)
 * Manages official Vulcan upcoming tests, homework deadlines, and live GPA tracking for TUM.
 */

window.Study = {
  examsList: [],
  homeworkList: [],
  tumData: null,

  async init() {
    await this.load();
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;

      // 1. Fetch upcoming exams
      if (typeof window.pywebview.api.get_upcoming_exams === "function") {
        const rawExams = await window.pywebview.api.get_upcoming_exams();
        // Strict filter: purge any mock phantom tests
        this.examsList = (rawExams || []).filter((e) => {
          const t = ((e.title || "") + " " + (e.scope || "")).toLowerCase();
          return (
            !t.includes("trygonometria") &&
            !t.includes("kinematyka") &&
            !t.includes("wyszukiwania") &&
            !t.includes("powstanie styczniowe")
          );
        });
      }

      // 2. Fetch upcoming homework
      if (typeof window.pywebview.api.get_upcoming_homework === "function") {
        const rawHw = await window.pywebview.api.get_upcoming_homework();
        this.homeworkList = (rawHw || []).filter((h) => {
          const t = (h.title || "").toLowerCase();
          return !t.includes("plecakowy") && !t.includes("trading");
        });
      }

      // 3. Fetch TUM grades overview
      if (typeof window.pywebview.api.get_tum_overview === "function") {
        this.tumData = await window.pywebview.api.get_tum_overview();
      }

      this.render();
    } catch (err) {
      console.error("[Study] Error loading study data:", err);
    }
  },

  render() {
    this.renderExams();
    this.renderHomework();
    this.renderGrades();
  },

  renderExams() {
    const container = document.getElementById("studyExamsList");
    const badge = document.getElementById("studyExamsCountBadge");
    if (!container) return;

    if (badge) {
      badge.textContent = `${this.examsList.length} Scheduled`;
    }

    if (this.examsList.length === 0) {
      container.innerHTML = `
        <div style="font-size: 11px; color: var(--text-tertiary); padding: 12px 6px; text-align: center;">
          No upcoming sprawdziany or kartkówki recorded. Clean schedule.
        </div>
      `;
      return;
    }

    container.innerHTML = this.examsList
      .map((ex) => {
        let badgeColor = "border-color: var(--border-medium); color: var(--text-secondary);";
        let dueLabel = `${ex.exam_date}`;
        if (ex.days_left === 0) {
          dueLabel = "TODAY";
          badgeColor = "border-color: var(--color-red-border); color: var(--color-red); background: var(--color-red-subtle); font-weight: 700;";
        } else if (ex.days_left === 1) {
          dueLabel = "TOMORROW";
          badgeColor = "border-color: var(--color-amber-border); color: var(--color-amber); background: var(--color-amber-subtle); font-weight: 700;";
        } else if (ex.days_left > 1 && ex.days_left <= 7) {
          dueLabel = `in ${ex.days_left}d`;
          badgeColor = "border-color: var(--color-purple-border); color: var(--color-purple); background: var(--color-purple-subtle); font-weight: 600;";
        } else if (ex.days_left > 7) {
          dueLabel = `in ${ex.days_left}d`;
        }

        const scopeHtml = ex.scope
          ? `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; line-height: 1.4;">${this.escapeHtml(ex.scope)}</div>`
          : "";

        return `
          <div id="study-exam-${ex.id}" data-exam-id="${ex.id}" class="study-exam-card" style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 9px 12px; transition: outline 0.2s ease;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: var(--text-primary);">
                    [${this.escapeHtml(ex.subject)}]
                  </span>
                  <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">
                    ${this.escapeHtml(ex.title)}
                  </span>
                </div>
                ${scopeHtml}
              </div>
              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="key-pill" style="font-size: 9px; padding: 2px 6px; ${badgeColor}">${dueLabel}</span>
                <button type="button" class="btn-ghost-icon" style="padding: 2px 5px; font-size: 9px;" onclick="Study.deleteExam(${ex.id})" title="Delete test">&times;</button>
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  },

  renderHomework() {
    const container = document.getElementById("studyHomeworkList");
    const badge = document.getElementById("studyHomeworkCountBadge");
    if (!container) return;

    if (badge) {
      badge.textContent = `${this.homeworkList.length} Tasks`;
    }

    if (this.homeworkList.length === 0) {
      container.innerHTML = `
        <div style="font-size: 11px; color: var(--text-tertiary); padding: 12px 6px; text-align: center;">
          All homework completed.
        </div>
      `;
      return;
    }

    container.innerHTML = this.homeworkList
      .map((hw) => {
        let badgeColor = "border-color: var(--border-subtle); color: var(--text-tertiary);";
        let dueLabel = `${hw.due_date}`;
        if (hw.days_left === 0) {
          dueLabel = "TODAY";
          badgeColor = "border-color: var(--color-red-border); color: var(--color-red); background: var(--color-red-subtle); font-weight: 700;";
        } else if (hw.days_left === 1) {
          dueLabel = "TOMORROW";
          badgeColor = "border-color: var(--color-amber-border); color: var(--color-amber); background: var(--color-amber-subtle); font-weight: 700;";
        } else if (hw.days_left > 1) {
          dueLabel = `in ${hw.days_left}d`;
        }

        const notesHtml = hw.notes && hw.notes !== hw.title
          ? `<div style="font-size: 10px; color: var(--text-secondary); margin-top: 3px;">${this.escapeHtml(hw.notes)}</div>`
          : "";

        return `
          <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 8px 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
              <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
                <div class="check-dot ${hw.completed ? "checked" : ""}" onclick="Study.toggleHomework(${hw.id})" title="Toggle completion"></div>
                <div style="min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: var(--text-primary);">
                      [${this.escapeHtml(hw.subject)}]
                    </span>
                    <span style="font-size: 11px; color: var(--text-primary); text-decoration: ${hw.completed ? "line-through" : "none"};">
                      ${this.escapeHtml(hw.title)}
                    </span>
                  </div>
                  ${notesHtml}
                </div>
              </div>
              <span class="key-pill" style="font-size: 9px; padding: 1px 5px; flex-shrink: 0; ${badgeColor}">${dueLabel}</span>
            </div>
          </div>
        `;
      })
      .join("");
  },

  renderGrades() {
    const container = document.getElementById("studySubjectGradesList");
    const gpaEl = document.getElementById("studyCurrentGpaVal");
    if (!this.tumData) return;

    if (gpaEl && this.tumData.current_gpa) {
      gpaEl.textContent = Number(this.tumData.current_gpa).toFixed(2);
    }

    if (!container) return;

    const grades = this.tumData.grades || [];
    // Prioritize key STEM subjects for TUM
    const priorityOrder = ["Matematyka", "Informatyka", "Język Angielski", "Fizyka", "Język Polski", "Historia", "Geografia"];
    const sem1Grades = grades.filter((g) => g.semester === 1);

    sem1Grades.sort((a, b) => {
      const idxA = priorityOrder.indexOf(a.subject);
      const idxB = priorityOrder.indexOf(b.subject);
      return (idxA === -1 ? 99 : idxA) - (idxB === -1 ? 99 : idxB);
    });

    container.innerHTML = sem1Grades
      .map((g) => {
        const actual = g.actual_grade ? Number(g.actual_grade).toFixed(1) : "--";
        const target = g.target_grade ? Number(g.target_grade).toFixed(1) : "5.0";
        const isStem = ["Matematyka", "Informatyka", "Fizyka"].includes(g.subject);

        return `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm);">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 11px; font-weight: ${isStem ? "700" : "500"}; color: var(--text-primary);">
                ${this.escapeHtml(g.subject)}
              </span>
              ${isStem ? '<span class="key-pill" style="font-size: 8px; padding: 0 4px;">2x WEIGHT</span>' : ""}
            </div>
            <div style="display: flex; align-items: center; gap: 12px; font-family: var(--font-mono); font-size: 11px;">
              <span style="color: var(--text-primary); font-weight: 700;">${actual}</span>
              <span style="color: var(--text-tertiary);">/ ${target}</span>
            </div>
          </div>
        `;
      })
      .join("");
  },

  async toggleHomework(hwId) {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_homework) {
        await window.pywebview.api.toggle_homework(hwId);
        await this.load();
        if (window.Today) window.Today.load();
      }
    } catch (e) {
      console.error("[Study] Error toggling homework:", e);
    }
  },

  async deleteExam(examId) {
    if (!confirm("Remove this exam from schedule?")) return;
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.delete_exam) {
        await window.pywebview.api.delete_exam(examId);
        await this.load();
        if (window.Today) window.Today.load();
      }
    } catch (e) {
      console.error("[Study] Error deleting exam:", e);
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
