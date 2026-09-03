/**
 * Section 2: TUM MULTI-STREAM METRO TRANSIT MAP (Version 3.1)
 * Authentic schematic subway transit diagram with distinct parallel colored lines:
 * - Line 1: Academics (Violet // #a855f7)
 * - Line 2: Code (Cyan // #38bdf8)
 * - Line 3: SIGG GPW (Orange // #f97316)
 * - Line 4: German (Emerald // #10b981)
 * - Line 5: Physical (Rose // #f43f5e)
 *
 * Features:
 * - Multi-line schematic tracks with interchange transfer capsules
 * - Stream line filter highlighting
 * - Real-Time Day Beacon
 * - Station Slide-over Drawer with stream-categorized deliverables checklist
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  currentBeaconX: 0,

  // Stream Line Definitions
  streamLines: [
    { id: "academics", name: "Academics", code: "AC", color: "#a855f7", bgGlow: "rgba(168, 85, 247, 0.25)", y: 120 },
    { id: "code", name: "Code Sprint", code: "CD", color: "#38bdf8", bgGlow: "rgba(56, 189, 248, 0.25)", y: 180 },
    { id: "sigg", name: "SIGG GPW", code: "SG", color: "#f97316", bgGlow: "rgba(249, 115, 22, 0.25)", y: 240 },
    { id: "german", name: "German Ladder", code: "DE", color: "#10b981", bgGlow: "rgba(16, 185, 129, 0.25)", y: 300 },
    { id: "physical", name: "Physical / Mass", code: "PH", color: "#f43f5e", bgGlow: "rgba(244, 63, 94, 0.25)", y: 360 },
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
      if (e.target.closest(".metro-station-pill") || e.target.closest(".station-drawer") || e.target.closest("button") || e.target.closest(".station-node-disc")) return;
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
    const spacing = 200;
    const startX = 220;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 360;

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

    // Phases
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
          <div style="position: absolute; top: 12px; left: ${p.x - 20}px; font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.8px; padding-left: 8px; border-left: 2px solid var(--border-subtle); pointer-events: none;">
            ${p.name}
          </div>
        `;
      })
      .join("");

    // Left Rail Legend & Badges (Stationary origin tags)
    let leftRailHtml = `
      <div style="position: absolute; left: 16px; top: 0; width: 180px; height: 520px; pointer-events: none; z-index: 30;">
        <div style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); margin-top: 14px; margin-bottom: 24px;">
          TRANSIT LINES
        </div>
        ${this.streamLines
          .map((stream) => {
            const isFiltered = this.activeStreamFilter !== "all" && this.activeStreamFilter !== stream.id;
            const opacity = isFiltered ? 0.35 : 1.0;
            return `
              <div style="position: absolute; top: ${stream.y - 12}px; left: 0; display: flex; align-items: center; gap: 8px; opacity: ${opacity}; transition: opacity 0.15s ease;">
                <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 800; background: ${stream.color}; color: #ffffff; padding: 2px 5px; border-radius: 3px; box-shadow: 0 0 8px ${stream.bgGlow};">
                  ${stream.code}
                </span>
                <span style="font-size: 11px; font-weight: 600; color: var(--text-primary); text-shadow: 0 1px 4px rgba(0,0,0,0.8);">
                  ${stream.name}
                </span>
              </div>
            `;
          })
          .join("")}
      </div>
    `;

    // SVG Rendering for Schematic Transit Tracks
    let svgHtml = `
      <svg width="${totalWidth}" height="520" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <defs>
          ${this.streamLines
            .map(
              (stream) => `
            <linearGradient id="grad-${stream.id}" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="${stream.color}" />
              <stop offset="100%" stop-color="${stream.color}" />
            </linearGradient>
          `
            )
            .join("")}
        </defs>

        <!-- Phase Vertical Guidelines -->
        ${phases
          .map(
            (p) =>
              `<line x1="${p.x - 20}" y1="36" x2="${p.x - 20}" y2="480" stroke="rgba(255,255,255,0.04)" stroke-dasharray="3 4" stroke-width="1" />`
          )
          .join("")}

        <!-- 5 Parallel Stream Subway Lines -->
        ${this.streamLines
          .map((stream) => {
            const isFiltered = this.activeStreamFilter !== "all" && this.activeStreamFilter !== stream.id;
            const lineOpacity = isFiltered ? 0.2 : 0.9;
            const strokeWidth = isFiltered ? 3 : 5;

            return `
              <!-- Line Track Glow and Path -->
              <line x1="${startX - 20}" y1="${stream.y}" x2="${startX + totalTrackLength + 40}" y2="${stream.y}" 
                    stroke="${stream.color}" stroke-width="${strokeWidth}" stroke-linecap="round" opacity="${lineOpacity}" />
            `;
          })
          .join("")}

        <!-- Interchange Transfer Connectors for Stations -->
        ${stations
          .map((station, idx) => {
            const posX = startX + idx * spacing;
            const branches = station.branches || [];
            if (branches.length < 2) return "";

            // Find matching stream line Y positions
            const activeYs = this.streamLines.filter((s) => branches.includes(s.id)).map((s) => s.y);
            if (activeYs.length < 2) return "";

            const minY = Math.min(...activeYs);
            const maxY = Math.max(...activeYs);

            const isMatchingFilter =
              this.activeStreamFilter === "all" || branches.includes(this.activeStreamFilter);
            const opacity = isMatchingFilter ? 0.85 : 0.2;

            return `
              <!-- Transfer Interchange Capsule Bridge -->
              <rect x="${posX - 6}" y="${minY - 6}" width="12" height="${maxY - minY + 12}" rx="6" ry="6"
                    fill="rgba(18, 21, 29, 0.85)" stroke="rgba(255, 255, 255, 0.35)" stroke-width="1.5" opacity="${opacity}" />
            `;
          })
          .join("")}
      </svg>
    `;

    // Station Nodes and Pill Cards
    let nodesAndCardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isMajor = station.is_major;
        const status = station.status || "upcoming";
        const branches = station.branches || [];
        const isPassed = posX <= currentX;

        const isMatchingFilter =
          this.activeStreamFilter === "all" || branches.includes(this.activeStreamFilter);
        const opacityStyle = isMatchingFilter ? "opacity: 1;" : "opacity: 0.25;";

        // Deliverables progress
        const delivEntries = Object.keys(station.deliverables || {});
        const totalDelivs = delivEntries.length;
        const completedDelivs = (station.completed_deliverables || []).length;
        let checklistBadge = "";
        if (totalDelivs > 0) {
          if (completedDelivs >= totalDelivs) {
            checklistBadge = `<span class="chip-tag" style="background: var(--status-success-bg); color: var(--status-success); border-color: rgba(16,185,129,0.3);">✓ Done</span>`;
          } else {
            checklistBadge = `<span class="chip-tag" style="color: var(--text-secondary);">${completedDelivs}/${totalDelivs}</span>`;
          }
        }

        // Branch Stop Dots on Each Active Line
        let branchDotsHtml = this.streamLines
          .map((stream) => {
            if (!branches.includes(stream.id)) return "";

            let dotFill = stream.color;
            let dotBorder = "#ffffff";
            if (status === "completed" || (isPassed && !isPreLaunch)) {
              dotFill = "#ffffff";
              dotBorder = stream.color;
            }

            return `
              <div 
                class="station-node-disc" 
                style="position: absolute; left: ${posX}px; top: ${stream.y}px; transform: translate(-50%, -50%); width: 12px; height: 12px; border-radius: 50%; background: ${dotFill}; border: 2px solid ${dotBorder}; box-shadow: 0 0 6px rgba(0,0,0,0.6); cursor: pointer; z-index: 28; ${opacityStyle}"
                onclick="MetroMap.selectStation('${station.id}')"
                title="${stream.name} Stop • ${this.escapeHtml(station.name)}"
              ></div>
            `;
          })
          .join("");

        // Station Header Pill Card (Alternating Top / Bottom)
        const isTop = idx % 2 === 0;
        const cardY = isTop ? 42 : 405;
        const cardX = posX - 80;

        return `
          ${branchDotsHtml}

          <!-- Station Header Pill Card -->
          <div 
            class="metro-station-pill ${status === "completed" ? "completed-card" : ""} ${status === "active" ? "active-card" : ""}"
            style="position: absolute; left: ${cardX}px; top: ${cardY}px; width: 160px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px;">
              <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--accent-purple-light);">${station.month_label}</span>
              ${checklistBadge}
            </div>
            <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div style="display: flex; gap: 3px; flex-wrap: wrap;">
              ${branches
                .map((b) => {
                  const match = this.streamLines.find((s) => s.id === b);
                  const color = match ? match.color : "var(--text-tertiary)";
                  return `<span style="font-size: 8px; font-weight: 700; font-family: var(--font-mono); color: ${color}; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); padding: 1px 4px; border-radius: 2px;">${b.toUpperCase()}</span>`;
                })
                .join("")}
            </div>
          </div>
        `;
      })
      .join("");

    // Real-Time Day Beacon cutting across all 5 lines
    const beaconHtml = `
      <div style="position: absolute; left: ${currentX}px; top: 80px; width: 2px; height: 320px; background: linear-gradient(180deg, rgba(139,92,246,0) 0%, #8b5cf6 30%, #8b5cf6 70%, rgba(139,92,246,0) 100%); pointer-events: none; z-index: 45;">
        <div style="position: absolute; top: -38px; left: 50%; transform: translateX(-50%); background: var(--bg-surface-elevated); border: 1px solid var(--accent-purple); border-radius: var(--radius-sm); padding: 4px 10px; white-space: nowrap; box-shadow: var(--shadow-dropdown); text-align: center;">
          <div style="font-size: 9px; font-weight: 700; color: var(--accent-purple-light); font-family: var(--font-mono);">${beaconTitle}</div>
          <div style="font-size: 9px; color: var(--text-tertiary); font-family: var(--font-mono);">${beaconSub}</div>
        </div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + leftRailHtml + svgHtml + nodesAndCardsHtml + beaconHtml;
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

    // Deliverables breakdown categorized by stream line
    const deliverablesList = document.getElementById("drawerDeliverablesList");
    if (deliverablesList && station.deliverables) {
      const allEntries = Object.entries(station.deliverables);
      const totalDelivs = allEntries.length;
      const completedList = station.completed_deliverables || [];
      const completedCount = completedList.length;
      const progressPercent = totalDelivs > 0 ? Math.round((completedCount / totalDelivs) * 100) : 0;
      const isAllComplete = totalDelivs > 0 && completedCount >= totalDelivs;

      const progressHeader = `
        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 10px 12px; margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 11px; font-weight: 600;">
            <span style="color: var(--text-secondary);">Deliverables Progress (${completedCount}/${totalDelivs})</span>
            <span style="color: ${isAllComplete ? "var(--status-success)" : "var(--accent-purple-light)"}; font-weight: 700;">${isAllComplete ? "COMPLETED ✓" : `${progressPercent}%`}</span>
          </div>
          <div class="progress-bar-track" style="margin: 0;">
            <div class="progress-bar-fill" style="width: ${progressPercent}%; ${isAllComplete ? "background: var(--status-success);" : ""}"></div>
          </div>
        </div>
      `;

      const itemsHtml = allEntries
        .map(([key, val]) => {
          const streamMatch = this.streamLines.find((s) => s.name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(s.id));
          const lineBadgeColor = streamMatch ? streamMatch.color : "var(--accent-purple-light)";
          const isChecked = completedList.includes(key);

          return `
            <div 
              class="deliverable-item ${isChecked ? "checked" : ""}" 
              onclick="MetroMap.toggleDeliverable('${station.id}', '${this.escapeHtml(key)}')"
              title="Click to toggle deliverable"
            >
              <div class="check-dot ${isChecked ? "checked" : ""}" style="margin-top: 2px;"></div>
              <div style="flex: 1;">
                <div style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; text-transform: uppercase; color: ${lineBadgeColor}; margin-bottom: 2px;">
                  ${key} STREAM
                </div>
                <div class="deliverable-desc" style="font-size: 12px; color: var(--text-primary); line-height: 1.4;">
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
          window.HarnessApp.showToast(`Station Completed: ${st.name}! All deliverables met.`);
        } else if (res.is_checked) {
          window.HarnessApp.showToast(`Checked: ${deliverableKey} (${res.completed_count}/${res.total_count})`);
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
