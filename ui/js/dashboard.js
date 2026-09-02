/**
 * Layer 0: DASHBOARD CONTROLLER (Executive Home Page)
 * Features:
 * - GitHub-style daily execution activity heatmap with floating interactive tooltip
 * - Upcoming 7-day forecast reel with Schedule A/B/C and gym routine highlights
 * - Tri-pillar executive KPIs (TUM Heilbronn, Machine Body, Active Projects)
 */

window.Dashboard = {
  data: null,
  tooltipEl: null,

  async init() {
    this.tooltipEl = document.getElementById("heatmapTooltip");
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    const btnRefresh = document.getElementById("btnRefreshDashboard");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", async () => {
        await this.load();
        if (window.HarnessApp) window.HarnessApp.showToast("Dashboard refreshed");
      });
    }

    const btnGoToday = document.getElementById("btnJumpToTodayFromDash");
    if (btnGoToday) {
      btnGoToday.addEventListener("click", () => {
        if (window.HarnessApp) window.HarnessApp.switchView("today");
      });
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api || typeof window.pywebview.api.get_dashboard !== "function") {
        return;
      }
      this.data = await window.pywebview.api.get_dashboard();
      this.render();
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    }
  },

  render() {
    if (!this.data) return;

    this.renderHeader();
    this.renderHeatmap();
    this.renderUpcoming();
    this.renderPillars();
  },

  renderHeader() {
    const streakVal = document.getElementById("streakCountVal");
    if (streakVal) {
      streakVal.textContent = this.data.metrics?.current_streak || 0;
    }
  },

  renderHeatmap() {
    const heatmap = this.data.heatmap;
    if (!heatmap) return;

    // Header count text: "X checked boxes across active cycle"
    const countEl = document.getElementById("heatmapContributionsCount");
    if (countEl) {
      const count = heatmap.total_contributions || 0;
      countEl.textContent = `${count} ${count === 1 ? "box" : "boxes"} completed since launch`;
    }

    const container = document.getElementById("heatmapContainer");
    if (!container) return;

    const weeks = heatmap.weeks || [];
    const months = heatmap.months || [];

    // Left Day Labels (GitHub style: Mon, Wed, Fri)
    let html = `
      <div class="heatmap-day-labels">
        <span></span>
        <span>Mon</span>
        <span></span>
        <span>Wed</span>
        <span></span>
        <span>Fri</span>
        <span></span>
      </div>
      <div class="heatmap-grid-area">
        <div class="heatmap-months-row">
    `;

    // Month headers with collision prevention
    const colWidth = 18; // 14px cell + 4px gap
    let lastRightPx = -999;
    months.forEach((m) => {
      const leftPx = m.week_index * colWidth;
      if (leftPx >= lastRightPx + 28 || lastRightPx === -999) {
        html += `<span class="heatmap-month-label" style="left: ${leftPx}px;">${m.name}</span>`;
        lastRightPx = leftPx;
      }
    });

    html += `</div><div class="heatmap-weeks-grid">`;

    // Render columns of 7 day cells
    weeks.forEach((week) => {
      html += `<div class="heatmap-week-col">`;
      week.days.forEach((day) => {
        if (!day) {
          html += `<div class="heatmap-cell empty"></div>`;
        } else {
          const level = day.level || 0;
          const count = day.count || 0;
          const totalBoxes = day.total_boxes || 0;
          const dateStr = day.date || "";
          const isTodayClass = day.is_today ? " cell-today" : "";
          const isFutureClass = day.is_future ? " cell-future" : "";
          html += `
            <div 
              class="heatmap-cell lvl-${level}${isTodayClass}${isFutureClass}" 
              data-date="${dateStr}"
              data-count="${count}"
              data-total="${totalBoxes}"
              data-level="${level}"
              data-display="${day.display_date || dateStr}"
            ></div>
          `;
        }
      });
      html += `</div>`;
    });

    html += `</div></div>`;
    container.innerHTML = html;

    // Setup interactive tooltips
    this.attachHeatmapTooltips();
  },

  attachHeatmapTooltips() {
    const tooltip = this.tooltipEl || document.getElementById("heatmapTooltip");
    if (!tooltip) return;

    const cells = document.querySelectorAll(".heatmap-cell:not(.empty)");
    const dayMap = new Map();
    const weeks = this.data.heatmap?.weeks || [];
    weeks.forEach((w) => {
      (w.days || []).forEach((d) => {
        if (d && d.date) {
          dayMap.set(d.date, d);
        }
      });
    });

    cells.forEach((cell) => {
      cell.addEventListener("mouseenter", (e) => {
        const dateStr = cell.getAttribute("data-date");
        const dayInfo = dayMap.get(dateStr);
        if (!dayInfo) return;

        const count = dayInfo.count || 0;
        const total = dayInfo.total_boxes || 0;
        const level = dayInfo.level || 0;
        const displayDate = dayInfo.display_date || dateStr;
        const activities = dayInfo.activities || [];
        const isFuture = dayInfo.is_future;

        let statusBadge = "";
        if (isFuture) {
          statusBadge = `<span style="color: var(--text-tertiary); font-size: 10px;">(Upcoming)</span>`;
        } else if (total > 0 && count >= total) {
          statusBadge = `<span style="color: #c084fc; font-weight: 700; font-size: 11px;">100% (All ${total} Done!)</span>`;
        } else if (total > 0) {
          const pct = Math.round((count / total) * 100);
          statusBadge = `<span style="color: var(--text-secondary); font-size: 11px;">${count}/${total} (${pct}%)</span>`;
        } else {
          statusBadge = `<span style="color: var(--text-secondary); font-size: 11px;">${count} completed</span>`;
        }

        let tipContent = `
          <div class="heatmap-tooltip-date">${displayDate} ${statusBadge}</div>
        `;

        if (activities.length > 0) {
          tipContent += activities
            .slice(0, 8)
            .map((act) => `<div class="heatmap-tooltip-action">${this.escapeHtml(act)}</div>`)
            .join("");
          if (activities.length > 8) {
            tipContent += `<div class="heatmap-tooltip-action" style="color: var(--text-tertiary);">+ ${activities.length - 8} more</div>`;
          }
        } else {
          tipContent += `<div class="heatmap-tooltip-action" style="color: var(--text-tertiary);">${isFuture ? "Scheduled boxes pending" : "No boxes checked"}</div>`;
        }

        tooltip.innerHTML = tipContent;
        tooltip.classList.add("visible");
        this.positionTooltip(e, tooltip);
      });

      cell.addEventListener("mousemove", (e) => {
        this.positionTooltip(e, tooltip);
      });

      cell.addEventListener("mouseleave", () => {
        tooltip.classList.remove("visible");
      });
    });
  },

  positionTooltip(e, tooltip) {
    const offset = 12;
    let x = e.clientX + offset;
    let y = e.clientY - offset;

    const tooltipWidth = tooltip.offsetWidth || 200;
    const tooltipHeight = tooltip.offsetHeight || 80;

    if (x + tooltipWidth > window.innerWidth - 10) {
      x = e.clientX - tooltipWidth - offset;
    }
    if (y + tooltipHeight > window.innerHeight - 10) {
      y = window.innerHeight - tooltipHeight - 10;
    }
    if (y < 10) y = 10;

    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  },

  renderUpcoming() {
    const upcoming = this.data.upcoming || [];
    const container = document.getElementById("upcomingReelContainer");
    if (!container) return;

    container.innerHTML = upcoming
      .map((day) => {
        const isTomorrow = day.is_tomorrow;
        const schedKey = (day.schedule_key || "").toLowerCase();
        let badgeClass = "sched-a";
        if (schedKey.includes("b")) badgeClass = "sched-b";
        if (schedKey.includes("c")) badgeClass = "sched-c";

        let gymSnippet = "";
        if (day.gym_routine) {
          gymSnippet = `
            <div style="margin-top: 6px; font-size: 10px; color: var(--accent-gold-dim); font-family: var(--font-mono);">
              🏋️ ${this.escapeHtml(day.gym_routine.name.split("—")[1] || day.gym_routine.name)}
            </div>
          `;
        }

        // Render key time blocks directly from the actual routine
        const blocks = day.blocks || [];
        let blocksHtml = "";
        if (blocks.length > 0) {
          blocksHtml = `
            <div class="forecast-blocks-list">
              ${blocks
                .map((b) => {
                  const isDeep = b.type === "deep_work";
                  const isTraining = b.type === "training";
                  let blockClass = "";
                  if (isDeep) blockClass = "deep-work";
                  if (isTraining) blockClass = "training";
                  return `
                    <div class="forecast-block-row ${blockClass}">
                      <span class="forecast-block-time">${this.escapeHtml(b.time)}</span>
                      <span class="forecast-block-focus">${this.escapeHtml(b.focus)}</span>
                    </div>
                  `;
                })
                .join("")}
            </div>
          `;
        }

        return `
          <div class="forecast-day-card ${isTomorrow ? "tomorrow-highlight" : ""}">
            <div>
              <div class="forecast-header">
                <div class="forecast-day-name">
                  <span>${day.day_name}</span>
                  ${isTomorrow ? '<span class="forecast-tag-tomorrow">TOMORROW</span>' : ""}
                </div>
                <div class="forecast-date">${day.display_date}</div>
              </div>

              <div>
                <span class="forecast-schedule-badge ${badgeClass}">
                  ${day.schedule_key ? `SCHED ${day.schedule_key}` : "ROUTINE"}
                </span>
                <div class="forecast-highlight-text">${this.escapeHtml(day.key_highlight)}</div>
                ${day.cutoff_info ? `<div class="forecast-cutoff-text">${this.escapeHtml(day.cutoff_info)}</div>` : ""}
                ${gymSnippet}
                ${blocksHtml}
              </div>
            </div>

            <div class="forecast-footer-info">
              <span>${day.task_count > 0 ? `${day.task_count} tasks ready` : "Routine ready"}</span>
              <span style="color: var(--text-tertiary);">${day.is_tomorrow ? "Next day" : `in ${day.days_away}d`}</span>
            </div>
          </div>
        `;
      })
      .join("");
  },

  renderPillars() {
    const metrics = this.data.metrics || {};

    // 1. TUM Metro Pillar
    const stMonth = document.getElementById("dashActiveStationMonth");
    const stName = document.getElementById("dashActiveStationName");
    const stNext = document.getElementById("dashStationNextAction");
    const germanEl = document.getElementById("dashGermanLevel");
    const gpaEl = document.getElementById("dashOverallGpa");
    const maturaEl = document.getElementById("dashMaturaAvg");

    if (metrics.active_station) {
      if (stMonth) stMonth.textContent = metrics.active_station.month || "ACTIVE";
      if (stName) stName.textContent = metrics.active_station.name || "Station";
      if (stNext) stNext.textContent = metrics.active_station.next_action || "Complete station deliverables.";
    }
    if (germanEl) germanEl.textContent = metrics.german_stage || "A2";
    if (gpaEl) gpaEl.textContent = (metrics.overall_gpa || 0.0).toFixed(2);
    if (maturaEl) maturaEl.textContent = `${(metrics.avg_matura_mock || 0.0).toFixed(0)}%`;

    // 2. Body Pillar
    const weightVal = document.getElementById("dashWeightVal");
    const fillEl = document.getElementById("dashWeightProgressFill");
    const boxingCount = document.getElementById("dashBoxingCount");
    const gymCount = document.getElementById("dashGymCount");
    const runCount = document.getElementById("dashRunCount");

    const curWeight = metrics.latest_weight || 68.0;
    const targetWeight = metrics.target_weight || 80.0;
    if (weightVal) weightVal.textContent = `${curWeight.toFixed(1)} / ${targetWeight.toFixed(1)} kg`;

    // Progress bar from 68kg (0%) to 80kg (100%)
    if (fillEl) {
      const pct = Math.max(0, Math.min(100, ((curWeight - 68.0) / (80.0 - 68.0)) * 100));
      fillEl.style.width = `${pct}%`;
    }

    const wouts = metrics.weekly_workouts || {};
    if (boxingCount && wouts.boxing) boxingCount.textContent = `${wouts.boxing.count}/${wouts.boxing.target}`;
    if (gymCount && wouts.gym) gymCount.textContent = `${wouts.gym.count}/${wouts.gym.target}`;
    if (runCount && wouts.running) runCount.textContent = `${wouts.running.count}/${wouts.running.target}`;

    // 3. Projects Pillar
    const projList = document.getElementById("dashProjectsList");
    const projects = this.data.projects || [];
    if (projList) {
      projList.innerHTML = projects
        .slice(0, 3)
        .map((p) => {
          return `
            <div class="dash-project-row">
              <div class="dash-project-name">${this.escapeHtml(p.name)}</div>
              <div class="dash-project-next">${this.escapeHtml(p.next_action || p.current_milestone || "Active sprint")}</div>
            </div>
          `;
        })
        .join("");
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
