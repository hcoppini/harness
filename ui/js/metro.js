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

  // Stream Definitions with Dynamic Elevation Offsets
  streams: [
    {
      id: "academics",
      name: "Academics",
      code: "AC",
      color: "#c4b5fd",
      strokeWidth: 2.5,
      baseY: 175,
      // Dynamic height adjustments per station index (creates clean breaks in height)
      heightOffsets: [0, -10, 5, -10, 0, 5, -10, 0, -5, -15, 10, 10, -5, -15, -10, -15, -5, -10, -10, -15, -20, -15, 0],
    },
    {
      id: "code",
      name: "Code Sprint",
      code: "CD",
      color: "#7dd3fc",
      strokeWidth: 2.5,
      baseY: 210,
      heightOffsets: [-5, 5, -10, -5, 0, 10, -10, 10, -10, 5, -15, -10, -5, -10, -5, -5, -10, -10, -5, 10, -15, 5, 0],
    },
    {
      id: "sigg",
      name: "SIGG GPW",
      code: "SG",
      color: "#fdba74",
      strokeWidth: 3.0,
      baseY: 250,
      // Peaking and ramping during active trading competition months (Sep '26 - May '27)
      heightOffsets: [0, -15, -20, -15, -20, -25, -20, -25, -30, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20],
    },
    {
      id: "german",
      name: "German Ladder",
      code: "DE",
      color: "#6ee7b7",
      strokeWidth: 2.5,
      baseY: 295,
      heightOffsets: [0, 5, 10, -5, 10, -5, 10, 10, 10, -5, -15, -25, -5, 10, -10, 10, 10, -10, -10, -15, 10, -25, 0],
    },
    {
      id: "physical",
      name: "Physical / Mass",
      code: "PH",
      color: "#fda4af",
      strokeWidth: 2.5,
      baseY: 335,
      heightOffsets: [0, 10, -10, 10, 10, 10, 10, -10, 10, -10, -15, -20, -5, 10, 10, -10, 10, 10, 10, -15, 10, 10, 0],
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
    const spineY = 250;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 320;

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

    // Generate Height-Varying Stream Lines with 45° Chamfered Schematic Paths
    let streamPathsHtml = "";
    let streamPinsHtml = "";

    this.streams.forEach((stream) => {
      const activeIndices = [];
      stations.forEach((st, idx) => {
        if ((st.branches || []).includes(stream.id)) {
          activeIndices.push(idx);
        }
      });

      if (activeIndices.length < 2) return;

      const isFiltered = this.activeStreamFilter !== "all" && this.activeStreamFilter !== stream.id;
      const opacity = isFiltered ? 0.06 : (this.activeStreamFilter === stream.id ? 0.95 : 0.6);
      const strokeWidth = this.activeStreamFilter === stream.id ? 4 : stream.strokeWidth;

      // Construct SVG path with 45° chamfers across stations
      let d = "";
      for (let i = 0; i < activeIndices.length; i++) {
        const idx = activeIndices[i];
        const px = startX + idx * spacing;
        const offset = stream.heightOffsets[idx] || 0;
        const py = stream.baseY + offset;

        if (i === 0) {
          d += `M ${px} ${py}`;
        } else {
          const prevIdx = activeIndices[i - 1];
          const prevPx = startX + prevIdx * spacing;
          const prevOffset = stream.heightOffsets[prevIdx] || 0;
          const prevPy = stream.baseY + prevOffset;

          // 45° chamfered segment
          if (Math.abs(py - prevPy) > 2) {
            const midX = (prevPx + px) / 2;
            const chamfer = Math.min(25, Math.abs(py - prevPy));
            const sign = py > prevPy ? 1 : -1;

            d += ` L ${midX - chamfer} ${prevPy} L ${midX + chamfer} ${py} L ${px} ${py}`;
          } else {
            d += ` L ${px} ${py}`;
          }
        }

        // Add small stream station pin/dot connecting stream track to station node
        const isMatch = this.activeStreamFilter === "all" || this.activeStreamFilter === stream.id;
        const pinOpacity = isMatch ? 0.85 : 0.15;
        streamPinsHtml += `
          <!-- Stream Junction Pin -->
          <line x1="${px}" y1="${py}" x2="${px}" y2="${spineY}" 
                stroke="${stream.color}" stroke-width="1" stroke-dasharray="2 3" opacity="${pinOpacity}" />
          <circle cx="${px}" cy="${py}" r="3" fill="${stream.color}" opacity="${pinOpacity}" />
        `;
      }

      streamPathsHtml += `
        <!-- Stream Highlighter Line: ${stream.name} -->
        <path 
          d="${d}" 
          fill="none" 
          stroke="${stream.color}" 
          stroke-width="${strokeWidth}" 
          stroke-linecap="round" 
          stroke-linejoin="round"
          opacity="${opacity}" 
        />
      `;
    });

    // SVG Base Lines (Main Spine & Grid)
    let svgHtml = `
      <svg width="${totalWidth}" height="520" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <!-- Phase Vertical Grid Lines -->
        ${phases
          .map(
            (p) =>
              `<line x1="${p.x - 20}" y1="36" x2="${p.x - 20}" y2="480" stroke="rgba(255,255,255,0.03)" stroke-dasharray="3 4" stroke-width="1" />`
          )
          .join("")}

        <!-- Stream Junction Pin Connectors -->
        ${streamPinsHtml}

        <!-- Height-Varying Stream Lines -->
        ${streamPathsHtml}

        <!-- Singular Central Main Spine Line -->
        <line x1="${startX - 20}" y1="${spineY}" x2="${startX + totalTrackLength + 30}" y2="${spineY}" 
              stroke="#27272a" stroke-width="5" stroke-linecap="round" />

        <!-- Main Spine Reached / Completed Fill -->
        ${
          currentX > startX
            ? `<line x1="${startX - 20}" y1="${spineY}" x2="${currentX}" y2="${spineY}" stroke="var(--accent-lavender)" stroke-width="4" stroke-linecap="round" />`
            : ""
        }

        <!-- Connectors from Spine to Cards -->
        ${stations
          .map((station, idx) => {
            const posX = startX + idx * spacing;
            const isEven = idx % 2 === 0;
            const y1 = isEven ? spineY - 35 : spineY + 12;
            const y2 = isEven ? spineY - 12 : spineY + 35;

            return `
              <line x1="${posX}" y1="${y1}" x2="${posX}" y2="${y2}" 
                    stroke="rgba(255, 255, 255, 0.15)" stroke-width="1" stroke-dasharray="2 2" />
            `;
          })
          .join("")}
      </svg>
    `;

    // Station Nodes and Cards
    let nodesAndCardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isMajor = station.is_major;
        const isEven = idx % 2 === 0;
        const status = station.status || "upcoming";
        const branches = station.branches || [];
        const isPassed = posX <= currentX;

        // Card position: Even on top, Odd on bottom
        const cardTop = isEven ? spineY - 150 : spineY + 36;
        const cardLeft = posX - 85;

        // Filter opacity
        let isFilteredMatch = true;
        if (this.activeStreamFilter !== "all") {
          isFilteredMatch = branches.includes(this.activeStreamFilter);
        }
        const opacityStyle = isFilteredMatch ? "opacity: 1;" : "opacity: 0.25;";

        // Node disc style
        let nodeContent = "";
        let nodeStyle = "background: var(--bg-surface); border: 2px solid #52525b;";
        if (status === "completed" || (isPassed && !isPreLaunch)) {
          nodeStyle = "background: var(--accent-lavender); border: 2px solid #ffffff;";
          nodeContent = `<div style="width: 5px; height: 5px; background: #09090b; border-radius: 1px;"></div>`;
        } else if (status === "active") {
          nodeStyle = "background: #ffffff; border: 2px solid var(--accent-lavender); box-shadow: 0 0 10px rgba(216,180,254,0.3);";
        }

        const size = isMajor ? 18 : 14;

        // Stream dots on node
        const streamDots = branches
          .map((b) => {
            const streamObj = this.streams.find((s) => s.id === b);
            const color = streamObj ? streamObj.color : "#a1a1aa";
            return `<div style="width: 5px; height: 5px; border-radius: 50%; background: ${color};" title="${b.toUpperCase()}"></div>`;
          })
          .join("");

        // Deliverables progress
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
          <!-- Central Node On Main Spine -->
          <div 
            class="metro-station-node" 
            style="left: ${posX}px; top: ${spineY}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
            title="${this.escapeHtml(station.name)} (${station.month_label})"
          >
            <div 
              style="width: ${size}px; height: ${size}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; ${nodeStyle}"
            >
              ${nodeContent}
            </div>
            <div style="display: flex; gap: 2px; justify-content: center; margin-top: 3px;">
              ${streamDots}
            </div>
          </div>

          <!-- Station Card -->
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

    // Real-Time Day Beacon
    const beaconHtml = `
      <div style="position: absolute; left: ${currentX}px; top: ${spineY}px; transform: translate(-50%, -50%); pointer-events: none; z-index: 45;">
        <div style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--bg-surface-elevated); border: 1px solid var(--accent-lavender); border-radius: var(--radius-sm); padding: 3px 8px; white-space: nowrap; box-shadow: var(--shadow-dropdown); text-align: center;">
          <div style="font-size: 9px; font-weight: 700; color: var(--accent-lavender); font-family: var(--font-mono);">${beaconTitle}</div>
          <div style="font-size: 8px; color: var(--text-tertiary); font-family: var(--font-mono);">${beaconSub}</div>
        </div>
        <div style="width: 10px; height: 10px; background: #ffffff; border-radius: 50%; border: 2px solid var(--accent-lavender);"></div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + svgHtml + nodesAndCardsHtml + beaconHtml;
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
