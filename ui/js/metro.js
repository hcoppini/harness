/**
 * Section 2: TUM METRO ROADMAP & TIMELINE ENGINE (Version 3.0)
 * - Single horizontal timeline spine with clear station nodes.
 * - Interactive Stream Filter bar (All, Academics, Code, SIGG, German, Physical).
 * - Real-Time Day Beacon indicator.
 * - Slide-over drawer with deliverables checklist and progress tracker.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
  activeStreamFilter: "all",
  currentBeaconX: 0,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    const container = document.getElementById("metroScrollContainer");
    if (!container) return;

    // Mouse drag scrolling
    container.addEventListener("mousedown", (e) => {
      if (e.target.closest(".metro-spine-card") || e.target.closest(".station-drawer") || e.target.closest("button")) return;
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
    const spacing = 250;
    const startX = 180;
    const spineY = 240;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 360;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "480px";

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
      currentX = startX - 40;
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
          <div style="position: absolute; top: 12px; left: ${p.x - 30}px; font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.8px; padding-left: 8px; border-left: 2px solid var(--border-subtle); pointer-events: none;">
            ${p.name}
          </div>
        `;
      })
      .join("");

    // SVG Track Line
    let svgHtml = `
      <svg width="${totalWidth}" height="480" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <defs>
          <linearGradient id="trackGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#8b5cf6" />
            <stop offset="100%" stop-color="#a78bfa" />
          </linearGradient>
        </defs>

        <!-- Phase Dividers -->
        ${phases
          .map(
            (p) =>
              `<line x1="${p.x - 30}" y1="36" x2="${p.x - 30}" y2="440" stroke="rgba(255,255,255,0.04)" stroke-dasharray="3 4" stroke-width="1" />`
          )
          .join("")}

        <!-- Base Track Line -->
        <line x1="${startX}" y1="${spineY}" x2="${startX + totalTrackLength}" y2="${spineY}" 
              stroke="rgba(255, 255, 255, 0.12)" stroke-width="4" stroke-linecap="round" />

        <!-- Progress Filled Track -->
        ${
          currentX > startX
            ? `<line x1="${startX}" y1="${spineY}" x2="${currentX}" y2="${spineY}" stroke="url(#trackGrad)" stroke-width="4" stroke-linecap="round" />`
            : ""
        }

        <!-- Connectors from Spine to Cards -->
        ${stations
          .map((station, idx) => {
            const posX = startX + idx * spacing;
            const isEven = idx % 2 === 0;
            const y1 = isEven ? spineY - 40 : spineY + 10;
            const y2 = isEven ? spineY - 10 : spineY + 40;

            return `
              <line x1="${posX}" y1="${y1}" x2="${posX}" y2="${y2}" 
                    stroke="rgba(255, 255, 255, 0.2)" stroke-width="1.5" stroke-dasharray="2 2" />
            `;
          })
          .join("")}
      </svg>
    `;

    // Station Nodes and Cards
    let cardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isMajor = station.is_major;
        const isEven = idx % 2 === 0;
        const status = station.status || "upcoming";
        const isPassed = posX <= currentX;

        // Card position: Even on top, Odd on bottom
        const cardTop = isEven ? spineY - 160 : spineY + 40;
        const cardLeft = posX - 105;

        // Stream Filter match
        let isFilteredMatch = true;
        if (this.activeStreamFilter !== "all") {
          const branches = station.branches || [];
          isFilteredMatch = branches.includes(this.activeStreamFilter);
        }

        // Node disc style
        let nodeContent = "";
        let nodeStyle = "background: var(--bg-surface); border: 2px solid var(--border-medium);";
        if (status === "completed" || (isPassed && !isPreLaunch)) {
          nodeStyle = "background: var(--accent-purple); border: 2px solid #ffffff;";
          nodeContent = `<span style="color: #ffffff; font-size: 10px; font-weight: 800; line-height: 1;">✓</span>`;
        } else if (status === "active") {
          nodeStyle = "background: #ffffff; border: 2px solid var(--accent-purple); box-shadow: 0 0 14px var(--accent-purple-glow);";
        }

        const size = isMajor ? 22 : 16;

        // Stream tags
        const branches = station.branches || [];
        const chipsHtml = branches
          .slice(0, 3)
          .map((b) => {
            let cls = "chip-tag";
            if (b === "code") cls += " code";
            if (b === "sigg") cls += " sigg";
            if (b === "german") cls += " german";
            if (b === "academics") cls += " academics";
            return `<span class="${cls}">${b}</span>`;
          })
          .join("");

        // Deliverables progress
        const delivEntries = Object.keys(station.deliverables || {});
        const totalDelivs = delivEntries.length;
        const completedDelivs = (station.completed_deliverables || []).length;
        let checklistBadge = "";
        if (totalDelivs > 0) {
          if (completedDelivs >= totalDelivs) {
            checklistBadge = `<span class="chip-tag" style="background: var(--status-success-bg); color: var(--status-success); border-color: rgba(16,185,129,0.3);">✓ All ${totalDelivs}</span>`;
          } else {
            checklistBadge = `<span class="chip-tag" style="color: var(--text-secondary);">${completedDelivs}/${totalDelivs}</span>`;
          }
        }

        const opacityStyle = isFilteredMatch ? "opacity: 1;" : "opacity: 0.35;";

        return `
          <!-- Station Node On The Spine -->
          <div 
            class="station-node-point" 
            style="left: ${posX}px; top: ${spineY}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
            title="${this.escapeHtml(station.name)} (${station.month_label})"
          >
            <div 
              style="width: ${size}px; height: ${size}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; ${nodeStyle}"
            >
              ${nodeContent}
            </div>
          </div>

          <!-- Station Card -->
          <div 
            class="metro-spine-card ${isMajor ? "major" : ""} ${status === "completed" ? "completed-card" : ""} ${status === "active" ? "active-card" : ""}" 
            style="left: ${cardLeft}px; top: ${cardTop}px; ${opacityStyle}"
            onclick="MetroMap.selectStation('${station.id}')"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <span style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: var(--accent-purple-light);">${station.month_label}</span>
              ${checklistBadge}
            </div>
            <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px;" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${chipsHtml}
            </div>
          </div>
        `;
      })
      .join("");

    // Real-Time Beacon Pulse
    const beaconHtml = `
      <div style="position: absolute; left: ${currentX}px; top: ${spineY}px; transform: translate(-50%, -50%); pointer-events: none; z-index: 45;">
        <div style="position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--bg-surface-elevated); border: 1px solid var(--accent-purple); border-radius: var(--radius-sm); padding: 4px 10px; white-space: nowrap; box-shadow: var(--shadow-dropdown); text-align: center;">
          <div style="font-size: 9px; font-weight: 700; color: var(--accent-purple-light); font-family: var(--font-mono);">${beaconTitle}</div>
          <div style="font-size: 9px; color: var(--text-tertiary); font-family: var(--font-mono);">${beaconSub}</div>
        </div>
        <div style="width: 14px; height: 14px; background: #ffffff; border-radius: 50%; border: 3px solid var(--accent-purple); box-shadow: 0 0 12px var(--accent-purple-glow);"></div>
      </div>
    `;

    canvasWrap.innerHTML = phaseHeadersHtml + svgHtml + cardsHtml + beaconHtml;
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

    // Deliverables breakdown
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
          let lineBadgeColor = "var(--text-secondary)";
          if (key.toLowerCase().includes("code")) lineBadgeColor = "var(--stream-code)";
          if (key.toLowerCase().includes("academic")) lineBadgeColor = "var(--stream-academic)";
          if (key.toLowerCase().includes("sigg")) lineBadgeColor = "var(--stream-sigg)";
          if (key.toLowerCase().includes("german")) lineBadgeColor = "var(--stream-german)";
          if (key.toLowerCase().includes("physical")) lineBadgeColor = "var(--stream-physical)";

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
