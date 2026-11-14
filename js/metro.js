/**
 * Section 2: TUM METRO ROADMAP // Sleek Two-Tier Transit Architecture (Version 6.0)
 *
 * Architecture:
 * - Tier 1: Crisp Horizontal Timeline Rail
 *   - Continuous progression rail (solid elapsed stroke, light future stroke).
 *   - Clean station nodes (Completed with ✓ checkmark, Active concentric blue ring with
 *     "Active 'TUM' station" label, Future hollow nodes, and Golden Terminal).
 *   - Clean Today vertical indicator with 2-line monospace date/progress typography.
 *   - Dynamic Multi-Tier Staggered School Exams: displays ALL upcoming exams on vertical
 *     leader lines with non-colliding staggered heights (Tier 0-3) and crisp '[Xd] Subject'
 *     labels, eliminating stacked badge pills and visual clutter.
 * - Tier 2: Responsive Milestone Cards Grid (Matching User Mockup)
 *   - Uniform, elegant cards with Month tag, status chip, milestone title, stream micro-tags,
 *     and slim progress bar.
 *   - Active station spotlight with 1.5px accent border and elevated styling.
 *   - Two-way interaction: hovering/clicking a card highlights the station node on the rail
 *     above and opens the detailed milestone drawer.
 */

const MetroMap = {
  mobileSelectedStationId: null,
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  focusedStationId: null,
  currentBeaconX: 0,
  stationProgress: [],
  paceVelocity: null,
  upcomingExams: [],

  // Stream Definitions
  streams: [
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      color: "#a855f7",
      yOffset: -28,
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      color: "#38bdf8",
      yOffset: -14,
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      color: "#f59e0b",
      yOffset: 20,
    },
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      color: "#10b981",
      yOffset: -40,
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      color: "#f43f5e",
      yOffset: 34,
    },
  ],

  getStreamColor(streamId) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    switch (streamId) {
      case "academics": return isDark ? "#c084fc" : "#7e22ce";
      case "code": return isDark ? "#38bdf8" : "#0284c7";
      case "sigg": return isDark ? "#fbbf24" : "#d97706";
      case "german": return isDark ? "#34d399" : "#059669";
      case "physical": return isDark ? "#fb7185" : "#e11d48";
      default: return isDark ? "#ffffff" : "#111827";
    }
  },

  saveState() {
    if (!this.data) return;
    try {
      localStorage.setItem("harness_metro_roadmap_v4", JSON.stringify(this.data));
    } catch (e) {
      console.warn("[MetroMap] saveState error:", e);
    }
  },

    selectMobileStation(stationId) {
    this.mobileSelectedStationId = stationId;
    this.renderMobileHud();
  },

  renderMobileHud() {
    const container = document.getElementById("mobileMetroHud");
    if (!container || !this.data || !this.data.stations) return;

    const stations = this.data.stations;
    let activeIndex = stations.findIndex((s) => s.status === "active");
    if (activeIndex === -1) activeIndex = 0;

    let currentStationId = this.mobileSelectedStationId || stations[activeIndex].id;
    let station = stations.find((s) => s.id === currentStationId) || stations[activeIndex];
    const stationIndex = stations.findIndex((s) => s.id === station.id);

    const status = station.status || "upcoming";
    const progressPercent = this.calculateStationProgress(station);
    const delivEntries = Object.entries(station.deliverables || {});
    const completedList = station.completed_deliverables || [];

    const now = new Date();
    const dayOfMonth = now.getDate();
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const timeElapsedPct = Math.min(100, Math.max(0, Math.round((dayOfMonth / daysInMonth) * 100)));

    let velocity = this.paceVelocity;
    if (!velocity || velocity.station_id !== station.id) {
      const isBehind = progressPercent < timeElapsedPct;
      velocity = {
        station_id: station.id,
        day_of_month: dayOfMonth,
        total_days: daysInMonth,
        elapsed_pct: timeElapsedPct,
        is_behind: isBehind,
        status_text: isBehind
          ? `Pace Deficit: ${Math.round(timeElapsedPct - progressPercent)}% behind schedule`
          : `Pace Velocity: Optimal (+${Math.max(0, Math.round(progressPercent - timeElapsedPct))}%)`,
        badge_variant: isBehind ? "amber" : "optimal",
      };
    }

    const validDayOfMonth = velocity?.day_of_month || dayOfMonth;
    const validTotalDays = velocity?.total_days || daysInMonth;
    const validElapsedPct = (velocity?.elapsed_pct !== undefined && !isNaN(velocity.elapsed_pct))
      ? velocity.elapsed_pct
      : (validTotalDays > 0 ? Math.min(100, Math.max(0, Math.round((validDayOfMonth / validTotalDays) * 100))) : timeElapsedPct);

    let statusText = velocity?.status_text || (velocity?.is_behind ? "Pace Deficit: Behind schedule" : "Pace Velocity: Optimal");
    statusText = statusText.replace(/Pace Deficit:\s*-\s*/i, "Pace Deficit: ").replace(/undefined/g, "").replace(/NaN/g, "0");

    // Build select dropdown options
    const optionsHtml = stations
      .map((s, idx) => {
        const isCur = s.id === station.id;
        const tag = s.status === "active" ? " • ACTIVE" : (s.status === "completed" ? " ✓" : "");
        return `<option value="${s.id}" ${isCur ? "selected" : ""}>${String(idx + 1).padStart(2, "0")}: ${s.month_label} - ${this.escapeHtml(s.name)}${tag}</option>`;
      })
      .join("");

    // Build deliverables HTML (Clean, informative, zero checkboxes)
    let delivsHtml = "";
    if (delivEntries.length === 0) {
      delivsHtml = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px 0;">No active deliverables defined.</div>`;
    } else {
      delivsHtml = delivEntries
        .map(([key, val]) => {
          const streamMatch = this.streams.find((s) => s.name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(s.id));
          const lineBadgeColor = streamMatch ? streamMatch.color : "var(--accent-lavender)";

          const pMatch = (this.stationProgress || []).find(
            (p) => p.stream.toLowerCase() === key.toLowerCase() || (streamMatch && p.stream.toLowerCase() === streamMatch.id)
          );

          const isChecked = completedList.includes(key);
          const countObj = (station.deliverable_counts && station.deliverable_counts[key])
            || (pMatch ? { count: pMatch.completed_count, total: pMatch.total_required, unit: pMatch.unit_label } : null)
            || this.getDeliverableCounter(station.id, key, val);

          const curCount = isChecked ? countObj.total : (countObj.count || 0);
          const totalReq = countObj.total;
          const unitLabel = countObj.unit || "reps";
          const itemPct = totalReq > 0 ? Math.min(100, Math.round((curCount / totalReq) * 100)) : 0;

          const targetPace = Math.round(((validDayOfMonth / validTotalDays) * totalReq) * 10) / 10;
          const deficit = Math.round((targetPace - curCount) * 10) / 10;
          const isBehind = deficit > 0;

          return `
            <div class="mobile-hud-deliv-item ${isChecked || curCount >= totalReq ? "completed" : ""}" style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 10px 12px; margin-bottom: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 4px;">
                <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: ${lineBadgeColor}; text-transform: uppercase; letter-spacing: 0.04em;">
                  ${this.escapeHtml(key)} STREAM
                </span>
                <span style="font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; color: var(--text-primary);">
                  ${curCount} / ${totalReq} ${this.escapeHtml(unitLabel)}
                </span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 6px;">
                ${this.escapeHtml(val)}
              </div>
              <div style="height: 4px; background: var(--border-hairline); border-radius: 2px; overflow: hidden; margin-bottom: 4px;">
                <div style="width: ${itemPct}%; height: 100%; background: ${lineBadgeColor}; transition: width 0.3s ease;"></div>
              </div>
              ${status === "active" ? `
                <div style="font-family: var(--font-mono); font-size: 9px; color: ${isBehind ? 'var(--color-amber-light)' : 'var(--text-tertiary)'};">
                  ${isBehind ? `Pace Deficit: ${deficit} ${unitLabel} behind target` : `On pace (+${Math.abs(Math.round((curCount - targetPace) * 10) / 10)} ahead)`}
                </div>
              ` : ""}
            </div>
          `;
        })
        .join("");
    }

    const prevDisabled = stationIndex === 0;
    const nextDisabled = stationIndex >= stations.length - 1;

    container.innerHTML = `
      <div class="monotone-card mobile-hud-card" style="background: var(--bg-card); border: 1px solid var(--border-hairline); border-radius: 12px; padding: 14px; margin-bottom: 12px;">
        <!-- Station Selector Row -->
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-bottom: 12px;">
          <button type="button" class="btn-ghost-icon" style="padding: 4px 10px; font-size: 11px;" ${prevDisabled ? 'disabled style="opacity: 0.3;"' : `onclick="MetroMap.selectMobileStation('${stations[stationIndex - 1]?.id}')"`}>&larr; Prev</button>
          
          <select class="form-input theme-select" style="flex: 1; min-width: 0; padding: 5px 8px; font-size: 11px; font-weight: 600; font-family: var(--font-mono); text-align: center; border-radius: 6px; background: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border-subtle);" onchange="MetroMap.selectMobileStation(this.value)">
            ${optionsHtml}
          </select>

          <button type="button" class="btn-ghost-icon" style="padding: 4px 10px; font-size: 11px;" ${nextDisabled ? 'disabled style="opacity: 0.3;"' : `onclick="MetroMap.selectMobileStation('${stations[stationIndex + 1]?.id}')"`}>Next &rarr;</button>
        </div>

        <!-- Station Headline & Status -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 10px;">
          <div>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="mono-chip lavender" style="font-size: 9px; padding: 2px 6px;">${station.month_label || "2026"}</span>
              <span class="mono-chip ${status === "active" ? "lavender" : status === "completed" ? "green" : ""}" style="font-size: 9px; padding: 2px 6px; text-transform: uppercase;">${status === "active" ? "ACTIVE MILESTONE" : status}</span>
            </div>
            <h2 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin-top: 4px; letter-spacing: -0.01em;">
              ${this.escapeHtml(station.name)}
            </h2>
          </div>
          <div style="text-align: right; flex-shrink: 0;">
            <div style="font-family: var(--font-mono); font-size: 16px; font-weight: 800; color: var(--text-primary);">
              ${progressPercent}%
            </div>
            <div style="font-family: var(--font-mono); font-size: 9.5px; color: var(--text-tertiary);">
              COMPLETION
            </div>
          </div>
        </div>

        <!-- Dual Progress Indicators -->
        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; font-size: 9.5px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 3px;">
            <span>MONTH PACE</span>
            <span style="font-weight: 700; color: var(--text-primary);">Day ${validDayOfMonth}/${validTotalDays} (${validElapsedPct}%)</span>
          </div>
          <div style="height: 4px; background: var(--border-hairline); border-radius: 2px; overflow: hidden; margin-bottom: 8px;">
            <div style="width: ${validElapsedPct}%; height: 100%; background: var(--border-medium);"></div>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 9.5px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 3px;">
            <span>DELIVERABLES PACE</span>
            <span style="font-weight: 700; color: var(--accent-lavender);">${progressPercent}%</span>
          </div>
          <div style="height: 4px; background: var(--border-hairline); border-radius: 2px; overflow: hidden;">
            <div style="width: ${progressPercent}%; height: 100%; background: var(--accent-lavender);"></div>
          </div>
        </div>

        ${status === "active" ? `
          <div style="font-family: var(--font-mono); font-size: 10px; font-weight: 600; padding: 6px 10px; border-radius: 4px; margin-bottom: 10px; ${velocity?.is_behind ? "background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); color: #f59e0b;" : "background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-subtle); color: var(--text-primary);"}">
            ${this.escapeHtml(statusText)}
          </div>
        ` : ""}

        <!-- Core Objective Box -->
        ${station.objective ? `
          <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 10px;">
            <div class="card-label" style="font-size: 8.5px; margin-bottom: 2px;">CORE OBJECTIVE</div>
            <div style="font-size: 11.5px; color: var(--text-primary); line-height: 1.4;">${this.escapeHtml(station.objective)}</div>
          </div>
        ` : ""}

        <!-- Deliverables Breakdown -->
        <div style="margin-bottom: 10px;">
          <div class="card-label" style="font-size: 9px; margin-bottom: 6px; letter-spacing: 0.05em;">DELIVERABLES STATUS</div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${delivsHtml}
          </div>
          <div style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); margin-top: 6px; padding: 6px 8px; background: var(--bg-surface); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm);">
            💡 Check off tasks in the <strong>Daily</strong> tab to log progress.
          </div>
        </div>

        <!-- Bavarian GPA & Ledger Toggle -->
        <div style="border-top: 1px solid var(--border-hairline); padding-top: 10px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
          <div style="font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary);">
            Bavarian GPA: <span style="font-weight: 700; color: var(--text-primary);">${(() => {
              const gpaEl = document.getElementById("tumGermanGpaVal");
              const scoreEl = document.getElementById("tumTotalScoreVal");
              if (gpaEl && gpaEl.textContent && gpaEl.textContent !== "--") {
                return `${gpaEl.textContent} DE • ${scoreEl?.textContent || ""}`;
              }
              if (window.TumAptitude && window.TumAptitude.data && window.TumAptitude.data.bavarian_gpa) {
                return `${window.TumAptitude.data.bavarian_gpa.toFixed(2)} DE • ${Math.round(window.TumAptitude.data.total_score || 0)} pts`;
              }
              return "3.06 DE • 29.1 pts";
            })()}</span>
          </div>
          <button type="button" class="btn-ghost-icon" style="font-size: 10.5px; padding: 3px 8px;" onclick="document.getElementById('btnToggleGradesView')?.click()">
            Ledger &rarr;
          </button>
        </div>
      </div>
    `;
  },

  calculateStationProgress(station) {
    if (!station || !station.deliverables) return 0;
    if (station.status === "completed") return 100;
    const entries = Object.entries(station.deliverables);
    if (entries.length === 0) return 0;

    const completedList = station.completed_deliverables || [];
    const passedOverList = station.passed_over_deliverables || [];
    const countsMap = station.deliverable_counts || {};

    let totalScore = 0;
    entries.forEach(([key, val]) => {
      if (completedList.includes(key)) {
        totalScore += 1.0;
      } else if (passedOverList.includes(key)) {
        totalScore += 1.0;
      } else {
        const countObj = countsMap[key] || this.getDeliverableCounter(station.id, key, val);
        if (countObj && countObj.total > 0) {
          const frac = Math.min(1.0, Math.max(0, countObj.count / countObj.total));
          totalScore += frac;
        }
      }
    });

    return Math.min(100, Math.round((totalScore / entries.length) * 100));
  },

  getDeliverableCounter(stationId, key, val) {
    const st = this.data?.stations?.find((s) => s.id === stationId);
    if (st?.deliverable_counts?.[key]) {
      return st.deliverable_counts[key];
    }

    const kLow = (key || "").toLowerCase();
    const vLow = (val || "").toLowerCase();

    if (kLow.includes("code") || kLow.includes("syntax") || vLow.includes("leetcode") || vLow.includes("program")) {
      return { count: (stationId === "sep-2026" ? 4 : 0), total: 15, unit: "exercises" };
    }
    if (kLow.includes("math") || kLow.includes("academic") || vLow.includes("math") || vLow.includes("test")) {
      return { count: 0, total: 40, unit: "problems" };
    }
    if (kLow.includes("german") || vLow.includes("anki") || vLow.includes("vocab") || vLow.includes("words")) {
      return { count: 0, total: 100, unit: "words" };
    }
    if (kLow.includes("phys") || vLow.includes("protein") || vLow.includes("weight") || vLow.includes("fitness")) {
      return { count: 0, total: 30, unit: "days" };
    }
    if (kLow.includes("sigg") || vLow.includes("module") || vLow.includes("elearning")) {
      return { count: 0, total: 5, unit: "modules" };
    }

    const numMatch = (val || "").match(/\b(\d+)\b/);
    if (numMatch) {
      const parsedNum = parseInt(numMatch[1], 10);
      if (parsedNum > 1 && parsedNum <= 500) {
        return { count: 0, total: parsedNum, unit: "reps" };
      }
    }

    return { count: 0, total: 10, unit: "reps" };
  },

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    const container = document.getElementById("metroScrollContainer");
    if (!container) return;

    // Mouse drag scrolling
    container.addEventListener("mousedown", (e) => {
      if (
        e.target.closest(".metro-station-card") ||
        e.target.closest(".metro-grid-card") ||
        e.target.closest(".station-drawer") ||
        e.target.closest("button") ||
        e.target.closest(".metro-station-node") ||
        e.target.closest(".metro-test-tick")
      ) return;
      this.isDragging = true;
      container.classList.add("grabbing");
      this.startX = e.pageX - container.offsetLeft;
      this.scrollLeft = container.scrollLeft;
    });

    window.addEventListener("mouseup", () => {
      this.isDragging = false;
      container.classList.remove("grabbing");
    });

    container.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      e.preventDefault();
      const x = e.pageX - container.offsetLeft;
      const walk = (x - this.startX) * 1.5;
      container.scrollLeft = this.scrollLeft - walk;
    });

    // Touch swipe scrolling for mobile devices
    let touchStartX = 0;
    let touchScrollLeft = 0;

    container.addEventListener("touchstart", (e) => {
      if (
        e.target.closest(".metro-station-card") ||
        e.target.closest(".metro-grid-card") ||
        e.target.closest(".station-drawer") ||
        e.target.closest("button") ||
        e.target.closest(".metro-station-node") ||
        e.target.closest(".metro-test-tick")
      ) return;
      touchStartX = e.touches[0].pageX - container.offsetLeft;
      touchScrollLeft = container.scrollLeft;
    }, { passive: true });

    container.addEventListener("touchmove", (e) => {
      if (!touchStartX) return;
      const x = e.touches[0].pageX - container.offsetLeft;
      const walk = (x - touchStartX) * 1.3;
      container.scrollLeft = touchScrollLeft - walk;
    }, { passive: true });

    container.addEventListener("touchend", () => {
      touchStartX = 0;
    }, { passive: true });

    // Horizontal wheel navigation
    container.addEventListener(
      "wheel",
      (e) => {
        if (e.deltaY !== 0) {
          e.preventDefault();
          container.scrollLeft += e.deltaY;
        }
      },
      { passive: false }
    );

    // Close drawer button
    const closeBtn = document.getElementById("closeStationDrawerBtn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeDrawer());
    }

    // Station status selector change
    const statusSelect = document.getElementById("drawerStationStatus");
    if (statusSelect) {
      statusSelect.addEventListener("change", async (e) => {
        if (this.selectedStation) {
          await this.updateStatus(this.selectedStation.id, e.target.value);
        }
      });
    }

    // Jump to active station / beacon
    const btnJump = document.getElementById("btnJumpCurrentStation");
    if (btnJump) {
      btnJump.addEventListener("click", () => this.scrollToBeacon());
    }

    // Stream Filter Buttons
    const filterBtns = document.querySelectorAll(".metro-filter-btn");
    filterBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        filterBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeStreamFilter = btn.getAttribute("data-stream") || "all";
        this.render();
      });
    });
  },

  async load() {
    try {
      // 1. Immediately hydrate from localStorage if available
      let localRoadmap = null;
      try {
        const cached = localStorage.getItem("harness_metro_roadmap_v4");
        if (cached) localRoadmap = JSON.parse(cached);
      } catch (e) {}

      if (localRoadmap && localRoadmap.stations) {
        this.data = localRoadmap;
        this.render();
      }

      if (window.pywebview && window.pywebview.api) {
        const apiRoadmap = await window.pywebview.api.get_metro_roadmap();
        if (apiRoadmap && apiRoadmap.stations) {
          this.data = apiRoadmap;
          this.saveState();
        }
        if (window.pywebview.api.get_station_deliverables) {
          const activeStation = this.data?.stations?.find((s) => s.status === "active") || this.data?.stations?.[0];
          const stId = activeStation ? activeStation.id : "sep-2026";
          this.stationProgress = (await window.pywebview.api.get_station_deliverables(stId)) || [];
        }
        if (window.pywebview.api.get_station_pace_velocity) {
          const activeStation = this.data?.stations?.find((s) => s.status === "active") || this.data?.stations?.[0];
          const stId = activeStation ? activeStation.id : "sep-2026";
          this.paceVelocity = (await window.pywebview.api.get_station_pace_velocity(stId)) || null;
        }
        if (window.pywebview.api.get_upcoming_exams) {
          const rawExams = await window.pywebview.api.get_upcoming_exams();
          this.upcomingExams = (rawExams || []).filter((e) => {
            const t = ((e.title || "") + " " + (e.scope || "")).toLowerCase();
            return (
              !t.includes("trygonometria") &&
              !t.includes("kinematyka") &&
              !t.includes("wyszukiwania") &&
              !t.includes("powstanie styczniowe")
            );
          });
        }
      }

      if (!this.upcomingExams || this.upcomingExams.length === 0) {
        let cachedExams = null;
        try {
          const cachedStr = localStorage.getItem("harness_exams_v3");
          if (cachedStr) cachedExams = JSON.parse(cachedStr);
        } catch (e) {}

        if (Array.isArray(cachedExams) && cachedExams.length > 0) {
          const todayStr = (() => {
            const d = new Date();
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
          })();
          this.upcomingExams = cachedExams.filter((e) => {
            if (e.completed || (e.exam_date && e.exam_date < todayStr)) return false;
            const t = ((e.title || "") + " " + (e.scope || "")).toLowerCase();
            return !t.includes("trygonometria") && !t.includes("kinematyka") && !t.includes("wyszukiwania") && !t.includes("powstanie styczniowe");
          });
        }
      }
      if (!this.upcomingExams) this.upcomingExams = [];

      this.render();
      setTimeout(() => this.scrollToBeacon(), 200);
    } catch (err) {
      console.error("Error loading Metro Roadmap:", err);
    }
  },

  highlightStationOnRail(stationId) {
    this.focusedStationId = stationId;
    const ring = document.getElementById(`rail-ring-${stationId}`);
    if (ring) {
      ring.setAttribute("stroke-width", "3.5");
      ring.setAttribute("stroke", "var(--accent-lavender)");
    }
  },

  clearHighlightStationOnRail() {
    this.focusedStationId = null;
    document.querySelectorAll(".station-rail-node-ring").forEach((el) => {
      const origStroke = el.getAttribute("data-orig-stroke");
      const origWidth = el.getAttribute("data-orig-width");
      if (origStroke) el.setAttribute("stroke", origStroke);
      if (origWidth) el.setAttribute("stroke-width", origWidth);
    });
  },

  highlightCardInGrid(stationId) {
    document.querySelectorAll(".metro-grid-card").forEach((card) => {
      if (card.getAttribute("data-station-id") === stationId) {
        card.classList.add("highlighted-card");
      } else {
        card.classList.remove("highlighted-card");
      }
    });
  },

  clearHighlightCardInGrid() {
    document.querySelectorAll(".metro-grid-card").forEach((card) => {
      card.classList.remove("highlighted-card");
    });
  },

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    const cardsGrid = document.getElementById("metroCardsGrid");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 220;
    const startX = 120;
    const spineY = 110;
    const totalTrackLength = (stations.length - 1) * spacing;
    const terminusX = startX + totalTrackLength + 120;
    const totalWidth = terminusX + 160;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "210px";

    // Date calculations
    const startDate = new Date(2026, 8, 1);
    const endDate = new Date(2028, 6, 31);
    const now = new Date();

    let currentX = startX;
    let beaconTitle = "";
    let beaconSub = "";
    let isPreLaunch = false;
    let totalDays = 699;
    let elapsedDays = 31;
    let progressRatio = 0.044;

    if (now < startDate) {
      isPreLaunch = true;
      const msDiff = startDate.getTime() - now.getTime();
      const daysUntil = Math.max(1, Math.ceil(msDiff / (1000 * 60 * 60 * 24)));
      currentX = startX - 35;
      beaconTitle = "LAUNCH GATE";
      beaconSub = `${daysUntil}d to kickoff`;
    } else {
      const totalMs = endDate.getTime() - startDate.getTime();
      const elapsedMs = Math.min(totalMs, Math.max(0, now.getTime() - startDate.getTime()));
      progressRatio = elapsedMs / totalMs;
      totalDays = Math.round(totalMs / (1000 * 60 * 60 * 24));
      elapsedDays = Math.min(totalDays, Math.round(elapsedMs / (1000 * 60 * 60 * 24)));

      currentX = startX + progressRatio * totalTrackLength;
      const dateStr = now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      beaconTitle = `DAY ${elapsedDays + 1}/${totalDays}`;
      beaconSub = dateStr;
    }

    this.currentBeaconX = currentX;

    // Phase Milestones Headers (Top Zone, Y=14)
    const phases = [
      { name: "Phase 1: Year 3 Liceum", startIdx: 0, endIdx: 6 },
      { name: "Phase 2: SIGG Finals & Year 3 Lock", startIdx: 7, endIdx: 10 },
      { name: "Phase 3: Summer Mass & B1", startIdx: 11, endIdx: 11 },
      { name: "Phase 4: Matura Crucible", startIdx: 12, endIdx: 19 },
      { name: "Phase 5: Official CKE & TUM", startIdx: 20, endIdx: 21 },
    ];

    let phaseHeadersHtml = phases
      .map((p) => {
        const x1 = startX + p.startIdx * spacing - 30;
        const x2 = startX + p.endIdx * spacing + 80;
        const width = Math.max(120, x2 - x1);
        return `
          <div style="position: absolute; top: 12px; left: ${x1}px; width: ${width}px; pointer-events: none; z-index: 5;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.05em; white-space: nowrap;">
                ${p.name}
              </span>
              <div style="flex: 1; height: 1px; background: var(--border-hairline);"></div>
            </div>
          </div>
        `;
      })
      .join("");

    // Single Main Track (Elapsed solid black/dark, Future light subtle grey)
    const trunkHtml = `
      <!-- Future Track -->
      <line x1="${startX - 20}" y1="${spineY}" x2="${terminusX}" y2="${spineY}" 
            stroke="var(--border-subtle)" stroke-width="4" stroke-linecap="round" />
      
      <!-- Completed / Active Track up to Today -->
      ${
        currentX > startX - 20
          ? `<line x1="${startX - 20}" y1="${spineY}" x2="${Math.min(terminusX, currentX)}" y2="${spineY}" 
                  stroke="var(--text-primary)" stroke-width="4" stroke-linecap="round" />`
          : ""
      }
    `;

    // Dynamic 45° Tributary Rails (On demand when a stream filter is selected)
    let tributaryPathsHtml = "";
    if (this.activeStreamFilter !== "all") {
      const stream = this.streams.find((s) => s.id === this.activeStreamFilter);
      if (stream) {
        const color = this.getStreamColor(stream.id);
        const yOffset = stream.yOffset;
        const branchY = spineY + yOffset;
        const ramp = Math.abs(yOffset);

        const indices = [];
        stations.forEach((st, idx) => {
          if ((st.branches || []).includes(stream.id)) {
            indices.push(idx);
          }
        });

        if (indices.length > 0) {
          const segments = [];
          let cur = [indices[0]];
          for (let i = 1; i < indices.length; i++) {
            if (indices[i] === indices[i - 1] + 1) {
              cur.push(indices[i]);
            } else {
              segments.push(cur);
              cur = [indices[i]];
            }
          }
          segments.push(cur);

          segments.forEach((seg) => {
            const firstIdx = seg[0];
            const lastIdx = seg[seg.length - 1];
            const segStartX = startX + firstIdx * spacing;
            const segEndX = startX + lastIdx * spacing;
            const ingressX = segStartX - ramp;
            const egressX = segEndX + ramp;

            const pathD = `M ${ingressX} ${spineY} L ${segStartX} ${branchY} L ${segEndX} ${branchY} L ${egressX} ${spineY}`;

            tributaryPathsHtml += `
              <g class="stream-tributary-branch">
                <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />
            `;

            seg.forEach((idx) => {
              const px = startX + idx * spacing;
              tributaryPathsHtml += `
                <line x1="${px}" y1="${branchY}" x2="${px}" y2="${spineY}" stroke="${color}" stroke-width="1" stroke-dasharray="2 2" opacity="0.5" />
                <circle cx="${px}" cy="${branchY}" r="3" fill="${color}" stroke="var(--bg-canvas)" stroke-width="1.2" />
              `;
            });

            tributaryPathsHtml += `</g>`;
          });
        }
      }
    }

    // Dynamic School Exams on Track (Deduplicated, 55px non-overlapping clusters, alternating tiers)
    let examsSvgHtml = "";
    const showExamsOnTrack = this.activeStreamFilter === "all" || this.activeStreamFilter === "academics";
    const clusters = [];

    if (showExamsOnTrack && this.upcomingExams && this.upcomingExams.length > 0) {
      const todayMid = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

      // 1. Deduplicate exams by subject + date + title
      const seenExams = new Set();
      const uniqueExams = [];
      this.upcomingExams
        .filter((e) => !e.completed)
        .forEach((exam) => {
          const key = `${(exam.subject || "").trim().toLowerCase()}|${(exam.exam_date || "").trim()}|${(exam.title || "").trim().toLowerCase()}`;
          if (!seenExams.has(key)) {
            seenExams.add(key);
            uniqueExams.push(exam);
          }
        });

      const validExams = [];
      uniqueExams.forEach((exam) => {
        try {
          const exDate = new Date(exam.exam_date + "T12:00:00");
          const diffDays = Math.round((exDate.getTime() - todayMid) / (1000 * 60 * 60 * 24));
          // Only upcoming exams (diffDays >= 0) within roadmap horizon
          if (diffDays >= 0 && exDate >= startDate && exDate <= endDate) {
            const elapsed = exDate.getTime() - startDate.getTime();
            const totalMs = endDate.getTime() - startDate.getTime();
            const ratio = elapsed / totalMs;
            const testX = startX + ratio * totalTrackLength;
            const dueLabel = diffDays === 0 ? "TODAY" : diffDays === 1 ? "1d" : `${diffDays}d`;
            validExams.push({
              ...exam,
              exDate,
              testX,
              diffDays,
              dueLabel,
            });
          }
        } catch (e) {}
      });

      // Sort by horizontal position / date
      validExams.sort((a, b) => a.testX - b.testX);

      // Group nearby exams into non-overlapping clusters (55px collision threshold)
      validExams.forEach((exam) => {
        const lastCluster = clusters[clusters.length - 1];
        if (lastCluster && Math.abs(exam.testX - lastCluster.centerX) < 55) {
          lastCluster.exams.push(exam);
          if (exam.diffDays < lastCluster.diffDays) {
            lastCluster.diffDays = exam.diffDays;
            lastCluster.dueLabel = exam.dueLabel;
          }
        } else {
          clusters.push({
            centerX: exam.testX,
            diffDays: exam.diffDays,
            dueLabel: exam.dueLabel,
            exams: [exam],
          });
        }
      });

      // Assign non-colliding alternating vertical tiers:
      // Upper tier: tickTopY = 38, pillY = 23 (h=15, from y=23 to 38)
      // Lower tier: tickTopY = 72, pillY = 57 (h=15, from y=57 to 72)
      // Active station radar ring sits at y=94..126, so 72 < 94 gives 22px of clear margin!
      clusters.forEach((cl, idx) => {
        let labelText = "";
        if (cl.exams.length === 1) {
          const rawSubj = cl.exams[0].subject || "";
          const shortSubj = rawSubj.length > 8 ? rawSubj.slice(0, 7) + "." : rawSubj;
          labelText = `[${cl.dueLabel}] ${shortSubj}`;
        } else if (cl.exams.length === 2) {
          const s1 = (cl.exams[0].subject || "").slice(0, 4);
          const s2 = (cl.exams[1].subject || "").slice(0, 4);
          labelText = `[${cl.dueLabel}] ${s1}&${s2}`;
        } else {
          labelText = `[${cl.dueLabel}] ${cl.exams.length} Tests`;
        }

        const labelW = Math.max(54, labelText.length * 6.2 + 14);
        cl.w = labelW;
        cl.minX = cl.centerX - labelW / 2;
        cl.maxX = cl.centerX + labelW / 2;
        cl.labelText = labelText;

        if (idx === 0) {
          cl.tier = 1;
        } else {
          const prev = clusters[idx - 1];
          cl.tier = prev.tier === 1 ? 0 : 1;
        }

        cl.tickTopY = cl.tier === 0 ? 38 : 72;
        cl.pillY = cl.tier === 0 ? 23 : 57;
      });

      clusters.forEach((cl) => {
        const testX = cl.centerX;
        const tickTopY = cl.tickTopY;
        const isUrgent = cl.diffDays >= 0 && cl.diffDays <= 2;
        const lineColor = isUrgent ? "#ef4444" : "var(--border-medium)";
        const textColor = isUrgent ? "#ef4444" : "var(--text-primary)";
        const pillY = cl.pillY;
        const pillX = testX - cl.w / 2;

        const firstExam = cl.exams[0];
        const examsPayload = encodeURIComponent(
          JSON.stringify(
            cl.exams.map((e) => ({
              id: e.id,
              subject: e.subject,
              title: e.title,
              exam_date: e.exam_date,
              due: cl.dueLabel,
              scope: e.scope || "",
            }))
          )
        );

        examsSvgHtml += `
          <g class="metro-test-tick" data-cluster="${examsPayload}" data-id="${firstExam.id}" data-subject="${this.escapeHtml(firstExam.subject)}" data-title="${this.escapeHtml(firstExam.title)}" data-date="${firstExam.exam_date}" data-due="${cl.dueLabel}" data-count="${cl.exams.length}" style="cursor: pointer; pointer-events: all;">
            <!-- Vertical leader line -->
            <line x1="${testX}" y1="${spineY - 4}" x2="${testX}" y2="${tickTopY}" stroke="${lineColor}" stroke-width="1.2" stroke-dasharray="${isUrgent ? 'none' : '2 2'}" opacity="0.75" />
            <!-- Pin dot on track -->
            <circle cx="${testX}" cy="${spineY}" r="${cl.exams.length > 1 ? 3.5 : 2.5}" fill="${isUrgent ? '#ef4444' : 'var(--text-secondary)'}" stroke="var(--bg-canvas)" stroke-width="1.5" />
            <!-- Small top notch pip -->
            <circle cx="${testX}" cy="${tickTopY}" r="${cl.exams.length > 1 ? 2 : 1.5}" fill="${lineColor}" />
            <!-- Background pill: Prevents lines or dots from cutting through text -->
            <rect x="${pillX}" y="${pillY}" width="${cl.w}" height="15" rx="3" fill="var(--bg-canvas)" stroke="${isUrgent ? 'rgba(239, 68, 68, 0.45)' : 'var(--border-subtle)'}" stroke-width="1" />
            <!-- Clean monospace text label -->
            <text x="${testX}" y="${pillY + 11}" font-family="var(--font-mono)" font-size="8.5" font-weight="${isUrgent ? '700' : '600'}" text-anchor="middle" fill="${textColor}" letter-spacing="0.02em">
              ${this.escapeHtml(cl.labelText)}
            </text>
          </g>
        `;
      });
    }

    // Station Nodes along Track
    let stationsSvgHtml = "";
    stations.forEach((station, idx) => {
      const posX = startX + idx * spacing;
      const status = station.status || "upcoming";
      const isActive = status === "active";
      const isCompleted = status === "completed";
      const branches = station.branches || [];

      let nodeCircles = "";
      let labelSubText = station.month_label;
      let labelSubColor = "var(--text-tertiary)";

      if (isActive) {
        labelSubText = "ACTIVE STATION";
        labelSubColor = "var(--accent-lavender)";
        nodeCircles = `
          <!-- Concentric Precision Radar Rings for Active Station -->
          <circle cx="${posX}" cy="${spineY}" r="16" fill="none" stroke="var(--accent-lavender)" stroke-width="1" opacity="0.25" class="beacon-pulse" />
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--accent-lavender)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="11" fill="none" stroke="var(--accent-lavender)" stroke-width="2" />
          <circle cx="${posX}" cy="${spineY}" r="7" fill="var(--bg-canvas)" />
          <circle cx="${posX}" cy="${spineY}" r="4" fill="var(--accent-lavender)" />
        `;
      } else if (isCompleted) {
        const passedOverList = station.passed_over_deliverables || [];
        const isAudited = passedOverList.length > 0 && (!station.completed_deliverables || station.completed_deliverables.length === 0);
        if (isAudited) {
          labelSubText = "Audited";
          labelSubColor = "#f59e0b";
          nodeCircles = `
            <!-- Audited / Reallocated Node -->
            <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="#f59e0b" data-orig-width="1.8" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--bg-card)" stroke="#f59e0b" stroke-width="1.8" stroke-dasharray="3,2" />
            <circle cx="${posX}" cy="${spineY}" r="4" fill="#f59e0b" opacity="0.85" />
          `;
        } else {
          labelSubText = "Completed";
          nodeCircles = `
            <!-- Solid Circle with Checkmark -->
            <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--bg-card)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--text-primary)" stroke="var(--bg-card)" stroke-width="2" />
            <polyline points="${posX - 3},${spineY} ${posX - 1},${spineY + 2} ${posX + 3},${spineY - 2}" fill="none" stroke="var(--bg-card)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          `;
        }
      } else {
        nodeCircles = `
          <!-- Clean Hollow Circle for Future Stations -->
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--border-medium)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--bg-card)" stroke="var(--border-medium)" stroke-width="2" />
        `;
      }

      // Stream Micro-Pips beneath station
      const pipSpacing = 6;
      const pipsStartX = posX - ((branches.length - 1) * pipSpacing) / 2;
      let pipsSvg = "";
      branches.forEach((b, pIdx) => {
        const c = this.getStreamColor(b);
        pipsSvg += `<circle cx="${pipsStartX + pIdx * pipSpacing}" cy="${spineY + 42}" r="2" fill="${c}" />`;
      });

      // Station Labels Below the Rail
      const labelNameColor = isActive ? "var(--accent-lavender)" : isCompleted ? "var(--text-secondary)" : "var(--text-tertiary)";
      const labelFontWeight = isActive ? "800" : "600";

      stationsSvgHtml += `
        <g class="metro-rail-station-node" style="cursor: pointer; pointer-events: all;"
           onclick="MetroMap.selectStation('${station.id}')"
           onmouseenter="MetroMap.highlightCardInGrid('${station.id}')"
           onmouseleave="MetroMap.clearHighlightCardInGrid()">
          ${nodeCircles}
          <!-- Station Title Below Node -->
          <text x="${posX}" y="${spineY + 18}" text-anchor="middle" font-size="10.5" font-weight="${labelFontWeight}" fill="${labelNameColor}">
            ${this.escapeHtml(station.name)}
          </text>
          <!-- Status / Subtitle Below -->
          <text x="${posX}" y="${spineY + 30}" text-anchor="middle" font-family="var(--font-mono)" font-size="8.5" font-weight="${isActive ? '700' : '500'}" fill="${labelSubColor}">
            ${labelSubText}
          </text>
          <!-- Stream Pips -->
          ${pipsSvg}
          <!-- Transparent Hit Target -->
          <circle cx="${posX}" cy="${spineY}" r="20" fill="transparent" />
        </g>
      `;
    });

    // TUM '28 Golden Terminal at the Horizon
    const terminalSvgHtml = `
      <g style="cursor: pointer; pointer-events: all;" onclick="HarnessApp.switchView('study')">
        <circle cx="${terminusX}" cy="${spineY}" r="16" fill="none" stroke="#f59e0b" stroke-width="1.2" opacity="0.3" class="beacon-pulse" />
        <circle cx="${terminusX}" cy="${spineY}" r="11" fill="var(--bg-card)" stroke="#f59e0b" stroke-width="2" />
        <circle cx="${terminusX}" cy="${spineY}" r="4" fill="#f59e0b" />
        <text x="${terminusX}" y="${spineY + 18}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#f59e0b">
          TUM ’28
        </text>
        <text x="${terminusX}" y="${spineY + 30}" text-anchor="middle" font-family="var(--font-mono)" font-size="8" font-weight="700" fill="#f59e0b">
          Campus Heilbronn
        </text>
      </g>
    `;

    // Today Vertical Indicator (Sharp Needle with Non-Colliding Monospace Telemetry Pill Badge)
    const todayPillW = 146;
    const todayPillH = 28;
    const todayPillY = 20;

    // Check if any upcoming exam cluster falls within 85px of Today to avoid collision
    const nearExam = clusters.find((c) => c.centerX >= currentX && c.centerX < currentX + 85);
    const shiftTodayLeft = Boolean(nearExam);
    const todayPillX = shiftTodayLeft ? currentX - todayPillW - 4 : currentX - todayPillW / 2;

    const todayBeaconSvg = `
      <g class="metro-today-beacon" style="pointer-events: none; z-index: 25;">
        <!-- Clean vertical needle rising from rail -->
        <line x1="${currentX}" y1="${spineY - 4}" x2="${currentX}" y2="${todayPillY + todayPillH}" stroke="#ffffff" stroke-width="1.8" />
        <circle cx="${currentX}" cy="${spineY - 4}" r="2.5" fill="#ffffff" />
        ${shiftTodayLeft ? `
          <!-- Hairline connector arm to left-anchored pill -->
          <line x1="${currentX}" y1="${todayPillY + todayPillH / 2}" x2="${todayPillX + todayPillW}" y2="${todayPillY + todayPillH / 2}" stroke="rgba(255, 255, 255, 0.35)" stroke-width="1" stroke-dasharray="2 2" />
        ` : ""}
        
        <!-- Floating Pill Badge with Pitch-Black Backdrop -->
        <rect x="${todayPillX}" y="${todayPillY}" width="${todayPillW}" height="${todayPillH}" rx="4" fill="var(--bg-canvas)" stroke="rgba(255, 255, 255, 0.22)" stroke-width="1" />
        <text x="${todayPillX + todayPillW / 2}" y="${todayPillY + 11}" font-family="var(--font-mono)" font-size="8.5" font-weight="800" text-anchor="middle" fill="#ffffff" letter-spacing="0.04em">
          TODAY // ${now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase()}
        </text>
        <text x="${todayPillX + todayPillW / 2}" y="${todayPillY + 22}" font-family="var(--font-mono)" font-size="8" font-weight="700" text-anchor="middle" fill="var(--accent-lavender)" letter-spacing="0.02em">
          DAY ${elapsedDays + 1} OF ${totalDays} • ${(progressRatio * 100).toFixed(1)}% OF '26–'28
        </text>
      </g>
    `;

    // Assemble Track SVG
    canvasWrap.innerHTML = `
      ${phaseHeadersHtml}
      <svg width="${totalWidth}" height="210" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 20;">
        ${trunkHtml}
        ${tributaryPathsHtml}
        ${examsSvgHtml}
        ${stationsSvgHtml}
        ${terminalSvgHtml}
        ${todayBeaconSvg}
      </svg>
    `;

    // Render Tier 2: Responsive Milestone Cards Grid (Matching User Mockup)
    if (cardsGrid) {
      let gridCardsHtml = stations
        .map((station) => {
          const status = station.status || "upcoming";
          const isActive = status === "active";
          const isCompleted = status === "completed";
          const branches = station.branches || [];

          const isFilteredMatch = this.activeStreamFilter === "all" || branches.includes(this.activeStreamFilter);
          const filterStyle = isFilteredMatch ? "" : "opacity: 0.28; filter: grayscale(0.5);";

          const delivEntries = Object.entries(station.deliverables || {});
          const completedList = station.completed_deliverables || [];
          const totalDelivs = delivEntries.length;
          const progressPercent = this.calculateStationProgress(station);

          const passedOverList = station.passed_over_deliverables || [];
          const isAudited = isCompleted && passedOverList.length > 0 && (completedList.length === 0 || passedOverList.length >= totalDelivs);

          // Header Chip
          let chipHtml = "";
          if (isActive) {
            chipHtml = `<span class="metro-card-chip active">ACTIVE (${progressPercent}%)</span>`;
          } else if (isAudited) {
            chipHtml = `<span class="metro-card-chip" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.35);">AUDITED</span>`;
          } else if (isCompleted) {
            chipHtml = `<span class="metro-card-chip done">✓ DONE</span>`;
          } else {
            chipHtml = `<span class="metro-card-chip">${progressPercent}%</span>`;
          }

          // Micro-Tags
          const tagsHtml = branches
            .map((b) => {
              const c = this.getStreamColor(b);
              const streamObj = this.streams.find((s) => s.id === b);
              const sName = streamObj ? streamObj.name : b.toUpperCase();
              return `<span class="metro-micro-tag" style="background: ${c}15; color: ${c}; border: 1px solid ${c}35;">${sName}</span>`;
            })
            .join("");

          return `
            <div 
              class="metro-grid-card ${isActive ? 'active-card' : ''} ${isCompleted ? 'completed-card' : ''}"
              data-station-id="${station.id}"
              style="${filterStyle}"
              onclick="MetroMap.selectStation('${station.id}')"
              onmouseenter="MetroMap.highlightStationOnRail('${station.id}')"
              onmouseleave="MetroMap.clearHighlightStationOnRail()"
            >
              <!-- Card Header -->
              <div class="metro-card-header">
                <span class="metro-card-month">${station.month_label}:</span>
                ${chipHtml}
              </div>

              <!-- Milestone Title -->
              <div class="metro-card-title" title="${this.escapeHtml(station.name)}">
                ${this.escapeHtml(station.name.toUpperCase())}
              </div>

              <!-- Micro-Tags Row -->
              <div class="metro-micro-tags">
                ${tagsHtml}
              </div>

              <!-- Progress Bar (Dual for Active Station, Slim for Standard) -->
              ${
                isActive
                  ? (() => {
                      const now = new Date();
                      const dayOfMonth = now.getDate();
                      const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
                      const timeElapsedPct = Math.min(100, Math.max(0, Math.round((dayOfMonth / daysInMonth) * 100)));
                      const completedCount = completedList.length;
                      return `
                        <div class="metro-card-active-progress" title="Time Pace: Day ${dayOfMonth} of ${daysInMonth} (${timeElapsedPct}%) | Deliverables: ${completedCount}/${totalDelivs} (${progressPercent}%)">
                          <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 8.5px;">
                            <span style="color: var(--text-tertiary); font-weight: 600;">📅 TIME: Day ${dayOfMonth}/${daysInMonth}</span>
                            <span style="color: rgba(167, 139, 250, 0.9); font-weight: 700;">${timeElapsedPct}%</span>
                          </div>
                          <div class="metro-progress-track">
                            <div class="metro-progress-fill time-fill" style="width: ${timeElapsedPct}%;"></div>
                          </div>

                          <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 8.5px; margin-top: 2px;">
                            <span style="color: var(--text-tertiary); font-weight: 600;">🎯 GOALS: ${completedCount}/${totalDelivs}</span>
                            <span style="color: var(--accent-lavender); font-weight: 700;">${progressPercent}%</span>
                          </div>
                          <div class="metro-progress-track">
                            <div class="metro-progress-fill goals-fill" style="width: ${progressPercent}%;"></div>
                          </div>
                        </div>
                      `;
                    })()
                  : `
                    <!-- Slim Progress Bar -->
                    <div class="metro-card-progress">
                      <div class="metro-progress-track">
                        <div class="metro-progress-fill" style="width: ${progressPercent}%;"></div>
                      </div>
                      <span class="metro-progress-pct">${progressPercent}%</span>
                    </div>
                  `
              }
            </div>
          `;
        })
        .join("");

      // Destination Milestone Card at the end of grid
      gridCardsHtml += `
        <div 
          class="metro-grid-card" 
          style="border: 1px solid rgba(245, 158, 11, 0.35); background: var(--bg-surface); cursor: pointer;"
          onclick="HarnessApp.switchView('study')"
          title="TUM Campus Heilbronn Destination"
        >
          <div class="metro-card-header">
            <span class="metro-card-month" style="color: #f59e0b;">OCT '28:</span>
            <span class="metro-card-chip" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border-color: rgba(245, 158, 11, 0.3);">TARGET</span>
          </div>
          <div class="metro-card-title" style="color: #f59e0b;">
            TUM ’28 HEILBRONN
          </div>
          <div class="metro-micro-tags">
            <span class="metro-micro-tag" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.35);">B.Sc. MDS</span>
            <span class="metro-micro-tag" style="background: rgba(139, 92, 246, 0.15); color: var(--accent-lavender); border: 1px solid rgba(139, 92, 246, 0.35);">&ge; 88 pts</span>
          </div>
          <div class="metro-card-progress">
            <div class="metro-progress-track">
              <div class="metro-progress-fill" style="width: ${(progressRatio * 100).toFixed(1)}%; background: #f59e0b;"></div>
            </div>
            <span class="metro-progress-pct" style="color: #f59e0b;">${(progressRatio * 100).toFixed(1)}%</span>
          </div>
        </div>
      `;

      cardsGrid.innerHTML = gridCardsHtml;
    }

    this.attachTestDotEvents();
  },

  attachTestDotEvents() {
    let tooltip = document.getElementById("metroTestTooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "metroTestTooltip";
      tooltip.className = "metro-test-tooltip";
      tooltip.style.display = "none";
      document.body.appendChild(tooltip);
    }

    document.querySelectorAll(".metro-test-tick").forEach((dot) => {
      dot.addEventListener("mouseenter", (e) => {
        const clusterRaw = dot.getAttribute("data-cluster");
        let clusterExams = null;
        if (clusterRaw) {
          try {
            clusterExams = JSON.parse(decodeURIComponent(clusterRaw));
          } catch (err) {}
        }

        const subj = dot.getAttribute("data-subject");
        const title = dot.getAttribute("data-title");
        const dateStr = dot.getAttribute("data-date");
        const due = dot.getAttribute("data-due");
        const scope = dot.getAttribute("data-scope");

        let content = "";
        if (Array.isArray(clusterExams) && clusterExams.length > 1) {
          content = `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;">
              <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: var(--accent-lavender);">${clusterExams.length} Scheduled Tests</span>
              <span class="key-pill" style="font-size: 9px; padding: 1px 5px;">${due}</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
              ${clusterExams
                .map(
                  (ex) => `
                <div style="border-left: 2px solid var(--accent-lavender); padding-left: 6px;">
                  <div style="font-size: 11px; font-weight: 700; color: var(--text-primary);">[${this.escapeHtml(ex.subject)}] ${this.escapeHtml(ex.title)}</div>
                  <div style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary);">${ex.exam_date}</div>
                  ${ex.scope ? `<div style="font-size: 9.5px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(ex.scope)}</div>` : ""}
                </div>
              `
                )
                .join("")}
            </div>
            <div style="font-size: 9px; color: var(--text-muted); margin-top: 6px; font-style: italic;">Click to open in Study ledger</div>
          `;
        } else {
          content = `
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
              <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: var(--text-primary);">[${subj}]</span>
              <span style="font-size: 12px; font-weight: 700; color: var(--text-primary);">${title}</span>
              <span class="key-pill" style="font-size: 9px; padding: 1px 5px;">${due}</span>
            </div>
            <div style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary);">${dateStr}</div>
          `;
          if (scope) {
            content += `<div style="font-size: 10px; color: var(--text-secondary); margin-top: 3px; max-width: 260px;">${scope}</div>`;
          }
          content += `<div style="font-size: 9px; color: var(--text-muted); margin-top: 4px; font-style: italic;">Click to open in Study ledger</div>`;
        }

        tooltip.innerHTML = content;
        tooltip.style.display = "block";
        this.positionTestTooltip(e, tooltip);
      });

      dot.addEventListener("mousemove", (e) => {
        this.positionTestTooltip(e, tooltip);
      });

      dot.addEventListener("mouseleave", () => {
        tooltip.style.display = "none";
      });

      dot.addEventListener("click", () => {
        const id = dot.getAttribute("data-id");
        this.handleTestDotClick(id);
      });
    });
  },

  positionTestTooltip(e, tooltip) {
    const x = e.clientX + 12;
    const y = e.clientY - 12;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  },

  handleTestDotClick(examId) {
    if (window.HarnessApp) {
      window.HarnessApp.switchView("study");
      setTimeout(() => {
        const el = document.querySelector(`[data-exam-id="${examId}"]`) || document.getElementById("studyExamsList");
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.style.outline = "2px solid var(--text-primary)";
          setTimeout(() => { el.style.outline = ""; }, 2500);
        }
      }, 150);
    }
  },

  selectStation(stationId) {
    const station = this.data.stations.find((s) => s.id === stationId);
    if (!station) return;

    this.selectedStation = station;
    this.openDrawer(station);
  },

  async openDrawer(station) {
    const drawer = document.getElementById("stationDrawer");
    if (!drawer) return;

    // Refresh deliverables and pace velocity for THIS station
    if (window.pywebview && window.pywebview.api) {
      if (window.pywebview.api.get_station_deliverables) {
        this.stationProgress = (await window.pywebview.api.get_station_deliverables(station.id)) || [];
      }
      if (window.pywebview.api.get_station_pace_velocity) {
        this.paceVelocity = (await window.pywebview.api.get_station_pace_velocity(station.id)) || null;
      }
    }

    document.getElementById("drawerStationTitle").textContent = station.name;
    document.getElementById("drawerStationMonth").textContent = `${station.month_label} // ${station.phase}`;
    document.getElementById("drawerStationObjective").textContent = station.objective || "No objective stated.";
    document.getElementById("drawerStationNextAction").textContent = station.next_action || "--";

    const statusVal = station.status || "upcoming";
    const statusInput = document.getElementById("drawerStationStatus");
    if (statusInput) statusInput.value = statusVal;

    const delivEntries = Object.entries(station.deliverables || {});
    const totalDelivs = delivEntries.length;
    const completedList = station.completed_deliverables || [];
    const passedOverList = station.passed_over_deliverables || [];
    const isAudited = (statusVal === "completed" && passedOverList.length > 0 && (completedList.length === 0 || passedOverList.length >= totalDelivs));
    const progressPercent = this.calculateStationProgress(station);

    // Read-only Status Badge
    const statusContainer = document.getElementById("drawerStationStatusContainer");
    if (statusContainer) {
      if (statusVal === "active") {
        statusContainer.innerHTML = `
          <div class="station-status-badge active">
            <span class="beacon-dot optimal" style="width: 6px; height: 6px;"></span>
            <span>ACTIVE MILESTONE // TUM HEILBRONN TRACK</span>
          </div>
        `;
      } else if (isAudited) {
        statusContainer.innerHTML = `
          <div class="station-status-badge audited">
            <span class="beacon-dot" style="width: 6px; height: 6px; background: #f59e0b;"></span>
            <span>AUDITED // REALLOCATED TO SUMMER RUNWAY</span>
          </div>
        `;
      } else if (statusVal === "completed") {
        statusContainer.innerHTML = `
          <div class="station-status-badge completed">
            <span>✓</span>
            <span>COMPLETED MILESTONE</span>
          </div>
        `;
      } else {
        statusContainer.innerHTML = `
          <div class="station-status-badge upcoming">
            <span>○</span>
            <span>UPCOMING MILESTONE</span>
          </div>
        `;
      }
    }

    // Deliverables breakdown categorized by stream - Clean, Informative HUD
    const deliverablesList = document.getElementById("drawerDeliverablesList");
    if (deliverablesList && station.deliverables) {
      const now = new Date();
      const dayOfMonth = now.getDate();
      const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
      const timeElapsedPct = Math.min(100, Math.max(0, Math.round((dayOfMonth / daysInMonth) * 100)));

      let velocity = this.paceVelocity;
      if (!velocity || velocity.station_id !== station.id) {
        const isBehind = progressPercent < timeElapsedPct;
        velocity = {
          station_id: station.id,
          day_of_month: dayOfMonth,
          total_days: daysInMonth,
          elapsed_pct: timeElapsedPct,
          is_behind: isBehind,
          status_text: isBehind
            ? `Pace Deficit: ${Math.round(timeElapsedPct - progressPercent)}% behind schedule`
            : `Pace Velocity: Optimal (+${Math.max(0, Math.round(progressPercent - timeElapsedPct))}%)`,
          badge_variant: isBehind ? "amber" : "optimal",
        };
      }

      const validDayOfMonth = velocity?.day_of_month || dayOfMonth;
      const validTotalDays = velocity?.total_days || daysInMonth;
      const validElapsedPct = (velocity?.elapsed_pct !== undefined && !isNaN(velocity.elapsed_pct))
        ? velocity.elapsed_pct
        : (validTotalDays > 0 ? Math.min(100, Math.max(0, Math.round((validDayOfMonth / validTotalDays) * 100))) : timeElapsedPct);

      let velocityHeader = "";
      if (statusVal === "active") {
        const isBehind = Boolean(velocity?.is_behind);
        let statusText = velocity?.status_text || (isBehind ? "Pace Deficit: Behind schedule" : "Pace Velocity: Optimal");
        statusText = statusText.replace(/Pace Deficit:\s*-\s*/i, "Pace Deficit: ").replace(/undefined/g, "").replace(/NaN/g, "0");

        velocityHeader = `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 10px; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 10px; ${isBehind ? "background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); color: #f59e0b;" : "background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-subtle); color: var(--text-primary);"}">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="beacon-dot ${isBehind ? "pulse" : "optimal"}" style="width: 6px; height: 6px;"></span>
              <span style="font-weight: 700;">${this.escapeHtml(statusText)}</span>
            </div>
            <span style="opacity: 0.85;">Day ${validDayOfMonth}/${validTotalDays} (${validElapsedPct}%)</span>
          </div>
        `;
      }

      const progressHeader = `
        ${velocityHeader}
        <div style="background: var(--bg-card); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 14px;">
          <!-- Track 1: Days Elapsed in Month -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 10px; font-family: var(--font-mono);">
            <span style="color: var(--text-tertiary); font-weight: 700;">TIME ELAPSED (MONTH PACE)</span>
            <span style="color: var(--text-secondary); font-weight: 700;">Day ${validDayOfMonth} of ${validTotalDays} &bull; ${validElapsedPct}%</span>
          </div>
          <div class="progress-bar-track" style="margin: 0 0 10px 0; height: 4px;">
            <div class="progress-bar-fill time-fill" style="width: ${validElapsedPct}%; background: var(--border-medium);"></div>
          </div>

          <!-- Track 2: Goals Verified -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 10px; font-family: var(--font-mono);">
            <span style="color: var(--text-tertiary); font-weight: 700;">DELIVERABLES STATUS</span>
            <span style="color: var(--accent-lavender); font-weight: 700;">${progressPercent}% (${completedList.length}/${totalDelivs} GOALS)</span>
          </div>
          <div class="progress-bar-track" style="margin: 0; height: 4px;">
            <div class="progress-bar-fill goals-fill" style="width: ${progressPercent}%; background: var(--accent-lavender);"></div>
          </div>
        </div>
      `;

      const allEntries = delivEntries;
      const itemsHtml = allEntries
        .map(([key, val]) => {
          const streamMatch = this.streams.find((s) => s.name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(s.id));
          const lineBadgeColor = streamMatch ? streamMatch.color : "var(--accent-lavender)";

          const pMatch = (this.stationProgress || []).find(
            (p) => p.stream.toLowerCase() === key.toLowerCase() || (streamMatch && p.stream.toLowerCase() === streamMatch.id)
          );

          const isChecked = completedList.includes(key);
          const isPassedOver = passedOverList.includes(key);

          const countObj = (station.deliverable_counts && station.deliverable_counts[key])
            || (pMatch ? { count: pMatch.completed_count, total: pMatch.total_required, unit: pMatch.unit_label } : null)
            || this.getDeliverableCounter(station.id, key, val);

          const curCount = isChecked ? countObj.total : (countObj.count || 0);
          const totalReq = countObj.total;
          const unitLabel = countObj.unit || "reps";
          const itemPct = totalReq > 0 ? Math.min(100, Math.round((curCount / totalReq) * 100)) : 0;

          // Status Pill
          let statusPill = "";
          if (isAudited || isPassedOver) {
            statusPill = `<span class="telemetry-status-pill audited">REALLOCATED</span>`;
          } else if (isChecked || curCount >= totalReq) {
            statusPill = `<span class="telemetry-status-pill done">VERIFIED ✓</span>`;
          } else if (statusVal === "active") {
            statusPill = `<span class="telemetry-status-pill active">${itemPct}% LOGGED</span>`;
          } else {
            statusPill = `<span class="telemetry-status-pill upcoming">TARGET QUEUED</span>`;
          }

          const targetPace = Math.round(((validDayOfMonth / validTotalDays) * totalReq) * 10) / 10;
          const deficit = Math.round((targetPace - curCount) * 10) / 10;
          const isBehind = deficit > 0;
          const paceStatusText = isBehind
            ? `Pace Deficit: ${deficit} ${unitLabel} behind target`
            : `Optimal Pace (+${Math.abs(Math.round((curCount - targetPace) * 10) / 10)} ${unitLabel} ahead)`;

          return `
            <div class="deliverable-item telemetry-deliverable-card ${isChecked || curCount >= totalReq ? "completed-deliv" : ""}" style="cursor: default; padding: 12px; margin-bottom: 8px; border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); background: var(--bg-card);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 6px;">
                <div>
                  <span class="telemetry-stream-name" style="color: ${lineBadgeColor}; font-family: var(--font-mono); font-size: 10px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">
                    ${this.escapeHtml(key)} STREAM
                  </span>
                  <span class="telemetry-counter-pill" style="font-family: var(--font-mono); font-size: 9.5px; color: var(--text-tertiary); margin-left: 6px;">[${curCount} / ${totalReq} ${this.escapeHtml(unitLabel)}]</span>
                </div>
                ${statusPill}
              </div>

              <div class="telemetry-desc" style="font-size: 11.5px; color: var(--text-primary); line-height: 1.45; margin-bottom: 8px;">
                ${this.escapeHtml(val)}
              </div>

              <!-- Progress Bar -->
              <div style="margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); margin-bottom: 3px;">
                  <span>PROGRESS</span>
                  <span style="font-weight: 700; color: var(--text-primary);">${curCount} of ${totalReq} (${itemPct}%)</span>
                </div>
                <div class="progress-bar-track" style="margin: 0; height: 4px;">
                  <div class="progress-bar-fill" style="width: ${itemPct}%; background: ${lineBadgeColor};"></div>
                </div>
              </div>

              <!-- Pace Diagnostic -->
              ${statusVal === "active" ? `
                <div style="font-family: var(--font-mono); font-size: 9px; color: ${isBehind ? 'var(--color-amber-light)' : 'var(--text-tertiary)'}; display: flex; align-items: center; gap: 4px;">
                  <span>${isBehind ? '⚠' : '✓'}</span>
                  <span>${paceStatusText}</span>
                </div>
              ` : ""}
            </div>
          `;
        })
        .join("");

      const infoFooter = `
        <div style="font-family: var(--font-mono); font-size: 9.5px; color: var(--text-tertiary); margin-top: 10px; padding: 8px 10px; background: var(--bg-surface); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); line-height: 1.4;">
          💡 <strong>Execution Rule:</strong> Check off daily routine &amp; study blocks in the <strong>Daily</strong> tab to advance TUM milestone metrics.
        </div>
      `;

      const advanceFooter = `
        <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-hairline);">
          <button 
            type="button" 
            class="btn btn-secondary btn-advance-station" 
            style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 12px; font-size: 11px; font-weight: 700; font-family: var(--font-mono); color: var(--accent-lavender); border-color: rgba(167, 139, 250, 0.3); background: rgba(167, 139, 250, 0.06); cursor: pointer;"
            onclick="MetroMap.advanceStation('${station.id}')"
          >
            ADVANCE TO NEXT STATION &rarr;
          </button>
          <div style="text-align: center; font-size: 9px; color: var(--text-tertiary); font-family: var(--font-mono); margin-top: 4px;">
            Passes over any unfinished items and activates the next milestone.
          </div>
        </div>
      `;

      deliverablesList.innerHTML = progressHeader + itemsHtml + infoFooter + advanceFooter;
    }

    drawer.classList.add("open");
  },

  async stepDeliverableKey(stationId, key, delta, deliverableId = null) {
    const st = this.data?.stations?.find((s) => s.id === stationId);
    if (!st) return;

    if (!st.deliverable_counts) st.deliverable_counts = {};
    const cur = st.deliverable_counts[key] || this.getDeliverableCounter(stationId, key, st.deliverables?.[key]);
    const newCount = Math.max(0, Math.min(cur.total, cur.count + delta));
    cur.count = newCount;
    st.deliverable_counts[key] = cur;

    if (!st.completed_deliverables) st.completed_deliverables = [];
    if (!st.passed_over_deliverables) st.passed_over_deliverables = [];

    if (newCount >= cur.total && !st.completed_deliverables.includes(key)) {
      st.completed_deliverables.push(key);
      st.passed_over_deliverables = st.passed_over_deliverables.filter((k) => k !== key);
    } else if (newCount < cur.total && st.completed_deliverables.includes(key)) {
      st.completed_deliverables = st.completed_deliverables.filter((k) => k !== key);
    }

    // Check if station completes
    const allKeys = Object.keys(st.deliverables || {});
    let allDone = allKeys.length > 0 && allKeys.every((k) => st.completed_deliverables.includes(k) || st.passed_over_deliverables.includes(k));
    let nextStation = null;
    if (allDone) {
      st.status = "completed";
      const sIdx = this.data.stations.findIndex((s) => s.id === stationId);
      if (sIdx !== -1 && sIdx + 1 < this.data.stations.length) {
        nextStation = this.data.stations[sIdx + 1];
        if (nextStation.status === "upcoming") {
          nextStation.status = "active";
        }
      }
    }

    this.saveState();
    this.render();
    if (this.selectedStation && this.selectedStation.id === stationId) {
      this.openDrawer(st);
    }

    // Sync to backend if deliverableId exists
    if (deliverableId && window.pywebview?.api?.update_deliverable_progress) {
      window.pywebview.api.update_deliverable_progress(deliverableId, newCount, 0).catch(() => {});
    }

    if (allDone && nextStation && window.HarnessApp?.showToast) {
      window.HarnessApp.showToast(`Station Completed! Next: ${nextStation.name}`);
    }

    if (window.KillListDrawer) window.KillListDrawer.load();
    if (window.Today) window.Today.load();
    if (window.Dashboard) window.Dashboard.load();
  },

  async setDeliverableKeyProgress(stationId, key, newCountVal, deliverableId = null) {
    const st = this.data?.stations?.find((s) => s.id === stationId);
    if (!st) return;

    const count = parseInt(newCountVal, 10);
    if (isNaN(count)) return;

    if (!st.deliverable_counts) st.deliverable_counts = {};
    const cur = st.deliverable_counts[key] || this.getDeliverableCounter(stationId, key, st.deliverables?.[key]);
    const newCount = Math.max(0, Math.min(cur.total, count));
    cur.count = newCount;
    st.deliverable_counts[key] = cur;

    if (!st.completed_deliverables) st.completed_deliverables = [];
    if (!st.passed_over_deliverables) st.passed_over_deliverables = [];

    if (newCount >= cur.total && !st.completed_deliverables.includes(key)) {
      st.completed_deliverables.push(key);
      st.passed_over_deliverables = st.passed_over_deliverables.filter((k) => k !== key);
    } else if (newCount < cur.total && st.completed_deliverables.includes(key)) {
      st.completed_deliverables = st.completed_deliverables.filter((k) => k !== key);
    }

    const allKeys = Object.keys(st.deliverables || {});
    let allDone = allKeys.length > 0 && allKeys.every((k) => st.completed_deliverables.includes(k) || st.passed_over_deliverables.includes(k));
    let nextStation = null;
    if (allDone) {
      st.status = "completed";
      const sIdx = this.data.stations.findIndex((s) => s.id === stationId);
      if (sIdx !== -1 && sIdx + 1 < this.data.stations.length) {
        nextStation = this.data.stations[sIdx + 1];
        if (nextStation.status === "upcoming") {
          nextStation.status = "active";
        }
      }
    }

    this.saveState();
    this.render();
    if (this.selectedStation && this.selectedStation.id === stationId) {
      this.openDrawer(st);
    }

    if (deliverableId && window.pywebview?.api?.update_deliverable_progress) {
      window.pywebview.api.update_deliverable_progress(deliverableId, newCount, 0).catch(() => {});
    }

    if (allDone && nextStation && window.HarnessApp?.showToast) {
      window.HarnessApp.showToast(`Station Completed! Next: ${nextStation.name}`);
    }

    if (window.KillListDrawer) window.KillListDrawer.load();
    if (window.Today) window.Today.load();
    if (window.Dashboard) window.Dashboard.load();
  },

  async stepDeliverable(deliverableId, delta) {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.update_deliverable_progress(deliverableId, null, delta);
      if (this.selectedStation) {
        await this.openDrawer(this.selectedStation);
      }
      await this.load();
      if (window.KillListDrawer) window.KillListDrawer.load();
      if (window.Today) window.Today.load();
      if (window.Dashboard) window.Dashboard.load();
      if (window.HarnessApp && window.HarnessApp.showToast && res && res.deliverable) {
        window.HarnessApp.showToast(`${res.deliverable.title}: ${res.deliverable.completed_count}/${res.deliverable.total_required}`);
      }
    } catch (err) {
      console.error("Error stepping deliverable:", err);
    }
  },

  async setDeliverableProgress(deliverableId, newCount) {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      const count = parseInt(newCount, 10);
      if (isNaN(count)) return;
      const res = await window.pywebview.api.update_deliverable_progress(deliverableId, count, 0);
      if (this.selectedStation) {
        await this.openDrawer(this.selectedStation);
      }
      await this.load();
      if (window.KillListDrawer) window.KillListDrawer.load();
      if (window.Today) window.Today.load();
      if (window.Dashboard) window.Dashboard.load();
      if (window.HarnessApp && window.HarnessApp.showToast && res && res.deliverable) {
        window.HarnessApp.showToast(`${res.deliverable.title}: ${res.deliverable.completed_count}/${res.deliverable.total_required}`);
      }
    } catch (err) {
      console.error("Error setting deliverable progress:", err);
    }
  },

  closeDrawer() {
    const drawer = document.getElementById("stationDrawer");
    if (!drawer) return;

    drawer.classList.remove("open");
    this.selectedStation = null;
  },

  async toggleDeliverable(stationId, deliverableKey) {
    try {
      const st = this.data?.stations?.find((s) => s.id === stationId);
      if (!st) return;

      if (!st.completed_deliverables) st.completed_deliverables = [];
      if (!st.passed_over_deliverables) st.passed_over_deliverables = [];
      if (!st.deliverable_counts) st.deliverable_counts = {};

      const isChecked = st.completed_deliverables.includes(deliverableKey);
      const counter = st.deliverable_counts[deliverableKey] || this.getDeliverableCounter(stationId, deliverableKey, st.deliverables?.[deliverableKey]);

      if (isChecked) {
        st.completed_deliverables = st.completed_deliverables.filter((k) => k !== deliverableKey);
        if (counter) {
          counter.count = 0;
          st.deliverable_counts[deliverableKey] = counter;
        }
        if (st.status === "completed") {
          st.status = "active";
        }
      } else {
        st.completed_deliverables.push(deliverableKey);
        st.passed_over_deliverables = st.passed_over_deliverables.filter((k) => k !== deliverableKey);
        if (counter) {
          counter.count = counter.total;
          st.deliverable_counts[deliverableKey] = counter;
        }
      }

      const allKeys = Object.keys(st.deliverables || {});
      let nextStation = null;
      if (allKeys.length > 0 && allKeys.every((k) => st.completed_deliverables.includes(k) || st.passed_over_deliverables.includes(k))) {
        st.status = "completed";
        const sIdx = this.data.stations.findIndex((s) => s.id === stationId);
        if (sIdx !== -1 && sIdx + 1 < this.data.stations.length) {
          nextStation = this.data.stations[sIdx + 1];
          if (nextStation.status === "upcoming") {
            nextStation.status = "active";
          }
        }
      }

      this.saveState();

      let res = null;
      if (window.pywebview?.api?.toggle_station_deliverable) {
        res = await window.pywebview.api.toggle_station_deliverable(stationId, deliverableKey);
        if (res && res.success && res.completed_deliverables) {
          st.completed_deliverables = res.completed_deliverables;
          st.status = res.station_status;
          this.saveState();
        }
      }

      this.render();
      if (this.selectedStation && this.selectedStation.id === stationId) {
        this.openDrawer(st);
      }

      if (window.HarnessApp?.showToast) {
        if (st.status === "completed" && (nextStation || res?.next_station_name)) {
          const nextName = nextStation?.name || res?.next_station_name;
          window.HarnessApp.showToast(`Station Completed! Next: ${nextName}`);
        } else if (!isChecked) {
          window.HarnessApp.showToast(`Checked: ${deliverableKey}`);
        } else {
          window.HarnessApp.showToast(`Unchecked: ${deliverableKey}`);
        }
      }

      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error toggling deliverable:", err);
    }
  },

  async passOverDeliverable(stationId, deliverableKey) {
    try {
      const st = this.data?.stations?.find((s) => s.id === stationId);
      if (!st) return;

      if (!st.completed_deliverables) st.completed_deliverables = [];
      if (!st.passed_over_deliverables) st.passed_over_deliverables = [];

      let isPassedOver = false;
      if (st.passed_over_deliverables.includes(deliverableKey)) {
        st.passed_over_deliverables = st.passed_over_deliverables.filter((k) => k !== deliverableKey);
        isPassedOver = false;
      } else {
        st.passed_over_deliverables.push(deliverableKey);
        st.completed_deliverables = st.completed_deliverables.filter((k) => k !== deliverableKey);
        isPassedOver = true;
      }

      const allKeys = Object.keys(st.deliverables || {});
      let nextStation = null;
      if (allKeys.length > 0 && allKeys.every((k) => st.completed_deliverables.includes(k) || st.passed_over_deliverables.includes(k))) {
        st.status = "completed";
        const sIdx = this.data.stations.findIndex((s) => s.id === stationId);
        if (sIdx !== -1 && sIdx + 1 < this.data.stations.length) {
          nextStation = this.data.stations[sIdx + 1];
          if (nextStation.status === "upcoming") {
            nextStation.status = "active";
          }
        }
      }

      this.saveState();

      if (window.pywebview?.api?.pass_over_station_deliverable) {
        await window.pywebview.api.pass_over_station_deliverable(stationId, deliverableKey);
      }

      this.render();
      if (this.selectedStation && this.selectedStation.id === stationId) {
        this.openDrawer(st);
      }

      if (window.HarnessApp?.showToast) {
        if (st.status === "completed" && nextStation) {
          window.HarnessApp.showToast(`Station Completed! Next: ${nextStation.name}`);
        } else {
          window.HarnessApp.showToast(isPassedOver ? `Passed over: ${deliverableKey}` : `Restored: ${deliverableKey}`);
        }
      }

      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error passing over deliverable:", err);
    }
  },

  async advanceStation(stationId) {
    try {
      const st = this.data?.stations?.find((s) => s.id === stationId);
      if (!st) return;

      if (!st.completed_deliverables) st.completed_deliverables = [];
      if (!st.passed_over_deliverables) st.passed_over_deliverables = [];

      const allKeys = Object.keys(st.deliverables || {});
      allKeys.forEach((k) => {
        if (!st.completed_deliverables.includes(k) && !st.passed_over_deliverables.includes(k)) {
          st.passed_over_deliverables.push(k);
        }
      });

      st.status = "completed";

      const sIdx = this.data.stations.findIndex((s) => s.id === stationId);
      let nextStation = null;
      if (sIdx !== -1 && sIdx + 1 < this.data.stations.length) {
        nextStation = this.data.stations[sIdx + 1];
        nextStation.status = "active";
      }

      this.saveState();

      if (window.pywebview?.api?.advance_station) {
        await window.pywebview.api.advance_station(stationId, true);
      }

      this.render();

      if (nextStation) {
        this.selectedStation = nextStation;
        this.openDrawer(nextStation);
        if (window.HarnessApp?.showToast) {
          window.HarnessApp.showToast(`Advanced to ${nextStation.name}!`);
        }
      } else {
        this.closeDrawer();
        if (window.HarnessApp?.showToast) {
          window.HarnessApp.showToast(`Station ${st.name} completed!`);
        }
      }

      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error advancing station:", err);
    }
  },

  async updateStatus(stationId, newStatus) {
    try {
      await window.pywebview.api.update_station_status(stationId, newStatus);
      const st = this.data.stations.find((s) => s.id === stationId);
      if (st) st.status = newStatus;
      this.saveState();
      this.render();
      window.HarnessApp.showToast(`Station status updated to ${newStatus}`);
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error updating station status:", err);
    }
  },

  scrollToBeacon() {
    const container = document.getElementById("metroScrollContainer");
    if (!container) return;
    const activeStation = this.data?.stations?.find((s) => s.status === "active");
    let targetX = this.currentBeaconX;
    if (activeStation) {
      const idx = this.data.stations.indexOf(activeStation);
      if (idx !== -1) {
        targetX = 120 + idx * 220;
      }
    }
    if (targetX) {
      const targetScroll = Math.max(0, targetX - container.clientWidth / 2);
      container.scrollTo({ left: targetScroll, behavior: "smooth" });
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

window.MetroMap = MetroMap;
