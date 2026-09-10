/**
 * TUM Layer Controller: Metro Map coordinator, Bavarian Formula, and Real-Time Grade Ledger.
 * Supports granular grade logging (points, percentages, pluses/minuses, np, bz),
 * running subject averages, and immediate GPA recalculations.
 */

const Tum = {
  data: null,
  activeSemester: 1,
  showingGradesTable: false,

  async init() {
    this.bindEvents();
    this.initAptitudeSimulator();
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
          btnToggle.textContent = this.showingGradesTable ? "Hide Grades Ledger" : "Grades Ledger";
        }
      });
    }

    // Open Add Grade Modal from header button
    const btnAddGrade = document.getElementById("btnOpenAddGradeModal");
    if (btnAddGrade) {
      btnAddGrade.addEventListener("click", () => {
        this.openAddGradeModal("", this.activeSemester);
      });
    }

    // Add Grade Form submission
    const form = document.getElementById("addGradeForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleSaveGrade();
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
      this.renderBavarianAssessment();
    } catch (err) {
      console.error("Error loading TUM overview:", err);
    }
  },

  renderGradesTable() {
    const tbody = document.getElementById("gradesTableBody");
    if (!tbody || !this.data || !this.data.semesters) return;

    const list = this.data.semesters[this.activeSemester] || [];
    const semGpa = this.data.semester_gpas ? this.data.semester_gpas[this.activeSemester] : null;

    if (list.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="padding: 24px 0; text-align: center; color: var(--text-tertiary); font-size: 11px;">
            No curricular subjects initialized for Semester ${this.activeSemester}.
          </td>
        </tr>
      `;
      return;
    }

    const rowsHtml = list
      .map((grade) => {
        const entries = grade.entries || [];
        const runningAvg = grade.running_average;
        const actual = grade.actual_grade;
        const target = grade.target_grade || 5.0;

        // Render chips for individual marks
        let chipsHtml = "";
        if (entries.length === 0) {
          chipsHtml = `<span style="color: var(--text-tertiary); font-size: 11px; font-style: italic;">No grades logged</span>`;
        } else {
          chipsHtml = `
            <div class="grade-chip-container">
              ${entries
                .map((e) => {
                  const color = e.badge_color || "#a1a1aa";
                  const weightStr = e.weight && e.weight !== 1.0 ? `<span style="font-size: 8px; opacity: 0.75;"> &times;${e.weight}</span>` : "";
                  const countMarker = !e.counts_in_average ? ' <span style="font-size: 8px; opacity: 0.6;">(0x)</span>' : "";
                  const titleTip = `${this.escapeHtml(e.category || "Grade")} • Weight: ${e.weight}${e.description ? ` • ${this.escapeHtml(e.description)}` : ""}${e.date ? ` • ${e.date}` : ""} (Click to remove)`;

                  return `
                    <span 
                      class="grade-chip" 
                      style="color: ${color}; border-color: ${color}44; background: ${color}12;" 
                      title="${titleTip}"
                      onclick="Tum.confirmDeleteGradeEntry(${e.id}, '${this.escapeJs(e.raw_input)}', '${this.escapeJs(grade.subject)}')"
                    >
                      <span>${this.escapeHtml(e.display_label || e.raw_input)}</span>${weightStr}${countMarker}
                      <span class="chip-del-btn">&times;</span>
                    </span>
                  `;
                })
                .join("")}
            </div>
          `;
        }

        // Running average badge styling
        let avgHtml = `<span style="color: var(--text-tertiary); font-family: var(--font-mono); font-size: 11px;">--</span>`;
        if (runningAvg !== null && runningAvg !== undefined) {
          let avgBg = "rgba(196, 181, 253, 0.1)";
          let avgColor = "var(--accent-lavender)";
          let avgBorder = "rgba(196, 181, 253, 0.3)";

          if (runningAvg < 4.0) {
            avgBg = "rgba(239, 68, 68, 0.12)";
            avgColor = "#f87171";
            avgBorder = "rgba(239, 68, 68, 0.3)";
          } else if (runningAvg >= target) {
            avgBg = "rgba(110, 231, 183, 0.12)";
            avgColor = "#6ee7b7";
            avgBorder = "rgba(110, 231, 183, 0.3)";
          }

          avgHtml = `
            <span class="grade-avg-pill" style="background: ${avgBg}; color: ${avgColor}; border: 1px solid ${avgBorder};">
              ${runningAvg.toFixed(2)}
            </span>
          `;
        }

        // Status badge
        let statusBadge = `<span class="key-pill">Pending</span>`;
        if (runningAvg !== null && runningAvg !== undefined) {
          if (runningAvg < 4.0) {
            statusBadge = `<span class="key-pill" style="color: #f87171; border-color: rgba(239, 68, 68, 0.35);">Risk (&lt; 4.0)</span>`;
          } else if (runningAvg >= target) {
            statusBadge = `<span class="key-pill done" style="color: #6ee7b7; border-color: rgba(110, 231, 183, 0.35);">Target Met</span>`;
          } else {
            statusBadge = `<span class="key-pill" style="color: var(--text-primary);">On Track</span>`;
          }
        }

        return `
          <tr style="border-bottom: 1px solid var(--border-hairline);">
            <td style="padding: 10px 0; font-weight: 600; color: var(--text-primary); font-size: 12px;">
              ${this.escapeHtml(grade.subject)}
            </td>
            <td style="padding: 10px 10px;">
              ${chipsHtml}
            </td>
            <td style="padding: 10px 10px;">
              ${avgHtml}
            </td>
            <td style="padding: 10px 10px; font-family: var(--font-mono); color: var(--text-secondary); font-size: 11px;">
              ${target.toFixed(1)}
            </td>
            <td style="padding: 10px 10px;">
              ${statusBadge}
            </td>
            <td style="padding: 10px 0; text-align: right;">
              <button 
                class="btn-ghost-icon" 
                style="padding: 3px 8px; font-size: 10px;" 
                onclick="Tum.openAddGradeModal('${this.escapeJs(grade.subject)}', ${this.activeSemester})"
                title="Log a new grade for ${this.escapeHtml(grade.subject)}"
              >
                + Grade
              </button>
            </td>
          </tr>
        `;
      })
      .join("");

    // Semester summary footer row
    const gpaDisplay = semGpa && semGpa > 0 ? semGpa.toFixed(2) : "--";
    const overallDisplay = this.data.overall_gpa && this.data.overall_gpa > 0 ? this.data.overall_gpa.toFixed(2) : "--";

    const footerHtml = `
      <tr style="border-top: 1px solid rgba(255, 255, 255, 0.12); background: rgba(255, 255, 255, 0.02); font-family: var(--font-mono); font-size: 11px;">
        <td colspan="2" style="padding: 10px 0; font-weight: 700; color: var(--text-primary);">
          SEMESTER ${this.activeSemester} RUNNING GPA
        </td>
        <td colspan="2" style="padding: 10px 10px;">
          <span class="mono-chip lavender" style="font-weight: 700; font-size: 11px; padding: 3px 8px;">
            ${gpaDisplay} GPA
          </span>
        </td>
        <td colspan="2" style="padding: 10px 0; text-align: right; color: var(--text-tertiary);">
          Overall: <strong style="color: var(--text-primary);">${overallDisplay}</strong>
        </td>
      </tr>
    `;

    tbody.innerHTML = rowsHtml + footerHtml;
  },

  renderBavarianAssessment() {
    if (!this.data || !this.data.bavarian_assessment) return;
    const b = this.data.bavarian_assessment;
    this.actualAptitudeValues = {
      gpa: b.gpa_pl !== undefined ? Number(b.gpa_pl) : 5.0,
      math: b.math_pl !== undefined ? Number(b.math_pl) : 5.5,
      cs: b.cs_pl !== undefined ? Number(b.cs_pl) : 5.5,
      lang: b.lang_pl !== undefined ? Number(b.lang_pl) : 5.5,
    };

    if (!this.isSimulating) {
      const sliderGpa = document.getElementById("simSliderGpa");
      const sliderMath = document.getElementById("simSliderMath");
      const sliderCs = document.getElementById("simSliderCs");
      const sliderLang = document.getElementById("simSliderLang");
      if (sliderGpa) sliderGpa.value = this.actualAptitudeValues.gpa;
      if (sliderMath) sliderMath.value = this.actualAptitudeValues.math;
      if (sliderCs) sliderCs.value = this.actualAptitudeValues.cs;
      if (sliderLang) sliderLang.value = this.actualAptitudeValues.lang;
      this.updateSimulatorDisplay(
        this.actualAptitudeValues.gpa,
        this.actualAptitudeValues.math,
        this.actualAptitudeValues.cs,
        this.actualAptitudeValues.lang,
        false
      );
    }
  },

  initAptitudeSimulator() {
    const sliderGpa = document.getElementById("simSliderGpa");
    const sliderMath = document.getElementById("simSliderMath");
    const sliderCs = document.getElementById("simSliderCs");
    const sliderLang = document.getElementById("simSliderLang");
    const syncBtn = document.getElementById("tumSimulatorSyncBtn");

    const onSliderChange = () => {
      this.isSimulating = true;
      const gpa = parseFloat(sliderGpa ? sliderGpa.value : 5.0);
      const math = parseFloat(sliderMath ? sliderMath.value : 5.5);
      const cs = parseFloat(sliderCs ? sliderCs.value : 5.5);
      const lang = parseFloat(sliderLang ? sliderLang.value : 5.5);
      this.updateSimulatorDisplay(gpa, math, cs, lang, true);
    };

    if (sliderGpa) sliderGpa.addEventListener("input", onSliderChange);
    if (sliderMath) sliderMath.addEventListener("input", onSliderChange);
    if (sliderCs) sliderCs.addEventListener("input", onSliderChange);
    if (sliderLang) sliderLang.addEventListener("input", onSliderChange);

    if (syncBtn) {
      syncBtn.addEventListener("click", () => {
        this.isSimulating = false;
        const vals = this.actualAptitudeValues || { gpa: 5.0, math: 5.5, cs: 5.5, lang: 5.5 };
        if (sliderGpa) sliderGpa.value = vals.gpa;
        if (sliderMath) sliderMath.value = vals.math;
        if (sliderCs) sliderCs.value = vals.cs;
        if (sliderLang) sliderLang.value = vals.lang;
        this.updateSimulatorDisplay(vals.gpa, vals.math, vals.cs, vals.lang, false);
      });
    }
  },

  calculateBavarianGrade(p, pMax = 6.0, pMin = 2.0) {
    if (p >= pMax) return 1.0;
    if (p <= pMin) return 4.0;
    return Math.round((1.0 + 3.0 * ((pMax - p) / (pMax - pMin))) * 100) / 100;
  },

  calculateAptitudeScore(gpaPl, mathPl, csPl, langPl) {
    const gGpa = this.calculateBavarianGrade(gpaPl);
    const gMath = this.calculateBavarianGrade(mathPl);
    const gCs = this.calculateBavarianGrade(csPl);
    const gLang = this.calculateBavarianGrade(langPl);

    const gradeToPoints = (g) => Math.max(0, Math.min(100, (4.0 - g) * (100.0 / 3.0)));
    const ptsGpa = gradeToPoints(gGpa);
    const ptsMath = gradeToPoints(gMath);
    const ptsCs = gradeToPoints(gCs);
    const ptsLang = gradeToPoints(gLang);

    const subjectScore = (ptsMath * 2 + ptsCs * 2 + ptsLang * 1) / 5.0;
    const totalScore = Math.round((0.65 * ptsGpa + 0.35 * subjectScore) * 10) / 10;

    let verdict = "DEFICIT: MATH/CS RECOVERY NEEDED";
    if (totalScore >= 88.0) {
      verdict = "DIRECT ADMISSION SAFE (Level 1)";
    } else if (totalScore >= 70.0) {
      verdict = "INTERVIEW THRESHOLD (Level 2)";
    }

    return {
      german_gpa: gGpa,
      total_tum_points: totalScore,
      verdict,
      gpa_pl: gpaPl,
      math_pl: mathPl,
      cs_pl: csPl,
      lang_pl: langPl,
      pts_subject: Math.round(subjectScore * 10) / 10,
    };
  },

  updateSimulatorDisplay(gpa, math, cs, lang, isSimulating = false) {
    const simValGpa = document.getElementById("simValGpa");
    const simValMath = document.getElementById("simValMath");
    const simValCs = document.getElementById("simValCs");
    const simValLang = document.getElementById("simValLang");
    const simModeBadge = document.getElementById("simModeBadge");

    if (simValGpa) simValGpa.textContent = Number(gpa).toFixed(2);
    if (simValMath) simValMath.textContent = Number(math).toFixed(2);
    if (simValCs) simValCs.textContent = Number(cs).toFixed(2);
    if (simValLang) simValLang.textContent = Number(lang).toFixed(2);

    if (simModeBadge) {
      if (isSimulating) {
        simModeBadge.textContent = "What-If Simulated";
        simModeBadge.style.color = "#f59e0b";
        simModeBadge.style.background = "rgba(245, 158, 11, 0.1)";
        simModeBadge.style.borderColor = "rgba(245, 158, 11, 0.3)";
      } else {
        simModeBadge.textContent = "Live Ledger Linked";
        simModeBadge.style.color = "var(--accent-lavender)";
        simModeBadge.style.background = "rgba(196, 181, 253, 0.1)";
        simModeBadge.style.borderColor = "rgba(196, 181, 253, 0.2)";
      }
    }

    const calc = this.calculateAptitudeScore(gpa, math, cs, lang);

    const badgeEl = document.getElementById("tumAdmissionBadge");
    const gpaEl = document.getElementById("tumGermanGpaVal");
    const plGpaEl = document.getElementById("tumPolishGpaVal");
    const totalEl = document.getElementById("tumTotalScoreVal");
    const subjEl = document.getElementById("tumSubjectScoreVal");
    const verdictEl = document.getElementById("tumVerdictText");

    if (gpaEl) gpaEl.textContent = Number(calc.german_gpa).toFixed(2);
    if (plGpaEl) plGpaEl.textContent = `Polish: ${Number(calc.gpa_pl).toFixed(2)}`;
    if (totalEl) totalEl.textContent = `${Number(calc.total_tum_points).toFixed(1)} / 100`;
    if (subjEl) subjEl.textContent = `${Number(calc.pts_subject).toFixed(1)} pts`;
    if (verdictEl) verdictEl.textContent = calc.verdict;

    if (badgeEl) {
      if (calc.total_tum_points >= 88.0) {
        badgeEl.innerHTML = `<span class="mono-chip done" style="background: rgba(110, 231, 183, 0.15); border-color: rgba(110, 231, 183, 0.4); color: #6ee7b7; font-size: 11px; padding: 4px 10px; font-weight: 700;">DIRECT ADMISSION SAFE (Level 1)</span>`;
      } else if (calc.total_tum_points >= 70.0) {
        badgeEl.innerHTML = `<span class="mono-chip amber" style="background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.4); color: #f59e0b; font-size: 11px; padding: 4px 10px; font-weight: 700;">INTERVIEW THRESHOLD (Level 2)</span>`;
      } else {
        badgeEl.innerHTML = `<span class="mono-chip" style="background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #f87171; font-size: 11px; padding: 4px 10px; font-weight: 700;">DEFICIT: MATH/CS RECOVERY NEEDED</span>`;
      }
    }
  },

  openAddGradeModal(subject = "", semester = null) {
    const modal = document.getElementById("addGradeModal");
    if (!modal) return;

    const subjInput = document.getElementById("gradeFormSubject");
    const semInput = document.getElementById("gradeFormSemester");
    const rawInput = document.getElementById("gradeFormRaw");
    const weightInput = document.getElementById("gradeFormWeight");
    const catInput = document.getElementById("gradeFormCategory");
    const dateInput = document.getElementById("gradeFormDate");
    const descInput = document.getElementById("gradeFormDesc");

    if (subjInput) subjInput.value = subject;
    if (semInput) semInput.value = String(semester || this.activeSemester || 1);
    if (rawInput) rawInput.value = "";
    if (weightInput) weightInput.value = "1.0";
    if (catInput) catInput.value = "Sprawdzian";
    if (descInput) descInput.value = "";
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];

    modal.classList.add("open");
    if (rawInput) rawInput.focus();
  },

  closeAddGradeModal() {
    const modal = document.getElementById("addGradeModal");
    if (modal) modal.classList.remove("open");
  },

  async handleSaveGrade() {
    const subjInput = document.getElementById("gradeFormSubject");
    const semInput = document.getElementById("gradeFormSemester");
    const rawInput = document.getElementById("gradeFormRaw");
    const weightInput = document.getElementById("gradeFormWeight");
    const catInput = document.getElementById("gradeFormCategory");
    const dateInput = document.getElementById("gradeFormDate");
    const descInput = document.getElementById("gradeFormDesc");

    const subject = subjInput ? subjInput.value.trim() : "";
    const semester = semInput ? parseInt(semInput.value, 10) : this.activeSemester;
    const rawGrade = rawInput ? rawInput.value.trim() : "";
    const weight = weightInput ? parseFloat(weightInput.value) || 1.0 : 1.0;
    const category = catInput ? catInput.value : "Sprawdzian";
    const dateStr = dateInput ? dateInput.value : "";
    const description = descInput ? descInput.value.trim() : "";

    if (!subject || !rawGrade) {
      alert("Please enter both a subject and a grade/mark.");
      return;
    }

    try {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.add_grade_entry(
          subject,
          semester,
          rawGrade,
          weight,
          category,
          description,
          dateStr
        );

        this.closeAddGradeModal();
        await this.load();
        if (window.Dashboard) await window.Dashboard.load();

        if (window.HarnessApp && window.HarnessApp.showToast) {
          const avgText = res.new_running_average !== null ? ` (New Avg: ${Number(res.new_running_average).toFixed(2)})` : "";
          window.HarnessApp.showToast(`Logged "${rawGrade}" in ${subject}${avgText}`);
        }
      }
    } catch (err) {
      console.error("Error saving grade entry:", err);
      alert(err.message || "Failed to save grade entry.");
    }
  },

  async confirmDeleteGradeEntry(entryId, rawLabel, subject) {
    if (!confirm(`Delete grade "${rawLabel}" from ${subject}?`)) {
      return;
    }

    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.delete_grade_entry(entryId);
        await this.load();
        if (window.Dashboard) await window.Dashboard.load();

        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast(`Removed "${rawLabel}" from ${subject}`);
        }
      }
    } catch (err) {
      console.error("Error deleting grade entry:", err);
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

window.Tum = Tum;
