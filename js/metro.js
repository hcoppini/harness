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
  tumOverview: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  activePhaseFilter: "all",
  focusedStationId: null,
  currentBeaconX: 0,
  stationProgress: [],
  paceVelocity: null,
  upcomingExams: [],

  // Stream Definitions (Evenly pitched horizontal subway lanes clear of station rings)
  streams: [
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      color: "#10b981",
      yOffset: -30,
    },
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      color: "#a855f7",
      yOffset: -18,
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      color: "#38bdf8",
      yOffset: 18,
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      color: "#f59e0b",
      yOffset: 30,
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      color: "#f43f5e",
      yOffset: 42,
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

  normalizeStreamKey(raw) {
    const k = String(raw || "").trim().toLowerCase();
    if (k.includes("phys") || k.includes("mass") || k.includes("gym") || k.includes("run") || k.includes("fit")) return "physical";
    if (k.includes("sigg") || k.includes("gpw") || k.includes("invest")) return "sigg";
    if (k.includes("germ") || k.includes("deutsch") || k.includes("anki") || k === "de") return "german";
    if (k.includes("code") || k.includes("syntax") || k.includes("prog") || k.includes("alg")) return "code";
    if (k.includes("acad") || k.includes("math") || k.includes("school") || k.includes("matura")) return "academics";
    return k;
  },

  getStationPhaseKey(station, idx) {
    const phaseLow = (station?.phase || "").toLowerCase();
    const monthLow = (station?.month_label || "").toLowerCase();
    const idLow = (station?.id || "").toLowerCase();
    if (phaseLow.includes("summer") || idx === 11 || (monthLow.includes("jul") && monthLow.includes("27")) || idLow.includes("summer-2027")) {
      return "phase2";
    }
    if (
      idx >= 12 ||
      phaseLow.includes("matura") ||
      phaseLow.includes("cke") ||
      phaseLow.includes("tum") ||
      monthLow.includes("'28") ||
      idLow.includes("2028")
    ) {
      return "phase3";
    }
    return "phase1";
  },

  /** Compute overall '26-'28 calendar progress for badges and target summary card. */
  calculateJourneyProgress(now = new Date()) {
    const startDate = new Date(2026, 8, 1);
    const endDate = new Date(2028, 6, 31);
    const totalMs = endDate.getTime() - startDate.getTime();
    const totalDays = Math.round(totalMs / (1000 * 60 * 60 * 24));
    if (now < startDate) {
      return { startDate, endDate, totalDays, elapsedDays: 31, progressRatio: 0.044 };
    }
    const elapsedMs = Math.min(totalMs, Math.max(0, now.getTime() - startDate.getTime()));
    const progressRatio = elapsedMs / totalMs;
    const elapsedDays = Math.min(totalDays, Math.round(elapsedMs / (1000 * 60 * 60 * 24)));
    return { startDate, endDate, totalDays, elapsedDays, progressRatio };
  },

  /** Parse station date ("YYYY-MM-DD" or "YYYY-MM") into local midnight timestamp. */
  parseStationAnchorTime(dateStr) {
    if (!dateStr) return null;
    const str = String(dateStr).trim();
    const fullMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str);
    if (fullMatch) {
      return new Date(Number(fullMatch[1]), Number(fullMatch[2]) - 1, Number(fullMatch[3]), 0, 0, 0).getTime();
    }
    const monthMatch = /^(\d{4})-(\d{2})$/.exec(str);
    if (monthMatch) {
      return new Date(Number(monthMatch[1]), Number(monthMatch[2]) - 1, 1, 0, 0, 0).getTime();
    }
    const parsed = new Date(str);
    return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
  },

  /** Map any calendar date onto visual track X via piecewise-linear station anchors. */
  buildTrackDateMapper(stations, startX, spacing, terminusX, startDate, endDate) {
    const endAnchorTime = new Date(
      endDate.getFullYear(),
      endDate.getMonth(),
      endDate.getDate(),
      23,
      59,
      59,
      999
    ).getTime();

    const anchors = (stations || []).map((st, idx) => ({
      x: startX + idx * spacing,
      rawTime: this.parseStationAnchorTime(st?.date),
      time: null,
    }));

    if (anchors.length > 0) {
      anchors[0].time = anchors[0].rawTime !== null ? anchors[0].rawTime : startDate.getTime();
      for (let i = 1; i < anchors.length; i++) {
        const prevTime = anchors[i - 1].time;
        const cand = anchors[i].rawTime;
        if (cand !== null && cand > prevTime) {
          anchors[i].time = cand;
          continue;
        }
        // Consecutive stations sharing a start month (e.g. kickoff-2026 & sep-2026) spread evenly before the next distinct anchor.
        let nextValidIdx = -1;
        let nextValidTime = endAnchorTime;
        for (let j = i + 1; j < anchors.length; j++) {
          if (anchors[j].rawTime !== null && anchors[j].rawTime > prevTime) {
            nextValidIdx = j;
            nextValidTime = anchors[j].rawTime;
            break;
          }
        }
        const spanEndIdx = nextValidIdx !== -1 ? nextValidIdx : anchors.length;
        const spanSteps = spanEndIdx - (i - 1);
        const fillEnd = nextValidIdx !== -1 ? nextValidIdx - 1 : anchors.length - 1;
        for (let k = i; k <= fillEnd; k++) {
          anchors[k].time = prevTime + ((k - (i - 1)) / spanSteps) * (nextValidTime - prevTime);
        }
        i = fillEnd;
      }

      const lastStationTime = anchors[anchors.length - 1].time;
      anchors.push({
        x: terminusX,
        rawTime: endAnchorTime,
        time: Math.max(endAnchorTime, lastStationTime + 24 * 60 * 60 * 1000),
      });
    }

    return (dateInput) => {
      if (!anchors.length) return startX;
      const t = dateInput instanceof Date ? dateInput.getTime() : new Date(dateInput).getTime();
      if (Number.isNaN(t)) return startX;
      if (t < anchors[0].time) return startX - 35;
      if (t >= anchors[anchors.length - 1].time) return terminusX;
      for (let i = 0; i < anchors.length - 1; i++) {
        const a = anchors[i];
        const b = anchors[i + 1];
        if (t >= a.time && t <= b.time) {
          const spanMs = b.time - a.time;
          const frac = spanMs > 0 ? (t - a.time) / spanMs : 0;
          return a.x + frac * (b.x - a.x);
        }
      }
      return terminusX;
    };
  },

  setPhaseFilter(phase) {
    this.activePhaseFilter = phase || "all";
    document.querySelectorAll(".metro-phase-btn").forEach((btn) => {
      btn.classList.toggle("active", (btn.getAttribute("data-phase") || "all") === this.activePhaseFilter);
    });
    if (this.data?.stations) {
      const { progressRatio } = this.calculateJourneyProgress();
      this.renderCardsGrid(this.data.stations, progressRatio);
    }
  },

  getSafeVelocity(station, progressPercent) {
    const now = new Date();
    const dayFallback = now.getDate();
    const daysInMonthFallback = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const fallbackPct = Math.min(100, Math.max(0, Math.round((dayFallback / daysInMonthFallback) * 100)));

    const rawVel = (this.paceVelocity && this.paceVelocity.station_id === station?.id) ? this.paceVelocity : null;
    const validDay = Number.isFinite(Number(rawVel?.day_of_month)) && Number(rawVel.day_of_month) > 0
      ? Number(rawVel.day_of_month)
      : dayFallback;
    const validTotal = Number.isFinite(Number(rawVel?.total_days)) && Number(rawVel.total_days) > 0
      ? Number(rawVel.total_days)
      : daysInMonthFallback;
    const validElapsedPct = Number.isFinite(Number(rawVel?.elapsed_pct))
      ? Math.min(100, Math.max(0, Math.round(Number(rawVel.elapsed_pct))))
      : (validTotal > 0 ? Math.min(100, Math.max(0, Math.round((validDay / validTotal) * 100))) : fallbackPct);

    const safeProgress = Number.isFinite(Number(progressPercent)) ? Number(progressPercent) : 0;
    const deltaPct = Math.round((safeProgress - validElapsedPct) * 10) / 10;
    const isBehind = rawVel?.is_behind !== undefined ? Boolean(rawVel.is_behind) : deltaPct < 0;

    let statusText = rawVel?.status_text ? String(rawVel.status_text) : "";
    statusText = statusText
      .replace(/undefined%?/gi, `${validElapsedPct}%`)
      .replace(/NaN/gi, "0")
      .replace(/Pace Deficit:\s*-\s*/i, "Pace Deficit: ")
      .trim();

    if (!statusText) {
      statusText = isBehind
        ? `Pace Deficit: ${Math.abs(deltaPct)}% behind month clock`
        : `On Pace: ${deltaPct >= 0 ? `+${deltaPct}%` : "0%"} vs month clock`;
    }

    return {
      day_of_month: validDay,
      total_days: validTotal,
      elapsed_pct: validElapsedPct,
      delta_pct: deltaPct,
      is_behind: isBehind,
      status_text: statusText,
    };
  },

  buildRadialRingHtml(pct, color = "var(--accent-lavender)", size = 84, subLabel = "OUTPUT") {
    const safePct = Math.min(100, Math.max(0, Math.round(Number(pct) || 0)));
    const strokeW = Math.max(5, Math.round(size * 0.085));
    const r = (size - strokeW) / 2;
    const circ = 2 * Math.PI * r;
    const dashOffset = circ - (safePct / 100) * circ;
    return `
      <div class="tum-radial-wrap" style="width: ${size}px; height: ${size}px;">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="tum-radial-svg">
          <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="${strokeW}" />
          <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="${strokeW}" stroke-linecap="round"
                  stroke-dasharray="${circ.toFixed(2)}" stroke-dashoffset="${dashOffset.toFixed(2)}"
                  transform="rotate(-90 ${size / 2} ${size / 2})" class="tum-radial-arc" />
        </svg>
        <div class="tum-radial-center">
          <span class="tum-radial-pct">${safePct}%</span>
          <span class="tum-radial-sub">${this.escapeHtml(subLabel)}</span>
        </div>
      </div>
    `;
  },

  openGradesLedger() {
    const drawer = document.getElementById("gradesTableDrawer");
    const btn = document.getElementById("btnToggleGradesView");
    if (drawer && (drawer.style.display === "none" || !drawer.style.display)) {
      if (btn) btn.click();
      else drawer.style.display = "block";
    }
    if (drawer) {
      setTimeout(() => drawer.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
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

    const currentStationId = this.mobileSelectedStationId || stations[activeIndex].id;
    const station = stations.find((s) => s.id === currentStationId) || stations[activeIndex];
    const stationIndex = stations.findIndex((s) => s.id === station.id);

    const status = station.status || "upcoming";
    const progressPercent = this.calculateStationProgress(station);
    const delivEntries = Object.entries(station.deliverables || {});
    const completedList = station.completed_deliverables || [];
    const velocity = this.getSafeVelocity(station, progressPercent);
    const validDayOfMonth = velocity.day_of_month;
    const validTotalDays = velocity.total_days;
    const validElapsedPct = velocity.elapsed_pct;

    const optionsHtml = stations
      .map((s, idx) => {
        const isCur = s.id === station.id;
        const tag = s.status === "active" ? " • ACTIVE" : (s.status === "completed" ? " ✓" : "");
        return `<option value="${s.id}" ${isCur ? "selected" : ""}>${String(idx + 1).padStart(2, "0")}: ${s.month_label} — ${this.escapeHtml(s.name)}${tag}</option>`;
      })
      .join("");

    let delivsHtml = "";
    if (delivEntries.length === 0) {
      delivsHtml = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px 0;">No active deliverables defined.</div>`;
    } else {
      delivsHtml = delivEntries
        .map(([key, val]) => {
          const normKey = this.normalizeStreamKey(key);
          const streamMatch = this.streams.find((s) => s.id === normKey || s.name.toLowerCase().includes(key.toLowerCase()));
          const lineBadgeColor = streamMatch ? this.getStreamColor(streamMatch.id) : "var(--accent-lavender)";

          const isChecked = completedList.includes(key);
          const countObj = this.getDeliverableCounter(station.id, key, val);
          const curCount = isChecked ? countObj.total : (countObj.count || 0);
          const totalReq = Math.max(1, countObj.total || 10);
          const unitLabel = countObj.unit || "reps";
          const itemPct = Math.min(100, Math.round((curCount / totalReq) * 100));

          const targetPace = Math.round(((validDayOfMonth / validTotalDays) * totalReq) * 10) / 10;
          const deficit = Math.round((targetPace - curCount) * 10) / 10;
          const isBehind = deficit > 0;

          return `
            <div class="mobile-hud-deliv-item ${isChecked || curCount >= totalReq ? "completed" : ""}" style="border-left: 2px solid ${lineBadgeColor};">
              <div class="mobile-hud-deliv-top">
                <span class="mobile-hud-stream" style="color: ${lineBadgeColor};">${this.escapeHtml(key)} STREAM</span>
                <span class="mobile-hud-count">${curCount} / ${totalReq} ${this.escapeHtml(unitLabel)}</span>
              </div>
              <div class="mobile-hud-desc">${this.escapeHtml(val)}</div>
              <div class="tum-mini-bar-track">
                <div class="tum-mini-bar-fill" style="width: ${itemPct}%; background: ${lineBadgeColor};"></div>
              </div>
              ${status === "active" ? `
                <div class="mobile-hud-pace ${isBehind ? "is-behind" : "is-optimal"}">
                  ${isBehind ? `Target: ${targetPace} today (${deficit} ${this.escapeHtml(unitLabel)} behind)` : `On pace (+${Math.abs(Math.round((curCount - targetPace) * 10) / 10)} ahead)`}
                </div>
              ` : ""}
            </div>
          `;
        })
        .join("");
    }

    const prevDisabled = stationIndex === 0;
    const nextDisabled = stationIndex >= stations.length - 1;

    // Live Bavarian Assessment Snapshot
    const ov = window.Tum?.data || this.tumOverview || {};
    const ba = ov.bavarian_assessment || {};
    const bavGpa = Number.isFinite(Number(ba.bavarian_gpa)) ? Number(ba.bavarian_gpa).toFixed(2) : "--";
    const totalScore = Number.isFinite(Number(ba.total_score)) ? Number(ba.total_score) : null;
    const scorePct = totalScore !== null ? Math.min(100, Math.max(0, totalScore)) : 0;
    const verdict = ba.admission_verdict || "Syncing Ledger...";

    container.innerHTML = `
      <div class="monotone-card mobile-hud-card">
        <div class="mobile-hud-nav">
          <button type="button" class="btn-ghost-icon mobile-hud-nav-btn" ${prevDisabled ? 'disabled' : `onclick="MetroMap.selectMobileStation('${stations[stationIndex - 1]?.id}')"`}>&larr; Prev</button>
          <select class="mobile-hud-select" onchange="MetroMap.selectMobileStation(this.value)">
            ${optionsHtml}
          </select>
          <button type="button" class="btn-ghost-icon mobile-hud-nav-btn" ${nextDisabled ? 'disabled' : `onclick="MetroMap.selectMobileStation('${stations[stationIndex + 1]?.id}')"`}>Next &rarr;</button>
        </div>

        <div class="mobile-hud-hero-row">
          ${this.buildRadialRingHtml(progressPercent, status === "completed" ? "var(--color-green-light)" : "var(--accent-lavender)", 76, "MILESTONE")}
          <div class="mobile-hud-hero-meta">
            <div class="mobile-hud-badges">
              <span class="mono-chip lavender">${station.month_label || "2026"}</span>
              <span class="mono-chip ${status === "active" ? "lavender" : status === "completed" ? "green" : ""}">${status === "active" ? "ACTIVE" : status.toUpperCase()}</span>
            </div>
            <h2 class="mobile-hud-title">${this.escapeHtml(station.name)}</h2>
            <div class="mobile-hud-delta-tag ${velocity.is_behind ? "is-behind" : "is-optimal"}">
              ${this.escapeHtml(velocity.status_text)}
            </div>
          </div>
        </div>

        <div class="mobile-hud-pace-box">
          <div class="tum-pace-row">
            <span>SHOULD BE (DAY ${validDayOfMonth}/${validTotalDays})</span>
            <strong>${validElapsedPct}%</strong>
          </div>
          <div class="tum-mini-bar-track" style="margin-bottom: 8px;">
            <div class="tum-mini-bar-fill" style="width: ${validElapsedPct}%; background: rgba(255, 255, 255, 0.35);"></div>
          </div>
          <div class="tum-pace-row">
            <span>ACTUAL OUTPUT LOGGED</span>
            <strong style="color: var(--accent-lavender);">${progressPercent}%</strong>
          </div>
          <div class="tum-mini-bar-track">
            <div class="tum-mini-bar-fill" style="width: ${progressPercent}%; background: var(--accent-lavender);"></div>
          </div>
        </div>

        ${station.objective ? `
          <div class="mobile-hud-objective">
            <div class="card-label" style="margin-bottom: 3px;">CORE OBJECTIVE</div>
            <div>${this.escapeHtml(station.objective)}</div>
          </div>
        ` : ""}

        <div style="margin-bottom: 12px;">
          <div class="card-label" style="margin-bottom: 6px;">LIVE STREAM PROGRESS (AUTO FROM DAILY)</div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${delivsHtml}
          </div>
        </div>

        <div class="mobile-hud-admissions">
          <div class="mobile-hud-adm-top">
            <div>
              <div class="card-label" style="margin-bottom: 2px;">TUM STAGE 1 ADMISSIONS</div>
              <div class="mobile-hud-adm-score">
                <span>${bavGpa} DE</span>
                <span class="adm-sep">/</span>
                <span class="adm-pts">${totalScore !== null ? totalScore.toFixed(1) : "--"} pts</span>
              </div>
            </div>
            <button type="button" class="btn-ghost-icon" style="font-size: 10px; padding: 4px 10px;" onclick="MetroMap.openGradesLedger()">
              Ledger &rarr;
            </button>
          </div>
          <div class="tum-threshold-track">
            <div class="tum-threshold-fill" style="width: ${scorePct}%;"></div>
            <div class="tum-threshold-pin" style="left: 88%;" title="88.0 pts Direct Admit Cutoff"></div>
          </div>
          <div class="mobile-hud-adm-sub">
            <span>${this.escapeHtml(verdict)}</span>
            <span>Direct Admit &ge; 88.0</span>
          </div>
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

    let totalScore = 0;
    entries.forEach(([key, val]) => {
      if (completedList.includes(key) || passedOverList.includes(key)) {
        totalScore += 1.0;
      } else {
        const countObj = this.getDeliverableCounter(station.id, key, val);
        if (countObj && countObj.total > 0) {
          const frac = Math.min(1.0, Math.max(0, (countObj.count || 0) / countObj.total));
          totalScore += frac;
        }
      }
    });

    return Math.min(100, Math.round((totalScore / entries.length) * 100));
  },

  getDeliverableCounter(stationId, key, val) {
    const st = this.data?.stations?.find((s) => s.id === stationId);
    const normKey = this.normalizeStreamKey(key);
    const liveList = (this.stationProgressById && this.stationProgressById[stationId]) || this.stationProgress || [];
    const pMatch = liveList.find((p) => {
      if (p.station_id && p.station_id !== stationId) return false;
      const pNorm = this.normalizeStreamKey(p.stream);
      const pLow = (p.stream || "").toLowerCase();
      const kLow = (key || "").toLowerCase();
      return pNorm === normKey || pLow === kLow || pLow.includes(kLow) || kLow.includes(pLow);
    });
    if (pMatch) {
      return {
        count: Number(pMatch.completed_count || 0),
        total: Math.max(1, Number(pMatch.total_required || 10)),
        unit: pMatch.unit_label || "reps",
        deliverable_id: pMatch.deliverable_id || null,
        fromSqlite: true,
      };
    }

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
        const activeStation = this.data?.stations?.find((s) => s.status === "active") || this.data?.stations?.[0];
        const targetStId = this.selectedStation?.id || (activeStation ? activeStation.id : "sep-2026");

        if (window.pywebview.api.get_station_deliverables) {
          this.stationProgress = (await window.pywebview.api.get_station_deliverables(targetStId)) || [];
        }
        if (window.pywebview.api.get_station_pace_velocity) {
          this.paceVelocity = (await window.pywebview.api.get_station_pace_velocity(activeStation ? activeStation.id : targetStId)) || null;
        }
        if (window.Tum?.data) {
          this.tumOverview = window.Tum.data;
        } else if (window.pywebview.api.get_tum_overview) {
          this.tumOverview = await window.pywebview.api.get_tum_overview();
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
      if (this.selectedStation) {
        const refreshed = this.data?.stations?.find((s) => s.id === this.selectedStation.id);
        if (refreshed) this.renderInspector(refreshed, true);
      }
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

  renderComparisonHero() {
    const heroEl = document.getElementById("tumComparisonHero");
    if (!heroEl || !this.data || !this.data.stations) return;

    const stations = this.data.stations;
    const station = stations.find((s) => s.status === "active") || stations[0];
    if (!station) return;

    const progressPercent = this.calculateStationProgress(station);
    const vel = this.getSafeVelocity(station, progressPercent);
    const completedList = station.completed_deliverables || [];
    const delivEntries = Object.entries(station.deliverables || {});

    const streamsHtml = delivEntries
      .map(([key, val]) => {
        const normKey = this.normalizeStreamKey(key);
        const color = this.getStreamColor(normKey);
        const countObj = this.getDeliverableCounter(station.id, key, val);
        const curCount = completedList.includes(key) ? countObj.total : (countObj.count || 0);
        const totalReq = Math.max(1, countObj.total || 10);
        const itemPct = Math.min(100, Math.round((curCount / totalReq) * 100));
        return `
          <div class="tum-hero-stream-row" title="${this.escapeHtml(val)}">
            <div class="tum-hero-stream-label">
              <span class="tum-stream-dot" style="background: ${color};"></span>
              <span>${this.escapeHtml(key)}</span>
            </div>
            <div class="tum-mini-bar-track" style="flex: 1;">
              <div class="tum-mini-bar-fill" style="width: ${itemPct}%; background: ${color};"></div>
            </div>
            <div class="tum-hero-stream-val">${curCount}/${totalReq} <span class="unit">${this.escapeHtml(countObj.unit || "")}</span></div>
          </div>
        `;
      })
      .join("");

    // TUM Admissions Assessment snapshot
    const ov = window.Tum?.data || this.tumOverview || {};
    const ba = ov.bavarian_assessment || {};
    const hasAssessment = ba && ba.total_score !== undefined && ba.total_score !== null;
    const bavGpa = Number.isFinite(Number(ba.bavarian_gpa)) ? Number(ba.bavarian_gpa).toFixed(2) : "--";
    const polishGpa = Number.isFinite(Number(ov.overall_gpa)) ? Number(ov.overall_gpa).toFixed(2) : "--";
    const totalScore = hasAssessment ? Number(ba.total_score) : null;
    const curricularScore = Number.isFinite(Number(ba.curricular_score)) ? Number(ba.curricular_score).toFixed(1) : "--";
    const dist88 = totalScore !== null ? Math.round((88.0 - totalScore) * 10) / 10 : null;
    const verdict = ba.admission_verdict || (hasAssessment ? "Evaluated" : "Syncing Ledger...");
    const isDirect = totalScore !== null && totalScore >= 88.0;
    const isInterview = totalScore !== null && totalScore >= 72.0 && totalScore < 88.0;
    const verdictClass = isDirect ? "optimal" : isInterview ? "lavender" : "amber";
    const barPct = totalScore !== null ? Math.min(100, Math.max(0, totalScore)) : 0;

    const deltaSign = vel.delta_pct >= 0 ? "+" : "";
    const paceChipClass = vel.is_behind ? "amber" : "optimal";

    heroEl.innerHTML = `
      <div class="tum-hero-card">
        <div class="tum-hero-card-top">
          <div>
            <div class="tum-hero-eyebrow">WHERE I AM VS. WHERE I SHOULD BE // ${this.escapeHtml(station.month_label || "ACTIVE")}</div>
            <h2 class="tum-hero-title">${this.escapeHtml(station.name)}</h2>
          </div>
          <span class="tum-pace-pill ${paceChipClass}">
            ${vel.is_behind ? `BEHIND ${Math.abs(vel.delta_pct)}%` : `AHEAD ${deltaSign}${vel.delta_pct}%`}
          </span>
        </div>

        <div class="tum-hero-pace-body">
          ${this.buildRadialRingHtml(progressPercent, vel.is_behind ? "#f59e0b" : "var(--accent-lavender)", 86, "EXECUTED")}
          <div class="tum-hero-bars">
            <div class="tum-pace-row">
              <span>SHOULD BE &bull; MONTH CLOCK (DAY ${vel.day_of_month}/${vel.total_days})</span>
              <strong>${vel.elapsed_pct}%</strong>
            </div>
            <div class="tum-mini-bar-track" style="height: 5px; margin-bottom: 10px;">
              <div class="tum-mini-bar-fill" style="width: ${vel.elapsed_pct}%; background: rgba(255, 255, 255, 0.35);"></div>
            </div>

            <div class="tum-pace-row">
              <span>ACTUAL DELIVERABLES (${completedList.length}/${delivEntries.length} COMPLETE)</span>
              <strong style="color: var(--accent-lavender);">${progressPercent}%</strong>
            </div>
            <div class="tum-mini-bar-track" style="height: 5px; margin-bottom: 8px;">
              <div class="tum-mini-bar-fill" style="width: ${progressPercent}%; background: var(--accent-lavender);"></div>
            </div>

            <div class="tum-hero-delta-line ${vel.is_behind ? "is-behind" : "is-optimal"}">
              ${this.escapeHtml(vel.status_text)} &bull; Checkboxes live in <strong>Daily</strong>
            </div>
          </div>
        </div>

        <div class="tum-hero-streams-list">
          ${streamsHtml || `<div style="font-size: 11px; color: var(--text-tertiary);">No stream deliverables bound.</div>`}
        </div>
      </div>

      <div class="tum-hero-card">
        <div class="tum-hero-card-top">
          <div>
            <div class="tum-hero-eyebrow">TUM HEILBRONN STAGE 1 ADMISSIONS // BAVARIAN SCALE</div>
            <h2 class="tum-hero-title">Direct Admit Standing (&ge; 88.0 pts)</h2>
          </div>
          <span class="tum-pace-pill ${verdictClass}">${this.escapeHtml(verdict)}</span>
        </div>

        <div class="tum-adm-kpi-row">
          <div class="tum-adm-kpi">
            <span class="kpi-lbl">BAVARIAN GPA</span>
            <span class="kpi-num">${bavGpa} <small>DE</small></span>
            <span class="kpi-sub">Polish Avg: ${polishGpa}</span>
          </div>
          <div class="tum-adm-kpi">
            <span class="kpi-lbl">PROJECTED STAGE 1</span>
            <span class="kpi-num accent">${totalScore !== null ? totalScore.toFixed(1) : "--"} <small>/ 100</small></span>
            <span class="kpi-sub">Curricular: ${curricularScore} pts</span>
          </div>
          <div class="tum-adm-kpi">
            <span class="kpi-lbl">DISTANCE TO 88.0</span>
            <span class="kpi-num ${isDirect ? "green" : ""}">${dist88 !== null ? (dist88 <= 0 ? `+${Math.abs(dist88).toFixed(1)}` : `-${dist88.toFixed(1)}`) : "--"} <small>pts</small></span>
            <span class="kpi-sub">${isDirect ? "Direct Admit Zone" : "Target Cutoff Gap"}</span>
          </div>
        </div>

        <div class="tum-threshold-block">
          <div class="tum-pace-row" style="margin-bottom: 6px;">
            <span>STAGE 1 SCORE GAUGE (0 &rarr; 100 PTS)</span>
            <strong style="color: ${isDirect ? "var(--color-green-light)" : "var(--text-primary)"};">CUTOFF 88.0 PTS</strong>
          </div>
          <div class="tum-threshold-track lg">
            <div class="tum-threshold-fill ${isDirect ? "is-direct" : ""}" style="width: ${barPct}%;"></div>
            <div class="tum-threshold-pin" style="left: 72%;" title="72.0 pts Stage 2 Interview Threshold"></div>
            <div class="tum-threshold-pin target" style="left: 88%;" title="88.0 pts Direct Admit Cutoff"></div>
          </div>
          <div class="tum-threshold-scale">
            <span>0</span>
            <span style="left: 72%;">72 Interview</span>
            <span style="left: 88%; color: var(--accent-lavender);">88 Direct</span>
            <span>100</span>
          </div>
        </div>

        <div class="tum-hero-adm-footer">
          <div class="tum-hero-adm-note">
            ${isDirect
              ? "Standing exceeds Direct Admission cutoff. Maintain Math R (2&times;) &amp; CS (2&times;)."
              : "Boost weighted Math R (2&times;) &amp; Informatics (2&times;) averages in Study to close gap."}
          </div>
          <button type="button" class="btn-ghost-icon tum-ledger-cta" onclick="MetroMap.openGradesLedger()">
            Grades Ledger &amp; Simulator &rarr;
          </button>
        </div>
      </div>
    `;
  },

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 220;
    const startX = 120;
    const spineY = 148;
    const svgHeight = 258;
    const totalTrackLength = (stations.length - 1) * spacing;
    const terminusX = startX + totalTrackLength + 120;
    const totalWidth = terminusX + 160;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = `${svgHeight}px`;

    // Date calculations (global badge % over '26-'28; track X anchored to station calendar dates)
    const now = new Date();
    const { startDate, endDate, totalDays, elapsedDays, progressRatio } = this.calculateJourneyProgress(now);
    const dateToX = this.buildTrackDateMapper(stations, startX, spacing, terminusX, startDate, endDate);
    const currentX = dateToX(now);

    this.currentBeaconX = currentX;

    // Update Band 1 & Mobile HUD alongside Track
    this.renderComparisonHero();
    this.renderMobileHud();

    // Phase Headers Ribbon (Top Zone Y=10)
    const phases = [
      { name: "Phase 1: Year 3 Liceum", startIdx: 0, endIdx: 6 },
      { name: "Phase 2: SIGG Finals & Year 3 Lock", startIdx: 7, endIdx: 10 },
      { name: "Phase 3: Summer Mass & B1", startIdx: 11, endIdx: 11 },
      { name: "Phase 4: Matura Crucible", startIdx: 12, endIdx: 19 },
      { name: "Phase 5: Official CKE & TUM", startIdx: 20, endIdx: 21 },
    ];

    const phaseHeadersHtml = phases
      .map((p) => {
        const x1 = startX + p.startIdx * spacing - 30;
        const x2 = startX + p.endIdx * spacing + 80;
        const width = Math.max(120, x2 - x1);
        return `
          <div style="position: absolute; top: 10px; left: ${x1}px; width: ${width}px; pointer-events: none; z-index: 5;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.06em; white-space: nowrap;">
                ${p.name}
              </span>
              <div style="flex: 1; height: 1px; background: var(--border-hairline);"></div>
            </div>
          </div>
        `;
      })
      .join("");

    // Continuous Architectural Parallel Subway Rails (no mid-route camel humps or eye loops)
    let streamRailsHtml = "";
    const filterStream = this.activeStreamFilter || "all";
    const stationActiveYs = {};
    stations.forEach((st) => {
      stationActiveYs[st.id] = [];
    });

    this.streams.forEach((stream) => {
      const isFocused = filterStream === stream.id;
      const isAll = filterStream === "all";
      const railOpacity = isFocused ? "0.94" : isAll ? "0.34" : "0.08";
      const strokeW = isFocused ? "2.6" : "1.6";
      const color = this.getStreamColor(stream.id);
      const yOffset = stream.yOffset;
      const branchY = spineY + yOffset;
      const rampLen = Math.min(54, Math.abs(yOffset) * 1.15 + 16);

      const indices = [];
      stations.forEach((st, idx) => {
        const branches = st.branches || [];
        if (branches.includes(stream.id) || branches.some((b) => this.normalizeStreamKey(b) === stream.id)) {
          indices.push(idx);
          stationActiveYs[st.id].push({ y: branchY, color, isFocused });
        }
      });

      if (indices.length === 0) return;

      const firstIdx = indices[0];
      const lastIdx = indices[indices.length - 1];
      const segStartX = startX + firstIdx * spacing;
      const segEndX = startX + lastIdx * spacing;
      const ingressX = firstIdx === 0 ? Math.max(24, startX - 44) : segStartX - rampLen;
      const egressX = lastIdx === stations.length - 1 ? terminusX : segEndX + rampLen;
      const midIn = (ingressX + segStartX) / 2;
      const midOut = (segEndX + egressX) / 2;

      const pathD = `M ${ingressX} ${spineY} C ${midIn} ${spineY}, ${midIn} ${branchY}, ${segStartX} ${branchY} L ${segEndX} ${branchY} C ${midOut} ${branchY}, ${midOut} ${spineY}, ${egressX} ${spineY}`;
      const approxLen = Math.round((egressX - ingressX) + Math.abs(yOffset) * 2 + 80);

      streamRailsHtml += `
        <g class="stream-tributary-branch ${isFocused ? "is-focused" : ""}" style="opacity: ${railOpacity}; transition: opacity 0.3s ease;">
          <path d="${pathD}" class="metro-rail-draw"
                style="--rail-len: ${approxLen}; stroke-dasharray: ${approxLen}; stroke-dashoffset: 0;"
                fill="none" stroke="${color}" stroke-width="${strokeW}" stroke-linecap="round" stroke-linejoin="round"
                ${isFocused ? `filter="url(#metroGlow)"` : ""} />
          ${
            isFocused || isAll
              ? indices
                  .map((idx) => {
                    const px = startX + idx * spacing;
                    return `<circle cx="${px}" cy="${branchY}" r="${isFocused ? 3.6 : 2.3}" fill="${color}" stroke="var(--bg-canvas)" stroke-width="1.2" />`;
                  })
                  .join("")
              : ""
          }
        </g>
      `;
    });

    // Subtle Vertical Station Interchange Spokes connecting active rails to their Station Hub
    let interchangeSpokesHtml = "";
    stations.forEach((st, idx) => {
      const pts = stationActiveYs[st.id] || [];
      if (pts.length === 0) return;
      const posX = startX + idx * spacing;
      const minY = Math.min(spineY, ...pts.map((p) => p.y));
      const maxY = Math.max(spineY, ...pts.map((p) => p.y));
      if (maxY > minY) {
        interchangeSpokesHtml += `<line x1="${posX}" y1="${minY}" x2="${posX}" y2="${maxY}" stroke="rgba(255, 255, 255, 0.1)" stroke-width="1.2" />`;
      }
    });

    // Main Spine Track
    const activeEndX = Math.min(terminusX, currentX);
    const activeSpineLen = Math.max(0, Math.round(activeEndX - (startX - 20)));
    const trunkHtml = `
      <line x1="${startX - 20}" y1="${spineY}" x2="${terminusX}" y2="${spineY}"
            stroke="rgba(255, 255, 255, 0.14)" stroke-width="3.5" stroke-linecap="round" />
      ${
        currentX > startX - 20
          ? `<line x1="${startX - 20}" y1="${spineY}" x2="${activeEndX}" y2="${spineY}"
                   class="metro-spine-progress"
                   style="--spine-len: ${activeSpineLen}; stroke-dasharray: ${activeSpineLen};"
                   stroke="url(#metroProgressGrad)" stroke-width="4" stroke-linecap="round" />`
          : ""
      }
    `;

    // Today Pill geometry computed FIRST so exam solver reserves its bounding box & needle corridor
    const todayPillW = 152;
    const todayPillH = 30;
    const todayPillY = 22;
    const todayPillX = Math.max(14, currentX - todayPillW / 2);

    const occupiedBoxes = [
      // Today Pill Bounding Box
      {
        x1: todayPillX - 8,
        x2: todayPillX + todayPillW + 8,
        y1: todayPillY - 4,
        y2: todayPillY + todayPillH + 6,
      },
      // Vertical Today Needle Corridor (guarantees NO exam pill cuts across Today's needle!)
      {
        x1: currentX - 18,
        x2: currentX + 18,
        y1: todayPillY + todayPillH,
        y2: spineY - 8,
      },
    ];

    const boxesOverlap = (a, b) => !(a.x2 <= b.x1 || a.x1 >= b.x2 || a.y2 <= b.y1 || a.y1 >= b.y2);

    // Dynamic School Exams on Track (Deduplicated, 2D Collision-Solved, Orthogonal Elbow Routing)
    let examsSvgHtml = "";
    const showExamsOnTrack = this.activeStreamFilter === "all" || this.activeStreamFilter === "academics";
    const clusters = [];

    if (showExamsOnTrack && this.upcomingExams && this.upcomingExams.length > 0) {
      const todayMid = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

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
          if (diffDays >= 0 && exDate >= startDate && exDate <= endDate) {
            const testX = dateToX(exDate);
            const dueLabel = diffDays === 0 ? "TODAY" : diffDays === 1 ? "1d" : `${diffDays}d`;
            validExams.push({ ...exam, exDate, testX, diffDays, dueLabel });
          }
        } catch (e) {}
      });

      validExams.sort((a, b) => a.testX - b.testX);

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

      const tierPillYs = [74, 50, 26]; // Tiers clear above highest green rail (-30 -> spineY - 30 = 118)
      const pillH = 16;

      clusters.forEach((cl, idx) => {
        let labelText = "";
        if (cl.exams.length === 1) {
          const rawSubj = (cl.exams[0].subject || "").trim();
          const shortSubj = rawSubj.length > 9 ? rawSubj.slice(0, 8) + "." : rawSubj;
          labelText = `[${cl.dueLabel}] ${shortSubj}`;
        } else if (cl.exams.length === 2) {
          const raw1 = (cl.exams[0].subject || "").trim();
          const raw2 = (cl.exams[1].subject || "").trim();
          if (raw1.toLowerCase() === raw2.toLowerCase() && raw1) {
            const shortSubj = raw1.length > 9 ? raw1.slice(0, 8) + "." : raw1;
            labelText = `[${cl.dueLabel}] 2\u00d7 ${shortSubj}`;
          } else {
            labelText = `[${cl.dueLabel}] ${raw1.slice(0, 4)} \u2022 ${raw2.slice(0, 4)}`;
          }
        } else {
          labelText = `[${cl.dueLabel}] ${cl.exams.length} Tests`;
        }

        const labelW = Math.max(60, Math.round(labelText.length * 6.3 + 16));
        cl.w = labelW;
        cl.labelText = labelText;

        const anchorX = cl.centerX;
        const candidateXs = [
          anchorX - labelW / 2,
          anchorX + 18,
          anchorX - labelW - 18,
          anchorX + 48,
          anchorX - labelW - 48,
          anchorX + 86,
          anchorX - labelW - 86,
          anchorX + 124,
          anchorX - labelW - 124,
        ];

        const preferredTierOrder = idx % 2 === 0 ? [0, 1, 2] : [1, 0, 2];
        let chosenX = candidateXs[0];
        let chosenY = tierPillYs[preferredTierOrder[0]];
        let placed = false;

        for (const cx of candidateXs) {
          if (cx < 12) continue;
          for (const tIdx of preferredTierOrder) {
            const cy = tierPillYs[tIdx];
            const testBox = { x1: cx - 5, x2: cx + labelW + 5, y1: cy - 3, y2: cy + pillH + 3 };
            if (!occupiedBoxes.some((b) => boxesOverlap(testBox, b))) {
              chosenX = cx;
              chosenY = cy;
              occupiedBoxes.push(testBox);
              placed = true;
              break;
            }
          }
          if (placed) break;
        }

        if (!placed) {
          occupiedBoxes.push({ x1: chosenX - 5, x2: chosenX + labelW + 5, y1: chosenY - 3, y2: chosenY + pillH + 3 });
        }

        cl.pillX = chosenX;
        cl.pillY = chosenY;
      });

      clusters.forEach((cl) => {
        const testX = cl.centerX;
        const pillX = cl.pillX;
        const pillY = cl.pillY;
        const pillCenterX = pillX + cl.w / 2;
        const pillBottomY = pillY + 16;
        const isUrgent = cl.diffDays >= 0 && cl.diffDays <= 3; // Aligned with 3-day reality rule
        const lineColor = isUrgent ? "#ef4444" : "rgba(255, 255, 255, 0.25)";
        const textColor = isUrgent ? "#fca5a5" : "var(--text-primary)";

        // Route cleanly via orthogonal elbow above upper stream rails
        const dx = Math.abs(pillCenterX - testX);
        const kneeY = Math.min(spineY - 40, pillBottomY + 6);
        const leaderPath =
          dx <= 3
            ? `M ${testX} ${spineY - 4} L ${testX} ${pillBottomY}`
            : `M ${testX} ${spineY - 4} L ${testX} ${kneeY} L ${pillCenterX} ${kneeY} L ${pillCenterX} ${pillBottomY}`;

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
            <path d="${leaderPath}" fill="none" stroke="${lineColor}" stroke-width="1.2" ${isUrgent ? "" : 'stroke-dasharray="2.5 2.5"'} opacity="0.85" />
            <circle cx="${testX}" cy="${spineY}" r="${cl.exams.length > 1 ? 3.5 : 2.5}" fill="${isUrgent ? "#ef4444" : "var(--text-secondary)"}" stroke="var(--bg-canvas)" stroke-width="1.5" />
            <circle cx="${pillCenterX}" cy="${pillBottomY}" r="1.6" fill="${isUrgent ? "#ef4444" : "rgba(255, 255, 255, 0.45)"}" />
            <rect x="${pillX}" y="${pillY}" width="${cl.w}" height="16" rx="4" fill="var(--bg-canvas)" stroke="${isUrgent ? "rgba(239, 68, 68, 0.55)" : "var(--border-subtle)"}" stroke-width="1" />
            <text x="${pillCenterX}" y="${pillY + 11.2}" font-family="var(--font-mono)" font-size="8.5" font-weight="${isUrgent ? "700" : "600"}" text-anchor="middle" fill="${textColor}" letter-spacing="0.02em">
              ${this.escapeHtml(cl.labelText)}
            </text>
          </g>
        `;
      });
    }

    // Station Nodes along Track (Labels safely pushed below lower stream rails at spineY + 46)
    let stationsSvgHtml = "";
    stations.forEach((station, idx) => {
      const posX = startX + idx * spacing;
      const status = station.status || "upcoming";
      const isActive = status === "active";
      const isCompleted = status === "completed";
      const isSelected = this.selectedStation?.id === station.id;
      const branches = station.branches || [];

      let nodeCircles = "";
      let labelSubText = station.month_label;
      let labelSubColor = "var(--text-tertiary)";

      if (isActive) {
        labelSubText = "ACTIVE STATION";
        labelSubColor = "var(--accent-lavender)";
        nodeCircles = `
          <circle cx="${posX}" cy="${spineY}" r="16" fill="none" stroke="var(--accent-lavender)" stroke-width="1" opacity="0.3" class="beacon-pulse" />
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--accent-lavender)" data-orig-width="${isSelected ? "3" : "2"}" cx="${posX}" cy="${spineY}" r="11" fill="none" stroke="var(--accent-lavender)" stroke-width="${isSelected ? "3" : "2"}" />
          <circle cx="${posX}" cy="${spineY}" r="7" fill="var(--bg-canvas)" />
          <circle cx="${posX}" cy="${spineY}" r="4.2" fill="var(--accent-lavender)" />
        `;
      } else if (isCompleted) {
        const passedOverList = station.passed_over_deliverables || [];
        const isAudited = passedOverList.length > 0 && (!station.completed_deliverables || station.completed_deliverables.length === 0);
        if (isAudited) {
          labelSubText = "Audited";
          labelSubColor = "#f59e0b";
          nodeCircles = `
            <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="#f59e0b" data-orig-width="${isSelected ? "3" : "1.8"}" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--bg-card)" stroke="#f59e0b" stroke-width="${isSelected ? "3" : "1.8"}" stroke-dasharray="3,2" />
            <circle cx="${posX}" cy="${spineY}" r="4" fill="#f59e0b" opacity="0.85" />
          `;
        } else {
          labelSubText = "Completed";
          nodeCircles = `
            <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--bg-card)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--text-primary)" stroke="${isSelected ? "var(--accent-lavender)" : "var(--bg-card)"}" stroke-width="${isSelected ? "2.5" : "2"}" />
            <polyline points="${posX - 3},${spineY} ${posX - 1},${spineY + 2} ${posX + 3},${spineY - 2}" fill="none" stroke="var(--bg-card)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          `;
        }
      } else {
        nodeCircles = `
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--border-medium)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--bg-card)" stroke="${isSelected ? "var(--accent-lavender)" : "var(--border-medium)"}" stroke-width="${isSelected ? "2.5" : "2"}" />
        `;
      }

      const pipSpacing = 6.5;
      const pipsStartX = posX - ((branches.length - 1) * pipSpacing) / 2;
      const pipsSvg = branches
        .map((b, pIdx) => `<circle cx="${pipsStartX + pIdx * pipSpacing}" cy="${spineY + 84}" r="2" fill="${this.getStreamColor(this.normalizeStreamKey(b))}" />`)
        .join("");

      const labelNameColor = isActive ? "var(--accent-lavender)" : isCompleted ? "var(--text-secondary)" : "var(--text-tertiary)";
      const labelFontWeight = isActive ? "800" : "600";

      stationsSvgHtml += `
        <g class="metro-rail-station-node" style="cursor: pointer; pointer-events: all;"
           onclick="MetroMap.selectStation('${station.id}')"
           onmouseenter="MetroMap.highlightCardInGrid('${station.id}')"
           onmouseleave="MetroMap.clearHighlightCardInGrid()">
          ${nodeCircles}
          <text x="${posX}" y="${spineY + 60}" text-anchor="middle" font-size="10.5" font-weight="${labelFontWeight}" fill="${labelNameColor}">
            ${this.escapeHtml(station.name)}
          </text>
          <text x="${posX}" y="${spineY + 73}" text-anchor="middle" font-family="var(--font-mono)" font-size="8.5" font-weight="${isActive ? "700" : "500"}" fill="${labelSubColor}">
            ${labelSubText}
          </text>
          ${pipsSvg}
          <circle cx="${posX}" cy="${spineY}" r="22" fill="transparent" />
        </g>
      `;
    });

    // TUM '28 Golden Terminal
    const terminalSvgHtml = `
      <g style="cursor: pointer; pointer-events: all;" onclick="MetroMap.openGradesLedger()">
        <circle cx="${terminusX}" cy="${spineY}" r="16" fill="none" stroke="#f59e0b" stroke-width="1.2" opacity="0.3" class="beacon-pulse" />
        <circle cx="${terminusX}" cy="${spineY}" r="11" fill="var(--bg-card)" stroke="#f59e0b" stroke-width="2" />
        <circle cx="${terminusX}" cy="${spineY}" r="4" fill="#f59e0b" />
        <text x="${terminusX}" y="${spineY + 60}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#f59e0b">
          TUM \u201928
        </text>
        <text x="${terminusX}" y="${spineY + 73}" text-anchor="middle" font-family="var(--font-mono)" font-size="8" font-weight="700" fill="#f59e0b">
          Campus Heilbronn
        </text>
      </g>
    `;

    // Today Needle & Pill (guaranteed collision-free in reserved corridor)
    const todayBeaconSvg = `
      <g class="metro-today-beacon" style="pointer-events: none; z-index: 25;">
        <line x1="${currentX}" y1="${spineY - 4}" x2="${currentX}" y2="${todayPillY + todayPillH}" stroke="#ffffff" stroke-width="1.8" stroke-opacity="0.9" />
        <circle cx="${currentX}" cy="${spineY - 4}" r="2.8" fill="#ffffff" />
        <rect x="${todayPillX}" y="${todayPillY}" width="${todayPillW}" height="${todayPillH}" rx="5" fill="var(--bg-canvas)" stroke="rgba(255, 255, 255, 0.28)" stroke-width="1" />
        <text x="${todayPillX + todayPillW / 2}" y="${todayPillY + 12}" font-family="var(--font-mono)" font-size="8.5" font-weight="800" text-anchor="middle" fill="#ffffff" letter-spacing="0.05em">
          TODAY // ${now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase()}
        </text>
        <text x="${todayPillX + todayPillW / 2}" y="${todayPillY + 23}" font-family="var(--font-mono)" font-size="8" font-weight="700" text-anchor="middle" fill="var(--accent-lavender)" letter-spacing="0.02em">
          DAY ${elapsedDays + 1}/${totalDays} \u2022 ${(progressRatio * 100).toFixed(1)}% OF \u201926\u2013\u201928
        </text>
      </g>
    `;

    canvasWrap.innerHTML = `
      ${phaseHeadersHtml}
      <svg width="${totalWidth}" height="${svgHeight}" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 20;">
        <defs>
          <linearGradient id="metroProgressGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="rgba(255, 255, 255, 0.65)" />
            <stop offset="100%" stop-color="#a78bfa" />
          </linearGradient>
          <filter id="metroGlow" x="-10%" y="-40%" width="120%" height="180%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        ${interchangeSpokesHtml}
        ${streamRailsHtml}
        ${trunkHtml}
        ${examsSvgHtml}
        ${stationsSvgHtml}
        ${terminalSvgHtml}
        ${todayBeaconSvg}
      </svg>
    `;

    // Sync 'All (N)' button label and render Phase-Filtered Cards Grid
    const allPhaseBtn = document.querySelector('.metro-phase-btn[data-phase="all"]');
    if (allPhaseBtn) {
      allPhaseBtn.textContent = `All (${stations.length})`;
    }
    this.renderCardsGrid(stations, progressRatio);
    this.attachTestDotEvents();
  },

  renderCardsGrid(stations, progressRatio = 0.044) {
    const cardsGrid = document.getElementById("metroCardsGrid");
    if (!cardsGrid || !stations) return;

    const phaseFilter = this.activePhaseFilter || "all";
    const visibleStations = stations
      .map((st, idx) => ({ st, idx }))
      .filter(({ st, idx }) => phaseFilter === "all" || this.getStationPhaseKey(st, idx) === phaseFilter);

    let gridCardsHtml = visibleStations
      .map(({ st: station }) => {
        const status = station.status || "upcoming";
        const isActive = status === "active";
        const isCompleted = status === "completed";
        const isSelected = this.selectedStation?.id === station.id;
        const branches = station.branches || [];

        const isFilteredMatch =
          this.activeStreamFilter === "all" ||
          branches.includes(this.activeStreamFilter) ||
          branches.some((b) => this.normalizeStreamKey(b) === this.activeStreamFilter);
        const filterStyle = isFilteredMatch ? "" : "opacity: 0.25; filter: grayscale(0.5);";

        const delivEntries = Object.entries(station.deliverables || {});
        const completedList = station.completed_deliverables || [];
        const totalDelivs = delivEntries.length;
        const progressPercent = this.calculateStationProgress(station);

        const passedOverList = station.passed_over_deliverables || [];
        const isAudited = isCompleted && passedOverList.length > 0 && (completedList.length === 0 || passedOverList.length >= totalDelivs);

        let chipHtml = "";
        if (isActive) {
          chipHtml = `<span class="metro-card-chip active">ACTIVE (${progressPercent}%)</span>`;
        } else if (isAudited) {
          chipHtml = `<span class="metro-card-chip" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.35);">AUDITED</span>`;
        } else if (isCompleted) {
          chipHtml = `<span class="metro-card-chip done">\u2713 DONE</span>`;
        } else {
          chipHtml = `<span class="metro-card-chip">${progressPercent}%</span>`;
        }

        const tagsHtml = branches
          .map((b) => {
            const c = this.getStreamColor(this.normalizeStreamKey(b));
            const streamObj = this.streams.find((s) => s.id === b || s.id === this.normalizeStreamKey(b));
            const sName = streamObj ? streamObj.name : b.toUpperCase();
            return `<span class="metro-micro-tag" style="background: ${c}15; color: ${c}; border: 1px solid ${c}35;">${sName}</span>`;
          })
          .join("");

        const sqList = Array.isArray(station.sidequests) ? station.sidequests : [];
        const sqDone = Array.isArray(station.completed_sidequests)
          ? station.completed_sidequests.filter((id) => sqList.some((q) => q.id === id)).length
          : 0;
        const sqTagHtml = sqList.length > 0
          ? `<span class="metro-micro-tag" style="background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.32);">SIDEQUESTS ${sqDone}/${sqList.length}</span>`
          : "";

        const vel = isActive ? this.getSafeVelocity(station, progressPercent) : null;

        return `
          <div
            class="metro-grid-card ${isActive ? "active-card" : ""} ${isCompleted ? "completed-card" : ""} ${isSelected ? "selected-card" : ""}"
            data-station-id="${station.id}"
            style="${filterStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
            onmouseenter="MetroMap.highlightStationOnRail('${station.id}')"
            onmouseleave="MetroMap.clearHighlightStationOnRail()"
          >
            <div class="metro-card-header">
              <span class="metro-card-month">${station.month_label}:</span>
              ${chipHtml}
            </div>
            <div class="metro-card-title" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name.toUpperCase())}
            </div>
            <div class="metro-micro-tags">
              ${tagsHtml}
              ${sqTagHtml}
            </div>
            ${
              isActive && vel
                ? `
                  <div class="metro-card-active-progress">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 8.5px;">
                      <span style="color: var(--text-tertiary); font-weight: 600;">CLOCK: Day ${vel.day_of_month}/${vel.total_days}</span>
                      <span style="color: rgba(255, 255, 255, 0.72); font-weight: 700;">${vel.elapsed_pct}%</span>
                    </div>
                    <div class="metro-progress-track">
                      <div class="metro-progress-fill time-fill" style="width: ${vel.elapsed_pct}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 8.5px; margin-top: 2px;">
                      <span style="color: var(--text-tertiary); font-weight: 600;">OUTPUT: ${completedList.length}/${totalDelivs}</span>
                      <span style="color: var(--accent-lavender); font-weight: 700;">${progressPercent}%</span>
                    </div>
                    <div class="metro-progress-track">
                      <div class="metro-progress-fill goals-fill" style="width: ${progressPercent}%;"></div>
                    </div>
                  </div>
                `
                : `
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

    if (phaseFilter === "all" || phaseFilter === "phase3") {
      gridCardsHtml += `
        <div
          class="metro-grid-card"
          style="border: 1px solid rgba(245, 158, 11, 0.35); background: var(--bg-surface); cursor: pointer;"
          onclick="MetroMap.openGradesLedger()"
          title="TUM Campus Heilbronn Destination"
        >
          <div class="metro-card-header">
            <span class="metro-card-month" style="color: #f59e0b;">OCT '28:</span>
            <span class="metro-card-chip" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border-color: rgba(245, 158, 11, 0.3);">TARGET</span>
          </div>
          <div class="metro-card-title" style="color: #f59e0b;">
            TUM \u201928 HEILBRONN
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
    }

    cardsGrid.innerHTML = gridCardsHtml;
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
    if (this.selectedStation && this.selectedStation.id === stationId) {
      const panel = document.getElementById("stationInspectorPanel");
      if (panel && panel.style.display === "block") {
        this.closeInspector();
        return;
      }
    }
    const station = this.data?.stations?.find((s) => s.id === stationId);
    if (!station) return;

    this.selectedStation = station;
    this.renderInspector(station);
  },

  closeInspector() {
    const panel = document.getElementById("stationInspectorPanel");
    if (panel) {
      panel.style.display = "none";
      panel.innerHTML = "";
    }
    this.selectedStation = null;
    document.querySelectorAll(".metro-grid-card.selected-card").forEach((el) => el.classList.remove("selected-card"));
  },

  async openDrawer(station) {
    return this.renderInspector(station, false);
  },

  async renderInspector(station, skipScroll = false) {
    const panel = document.getElementById("stationInspectorPanel");
    const legacyDrawer = document.getElementById("stationDrawer");
    if (legacyDrawer) legacyDrawer.classList.remove("open");
    if (!panel || !station) return;

    if (!this.stationProgressById) this.stationProgressById = {};

    let inspectedProgress = null;
    if (window.pywebview && window.pywebview.api) {
      if (window.pywebview.api.get_station_deliverables) {
        inspectedProgress = (await window.pywebview.api.get_station_deliverables(station.id)) || [];
        this.stationProgressById[station.id] = inspectedProgress;
        if (station.status === "active") {
          this.stationProgress = inspectedProgress;
        }
      }
      if (station.status === "active" && window.pywebview.api.get_station_pace_velocity) {
        this.paceVelocity = (await window.pywebview.api.get_station_pace_velocity(station.id)) || null;
      }
    }

    const statusVal = station.status || "upcoming";
    const delivEntries = Object.entries(station.deliverables || {});
    const totalDelivs = delivEntries.length;
    const completedList = station.completed_deliverables || [];
    const passedOverList = station.passed_over_deliverables || [];
    const isAudited = statusVal === "completed" && passedOverList.length > 0 && (completedList.length === 0 || passedOverList.length >= totalDelivs);

    const resolveCounter = (key, val) => {
      const normKey = this.normalizeStreamKey(key);
      const list = inspectedProgress || this.stationProgressById[station.id] || [];
      const pMatch = list.find((p) => {
        if (p.station_id && p.station_id !== station.id) return false;
        const pNorm = this.normalizeStreamKey(p.stream);
        const pLow = (p.stream || "").toLowerCase();
        const kLow = (key || "").toLowerCase();
        return pNorm === normKey || pLow === kLow || pLow.includes(kLow) || kLow.includes(pLow);
      });
      if (pMatch) {
        return {
          count: Number(pMatch.completed_count || 0),
          total: Math.max(1, Number(pMatch.total_required || 10)),
          unit: pMatch.unit_label || "reps",
        };
      }
      return this.getDeliverableCounter(station.id, key, val);
    };

    let progressPercent = this.calculateStationProgress(station);
    if (inspectedProgress && statusVal !== "completed" && delivEntries.length > 0) {
      let score = 0;
      delivEntries.forEach(([k, v]) => {
        if (completedList.includes(k) || passedOverList.includes(k)) {
          score += 1.0;
        } else {
          const cObj = resolveCounter(k, v);
          if (cObj.total > 0) score += Math.min(1.0, Math.max(0, (cObj.count || 0) / cObj.total));
        }
      });
      progressPercent = Math.min(100, Math.round((score / delivEntries.length) * 100));
    }

    const vel = this.getSafeVelocity(station, progressPercent);

    let statusBadgeHtml = "";
    if (statusVal === "active") {
      statusBadgeHtml = `<span class="tum-pace-pill ${vel.is_behind ? "amber" : "lavender"}">ACTIVE MILESTONE</span>`;
    } else if (isAudited) {
      statusBadgeHtml = `<span class="tum-pace-pill amber">AUDITED // REALLOCATED</span>`;
    } else if (statusVal === "completed") {
      statusBadgeHtml = `<span class="tum-pace-pill optimal">\u2713 COMPLETED</span>`;
    } else {
      statusBadgeHtml = `<span class="tum-pace-pill">UPCOMING TARGET</span>`;
    }

    const itemsHtml = delivEntries
      .map(([key, val]) => {
        const normKey = this.normalizeStreamKey(key);
        const lineBadgeColor = this.getStreamColor(normKey);
        const isChecked = completedList.includes(key);
        const isPassedOver = passedOverList.includes(key);
        const countObj = resolveCounter(key, val);
        const curCount = isChecked ? countObj.total : (countObj.count || 0);
        const totalReq = Math.max(1, countObj.total || 10);
        const unitLabel = countObj.unit || "reps";
        const itemPct = Math.min(100, Math.round((curCount / totalReq) * 100));

        const targetPace = Math.round(((vel.day_of_month / vel.total_days) * totalReq) * 10) / 10;
        const deficit = Math.round((targetPace - curCount) * 10) / 10;
        const isBehind = deficit > 0;

        let statusPill = "";
        if (isAudited || isPassedOver) {
          statusPill = `<span class="telemetry-status-pill audited">REALLOCATED</span>`;
        } else if (isChecked || curCount >= totalReq) {
          statusPill = `<span class="telemetry-status-pill done">VERIFIED \u2713</span>`;
        } else if (statusVal === "active") {
          statusPill = `<span class="telemetry-status-pill active">${itemPct}% LOGGED</span>`;
        } else {
          statusPill = `<span class="telemetry-status-pill upcoming">QUEUED</span>`;
        }

        return `
          <div class="inspector-deliv-card ${isChecked || curCount >= totalReq ? "completed-deliv" : ""}" style="border-top: 2px solid ${lineBadgeColor};">
            <div class="inspector-deliv-top">
              <div>
                <span class="telemetry-stream-name" style="color: ${lineBadgeColor};">${this.escapeHtml(key)}</span>
                <span class="telemetry-counter-pill">${curCount} / ${totalReq} ${this.escapeHtml(unitLabel)}</span>
              </div>
              ${statusPill}
            </div>
            <div class="telemetry-desc">${this.escapeHtml(val)}</div>
            <div class="tum-mini-bar-track" style="margin: 8px 0 6px;">
              <div class="tum-mini-bar-fill" style="width: ${itemPct}%; background: ${lineBadgeColor};"></div>
            </div>
            ${statusVal === "active" ? `
              <div class="inspector-pace-line ${isBehind ? "is-behind" : "is-optimal"}">
                ${isBehind ? `Pace Deficit: ${deficit} ${this.escapeHtml(unitLabel)} behind today's target (${targetPace})` : `On Pace (+${Math.abs(Math.round((curCount - targetPace) * 10) / 10)} ${this.escapeHtml(unitLabel)} buffer)`}
              </div>
            ` : ""}
          </div>
        `;
      })
      .join("");

    panel.innerHTML = `
      <div class="inspector-header">
        <div>
          <div class="inspector-eyebrow">${this.escapeHtml(station.month_label || "")} // ${this.escapeHtml(station.phase || "ROADMAP STATION")}</div>
          <div class="inspector-title-row">
            <h3 class="inspector-title">${this.escapeHtml(station.name)}</h3>
            ${statusBadgeHtml}
          </div>
        </div>
        <div class="inspector-actions">
          ${statusVal === "active" ? `
            <button type="button" class="btn-ghost-icon" style="color: var(--accent-lavender); border-color: rgba(167, 139, 250, 0.35);" onclick="MetroMap.advanceStation('${station.id}')">
              Advance Station &rarr;
            </button>
          ` : ""}
          <button type="button" class="btn-ghost-icon" onclick="MetroMap.closeInspector()" title="Close Inspector">&times; Close</button>
        </div>
      </div>

      <div class="inspector-meta-grid">
        <div class="inspector-meta-box">
          <div class="card-label" style="margin-bottom: 4px;">CORE OBJECTIVE</div>
          <div class="inspector-meta-text">${this.escapeHtml(station.objective || "No objective stated.")}</div>
        </div>
        <div class="inspector-meta-box">
          <div class="card-label" style="margin-bottom: 4px;">NEXT EXECUTION STEP</div>
          <div class="inspector-meta-text">${this.escapeHtml(station.next_action || "--")}</div>
        </div>
        <div class="inspector-meta-box">
          <div class="card-label" style="margin-bottom: 4px;">CLOCK VS. OUTPUT</div>
          <div class="inspector-clock-compare">
            <span>Month Clock: <strong>Day ${vel.day_of_month}/${vel.total_days} (${vel.elapsed_pct}%)</strong></span>
            <span>Deliverables: <strong style="color: var(--accent-lavender);">${progressPercent}%</strong></span>
          </div>
        </div>
      </div>

      <div class="inspector-delivs-grid">
        ${itemsHtml || `<div style="font-size: 11px; color: var(--text-tertiary);">No deliverables defined for this milestone.</div>`}
      </div>

      ${this.renderStationSidequestsHtml(station)}

      <div class="inspector-rule-footer">
        Check off workout &amp; Deep Work blocks in <strong>Daily</strong> to log Core Floor progress; complete Sidequests when you have spare time or on Break Sprint (zero penalty if skipped).
      </div>
    `;

    panel.style.display = "block";
    document.querySelectorAll(".metro-grid-card").forEach((card) => {
      card.classList.toggle("selected-card", card.getAttribute("data-station-id") === station.id);
    });
    if (!skipScroll) {
      setTimeout(() => panel.scrollIntoView({ behavior: "smooth", block: "nearest" }), 40);
    }
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
    this.closeInspector();
    const drawer = document.getElementById("stationDrawer");
    if (!drawer) return;

    drawer.classList.remove("open");
  },

  renderStationSidequestsHtml(station) {
    const sqList = Array.isArray(station?.sidequests) ? station.sidequests : [];
    if (sqList.length === 0) return "";
    const completedSq = Array.isArray(station.completed_sidequests) ? station.completed_sidequests : [];
    const doneCount = sqList.filter((q) => completedSq.includes(q.id)).length;

    const cardsHtml = sqList.map((sq) => {
      const normKey = this.normalizeStreamKey(sq.stream || "code");
      const badgeColor = this.getStreamColor(normKey);
      const isDone = completedSq.includes(sq.id);
      return `
        <div class="sidequest-card ${isDone ? "is-done" : ""}" style="border-left: 2px solid ${badgeColor};">
          <div class="sidequest-card-top">
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span class="telemetry-stream-name" style="color: ${badgeColor};">${this.escapeHtml(sq.stream || "Bonus")}</span>
              <span class="mono-chip" style="font-size: 8.5px; padding: 1px 5px;">${this.escapeHtml(sq.xp_label || "OPTIONAL")}</span>
            </div>
            <button
              type="button"
              class="sidequest-toggle-btn ${isDone ? "done" : ""}"
              onclick="MetroMap.toggleSidequest('${this.escapeJs(station.id)}', '${this.escapeJs(sq.id)}')"
            >${isDone ? "Completed \u2713" : "Mark Done"}</button>
          </div>
          <div class="sidequest-title">${this.escapeHtml(sq.title)}</div>
          <div class="sidequest-detail">${this.escapeHtml(sq.detail || "")}</div>
        </div>
      `;
    }).join("");

    return `
      <div class="sidequests-section">
        <div class="sidequests-header">
          <span class="card-label" style="color: #34d399;">OPTIONAL SIDEQUESTS &bull; BONUS XP (ZERO PENALTY IF SKIPPED)</span>
          <span class="mono-chip green" style="font-size: 9px;">${doneCount}/${sqList.length} Cleared</span>
        </div>
        <div class="sidequests-grid">
          ${cardsHtml}
        </div>
      </div>
    `;
  },

  async toggleSidequest(stationId, sidequestId) {
    try {
      const st = this.data?.stations?.find((s) => s.id === stationId);
      if (!st) return;
      if (!Array.isArray(st.completed_sidequests)) st.completed_sidequests = [];

      const wasDone = st.completed_sidequests.includes(sidequestId);
      if (wasDone) {
        st.completed_sidequests = st.completed_sidequests.filter((id) => id !== sidequestId);
      } else {
        st.completed_sidequests.push(sidequestId);
      }
      this.saveState();

      if (window.pywebview?.api?.toggle_station_sidequest) {
        const res = await window.pywebview.api.toggle_station_sidequest(stationId, sidequestId);
        if (res && res.success && Array.isArray(res.completed_sidequests)) {
          st.completed_sidequests = res.completed_sidequests;
          this.saveState();
        }
      }

      this.render();
      if (this.selectedStation && this.selectedStation.id === stationId) {
        this.renderInspector(st, true);
      }
      if (window.HarnessApp?.showToast) {
        window.HarnessApp.showToast(wasDone ? "Sidequest reopened" : "Sidequest cleared! Bonus XP logged.");
      }
    } catch (err) {
      console.error("Failed to toggle sidequest:", err);
    }
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

  escapeJs(str) {
    if (!str) return "";
    return String(str)
      .replace(/\\/g, "\\\\")
      .replace(/'/g, "\\'")
      .replace(/"/g, '\\"')
      .replace(/\r|\n/g, " ");
  },
};

window.MetroMap = MetroMap;
