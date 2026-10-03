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
              id: 13,
              subject: "Chemia",
              title: "Sprawdzian: Budowa atomu i wiązania",
              exam_date: "2026-09-29",
              scope: "Konfiguracje elektronowe, liczby kwantowe, typy wiązań.",
              completed: false,
            },
            {
              id: 16,
              subject: "Fizyka",
              title: "Kartkówka: Ruch jednostajny i przyspieszony",
              exam_date: "2026-10-01",
              scope: "Wykresy v(t), s(t), wzory na przyspieszenie.",
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
              id: 15,
              subject: "Fizyka",
              title: "Sprawdzian: Kinematyka",
              exam_date: "2026-10-05",
              scope: "Rzuty pionowe, poziome i ukośne.",
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
            {
              id: 14,
              subject: "Matematyka",
              title: "Sprawdzian: Funkcja kwadratowa",
              exam_date: "2026-10-07",
              scope: "Postać ogólna, kanoniczna, iloczynowa, nierówności kwadratowe.",
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

    // Dynamic Multi-Tier Staggered School Exams on Track
    let examsSvgHtml = "";
    if (this.upcomingExams && this.upcomingExams.length > 0) {
      const todayMid = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();

      const validExams = [];
      this.upcomingExams
        .filter((e) => !e.completed)
        .forEach((exam) => {
          try {
            const exDate = new Date(exam.exam_date + "T12:00:00");
            if (exDate >= startDate && exDate <= endDate) {
              const elapsed = exDate.getTime() - startDate.getTime();
              const totalMs = endDate.getTime() - startDate.getTime();
              const ratio = elapsed / totalMs;
              const testX = startX + ratio * totalTrackLength;
              const diffDays = Math.round((exDate.getTime() - todayMid) / (1000 * 60 * 60 * 24));
              const dueLabel = diffDays === 0 ? "TODAY" : diffDays === 1 ? "1d" : diffDays > 0 ? `${diffDays}d` : `${Math.abs(diffDays)}d ago`;
              validExams.push({
                ...exam,
                testX,
                diffDays,
                dueLabel,
              });
            }
          } catch (e) {}
        });

      // Sort by horizontal position
      validExams.sort((a, b) => a.testX - b.testX);

      // Multi-tier heights to avoid collision with Today's indicator:
      // Tier 0: 22px (low tick beneath Today's text)
      // Tier 1: 52px (standard tick, used when far from Today's text)
      // Tier 2: 78px (high tick towering above Today's text)
      // Tier 3: 98px (extra high tick for dense exam clusters)
      const tierHeights = [22, 52, 78, 98];
      const assignedTiers = [];

      validExams.forEach((ex, idx) => {
        const collidingTiers = new Set();
        // The Today indicator label sits between spineY - 42 and spineY - 58.
        // Any exam within 72px horizontally must avoid Tier 1 (52px).
        const isNearToday = Math.abs(ex.testX - currentX) < 72;
        if (isNearToday) {
          collidingTiers.add(1);
        }
        for (let j = 0; j < idx; j++) {
          const prev = validExams[j];
          if (Math.abs(ex.testX - prev.testX) < 75) {
            collidingTiers.add(assignedTiers[j]);
          }
        }
        let chosenTier = 0;
        if (isNearToday && !collidingTiers.has(2)) {
          chosenTier = 2; // Elevate above Today's indicator text
        } else {
          while (collidingTiers.has(chosenTier) && chosenTier < 3) {
            chosenTier++;
          }
        }
        assignedTiers.push(chosenTier);
        ex.tier = chosenTier;
        ex.tickHeight = tierHeights[chosenTier];
      });

      validExams.forEach((exam) => {
        const testX = exam.testX;
        const tickTopY = spineY - exam.tickHeight;
        const isUrgent = exam.diffDays >= 0 && exam.diffDays <= 2;
        const lineColor = isUrgent ? "#ef4444" : "var(--text-tertiary)";
        const textColor = isUrgent ? "#ef4444" : "var(--text-primary)";
        const labelText = `[${exam.dueLabel}] ${exam.subject}`;

        examsSvgHtml += `
          <g class="metro-test-tick" data-id="${exam.id}" data-subject="${this.escapeHtml(exam.subject)}" data-title="${this.escapeHtml(exam.title)}" data-date="${exam.exam_date}" data-due="${exam.dueLabel}" data-scope="${this.escapeHtml(exam.scope || '')}" style="cursor: pointer; pointer-events: all;">
            <!-- Pin dot on track -->
            <circle cx="${testX}" cy="${spineY}" r="3" fill="${isUrgent ? '#ef4444' : 'var(--text-secondary)'}" stroke="var(--bg-card)" stroke-width="1.5" />
            <!-- Vertical leader line -->
            <line x1="${testX}" y1="${spineY - 4}" x2="${testX}" y2="${tickTopY + 2}" stroke="${lineColor}" stroke-width="1.2" stroke-dasharray="${isUrgent ? 'none' : '2 2'}" opacity="0.8" />
            <!-- Small top notch pip -->
            <circle cx="${testX}" cy="${tickTopY + 2}" r="1.5" fill="${lineColor}" />
            <!-- Clean minimalist text label -->
            <text x="${testX}" y="${tickTopY - 3}" font-family="var(--font-mono)" font-size="9" font-weight="${isUrgent ? '700' : '600'}" text-anchor="middle" fill="${textColor}">
              ${this.escapeHtml(labelText)}
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
      const isPassed = posX <= currentX;
      const isActive = status === "active";
      const isCompleted = status === "completed" || (isPassed && !isPreLaunch);
      const branches = station.branches || [];

      let nodeCircles = "";
      let labelSubText = station.month_label;
      let labelSubColor = "var(--text-tertiary)";

      if (isActive) {
        labelSubText = "Active 'TUM' station";
        labelSubColor = "var(--accent-lavender)";
        nodeCircles = `
          <!-- Concentric Blue Rings for Active TUM Station (Matching Mockup) -->
          <circle cx="${posX}" cy="${spineY}" r="20" fill="none" stroke="var(--accent-lavender)" stroke-width="1.5" opacity="0.3" class="beacon-pulse" />
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--accent-lavender)" data-orig-width="2.5" cx="${posX}" cy="${spineY}" r="13" fill="none" stroke="var(--accent-lavender)" stroke-width="2.5" />
          <circle cx="${posX}" cy="${spineY}" r="9" fill="var(--bg-card)" />
          <circle cx="${posX}" cy="${spineY}" r="5.5" fill="var(--accent-lavender)" />
        `;
      } else if (isCompleted) {
        labelSubText = "Completed";
        nodeCircles = `
          <!-- Solid Dark Circle with White Checkmark (Matching Mockup) -->
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--bg-card)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--text-primary)" stroke="var(--bg-card)" stroke-width="2" />
          <polyline points="${posX - 3},${spineY} ${posX - 1},${spineY + 2} ${posX + 3},${spineY - 2}" fill="none" stroke="var(--bg-card)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        `;
      } else {
        nodeCircles = `
          <!-- Clean Hollow Circle for Future Stations (Matching Mockup) -->
          <circle id="rail-ring-${station.id}" class="station-rail-node-ring" data-orig-stroke="var(--border-medium)" data-orig-width="2" cx="${posX}" cy="${spineY}" r="8.5" fill="var(--bg-card)" stroke="var(--border-medium)" stroke-width="2" />
        `;
      }

      // Stream Micro-Pips beneath station
      const pipSpacing = 6;
      const pipsStartX = posX - ((branches.length - 1) * pipSpacing) / 2;
      let pipsSvg = "";
      branches.forEach((b, pIdx) => {
        const c = this.getStreamColor(b);
        pipsSvg += `<circle cx="${pipsStartX + pIdx * pipSpacing}" cy="${spineY + 44}" r="2" fill="${c}" />`;
      });

      // Station Labels Below the Rail (Matching Mockup)
      const labelNameColor = isActive ? "var(--accent-lavender)" : isCompleted ? "var(--text-secondary)" : "var(--text-tertiary)";
      const labelFontWeight = isActive ? "800" : "600";

      stationsSvgHtml += `
        <g class="metro-rail-station-node" style="cursor: pointer; pointer-events: all;"
           onclick="MetroMap.selectStation('${station.id}')"
           onmouseenter="MetroMap.highlightCardInGrid('${station.id}')"
           onmouseleave="MetroMap.clearHighlightCardInGrid()">
          ${nodeCircles}
          <!-- Station Title Below Node -->
          <text x="${posX}" y="${spineY + 20}" text-anchor="middle" font-size="10.5" font-weight="${labelFontWeight}" fill="${labelNameColor}">
            ${this.escapeHtml(station.name)}
          </text>
          <!-- Status / Subtitle Below -->
          <text x="${posX}" y="${spineY + 32}" text-anchor="middle" font-family="var(--font-mono)" font-size="8.5" font-weight="${isActive ? '700' : '500'}" fill="${labelSubColor}">
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
        <circle cx="${terminusX}" cy="${spineY}" r="18" fill="none" stroke="#f59e0b" stroke-width="1.5" opacity="0.3" class="beacon-pulse" />
        <circle cx="${terminusX}" cy="${spineY}" r="12" fill="var(--bg-card)" stroke="#f59e0b" stroke-width="2.5" />
        <circle cx="${terminusX}" cy="${spineY}" r="5" fill="#f59e0b" />
        <text x="${terminusX}" y="${spineY + 20}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#f59e0b">
          TUM ’28
        </text>
        <text x="${terminusX}" y="${spineY + 32}" text-anchor="middle" font-family="var(--font-mono)" font-size="8" font-weight="700" fill="#f59e0b">
          Campus Heilbronn
        </text>
      </g>
    `;

    // Today Vertical Indicator (Matching Mockup with 2-line minimalist text)
    const todayBeaconSvg = `
      <g class="metro-today-beacon" style="pointer-events: none;">
        <!-- Clean vertical indicator line rising from rail -->
        <line x1="${currentX}" y1="${spineY - 10}" x2="${currentX}" y2="${spineY - 42}" stroke="var(--accent-lavender)" stroke-width="1.8" />
        <circle cx="${currentX}" cy="${spineY - 10}" r="2" fill="var(--accent-lavender)" />
        <!-- 2-line clean monospace date and progress text -->
        <text x="${currentX}" y="${spineY - 54}" font-family="var(--font-mono)" font-size="9.5" font-weight="800" text-anchor="middle" fill="var(--text-primary)" letter-spacing="0.04em">
          ${beaconSub.toUpperCase()}
        </text>
        <text x="${currentX}" y="${spineY - 44}" font-family="var(--font-mono)" font-size="8.5" font-weight="700" text-anchor="middle" fill="var(--accent-lavender)">
          ${beaconTitle} (${(progressRatio * 100).toFixed(1)}%)
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
          const completedCount = completedList.length;
          const progressPercent = totalDelivs > 0 ? Math.round((completedCount / totalDelivs) * 100) : isCompleted ? 100 : 0;

          // Header Chip
          let chipHtml = "";
          if (isActive) {
            chipHtml = `<span class="metro-card-chip active">ACTIVE</span>`;
          } else if (isCompleted) {
            chipHtml = `<span class="metro-card-chip done">✓ DONE</span>`;
          } else {
            chipHtml = `<span class="metro-card-chip">${completedCount}/${totalDelivs}</span>`;
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

              <!-- Slim Progress Bar -->
              <div class="metro-card-progress">
                <div class="metro-progress-track">
                  <div class="metro-progress-fill" style="width: ${progressPercent}%; ${isActive ? 'background: var(--accent-lavender);' : ''}"></div>
                </div>
                <span class="metro-progress-pct">${progressPercent}%</span>
              </div>
            </div>
          `;
        })
        .join("");

      // Destination Milestone Card at the end of grid
      gridCardsHtml += `
        <div 
          class="metro-grid-card" 
          style="border: 1.5px solid rgba(245, 158, 11, 0.4); background: linear-gradient(135deg, rgba(245, 158, 11, 0.04), rgba(139, 92, 246, 0.04)); cursor: pointer;"
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
