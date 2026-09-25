/**
 * Section 2: TUM METRO ROADMAP // 3-Zone Transit Trunk Canvas Architecture (Version 4.0)
 *
 * Architecture:
 * - Zone 1 (Top, Y=14-160): Phase boundary headers + Staggered Exam Signal Flags.
 *   Completely eliminates overlapping collisions with active stations and beacon.
 * - Zone 2 (Middle, Y=220): Main Central Subway Trunk Track (12px rail) + Parallel
 *   Bundled Color Stream Lines (Academics, Code, SIGG, German, Physical).
 *   Features circular station transfer nodes with pulsing radar halo for active station.
 * - Zone 3 (Bottom, Y=264-520): Uniform horizontal Station Card Deck connected by
 *   clean vertical dashed stems to track nodes.
 * - Interactive filter highlights specific stream lines while keeping full transit context.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  currentBeaconX: 0,

  // Stream Definitions for Parallel Subway Trunk System
  streams: [
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      strokeWidth: 2.5,
      yOffset: -16,
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      strokeWidth: 2.5,
      yOffset: -8,
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      strokeWidth: 3.0,
      yOffset: 0,
    },
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      strokeWidth: 2.5,
      yOffset: 8,
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      strokeWidth: 2.5,
      yOffset: 16,
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
      if (e.target.closest(".metro-station-card") || e.target.closest(".station-drawer") || e.target.closest("button") || e.target.closest(".metro-station-node")) return;
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
      if (!window.pywebview || !window.pywebview.api) return;
      this.data = await window.pywebview.api.get_metro_roadmap();
      if (window.pywebview.api.get_station_deliverables) {
        this.stationProgress = await window.pywebview.api.get_station_deliverables("sep-2026") || [];
      }
      if (window.pywebview.api.get_station_pace_velocity) {
        this.paceVelocity = await window.pywebview.api.get_station_pace_velocity("sep-2026") || null;
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

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 240;
    const startX = 160;
    const spineY = 220;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 320;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "560px";

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
      beaconTitle = "LAUNCH GATE // SEP 1, 2026";
      beaconSub = `${daysUntil}d to kickoff • Pure Syntax`;
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

    // Zone 1: Phase Milestones Headers (Top Zone)
    const phases = [
      { name: "Phase 1: Year 3 Liceum", startIdx: 0, endIdx: 6 },
      { name: "Phase 2: SIGG Finals & Year 3 Lock", startIdx: 7, endIdx: 10 },
      { name: "Phase 3: Summer Mass & B1", startIdx: 11, endIdx: 11 },
      { name: "Phase 4: Matura Crucible", startIdx: 12, endIdx: 19 },
      { name: "Phase 5: Official CKE & TUM", startIdx: 20, endIdx: 21 },
    ];

    let phaseHeadersHtml = phases
      .map((p) => {
        const x1 = startX + p.startIdx * spacing - 40;
        const x2 = startX + p.endIdx * spacing + 100;
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

    // Zone 2: Central Subway Trunk Track Bed
    const trunkHtml = `
      <!-- Trunk Bed -->
      <line x1="${startX - 40}" y1="${spineY}" x2="${startX + totalTrackLength + 40}" y2="${spineY}" 
            stroke="var(--border-subtle)" stroke-width="12" stroke-linecap="round" />
      <!-- Reached / Elapsed Trunk Rail -->
      ${
        currentX > startX
          ? `<line x1="${startX - 40}" y1="${spineY}" x2="${currentX}" y2="${spineY}" stroke="var(--border-medium)" stroke-width="12" stroke-linecap="round" />`
          : ""
      }
    `;

    // Zone 2: Parallel Stream Line Bundle
    let streamPathsHtml = "";
    let streamJunctionDotsHtml = "";

    this.streams.forEach((stream) => {
      const color = this.getStreamColor(stream.id);
      const activeIndices = [];
      stations.forEach((st, idx) => {
        if ((st.branches || []).includes(stream.id)) {
          activeIndices.push(idx);
        }
      });

      if (activeIndices.length === 0) return;

      const isFiltered = this.activeStreamFilter !== "all" && this.activeStreamFilter !== stream.id;
      const opacity = isFiltered ? 0.08 : this.activeStreamFilter === stream.id ? 1.0 : 0.75;
      const strokeW = this.activeStreamFilter === stream.id ? 4.5 : stream.strokeWidth;
      const y = spineY + stream.yOffset;

      const lineStartX = startX + activeIndices[0] * spacing - 24;
      const lineEndX = startX + activeIndices[activeIndices.length - 1] * spacing + 24;

      streamPathsHtml += `
        <!-- Stream Line: ${stream.name} -->
        <path 
          d="M ${lineStartX} ${y} L ${lineEndX} ${y}" 
          fill="none" 
          stroke="${color}" 
          stroke-width="${strokeW}" 
          stroke-linecap="round" 
          opacity="${opacity}" 
        />
      `;

      // Junction dots for stations where this stream is active
      activeIndices.forEach((idx) => {
        const px = startX + idx * spacing;
        streamJunctionDotsHtml += `
          <circle cx="${px}" cy="${y}" r="2.5" fill="${color}" opacity="${opacity}" />
        `;
      });
    });

    // Zone 2: Station Transfer Nodes & Stems
    let svgStationStemsHtml = "";
    let svgStationCirclesHtml = "";

    stations.forEach((station, idx) => {
      const posX = startX + idx * spacing;
      const isMajor = station.is_major;
      const status = station.status || "upcoming";
      const isPassed = posX <= currentX;
      const isActive = status === "active";
      const isCompleted = status === "completed" || (isPassed && !isPreLaunch);
      const cardTop = spineY + 44;

      // Vertical connecting stem from node down to station card
      const stemColor = isActive ? "var(--accent-lavender)" : "var(--border-subtle)";
      const stemWidth = isActive ? 2 : 1.5;
      const stemDash = isActive ? "none" : "3 3";
      svgStationStemsHtml += `
        <line x1="${posX}" y1="${spineY + 14}" x2="${posX}" y2="${cardTop}" 
              stroke="${stemColor}" stroke-width="${stemWidth}" stroke-dasharray="${stemDash}" />
      `;

      // Station Transfer Circle Node on Main Spine (posX, spineY)
      const size = isMajor ? 20 : 16;
      const r = size / 2;
      let fill = "var(--bg-card)";
      let stroke = "var(--border-medium)";
      let strokeW = 2;
      let innerCore = "";
      let aura = "";

      if (isCompleted) {
        fill = "var(--accent-lavender)";
        stroke = "#ffffff";
        strokeW = 2;
        innerCore = `<circle cx="${posX}" cy="${spineY}" r="3" fill="#ffffff" />`;
      } else if (isActive) {
        fill = "#ffffff";
        stroke = "var(--accent-lavender)";
        strokeW = 3;
        innerCore = `<circle cx="${posX}" cy="${spineY}" r="3.5" fill="var(--accent-lavender)" />`;
        aura = `
          <circle cx="${posX}" cy="${spineY}" r="22" fill="none" stroke="var(--accent-lavender)" stroke-width="1.5" opacity="0.4" class="beacon-pulse" />
        `;
      }

      svgStationCirclesHtml += `
        ${aura}
        <circle cx="${posX}" cy="${spineY}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" />
        ${innerCore}
        <!-- Click target overlay for station node -->
        <circle cx="${posX}" cy="${spineY}" r="16" fill="transparent" cursor="pointer" onclick="MetroMap.selectStation('${station.id}')" style="pointer-events: all;" />
      `;
    });

    // Zone 1: Upcoming School Test Milestone Pins & Signal Flags
    let svgSchoolTestDotsHtml = "";
    if (this.upcomingExams && this.upcomingExams.length > 0) {
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

            // Staggered Y elevation in Zone 1 (Top) so adjacent exams never collide!
            const flagY = spineY - 65 - (eIdx % 2) * 32;
            const subjName = exam.subject || "Exam";
            const flagText = `[EXAM] ${dueLabel} • ${subjName}`;
            const flagW = Math.max(96, flagText.length * 6.8 + 18);

            svgSchoolTestDotsHtml += `
              <!-- School Test Milestone Pin & Flag -->
              <g class="metro-test-dot" data-id="${exam.id}" data-subject="${this.escapeHtml(exam.subject)}" data-title="${this.escapeHtml(exam.title)}" data-date="${exam.exam_date}" data-due="${dueLabel}" data-scope="${this.escapeHtml(exam.scope || '')}" style="cursor: pointer; pointer-events: all;">
                <!-- Vertical schematic stem to flag -->
                <line x1="${testX}" y1="${spineY - 8}" x2="${testX}" y2="${flagY + 22}" stroke="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" stroke-width="1.5" stroke-dasharray="2 2" />
                
                <!-- Main Spine Milestone Pin -->
                <circle cx="${testX}" cy="${spineY}" r="${isTodayExam ? 7 : 5}" fill="none" stroke="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" stroke-width="1.5" opacity="0.8">
                  <animate attributeName="r" values="${isTodayExam ? '6;10;6' : '4;7;4'}" dur="2s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.8;0.2;0.8" dur="2s" repeatCount="indefinite"/>
                </circle>
                <circle cx="${testX}" cy="${spineY}" r="4" fill="var(--bg-card)" stroke="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" stroke-width="1.8" />
                <circle cx="${testX}" cy="${spineY}" r="2" fill="${isTodayExam ? '#ef4444' : 'var(--color-red)'}" />

                <!-- Floating Editorial Signal Flag -->
                <rect x="${testX - flagW / 2}" y="${flagY}" width="${flagW}" height="22" rx="4" 
                      fill="${isTodayExam ? 'rgba(239, 68, 68, 0.16)' : 'var(--bg-surface-elevated)'}" 
                      stroke="${isTodayExam ? '#ef4444' : 'var(--border-medium)'}" 
                      stroke-width="1.2" />
                <text x="${testX}" y="${flagY + 14}" font-family="var(--font-mono)" font-size="9.5" font-weight="700" text-anchor="middle" fill="${isTodayExam ? '#ef4444' : 'var(--text-primary)'}">
                  ${flagText}
                </text>

                <!-- Expanded Hit Target -->
                <rect x="${testX - flagW / 2 - 4}" y="${flagY - 4}" width="${flagW + 8}" height="50" fill="transparent" />
              </g>
            `;
          }
        } catch (err) {
          console.warn("[Metro] Error plotting test milestone:", err);
        }
      });
    }

    // Assemble SVG Layers
    let svgHtml = `
      <svg width="${totalWidth}" height="560" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 25;">
        <!-- Phase Vertical Grid Lines -->
        ${phases
          .map(
            (p) => {
              const px = startX + p.startIdx * spacing - 40;
              return `<line x1="${px}" y1="36" x2="${px}" y2="520" stroke="rgba(255,255,255,0.03)" stroke-dasharray="3 4" stroke-width="1" />`;
            }
          )
          .join("")}

        <!-- Vertical Station Stems -->
        ${svgStationStemsHtml}

        <!-- Central Subway Trunk Bed -->
        ${trunkHtml}

        <!-- Bundled Parallel Stream Lines -->
        ${streamPathsHtml}

        <!-- Stream Active Junction Dots -->
        ${streamJunctionDotsHtml}

        <!-- Station Circles on Main Spine -->
        ${svgStationCirclesHtml}

        <!-- School Test Milestone Pins & Flags -->
        ${svgSchoolTestDotsHtml}
      </svg>
    `;

    // Zone 3: Station Cards Deck (Uniform Horizontal Deck below track)
    let cardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const status = station.status || "upcoming";
        const branches = station.branches || [];
        const cardTop = spineY + 44;
        const cardLeft = posX - 100;

        let isFilteredMatch = true;
        if (this.activeStreamFilter !== "all") {
          isFilteredMatch = branches.includes(this.activeStreamFilter);
        }
        const opacityStyle = isFilteredMatch ? "opacity: 1;" : "opacity: 0.25;";

        const delivEntries = Object.keys(station.deliverables || {});
        const totalDelivs = delivEntries.length;
        const completedDelivs = (station.completed_deliverables || []).length;
        let checklistBadge = "";
        if (status === "completed") {
          checklistBadge = `<span class="mono-chip done" style="font-size: 8.5px; padding: 1px 5px;">DONE</span>`;
        } else if (status === "active") {
          checklistBadge = `<span class="mono-chip" style="font-size: 8.5px; padding: 1px 5px; color: var(--accent-lavender); border-color: var(--accent-lavender-border); font-weight: 700;">ACTIVE</span>`;
        } else if (totalDelivs > 0) {
          checklistBadge = `<span class="mono-chip" style="font-size: 8.5px; padding: 1px 5px;">${completedDelivs}/${totalDelivs}</span>`;
        }

        return `
          <!-- Station Card Centered at posX -->
          <div 
            class="metro-station-card ${status === "completed" ? "completed-card" : ""} ${status === "active" ? "active-card" : ""}" 
            style="left: ${cardLeft}px; top: ${cardTop}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-family: var(--font-mono); font-size: 9.5px; font-weight: 700; color: ${status === "active" ? "var(--accent-lavender)" : "var(--text-tertiary)"};">${station.month_label}</span>
              ${checklistBadge}
            </div>
            <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px;" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px;">
              ${branches
                .map((b) => {
                  const color = this.getStreamColor(b);
                  return `<span style="font-family: var(--font-mono); font-size: 8px; font-weight: 700; color: ${color}; background: ${color}15; border: 1px solid ${color}30; padding: 1px 4px; border-radius: 3px;">${b.toUpperCase()}</span>`;
                })
                .join("")}
            </div>
            <div style="font-size: 10.5px; color: var(--text-secondary); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 4px;">
              ${this.escapeHtml(station.objective || "")}
            </div>
            ${
              status === "active" && this.paceVelocity
                ? `
                  <div style="margin-top: 6px; padding-top: 5px; border-top: 1px solid var(--border-hairline); font-family: var(--font-mono); font-size: 8.5px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; ${this.paceVelocity.is_behind ? "color: #f59e0b;" : "color: var(--accent-lavender);"}">
                    <span style="display: flex; align-items: center; gap: 4px;">
                      <span class="beacon-dot ${this.paceVelocity.is_behind ? "pulse" : "optimal"}" style="width: 5px; height: 5px;"></span>
                      <span>${this.paceVelocity.status_text}</span>
                    </span>
                    <span style="opacity: 0.8;">Day ${this.paceVelocity.day_of_month}/${this.paceVelocity.total_days}</span>
                  </div>
                `
                : ""
            }
          </div>
        `;
      })
      .join("");

    // Real-Time Day Beacon (Above Spine, pointing down to track)
    const beaconTooltipHtml = `
      <div style="position: absolute; left: ${currentX}px; top: ${spineY - 26}px; transform: translate(-50%, -100%); pointer-events: none; z-index: 35;">
        <div style="display: flex; flex-direction: column; align-items: center;">
          <div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px; background: var(--accent-lavender); color: #ffffff; font-family: var(--font-mono); font-size: 9.5px; font-weight: 700; box-shadow: var(--shadow-dropdown); letter-spacing: 0.02em; white-space: nowrap;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;" class="beacon-pulse"></span>
            <span>${beaconTitle} • ${beaconSub}</span>
          </div>
          <div style="width: 2px; height: 12px; background: var(--accent-lavender);"></div>
          <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent-lavender); box-shadow: 0 0 8px var(--accent-lavender);"></div>
        </div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + svgHtml + cardsHtml + beaconTooltipHtml;
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

          // Find linked deliverable in stationProgress
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
