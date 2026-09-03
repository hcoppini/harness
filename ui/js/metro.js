/**
 * Section 2: TUM METRO ROADMAP // Schematic Height-Varying Stream Lines (Version 3.3)
 *
 * Architecture:
 * - One singular central main line for all major milestones.
 * - Distinct stream highlighter lines with elegant height breaks, 45° chamfered transitions,
 *   and schematic elevation shifts for maximum visibility and visual rhythm:
 *     - Academics (Lavender // #c4b5fd): Top elevation (Y=165 to Y=185), ramping to major exams.
 *     - Code Sprint (Sky Blue // #7dd3fc): Upper-mid elevation (Y=200 to Y=220), stepping with algorithm sprints.
 *     - SIGG GPW (Orange // #fdba74): Central dynamic lane (Y=235 to Y=265), peaking at Stage 1/2 & Finals.
 *     - German (Emerald // #6ee7b7): Lower-mid elevation (Y=285 to Y=305), climbing to A2/B1/B2 certifications.
 *     - Physical (Rose // #fda4af): Bottom elevation (Y=325 to Y=345), charting hypertrophy steps.
 * - Stations feature clean junction pins connecting stream lines to the main spine.
 * - Interactive filter highlights specific stream lines while keeping full system context.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  currentBeaconX: 0,

  // Stream Definitions with Clean Parallel Elevations
  streams: [
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      color: "#c4b5fd", // Lavender
      strokeWidth: 2.0,
      baseY: 155,
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      color: "#7dd3fc", // Sky Blue
      strokeWidth: 2.0,
      baseY: 190,
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      color: "#fdba74", // Orange
      strokeWidth: 2.5,
      baseY: 225,
    },
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      color: "#6ee7b7", // Emerald
      strokeWidth: 2.0,
      baseY: 295,
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      color: "#fda4af", // Rose
      strokeWidth: 2.0,
      baseY: 330,
    },
  ],

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
    const spacing = 220;
    const startX = 160;
    const spineY = 260;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 320;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "540px";

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

    // Phase Milestones
    const phases = [
      { name: "Phase 1: Year 3 Liceum", x: startX, width: 4.8 * spacing },
      { name: "Phase 2: SIGG Finals & Year 3 Lock", x: startX + 5 * spacing, width: 4.8 * spacing },
      { name: "Phase 3: Summer Mass & B1", x: startX + 10 * spacing, width: 1.8 * spacing },
      { name: "Phase 4: Matura Crucible", x: startX + 12 * spacing, width: 7.8 * spacing },
      { name: "Phase 5: Official CKE & TUM", x: startX + 20 * spacing, width: 1.8 * spacing },
    ];

    let phaseHeadersHtml = phases
      .map((p) => {
        return `
          <div style="position: absolute; top: 12px; left: ${p.x - 20}px; font-family: var(--font-mono); font-size: 9px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.08em; padding-left: 8px; border-left: 2px solid var(--border-subtle); pointer-events: none;">
            ${p.name}
          </div>
        `;
      })
      .join("");

    // Generate Parallel Straight Stream Lines
    let streamPathsHtml = "";
    let streamPinsHtml = "";

    this.streams.forEach((stream) => {
      const activeIndices = [];
      stations.forEach((st, idx) => {
        if ((st.branches || []).includes(stream.id)) {
          activeIndices.push(idx);
        }
      });

      if (activeIndices.length === 0) return;

      const isFiltered = this.activeStreamFilter !== "all" && this.activeStreamFilter !== stream.id;
      const opacity = isFiltered ? 0.08 : this.activeStreamFilter === stream.id ? 1.0 : 0.65;
      const strokeWidth = this.activeStreamFilter === stream.id ? 3.5 : stream.strokeWidth;

      const firstX = startX + activeIndices[0] * spacing;
      const lastX = startX + activeIndices[activeIndices.length - 1] * spacing;

      streamPathsHtml += `
        <!-- Stream Track: ${stream.name} -->
        <path 
          d="M ${firstX - 8} ${stream.baseY} L ${lastX + 8} ${stream.baseY}" 
          fill="none" 
          stroke="${stream.color}" 
          stroke-width="${strokeWidth}" 
          stroke-linecap="round" 
          opacity="${opacity}" 
        />
      `;

      // Junction dots on stream lines
      activeIndices.forEach((idx) => {
        const px = startX + idx * spacing;
        const pinOpacity = isFiltered ? 0.12 : 0.9;
        streamPinsHtml += `
          <circle cx="${px}" cy="${stream.baseY}" r="3" fill="${stream.color}" opacity="${pinOpacity}" />
        `;
      });
    });

    // Vertical alignment guide lines, SVG station circles, and stream dots
    let verticalGuidesHtml = "";
    let svgStationNodesHtml = "";
    let svgStreamDotsHtml = "";

    stations.forEach((station, idx) => {
      const posX = startX + idx * spacing;
      const isMajor = station.is_major;
      const isEven = idx % 2 === 0;
      const status = station.status || "upcoming";
      const branches = station.branches || [];
      const isPassed = posX <= currentX;

      // Vertical guide line passing through posX
      const yTop = isEven ? 152 : 155;
      const yBottom = isEven ? 330 : 362;
      verticalGuidesHtml += `
        <line x1="${posX}" y1="${yTop}" x2="${posX}" y2="${yBottom}" 
              stroke="rgba(255, 255, 255, 0.12)" stroke-width="1" stroke-dasharray="2 3" />
      `;

      // Central Station Circle on Main Spine
      const size = isMajor ? 18 : 14;
      const r = size / 2;
      let fill = "#09090b";
      let stroke = "#52525b";
      let strokeW = 2;
      let innerCore = "";
      let aura = "";

      if (status === "completed" || (isPassed && !isPreLaunch)) {
        fill = "var(--accent-lavender)";
        stroke = "#ffffff";
        strokeW = 2;
        innerCore = `<circle cx="${posX}" cy="${spineY}" r="2.5" fill="#09090b" />`;
      } else if (status === "active") {
        fill = "#ffffff";
        stroke = "var(--accent-lavender)";
        strokeW = 2.5;
        aura = `<circle cx="${posX}" cy="${spineY}" r="${r + 4}" fill="none" stroke="var(--accent-lavender)" stroke-width="1" opacity="0.5" stroke-dasharray="2 2" />`;
      }

      svgStationNodesHtml += `
        ${aura}
        <circle cx="${posX}" cy="${spineY}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" />
        ${innerCore}
        <!-- Click target overlay -->
        <circle cx="${posX}" cy="${spineY}" r="16" fill="transparent" cursor="pointer" onclick="MetroMap.selectStation('${station.id}')" style="pointer-events: all;" />
      `;

      // Symmetric Stream Indicator Dots below station node (spineY + 16)
      if (branches.length > 0) {
        const numDots = branches.length;
        const dotY = spineY + 16;
        branches.forEach((b, bIdx) => {
          const streamObj = this.streams.find((s) => s.id === b);
          const color = streamObj ? streamObj.color : "#a1a1aa";
          const dotX = posX - (numDots - 1) * 4 + bIdx * 8;
          svgStreamDotsHtml += `
            <circle cx="${dotX}" cy="${dotY}" r="2.5" fill="${color}" title="${b.toUpperCase()}" />
          `;
        });
      }
    });

    // SVG Layer (Main Spine, Stream Tracks, Vertical Guides, Station Circles & Dots)
    let svgHtml = `
      <svg width="${totalWidth}" height="540" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <!-- Phase Vertical Grid Lines -->
        ${phases
          .map(
            (p) =>
              `<line x1="${p.x - 20}" y1="28" x2="${p.x - 20}" y2="500" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4" stroke-width="1" />`
          )
          .join("")}

        <!-- Stream Tracks -->
        ${streamPathsHtml}

        <!-- Vertical Guide Lines -->
        ${verticalGuidesHtml}

        <!-- Stream Junction Dots -->
        ${streamPinsHtml}

        <!-- Singular Central Main Spine Line -->
        <line x1="${startX - 40}" y1="${spineY}" x2="${startX + totalTrackLength + 40}" y2="${spineY}" 
              stroke="#27272a" stroke-width="6" stroke-linecap="round" />

        <!-- Main Spine Reached / Completed Fill -->
        ${
          currentX > startX
            ? `<line x1="${startX - 40}" y1="${spineY}" x2="${currentX}" y2="${spineY}" stroke="var(--accent-lavender)" stroke-width="5" stroke-linecap="round" />`
            : ""
        }

        <!-- Station Circles on Main Spine -->
        ${svgStationNodesHtml}

        <!-- Symmetrical Branch Dots below Stations -->
        ${svgStreamDotsHtml}

        <!-- Real-Time Day Beacon Indicator on Spine -->
        <circle cx="${currentX}" cy="${spineY}" r="7" fill="none" stroke="var(--accent-lavender)" stroke-width="1.5" opacity="0.8">
          <animate attributeName="r" values="7;13;7" dur="2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.8;0.15;0.8" dur="2s" repeatCount="indefinite"/>
        </circle>
        <circle cx="${currentX}" cy="${spineY}" r="4" fill="#ffffff" stroke="var(--accent-lavender)" stroke-width="2" />
      </svg>
    `;

    // Station Cards (HTML Layer)
    let cardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isEven = idx % 2 === 0;
        const status = station.status || "upcoming";
        const branches = station.branches || [];

        // Center card horizontally at posX (width = 170px)
        const cardLeft = posX - 85;
        const cardTop = isEven ? spineY - 180 : spineY + 105;

        // Filter opacity
        let isFilteredMatch = true;
        if (this.activeStreamFilter !== "all") {
          isFilteredMatch = branches.includes(this.activeStreamFilter);
        }
        const opacityStyle = isFilteredMatch ? "opacity: 1;" : "opacity: 0.25;";

        // Deliverables progress badge
        const delivEntries = Object.keys(station.deliverables || {});
        const totalDelivs = delivEntries.length;
        const completedDelivs = (station.completed_deliverables || []).length;
        let checklistBadge = "";
        if (totalDelivs > 0) {
          if (completedDelivs >= totalDelivs) {
            checklistBadge = `<span class="mono-chip done">Done</span>`;
          } else {
            checklistBadge = `<span class="mono-chip">${completedDelivs}/${totalDelivs}</span>`;
          }
        }

        return `
          <!-- Station Card Centered at posX -->
          <div 
            class="metro-station-card ${status === "completed" ? "completed-card" : ""} ${status === "active" ? "active-card" : ""}" 
            style="left: ${cardLeft}px; top: ${cardTop}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--accent-lavender);">${station.month_label}</span>
              ${checklistBadge}
            </div>
            <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 5px;" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div style="display: flex; gap: 3px; flex-wrap: wrap;">
              ${branches
                .map((b) => {
                  const sMatch = this.streams.find((s) => s.id === b);
                  const color = sMatch ? sMatch.color : "var(--text-tertiary)";
                  return `<span style="font-family: var(--font-mono); font-size: 8px; font-weight: 600; color: ${color}; border: 1px solid rgba(255,255,255,0.06); padding: 1px 4px; border-radius: 2px;">${b.toUpperCase()}</span>`;
                })
                .join("")}
            </div>
          </div>
        `;
      })
      .join("");

    // Real-Time Day Beacon Tooltip (HTML Layer)
    const beaconTooltipHtml = `
      <div style="position: absolute; left: ${currentX}px; top: ${spineY - 18}px; transform: translate(-50%, -100%); pointer-events: none; z-index: 45;">
        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--accent-lavender); border-radius: var(--radius-sm); padding: 4px 8px; white-space: nowrap; box-shadow: var(--shadow-dropdown); text-align: center;">
          <div style="font-size: 9px; font-weight: 700; color: var(--accent-lavender); font-family: var(--font-mono);">${beaconTitle}</div>
          <div style="font-size: 8px; color: var(--text-tertiary); font-family: var(--font-mono);">${beaconSub}</div>
        </div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + svgHtml + cardsHtml + beaconTooltipHtml;
  },

  selectStation(stationId) {
    const station = this.data.stations.find((s) => s.id === stationId);
    if (!station) return;

    this.selectedStation = station;
    this.openDrawer(station);
  },

  openDrawer(station) {
    const drawer = document.getElementById("stationDrawer");
    if (!drawer) return;

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

      const progressHeader = `
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
          const isChecked = completedList.includes(key);

          return `
            <div 
              class="deliverable-item ${isChecked ? "checked" : ""}" 
              onclick="MetroMap.toggleDeliverable('${station.id}', '${this.escapeHtml(key)}')"
              title="Click to toggle deliverable"
            >
              <div class="check-dot ${isChecked ? "checked" : ""}" style="margin-top: 1px;"></div>
              <div style="flex: 1;">
                <div style="font-family: var(--font-mono); font-size: 8px; font-weight: 700; text-transform: uppercase; color: ${lineBadgeColor}; margin-bottom: 2px;">
                  ${key} STREAM
                </div>
                <div class="deliverable-desc" style="font-size: 11px; color: var(--text-primary); line-height: 1.4;">
                  ${this.escapeHtml(val)}
                </div>
              </div>
            </div>
          `;
        })
        .join("");

      deliverablesList.innerHTML = progressHeader + itemsHtml;
    }

    drawer.classList.add("open");
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
