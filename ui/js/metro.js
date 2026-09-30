/**
 * Section 2: TUM METRO ROADMAP // Sleek Transit Trunk Architecture (Version 5.0)
 *
 * Architecture:
 * - Single Clean Progression Rail: One continuous, elegant rail with satisfying circular
 *   milestone station tokens.
 * - Dynamic 45° Tributary Rails: Stream tracks (Academics, Code, SIGG, German, Physical)
 *   are completely hidden from the track by default, appearing only as subtle colored
 *   micro-dots on each station. Selecting a stream filter or focusing a milestone station
 *   reveals smooth 45° tributary branches with chamfered connections.
 * - Station Hierarchy:
 *   - Active Station: Spotlight Hero Card with glowing visual emphasis, current focus,
 *     and interactive top deliverables.
 *   - Other Stations: Minimalist, airy milestone pills (Month + Title + Stream pips) with
 *     generous breathing room.
 * - Calm Today Beacon & Exam Radar: Eliminates the forest of tall red flags. Near the Today
 *   beacon, a consolidated radar pill reveals upcoming tests in a clean popover on hover.
 *   An optional toolbar toggle peeks at individual exam pins on demand.
 * - TUM '28 Golden Terminal: Celebratory destination gate milestone crowned at the horizon.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  focusedStationId: null,
  showAllExams: false,
  currentBeaconX: 0,
  stationProgress: [],
  paceVelocity: null,
  upcomingExams: [],

  // Stream Definitions for Transit Branches
  streams: [
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      color: "#a855f7",
      yOffset: -30,
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      color: "#38bdf8",
      yOffset: -16,
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      color: "#f59e0b",
      yOffset: 22,
    },
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      color: "#10b981",
      yOffset: -44,
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      color: "#f43f5e",
      yOffset: 36,
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
        e.target.closest(".metro-station-pill") ||
        e.target.closest(".metro-hero-card") ||
        e.target.closest(".metro-terminal-card") ||
        e.target.closest(".station-drawer") ||
        e.target.closest("button") ||
        e.target.closest(".metro-station-node") ||
        e.target.closest(".metro-exam-radar-pill")
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
    const filterBtns = document.querySelectorAll(".metro-filter-btn:not(#btnToggleExamPins)");
    filterBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        filterBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeStreamFilter = btn.getAttribute("data-stream") || "all";
        this.render();
      });
    });

    // Optional Exam Pins Toggle Button
    const toggleExamsBtn = document.getElementById("btnToggleExamPins");
    if (toggleExamsBtn) {
      toggleExamsBtn.addEventListener("click", () => {
        this.showAllExams = !this.showAllExams;
        toggleExamsBtn.classList.toggle("active", this.showAllExams);
        toggleExamsBtn.textContent = this.showAllExams ? "📌 Hide Exams" : "📌 Show Exams";
        this.render();
      });
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.data = await window.pywebview.api.get_metro_roadmap();
      if (window.pywebview.api.get_station_deliverables) {
        this.stationProgress = (await window.pywebview.api.get_station_deliverables("sep-2026")) || [];
      }
      if (window.pywebview.api.get_station_pace_velocity) {
        this.paceVelocity = (await window.pywebview.api.get_station_pace_velocity("sep-2026")) || null;
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

      if (!this.upcomingExams || this.upcomingExams.length === 0) {
        let cachedExams = null;
        try {
          const cachedStr = localStorage.getItem("harness_exams_v3");
          if (cachedStr) cachedExams = JSON.parse(cachedStr);
        } catch (e) {}

        if (Array.isArray(cachedExams) && cachedExams.length > 0) {
          this.upcomingExams = cachedExams.filter((e) => {
            const t = ((e.title || "") + " " + (e.scope || "")).toLowerCase();
            return !t.includes("trygonometria") && !t.includes("kinematyka") && !t.includes("wyszukiwania") && !t.includes("powstanie styczniowe");
          });
        }

        if (!this.upcomingExams || this.upcomingExams.length === 0) {
          this.upcomingExams = [
            {
              id: 7,
              subject: "Informatyka",
              title: "Sprawdzian: Podstawy programowania (C++)",
              exam_date: "2026-09-21",
              scope: "Podstawy programowania - pojęcia (algorytmy, cout, cin, instrukcja if)",
              completed: false,
            },
            {
              id: 5,
              subject: "Geografia",
              title: "Sprawdzian: Mapa fizyczna Polski",
              exam_date: "2026-10-02",
              scope: "Sprawdzian wiadomości - Mapa fizyczna Polski.",
              completed: false,
            },
            {
              id: 6,
              subject: "Język polski",
              title: "Sprawdzian: Rozprawka (romantyzm)",
              exam_date: "2026-10-06",
              scope: "Rozprawka (romantyzm) - wstęp, teza, argument, przykład, kontekst.",
              completed: false,
            },
          ];
        }
      }
      this.render();
      setTimeout(() => this.scrollToBeacon(), 200);
    } catch (err) {
      console.error("Error loading Metro Roadmap:", err);
    }
  },

  setFocusStation(stationId) {
    if (this.focusedStationId === stationId) return;
    this.focusedStationId = stationId;
    this.render();
  },

  showRadarPopover() {
    const pop = document.getElementById("metroRadarPopover");
    if (pop) pop.style.display = "block";
  },

  keepRadarPopover() {
    const pop = document.getElementById("metroRadarPopover");
    if (pop) pop.style.display = "block";
  },

  hideRadarPopover() {
    const pop = document.getElementById("metroRadarPopover");
    if (pop) pop.style.display = "none";
  },

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 260;
    const startX = 140;
    const spineY = 170;
    const totalTrackLength = (stations.length - 1) * spacing;
    const terminusX = startX + totalTrackLength + 140;
    const totalWidth = terminusX + 220;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "520px";

    // Date calculations
    const startDate = new Date(2026, 8, 1);
    const endDate = new Date(2028, 6, 31);
    const now = new Date();

    let currentX = startX;
    let beaconTitle = "";
    let beaconSub = "";
    let isPreLaunch = false;

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
      const progressRatio = elapsedMs / totalMs;
      const totalDays = Math.round(totalMs / (1000 * 60 * 60 * 24));
      const elapsedDays = Math.min(totalDays, Math.round(elapsedMs / (1000 * 60 * 60 * 24)));

      currentX = startX + progressRatio * totalTrackLength;
      const dateStr = now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      beaconTitle = `TODAY • DAY ${elapsedDays + 1} OF ${totalDays}`;
      beaconSub = dateStr;
    }

    this.currentBeaconX = currentX;

    // Zone 1: Phase Milestones Headers (Top Zone, Y=14)
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
          <div style="position: absolute; top: 14px; left: ${x1}px; width: ${width}px; pointer-events: none; z-index: 5;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: var(--font-mono); font-size: 9.5px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.06em; white-space: nowrap;">
                ${p.name}
              </span>
              <div style="flex: 1; height: 1px; background: var(--border-hairline);"></div>
            </div>
          </div>
        `;
      })
      .join("");

    // Zone 2: Single Clean Main Rail (6px stroke)
    const trunkHtml = `
      <!-- Base Main Rail -->
      <line x1="${startX - 30}" y1="${spineY}" x2="${terminusX}" y2="${spineY}" 
            stroke="var(--border-subtle)" stroke-width="6" stroke-linecap="round" />
      
      <!-- Completed / Progress Track up to Today -->
      ${
        currentX > startX - 30
          ? `<line x1="${startX - 30}" y1="${spineY}" x2="${Math.min(terminusX, currentX)}" y2="${spineY}" 
                  stroke="var(--accent-lavender)" stroke-width="6" stroke-linecap="round" />`
          : ""
      }
    `;

    // Zone 2: Dynamic 45° Tributary Rails
    // Only revealed when a stream filter is selected OR a station is hovered/focused
    const streamsToHighlight = new Set();
    if (this.activeStreamFilter !== "all") {
      streamsToHighlight.add(this.activeStreamFilter);
    }
    if (this.focusedStationId) {
      const fSt = stations.find((s) => s.id === this.focusedStationId);
      if (fSt && fSt.branches) {
        fSt.branches.forEach((b) => streamsToHighlight.add(b));
      }
    }

    let tributaryPathsHtml = "";
    if (streamsToHighlight.size > 0) {
      this.streams.forEach((stream) => {
        if (!streamsToHighlight.has(stream.id)) return;
        const color = this.getStreamColor(stream.id);
        const yOffset = stream.yOffset;
        const branchY = spineY + yOffset;
        const ramp = Math.abs(yOffset);

        // Find station indices where this stream is active
        const indices = [];
        stations.forEach((st, idx) => {
          if ((st.branches || []).includes(stream.id)) {
            indices.push(idx);
          }
        });
        if (indices.length === 0) return;

        // Group consecutive indices into segments
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
              <!-- 45° Chamfered Tributary Rail -->
              <path d="${pathD}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.9" />
          `;

          seg.forEach((idx) => {
            const px = startX + idx * spacing;
            tributaryPathsHtml += `
              <!-- Drop connector stem -->
              <line x1="${px}" y1="${branchY}" x2="${px}" y2="${spineY}" stroke="${color}" stroke-width="1.5" stroke-dasharray="2 3" opacity="0.6" />
              <!-- Junction dot on tributary rail -->
              <circle cx="${px}" cy="${branchY}" r="3.5" fill="${color}" stroke="var(--bg-canvas)" stroke-width="1.5" />
            `;
          });

          tributaryPathsHtml += `</g>`;
        });
      });
    }

    // Zone 2: Milestone Station Tokens & Stream Micro-Pips
    let stationsSvgHtml = "";
    stations.forEach((station, idx) => {
      const posX = startX + idx * spacing;
      const status = station.status || "upcoming";
      const isMajor = station.is_major;
      const isPassed = posX <= currentX;
      const isActive = status === "active";
      const isCompleted = status === "completed" || (isPassed && !isPreLaunch);
      const isHovered = this.focusedStationId === station.id;

      // Node circles
      let aura = "";
      let nodeCircles = "";
      if (isActive) {
        aura = `
          <circle cx="${posX}" cy="${spineY}" r="22" fill="none" stroke="var(--accent-lavender)" stroke-width="2" opacity="0.4" class="beacon-pulse" />
        `;
        nodeCircles = `
          <circle cx="${posX}" cy="${spineY}" r="11" fill="var(--bg-canvas)" stroke="var(--accent-lavender)" stroke-width="3.5" />
          <circle cx="${posX}" cy="${spineY}" r="4.5" fill="var(--accent-lavender)" />
        `;
      } else if (isCompleted) {
        nodeCircles = `
          <circle cx="${posX}" cy="${spineY}" r="9" fill="var(--accent-lavender)" stroke="var(--bg-canvas)" stroke-width="2" />
          <polyline points="${posX - 3},${spineY} ${posX - 1},${spineY + 2} ${posX + 3},${spineY - 2}" fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        `;
      } else {
        const r = isMajor ? 10 : 8;
        const strokeW = isMajor ? 2.5 : 2;
        const strokeColor = isHovered ? "var(--accent-lavender)" : "var(--border-medium)";
        nodeCircles = `
          <circle cx="${posX}" cy="${spineY}" r="${r}" fill="var(--bg-surface)" stroke="${strokeColor}" stroke-width="${strokeW}" />
        `;
      }

      // Stream Micro-Pips (Colored indicator dots beneath the station token)
      const branches = station.branches || [];
      const pipSpacing = 7;
      const pipsStartX = posX - ((branches.length - 1) * pipSpacing) / 2;
      let pipsSvg = "";
      branches.forEach((b, pIdx) => {
        const c = this.getStreamColor(b);
        pipsSvg += `<circle cx="${pipsStartX + pIdx * pipSpacing}" cy="${spineY + 16}" r="2.2" fill="${c}" />`;
      });

      // Connecting stem down to card/pill
      const stemColor = isActive || isHovered ? "var(--accent-lavender)" : "var(--border-hairline)";
      const stemWidth = isActive ? 1.5 : 1;
      const cardTop = isActive ? spineY + 36 : spineY + 44;
      const stemSvg = `
        <line x1="${posX}" y1="${spineY + 20}" x2="${posX}" y2="${cardTop}" stroke="${stemColor}" stroke-width="${stemWidth}" stroke-dasharray="2 3" opacity="${isActive || isHovered ? 0.8 : 0.4}" />
      `;

      stationsSvgHtml += `
        ${aura}
        ${stemSvg}
        ${nodeCircles}
        ${pipsSvg}
        <!-- Click & Hover Target -->
        <circle cx="${posX}" cy="${spineY}" r="18" fill="transparent" cursor="pointer"
                onclick="MetroMap.selectStation('${station.id}')"
                onmouseenter="MetroMap.setFocusStation('${station.id}')"
                onmouseleave="MetroMap.setFocusStation(null)"
                style="pointer-events: all;" />
      `;
    });

    // Zone 2: TUM '28 Golden Terminal Milestone Node
    const terminalSvgHtml = `
      <!-- TUM '28 Golden Terminal Milestone -->
      <g style="pointer-events: all; cursor: pointer;" onclick="MetroMap.scrollToBeacon()">
        <circle cx="${terminusX}" cy="${spineY}" r="22" fill="none" stroke="#f59e0b" stroke-width="2" opacity="0.35" class="beacon-pulse" />
        <circle cx="${terminusX}" cy="${spineY}" r="12" fill="var(--bg-canvas)" stroke="#f59e0b" stroke-width="3" />
        <circle cx="${terminusX}" cy="${spineY}" r="5" fill="#f59e0b" />
      </g>
    `;

    // Optional Individual Exam Pins (Only visible if showAllExams is toggled ON)
    let examsSvgHtml = "";
    if (this.showAllExams && this.upcomingExams && this.upcomingExams.length > 0) {
      const sortedExams = [...this.upcomingExams].sort((a, b) => new Date(a.exam_date) - new Date(b.exam_date));
      sortedExams.forEach((exam, eIdx) => {
        try {
          const exDate = new Date(exam.exam_date + "T12:00:00");
          if (exDate >= startDate && exDate <= endDate) {
            const elapsed = exDate.getTime() - startDate.getTime();
            const totalMs = endDate.getTime() - startDate.getTime();
            const ratio = elapsed / totalMs;
            const testX = startX + ratio * totalTrackLength;
            const todayMid = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
            const examMid = new Date(exDate.getFullYear(), exDate.getMonth(), exDate.getDate()).getTime();
            const diffDays = Math.round((examMid - todayMid) / (1000 * 60 * 60 * 24));
            const dueLabel = diffDays === 0 ? "TODAY" : diffDays === 1 ? "TMRW" : diffDays > 0 ? `in ${diffDays}d` : `${Math.abs(diffDays)}d ago`;
            const isTodayExam = diffDays === 0;

            const flagY = spineY - 55 - (eIdx % 2) * 28;
            const subjName = exam.subject || "Exam";
            const flagText = `[EXAM] ${dueLabel} • ${subjName}`;
            const flagW = Math.max(90, flagText.length * 6.6 + 16);

            examsSvgHtml += `
              <g class="metro-test-dot" data-id="${exam.id}" data-subject="${this.escapeHtml(exam.subject)}" data-title="${this.escapeHtml(exam.title)}" data-date="${exam.exam_date}" data-due="${dueLabel}" data-scope="${this.escapeHtml(exam.scope || '')}" style="cursor: pointer; pointer-events: all;">
                <line x1="${testX}" y1="${spineY - 8}" x2="${testX}" y2="${flagY + 20}" stroke="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" stroke-width="1.5" stroke-dasharray="2 2" />
                <circle cx="${testX}" cy="${spineY}" r="4" fill="var(--bg-card)" stroke="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" stroke-width="1.8" />
                <circle cx="${testX}" cy="${spineY}" r="2" fill="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" />
                <rect x="${testX - flagW / 2}" y="${flagY}" width="${flagW}" height="20" rx="4" 
                      fill="${isTodayExam ? 'rgba(239, 68, 68, 0.16)' : 'var(--bg-surface-elevated)'}" 
                      stroke="${isTodayExam ? '#ef4444' : 'var(--border-medium)'}" 
                      stroke-width="1.2" />
                <text x="${testX}" y="${flagY + 13}" font-family="var(--font-mono)" font-size="9" font-weight="700" text-anchor="middle" fill="${isTodayExam ? '#ef4444' : 'var(--text-primary)'}">
                  ${flagText}
                </text>
              </g>
            `;
          }
        } catch (err) {}
      });
    }

    // Assemble SVG Layers
    const svgHtml = `
      <svg width="${totalWidth}" height="520" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 25;">
        <!-- Phase Separation Vertical Guidelines -->
        ${phases
          .map((p) => {
            const px = startX + p.startIdx * spacing - 30;
            return `<line x1="${px}" y1="36" x2="${px}" y2="480" stroke="rgba(255,255,255,0.03)" stroke-dasharray="3 4" stroke-width="1" />`;
          })
          .join("")}

        <!-- Single Main Progression Rail -->
        ${trunkHtml}

        <!-- Dynamic 45° Tributary Rails -->
        ${tributaryPathsHtml}

        <!-- Station Tokens along Spine -->
        ${stationsSvgHtml}

        <!-- TUM '28 Golden Terminal -->
        ${terminalSvgHtml}

        <!-- Optional Full Exam Pins Layer -->
        ${examsSvgHtml}
      </svg>
    `;

    // Zone 3: Cards Deck (Active Hero Card vs Minimalist Milestone Pills)
    let cardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const status = station.status || "upcoming";
        const branches = station.branches || [];
        const isFilteredMatch = this.activeStreamFilter === "all" || branches.includes(this.activeStreamFilter);
        const opacityStyle = isFilteredMatch ? "opacity: 1;" : "opacity: 0.25;";

        const delivEntries = Object.entries(station.deliverables || {});
        const completedList = station.completed_deliverables || [];

        // 1. ACTIVE STATION: Spotlight Hero Card
        if (status === "active") {
          const heroLeft = posX - 130;
          const heroTop = spineY + 36;

          let heroDelivsHtml = "";
          if (delivEntries.length > 0) {
            heroDelivsHtml = `
              <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-hairline);">
                ${delivEntries.slice(0, 3).map(([key, val]) => {
                  const isChecked = completedList.includes(key);
                  return `
                    <div 
                      style="display: flex; align-items: flex-start; gap: 6px; font-size: 10px; color: ${isChecked ? 'var(--text-muted)' : 'var(--text-secondary)'}; cursor: pointer;"
                      onclick="event.stopPropagation(); MetroMap.toggleDeliverable('${station.id}', '${this.escapeHtml(key)}')"
                      title="Click to toggle deliverable"
                    >
                      <span style="color: ${isChecked ? '#10b981' : 'var(--text-tertiary)'}; font-size: 11px; line-height: 1;">${isChecked ? '✓' : '○'}</span>
                      <span style="line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 215px; ${isChecked ? 'text-decoration: line-through;' : ''}">${this.escapeHtml(val)}</span>
                    </div>
                  `;
                }).join("")}
              </div>
            `;
          }

          let heroNextAction = "";
          if (station.next_action) {
            heroNextAction = `
              <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--border-hairline); font-size: 9.5px; font-family: var(--font-mono); color: var(--accent-lavender); display: flex; align-items: center; gap: 4px;">
                <span>&rarr;</span>
                <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600;">${this.escapeHtml(station.next_action)}</span>
              </div>
            `;
          }

          return `
            <div 
              class="metro-hero-card"
              style="left: ${heroLeft}px; top: ${heroTop}px; ${opacityStyle}"
              onclick="MetroMap.selectStation('${station.id}')"
              onmouseenter="MetroMap.setFocusStation('${station.id}')"
              onmouseleave="MetroMap.setFocusStation(null)"
            >
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-family: var(--font-mono); font-size: 8.5px; font-weight: 800; color: var(--accent-lavender); letter-spacing: 0.05em; text-transform: uppercase;">
                  CURRENT FOCUS // ${station.month_label}
                </span>
                <span class="mono-chip" style="font-size: 8px; padding: 1px 5px; color: var(--accent-lavender); border-color: var(--accent-lavender-border); font-weight: 700;">
                  ACTIVE
                </span>
              </div>
              <div style="font-size: 14px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">
                ${this.escapeHtml(station.name)}
              </div>
              <div style="font-size: 10.5px; color: var(--text-secondary); line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                ${this.escapeHtml(station.objective || "")}
              </div>
              ${heroDelivsHtml}
              ${heroNextAction}
              <div style="margin-top: 8px; display: flex; justify-content: flex-end;">
                <span style="font-family: var(--font-mono); font-size: 8.5px; color: var(--text-tertiary); font-weight: 600;">Inspect Milestone &rarr;</span>
              </div>
            </div>
          `;
        }

        // 2. OTHER STATIONS: Minimalist Milestone Pill
        const pillLeft = posX - 70;
        const pillTop = spineY + 44;

        const pipsRow = branches
          .map((b) => {
            const color = this.getStreamColor(b);
            return `<span class="stream-pip-dot" style="background: ${color};" title="${b.toUpperCase()}"></span>`;
          })
          .join("");

        let statusChip = "";
        if (status === "completed") {
          statusChip = `<span class="mono-chip done" style="font-size: 8px; padding: 1px 4px;">DONE</span>`;
        } else if (delivEntries.length > 0) {
          statusChip = `<span class="mono-chip" style="font-size: 8px; padding: 1px 4px;">${completedList.length}/${delivEntries.length}</span>`;
        }

        return `
          <div 
            class="metro-station-pill ${status === "completed" ? "completed-pill" : ""}" 
            style="left: ${pillLeft}px; top: ${pillTop}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
            onmouseenter="MetroMap.setFocusStation('${station.id}')"
            onmouseleave="MetroMap.setFocusStation(null)"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
              <span style="font-family: var(--font-mono); font-size: 8.5px; font-weight: 700; color: var(--text-tertiary);">${station.month_label}</span>
              ${statusChip}
            </div>
            <div style="font-size: 11.5px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div style="display: flex; align-items: center; gap: 3.5px;">
              ${pipsRow}
            </div>
          </div>
        `;
      })
      .join("");

    // TUM '28 Golden Terminal Card
    const terminalCardHtml = `
      <div 
        class="metro-terminal-card" 
        style="left: ${terminusX - 88}px; top: ${spineY + 40}px;"
        onclick="HarnessApp.switchView('study')"
        title="Destination: TUM Campus Heilbronn"
      >
        <div style="font-family: var(--font-mono); font-size: 8.5px; font-weight: 800; color: #f59e0b; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2px;">
          ★ DESTINATION GATE ★
        </div>
        <div style="font-size: 13px; font-weight: 800; color: var(--text-primary); margin-bottom: 2px;">
          TUM ’28
        </div>
        <div style="font-size: 9.5px; color: var(--text-secondary); line-height: 1.3;">
          B.Sc. Management &amp; Data Science
        </div>
        <div style="margin-top: 5px; font-family: var(--font-mono); font-size: 8.5px; font-weight: 700; color: #f59e0b;">
          Aptitude Target: &ge; 88 pts
        </div>
      </div>
    `;

    // Today Beacon & Consolidated Next Exam Radar Pill
    let nextExamRadarHtml = "";
    if (this.upcomingExams && this.upcomingExams.length > 0) {
      const sortedExams = [...this.upcomingExams]
        .filter((e) => !e.completed)
        .sort((a, b) => new Date(a.exam_date) - new Date(b.exam_date));

      const todayMid = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const upcomingValid = sortedExams.filter((e) => {
        const eMid = new Date(e.exam_date + "T12:00:00").getTime();
        return eMid - todayMid >= 0;
      });

      if (upcomingValid.length > 0) {
        const nextEx = upcomingValid[0];
        const exDate = new Date(nextEx.exam_date + "T12:00:00");
        const diffDays = Math.round((exDate.getTime() - todayMid) / (1000 * 60 * 60 * 24));
        const dueLabel = diffDays === 0 ? "TODAY" : diffDays === 1 ? "TMRW" : `in ${diffDays}d`;

        const popoverItems = upcomingValid.slice(0, 3).map((e) => {
          const ed = new Date(e.exam_date + "T12:00:00");
          const dDays = Math.round((ed.getTime() - todayMid) / (1000 * 60 * 60 * 24));
          const dLbl = dDays === 0 ? "TODAY" : dDays === 1 ? "TMRW" : `in ${dDays}d`;
          return `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid var(--border-hairline);">
              <div style="max-width: 190px;">
                <div style="font-weight: 700; font-size: 10.5px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(e.subject)}: ${this.escapeHtml(e.title)}</div>
                <div style="font-size: 8.5px; color: var(--text-tertiary);">${e.exam_date}</div>
              </div>
              <span class="key-pill" style="font-size: 8.5px; padding: 1px 5px; flex-shrink: 0; margin-left: 8px;">${dLbl}</span>
            </div>
          `;
        }).join("");

        nextExamRadarHtml = `
          <div style="position: absolute; left: ${currentX + 90}px; top: ${spineY - 30}px; transform: translateY(-50%); z-index: 36;">
            <div class="metro-exam-radar-pill" id="metroRadarPill" onmouseenter="MetroMap.showRadarPopover()" onmouseleave="MetroMap.hideRadarPopover()">
              <span>⚡</span>
              <span>Next: ${this.escapeHtml(nextEx.subject)}</span>
              <span style="opacity: 0.85; font-weight: 600;">(${dueLabel})</span>
            </div>
            <div id="metroRadarPopover" class="metro-exam-popover" onmouseenter="MetroMap.keepRadarPopover()" onmouseleave="MetroMap.hideRadarPopover()">
              <div style="font-family: var(--font-mono); font-size: 8.5px; font-weight: 800; color: #ef4444; margin-bottom: 6px; letter-spacing: 0.05em; text-transform: uppercase;">
                UPCOMING SCHOOL TESTS
              </div>
              ${popoverItems}
              <div style="margin-top: 8px; text-align: right;">
                <button class="btn-ghost-icon" style="font-size: 9px; padding: 2px 6px;" onclick="HarnessApp.switchView('study')">View Study Ledger &rarr;</button>
              </div>
            </div>
          </div>
        `;
      }
    }

    // Real-Time Day Beacon (Above Spine, pointing down to track)
    const beaconTooltipHtml = `
      <div style="position: absolute; left: ${currentX}px; top: ${spineY - 22}px; transform: translate(-50%, -100%); pointer-events: none; z-index: 35;">
        <div style="display: flex; flex-direction: column; align-items: center;">
          <div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px; background: var(--accent-lavender); color: #ffffff; font-family: var(--font-mono); font-size: 9.5px; font-weight: 700; box-shadow: var(--shadow-dropdown); letter-spacing: 0.02em; white-space: nowrap;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;" class="beacon-pulse"></span>
            <span>${beaconTitle} • ${beaconSub}</span>
          </div>
          <div style="width: 2px; height: 10px; background: var(--accent-lavender);"></div>
          <div style="width: 5px; height: 5px; border-radius: 50%; background: var(--accent-lavender); box-shadow: 0 0 8px var(--accent-lavender);"></div>
        </div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + svgHtml + cardsHtml + terminalCardHtml + beaconTooltipHtml + nextExamRadarHtml;
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

    document.querySelectorAll(".metro-test-dot").forEach((dot) => {
      dot.addEventListener("mouseenter", (e) => {
        const subj = dot.getAttribute("data-subject");
        const title = dot.getAttribute("data-title");
        const dateStr = dot.getAttribute("data-date");
        const due = dot.getAttribute("data-due");
        const scope = dot.getAttribute("data-scope");

        let content = `
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
    document.getElementById("drawerStationStatus").value = station.status || "upcoming";

    // Deliverables breakdown categorized by stream
    const deliverablesList = document.getElementById("drawerDeliverablesList");
    if (deliverablesList && station.deliverables) {
      const allEntries = Object.entries(station.deliverables);
      const totalDelivs = allEntries.length;
      const completedList = station.completed_deliverables || [];
      const completedCount = completedList.length;
      const progressPercent = totalDelivs > 0 ? Math.round((completedCount / totalDelivs) * 100) : 0;
      const isAllComplete = totalDelivs > 0 && completedCount >= totalDelivs;

      let velocityHeader = "";
      if (this.paceVelocity && station.status === "active") {
        const isBehind = this.paceVelocity.is_behind;
        velocityHeader = `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; margin-bottom: 8px; border-radius: 4px; font-family: var(--font-mono); font-size: 10px; ${isBehind ? "background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #f59e0b;" : "background: rgba(161, 161, 170, 0.08); border: 1px solid rgba(161, 161, 170, 0.2); color: #a1a1aa;"}">
            <div style="display: flex; align-items: center; gap: 5px;">
              <span class="beacon-dot ${isBehind ? "pulse" : "optimal"}" style="width: 6px; height: 6px;"></span>
              <span style="font-weight: 700;">${this.paceVelocity.status_text}</span>
            </div>
            <span style="opacity: 0.8;">Day ${this.paceVelocity.day_of_month}/${this.paceVelocity.total_days}</span>
          </div>
        `;
      }

      const progressHeader = `
        ${velocityHeader}
        <div style="background: var(--bg-card); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 10px; font-family: var(--font-mono);">
            <span style="color: var(--text-tertiary);">DELIVERABLES (${completedCount}/${totalDelivs})</span>
            <span style="color: var(--accent-lavender); font-weight: 700;">${isAllComplete ? "DONE" : `${progressPercent}%`}</span>
          </div>
          <div class="progress-bar-track" style="margin: 0; height: 2px;">
            <div class="progress-bar-fill" style="width: ${progressPercent}%;"></div>
          </div>
        </div>
      `;

      const itemsHtml = allEntries
        .map(([key, val]) => {
          const streamMatch = this.streams.find((s) => s.name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(s.id));
          const lineBadgeColor = streamMatch ? streamMatch.color : "var(--accent-lavender)";

          const pMatch = (this.stationProgress || []).find(
            (p) => p.stream.toLowerCase() === key.toLowerCase() || (streamMatch && p.stream.toLowerCase() === streamMatch.id)
          );

          const isChecked = completedList.includes(key) || (pMatch && pMatch.is_completed);

          let counterPill = "";
          let stepperControls = "";

          if (pMatch) {
            const delivId = pMatch.deliverable_id;
            const curCount = pMatch.completed_count;
            const totalReq = pMatch.total_required;
            const unitLabel = pMatch.unit_label;

            counterPill = `<span style="font-family: var(--font-mono); font-size: 9px; color: var(--accent-lavender); font-weight: 700; margin-left: 6px; background: rgba(196, 181, 253, 0.08); padding: 1px 5px; border-radius: 2px;">[${curCount} / ${totalReq} ${unitLabel}]</span>`;

            let quickStepBtn = "";
            if (pMatch.stream === "german") {
              quickStepBtn = `<button type="button" class="deliv-stepper-btn" style="width: auto; padding: 0 6px; font-size: 10px;" onclick="event.stopPropagation(); MetroMap.stepDeliverable('${delivId}', 20)">+20 Words</button>`;
            } else if (pMatch.stream === "code") {
              quickStepBtn = `<button type="button" class="deliv-stepper-btn" style="width: auto; padding: 0 6px; font-size: 10px;" onclick="event.stopPropagation(); MetroMap.stepDeliverable('${delivId}', 1)">+1 Prob</button>`;
            } else if (pMatch.stream === "academics") {
              quickStepBtn = `<button type="button" class="deliv-stepper-btn" style="width: auto; padding: 0 6px; font-size: 10px;" onclick="event.stopPropagation(); MetroMap.stepDeliverable('${delivId}', 5)">+5 Probs</button>`;
            }

            stepperControls = `
              <div class="deliv-stepper" onclick="event.stopPropagation();" style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed rgba(255, 255, 255, 0.08);">
                <button type="button" class="deliv-stepper-btn" onclick="MetroMap.stepDeliverable('${delivId}', -1)" title="Decrement">&minus;</button>
                <input 
                  type="number" 
                  class="deliv-input-count" 
                  value="${curCount}" 
                  min="0" 
                  max="${totalReq}" 
                  onchange="MetroMap.setDeliverableProgress('${delivId}', this.value)" 
                  title="Direct rep count"
                />
                <button type="button" class="deliv-stepper-btn" onclick="MetroMap.stepDeliverable('${delivId}', 1)" title="Increment">+</button>
                ${quickStepBtn}
                <span style="color: var(--text-tertiary); font-size: 10px; font-family: var(--font-mono); margin-left: 2px;">/ ${totalReq} ${unitLabel}</span>
              </div>
            `;
          }

          return `
            <div 
              class="deliverable-item ${isChecked ? "checked" : ""}" 
              onclick="MetroMap.toggleDeliverable('${station.id}', '${this.escapeHtml(key)}')"
              title="Click to toggle deliverable completion"
            >
              <div class="check-dot ${isChecked ? "checked" : ""}" style="margin-top: 2px;"></div>
              <div style="flex: 1; min-width: 0;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                  <span style="font-family: var(--font-mono); font-size: 8px; font-weight: 700; text-transform: uppercase; color: ${lineBadgeColor};">
                    ${key} STREAM
                  </span>
                  ${counterPill}
                </div>
                <div class="deliverable-desc" style="font-size: 11px; color: var(--text-primary); line-height: 1.4;">
                  ${this.escapeHtml(val)}
                </div>
                ${stepperControls}
              </div>
            </div>
          `;
        })
        .join("");

      deliverablesList.innerHTML = progressHeader + itemsHtml;
    }

    drawer.classList.add("open");
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
      if (!window.pywebview || !window.pywebview.api) return;
      const res = await window.pywebview.api.toggle_station_deliverable(stationId, deliverableKey);
      if (res && res.success) {
        const st = this.data.stations.find((s) => s.id === stationId);
        if (st) {
          st.completed_deliverables = res.completed_deliverables;
          st.status = res.station_status;
          this.selectedStation = st;
        }

        this.render();
        if (this.selectedStation && this.selectedStation.id === stationId) {
          this.openDrawer(this.selectedStation);
        }

        if (res.station_completed) {
          window.HarnessApp.showToast(`Station Completed: ${st.name}!`);
        } else if (res.is_checked) {
          window.HarnessApp.showToast(`Checked: ${deliverableKey}`);
        }
        if (window.Dashboard) window.Dashboard.load();
      }
    } catch (err) {
      console.error("Error toggling deliverable:", err);
    }
  },

  async updateStatus(stationId, newStatus) {
    try {
      await window.pywebview.api.update_station_status(stationId, newStatus);
      const st = this.data.stations.find((s) => s.id === stationId);
      if (st) st.status = newStatus;
      this.render();
      window.HarnessApp.showToast(`Station status updated to ${newStatus}`);
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error updating station status:", err);
    }
  },

  scrollToBeacon() {
    const container = document.getElementById("metroScrollContainer");
    if (container && this.currentBeaconX) {
      const targetScroll = Math.max(0, this.currentBeaconX - container.clientWidth / 2);
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
