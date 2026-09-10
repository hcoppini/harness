/**
 * Layer 0: DASHBOARD CONTROLLER (Executive Cockpit)
 * Features:
 * - Top Executive Cockpit Trajectory Gauges
 * - Daily Execution Activity Heatmap with Tooltips
 * - Upcoming 7-Day Schedule Forecast
 * - Priority Radar (Homework & Exams)
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

    const btn7Day = document.getElementById("btnView7DaySchedule");
    if (btn7Day) {
      btn7Day.addEventListener("click", () => {
        this.openDetailedScheduleModal();
      });
    }

    const btnJumpToday = document.getElementById("btnDetailedJumpToday");
    if (btnJumpToday) {
      btnJumpToday.addEventListener("click", () => {
        const targetDate = this.selectedForecastDate || new Date().toISOString().split("T")[0];
        this.closeDetailedScheduleModal();
        if (window.HarnessApp) {
          window.HarnessApp.switchView("today");
          if (window.Today) {
            window.Today.selectDate(targetDate);
          }
        }
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

    this.renderCockpitGauges();
    this.renderHeatmap();
    this.renderUpcoming();
    this.renderRadar();
  },

  renderCockpitGauges() {
    const metrics = this.data.metrics || {};
    const velocity = this.data.today_velocity || {};
    const projects = this.data.projects || [];

    // Streak
    const streakVal = document.getElementById("streakCountVal");
    if (streakVal) {
      streakVal.textContent = metrics.current_streak || 0;
    }

    // Gauge 1: Today's Velocity
    const todayPctVal = document.getElementById("dashTodayProgressVal");
    const todayBar = document.getElementById("dashTodayProgressBar");
    const todayRoutineLabel = document.getElementById("dashTodayRoutineLabel");

    const pct = velocity.percentage || 0;
    if (todayPctVal) todayPctVal.textContent = `${pct}%`;
    if (todayBar) todayBar.style.width = `${pct}%`;
    if (todayRoutineLabel) {
      todayRoutineLabel.textContent = `${velocity.checked_boxes || 0}/${velocity.total_boxes || 0} boxes completed • ${velocity.schedule_name || "Daily routine"}`;
    }

    // Gauge 2: TUM Admissions Readiness
    const gpaEl = document.getElementById("dashOverallGpa");
    const maturaEl = document.getElementById("dashMaturaAvg");
    const germanEl = document.getElementById("dashGermanLevel");
    const stName = document.getElementById("dashActiveStationName");

    if (gpaEl) {
      const pl = (metrics.overall_gpa || 0.0).toFixed(2);
      const de = metrics.bavarian_gpa ? ` (DE: ${Number(metrics.bavarian_gpa).toFixed(2)})` : "";
      gpaEl.textContent = `${pl}${de}`;
    }
    if (maturaEl) maturaEl.textContent = `${(metrics.avg_matura_mock || 0.0).toFixed(0)}%`;
    if (germanEl) germanEl.textContent = metrics.german_stage || "A2 Active";
    if (stName) {
      stName.textContent = `Station: ${metrics.active_station?.name || "Pure Syntax"}`;
    }

    // Gauge 3: Body & Physique
    const weightVal = document.getElementById("dashWeightVal");
    const weightFill = document.getElementById("dashWeightProgressFill");
    const workoutsText = document.getElementById("dashWorkoutsSummaryText");

    const curWeight = metrics.latest_weight || 68.0;
    const targetWeight = metrics.target_weight || 80.0;
    if (weightVal) weightVal.textContent = `${curWeight.toFixed(1)} kg`;

    if (weightFill) {
      const weightPct = Math.max(0, Math.min(100, ((curWeight - 68.0) / (80.0 - 68.0)) * 100));
      weightFill.style.width = `${weightPct}%`;
    }

    const wouts = metrics.weekly_workouts || {};
    const boxCount = wouts.boxing ? `${wouts.boxing.count}/${wouts.boxing.target}` : "0/3";
    const gymCount = wouts.gym ? `${wouts.gym.count}/${wouts.gym.target}` : "0/4";
    const runCount = wouts.running ? `${wouts.running.count}/${wouts.running.target}` : "0/2";
    if (workoutsText) {
      workoutsText.textContent = `Boxing ${boxCount} • Gym ${gymCount} • Run ${runCount}`;
    }

    // Gauge 4: Active Builds
    const projCountEl = document.getElementById("dashProjectsCount");
    const topProjNext = document.getElementById("dashTopProjectNextAction");

    if (projCountEl) projCountEl.textContent = `${projects.length} Active Builds`;
    if (topProjNext && projects.length > 0) {
      topProjNext.textContent = `Next: ${projects[0].next_action || projects[0].current_milestone || "Execute sprint"}`;
    }
  },

  renderHeatmap() {
    const heatmap = this.data.heatmap;
    if (!heatmap) return;

    const countEl = document.getElementById("heatmapContributionsCount");
    if (countEl) {
      const count = heatmap.total_contributions || 0;
      countEl.textContent = `${count} ${count === 1 ? "box" : "boxes"} completed since cycle start`;
    }

    const container = document.getElementById("heatmapContainer");
    if (!container) return;

    const weeks = heatmap.weeks || [];
    const months = heatmap.months || [];

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

    const totalWeeks = Math.max(1, weeks.length);
    months.forEach((m) => {
      const leftPct = (m.week_index / totalWeeks) * 100;
      html += `<span class="heatmap-month-label" style="left: ${leftPct.toFixed(2)}%;">${m.name}</span>`;
    });

    html += `</div><div class="heatmap-weeks-grid">`;

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

    const scrollWrap = document.getElementById("heatmapScrollWrap");
    if (scrollWrap) {
      setTimeout(() => {
        scrollWrap.scrollLeft = scrollWrap.scrollWidth;
      }, 50);
    }

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
        const displayDate = dayInfo.display_date || dateStr;
        const activities = dayInfo.activities || [];
        const isFuture = dayInfo.is_future;

        let statusBadge = "";
        if (isFuture) {
          statusBadge = `<span style="color: var(--text-tertiary); font-size: 10px;">(Upcoming)</span>`;
        } else if (total > 0 && count >= total) {
          statusBadge = `<span style="color: var(--accent-purple-light); font-weight: 700; font-size: 11px;">100% (All ${total} Done!)</span>`;
        } else if (total > 0) {
          const pct = Math.round((count / total) * 100);
          statusBadge = `<span style="color: var(--text-secondary); font-size: 11px;">${count}/${total} (${pct}%)</span>`;
        } else {
          statusBadge = `<span style="color: var(--text-secondary); font-size: 11px;">${count} completed</span>`;
        }

        let tipContent = `
          <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; border-bottom: 1px solid var(--border-hairline); padding-bottom: 2px;">
            ${displayDate} ${statusBadge}
          </div>
        `;

        if (activities.length > 0) {
          tipContent += activities
            .slice(0, 6)
            .map((act) => `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(act)}</div>`)
            .join("");
          if (activities.length > 6) {
            tipContent += `<div style="font-size: 10px; color: var(--text-tertiary); margin-top: 2px;">+ ${activities.length - 6} more</div>`;
          }
        } else {
          tipContent += `<div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${isFuture ? "Scheduled routine pending" : "No activity recorded"}</div>`;
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

    const tooltipWidth = tooltip.offsetWidth || 220;
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
            <div style="margin-top: 4px; font-size: 10px; color: var(--accent-lavender); font-weight: 500; font-family: var(--font-mono);">
              LIFT: ${this.escapeHtml(day.gym_routine.name.split("—")[1] || day.gym_routine.name)}
            </div>
          `;
        }

        let actionsHtml = "";
        if (day.actions && day.actions.length > 0) {
          actionsHtml = `
            <div style="margin-top: 6px; display: flex; flex-direction: column; gap: 2px;">
              ${day.actions.slice(0, 3).map((act) => `
                <div class="forecast-action-item">
                  <span class="forecast-action-time">${this.escapeHtml(act.time.split(" - ")[0])}</span>
                  <span class="forecast-action-label">${this.escapeHtml(act.label)}</span>
                </div>
              `).join("")}
            </div>
          `;
        }

        const klCount = (day.kill_list_items || []).length;
        const taskCount = day.task_count || 0;
        const taskPill = klCount > 0 ? `${klCount} kill • ${taskCount} tasks` : taskCount > 0 ? `${taskCount} tasks` : "Routine ready";

        return `
          <div 
            class="forecast-day-card ${isTomorrow ? "tomorrow-highlight" : ""}" 
            onclick="Dashboard.openDetailedScheduleModal('${day.date}')"
            title="Click to view detailed timeline for ${day.day_name}"
            style="cursor: pointer;"
          >
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
                ${actionsHtml}
                ${gymSnippet}
              </div>
            </div>

            <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--border-hairline); font-size: 10px; color: var(--text-tertiary); display: flex; justify-content: space-between;">
              <span style="${klCount > 0 ? "color: var(--accent-lavender); font-weight: 600;" : ""}">${taskPill}</span>
              <span>${day.is_tomorrow ? "Next day" : `in ${day.days_away}d &rarr;`}</span>
            </div>
          </div>
        `;
      })
      .join("");
  },

  openDetailedScheduleModal(selectedDate = null) {
    const modal = document.getElementById("detailedScheduleModal");
    if (!modal || !this.data || !this.data.upcoming) return;

    const upcoming = this.data.upcoming;
    if (upcoming.length === 0) return;

    this.selectedForecastDate = selectedDate || upcoming[0].date;

    // Render day tabs
    const tabsContainer = document.getElementById("detailedScheduleDayTabs");
    if (tabsContainer) {
      tabsContainer.innerHTML = upcoming
        .map((day) => {
          const isSelected = day.date === this.selectedForecastDate;
          return `
            <button 
              class="btn-ghost-icon ${isSelected ? "active" : ""}" 
              onclick="Dashboard.selectDetailedDay('${day.date}')"
              style="white-space: nowrap; font-size: 11px; padding: 4px 8px; ${isSelected ? "border-color: var(--accent-lavender); color: var(--accent-lavender); font-weight: 700;" : ""}"
            >
              <span>${day.day_name.slice(0, 3)}</span> 
              <span style="font-family: var(--font-mono); font-size: 10px; opacity: 0.75;">${day.display_date.split(",")[1] || day.display_date}</span>
            </button>
          `;
        })
        .join("");
    }

    const currentDay = upcoming.find((d) => d.date === this.selectedForecastDate) || upcoming[0];
    this.renderDetailedScheduleDay(currentDay);

    modal.classList.add("open");
  },

  selectDetailedDay(dateStr) {
    this.selectedForecastDate = dateStr;
    const upcoming = this.data.upcoming || [];
    const currentDay = upcoming.find((d) => d.date === dateStr);

    const tabs = document.querySelectorAll("#detailedScheduleDayTabs button");
    tabs.forEach((btn) => {
      if (btn.textContent.includes(currentDay ? currentDay.day_name.slice(0, 3) : "")) {
        btn.classList.add("active");
        btn.style.borderColor = "var(--accent-lavender)";
        btn.style.color = "var(--accent-lavender)";
        btn.style.fontWeight = "700";
      } else {
        btn.classList.remove("active");
        btn.style.borderColor = "";
        btn.style.color = "";
        btn.style.fontWeight = "normal";
      }
    });

    if (currentDay) {
      this.renderDetailedScheduleDay(currentDay);
    }
  },

  renderDetailedScheduleDay(day) {
    const content = document.getElementById("detailedScheduleContent");
    if (!content || !day) return;

    const schedKey = (day.schedule_key || "").toLowerCase();
    let badgeClass = "sched-a";
    if (schedKey.includes("b")) badgeClass = "sched-b";
    if (schedKey.includes("c")) badgeClass = "sched-c";

    // 1. Day Banner
    const bannerHtml = `
      <div style="background: rgba(196, 181, 253, 0.05); border: 1px solid rgba(196, 181, 253, 0.18); border-radius: 6px; padding: 12px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="forecast-schedule-badge ${badgeClass}" style="font-size: 10px; padding: 2px 6px;">
              ${day.schedule_key ? `SCHEDULE ${day.schedule_key}` : "ROUTINE"}
            </span>
            <span style="font-size: 14px; font-weight: 700; color: var(--text-primary);">${day.day_name}, ${day.display_date}</span>
          </div>
          <span style="font-family: var(--font-mono); font-size: 10px; color: var(--accent-lavender);">
            ${day.is_tomorrow ? "TOMORROW" : `in ${day.days_away} days`}
          </span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; margin-top: 2px;">
          ${this.escapeHtml(day.schedule_name)}
        </div>
        ${day.cutoff_info ? `<div style="font-family: var(--font-mono); font-size: 10px; color: #f59e0b; margin-top: 4px;">⚠️ Cutoff Target: ${this.escapeHtml(day.cutoff_info)}</div>` : ""}
      </div>
    `;

    // 2. Timeline Blocks
    const blocks = day.blocks || [];
    let blocksHtml = "";
    if (blocks.length > 0) {
      blocksHtml = `
        <div style="margin-bottom: 14px;">
          <div class="card-label" style="margin-bottom: 8px;">PRE-CALIBRATED ROUTINE TIMELINE</div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${blocks
              .map((b) => `
                <div style="display: flex; align-items: baseline; justify-content: space-between; padding: 7px 10px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-hairline); border-radius: 4px;">
                  <div style="display: flex; align-items: baseline; gap: 10px;">
                    <span style="font-family: var(--font-mono); font-size: 10px; color: var(--accent-lavender); flex-shrink: 0; min-width: 85px;">
                      ${this.escapeHtml(b.time || "")}
                    </span>
                    <span style="font-size: 12px; font-weight: 500; color: var(--text-primary);">
                      ${this.escapeHtml(b.focus || "")}
                    </span>
                  </div>
                  ${b.cutoff ? `<span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary);">${this.escapeHtml(b.cutoff)}</span>` : ""}
                </div>
              `)
              .join("")}
          </div>
        </div>
      `;
    }

    // 3. Gym Protocol
    let gymHtml = "";
    if (day.gym_routine) {
      const g = day.gym_routine;
      const exercises = g.exercises || [];
      gymHtml = `
        <div style="margin-bottom: 14px; background: rgba(244, 63, 94, 0.04); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 6px; padding: 12px;">
          <div class="card-label" style="color: #fda4af; margin-bottom: 6px;">STRUCTURED HYPERTROPHY PROTOCOL</div>
          <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">
            ${this.escapeHtml(g.name)}
          </div>
          ${exercises.length > 0 ? `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
              ${exercises
                .map((ex) => `
                  <div style="font-size: 11px; padding: 4px 8px; background: rgba(0,0,0,0.25); border-radius: 3px; border: 1px solid var(--border-hairline);">
                    <span style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(ex.name)}</span>
                    <span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); margin-left: 4px;">${this.escapeHtml(ex.sets || "")}</span>
                  </div>
                `)
                .join("")}
            </div>
          ` : ""}
        </div>
      `;
    }

    // 4. Scheduled Tasks & Kill Items
    const tasks = day.tasks || [];
    const killItems = day.kill_list_items || [];
    let itemsHtml = "";
    if (tasks.length > 0 || killItems.length > 0) {
      itemsHtml = `
        <div style="margin-bottom: 10px;">
          <div class="card-label" style="margin-bottom: 6px;">SCHEDULED TASKS &amp; KILL ITEMS (${tasks.length + killItems.length})</div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            ${killItems
              .map((k) => `
                <div style="font-size: 11px; padding: 6px 10px; background: rgba(196,181,253,0.06); border: 1px solid rgba(196,181,253,0.18); border-radius: 4px; display: flex; align-items: center; justify-content: space-between;">
                  <span><strong>[${this.escapeHtml(k.category)}]</strong> ${this.escapeHtml(k.title)}</span>
                  <span class="mono-chip lavender" style="font-size: 8px;">Kill Item</span>
                </div>
              `)
              .join("")}
            ${tasks
              .map((t) => `
                <div style="font-size: 11px; padding: 6px 10px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-hairline); border-radius: 4px; display: flex; align-items: center; justify-content: space-between;">
                  <span>${this.escapeHtml(t.title)}</span>
                  <span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary);">${this.escapeHtml(t.category || "Task")}</span>
                </div>
              `)
              .join("")}
          </div>
        </div>
      `;
    }

    content.innerHTML = bannerHtml + blocksHtml + gymHtml + itemsHtml;
  },

  closeDetailedScheduleModal() {
    const modal = document.getElementById("detailedScheduleModal");
    if (modal) modal.classList.remove("open");
  },

  renderRadar() {
    const hwContainer = document.getElementById("dashHomeworkList");
    const examContainer = document.getElementById("dashExamsList");
    const radar = this.data.radar || {};

    const hwItems = radar.homework || [];
    const examItems = radar.exams || [];

    if (hwContainer) {
      if (hwItems.length === 0) {
        hwContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 6px 0;">All assignments cleared.</div>`;
      } else {
        hwContainer.innerHTML = hwItems
          .map((h) => {
            let dueBadge = `${h.due_date}`;
            if (h.days_left === 0) dueBadge = "Today";
            else if (h.days_left === 1) dueBadge = "Tomorrow";
            else if (h.days_left < 0) dueBadge = `${Math.abs(h.days_left)}d overdue`;
            else dueBadge = `in ${h.days_left}d`;

            const isOverdue = h.days_left < 0;

            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px;">
                <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 75%;">
                  <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 600;">[${this.escapeHtml(h.subject)}]</span>
                  <span style="font-size: 12px; color: var(--text-primary);">${this.escapeHtml(h.title)}</span>
                </div>
                <span class="key-pill" style="font-size: 9px; ${isOverdue ? "border-color: #ef4444; color: #ef4444;" : ""}">${dueBadge}</span>
              </div>
            `;
          })
          .join("");
      }
    }

    if (examContainer) {
      if (examItems.length === 0) {
        examContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 6px 0;">No upcoming tests scheduled.</div>`;
      } else {
        examContainer.innerHTML = examItems
          .map((e) => {
            let countdown = `${e.days_left}d left`;
            if (e.days_left === 0) countdown = "TODAY";
            else if (e.days_left === 1) countdown = "TOMORROW";

            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px;">
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 75%;">
                  <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); font-weight: 600;">[${this.escapeHtml(e.subject)}]</span>
                  <span style="font-size: 12px; color: var(--text-primary); margin-left: 4px;">${this.escapeHtml(e.title)}</span>
                </div>
                <span class="key-pill" style="font-size: 9px; color: var(--accent-purple-light);">${countdown}</span>
              </div>
            `;
          })
          .join("");
      }
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
