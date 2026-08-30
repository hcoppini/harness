/**
 * Section 2: TUM ROADMAP & HORIZON TRANSIT ENGINE (Version 3.0)
 * - Single dominant solid mainline spine (The TUM Trunk Line).
 * - Real-Time Day Beacon: Daily moving indicator that advances smoothly day after day.
 * - Alternating horizontal cards: Even above, odd below (Zero overlap, 100% legibility).
 * - Distinct SIGG GPW 45° branch line from Oct '26 to Apr '27.
 * - Five visual Phase Zones across the top header.
 * - Smooth drag, mouse-wheel scrolling, auto-centering on Today, and station slide-over ledger.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,
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
      if (e.target.closest(".metro-spine-card") || e.target.closest(".station-drawer")) return;
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

    // Jump to today's beacon
    const btnJump = document.getElementById("btnJumpCurrentStation");
    if (btnJump) {
      btnJump.textContent = "Jump to Today";
      btnJump.addEventListener("click", () => this.scrollToBeacon());
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.data = await window.pywebview.api.get_metro_roadmap();
      this.render();
      setTimeout(() => this.scrollToBeacon(), 150);
    } catch (err) {
      console.error("Error loading Metro Roadmap:", err);
    }
  },

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 260; // Generous horizontal breathing room between stations
    const startX = 220;
    const spineY = 255;  // Single dominant horizontal centerline
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 360;

    canvasWrap.style.minWidth = `${totalWidth}px`;
    canvasWrap.style.height = "520px";

    // 1. Real-Time Day Progress Calculation (Advances day by day)
    const startDate = new Date(2026, 8, 1);  // Sep 1, 2026
    const endDate = new Date(2028, 6, 31);    // Jul 31, 2028
    const now = new Date();

    let currentX = startX;
    let beaconTitle = "";
    let beaconSub = "";
    let isPreLaunch = false;

    if (now < startDate) {
      isPreLaunch = true;
      const msDiff = startDate.getTime() - now.getTime();
      const daysUntil = Math.max(1, Math.ceil(msDiff / (1000 * 60 * 60 * 24)));
      currentX = startX - 70;
      beaconTitle = `DEPARTURE GATE // SEP 1, 2026`;
      beaconSub = `${daysUntil} day(s) to Kickoff • Station 1: Pure Syntax`;
    } else {
      const totalMs = endDate.getTime() - startDate.getTime();
      const elapsedMs = Math.min(totalMs, Math.max(0, now.getTime() - startDate.getTime()));
      const progressRatio = elapsedMs / totalMs;
      const totalDays = Math.round(totalMs / (1000 * 60 * 60 * 24));
      const elapsedDays = Math.min(totalDays, Math.round(elapsedMs / (1000 * 60 * 60 * 24)));

      currentX = startX + progressRatio * totalTrackLength;

      const dateStr = now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      beaconTitle = `● TODAY • DAY ${elapsedDays + 1} OF ${totalDays}`;
      beaconSub = `${dateStr} • Real-time timeline position`;
    }

    this.currentBeaconX = currentX;

    // 2. SIGG Branch Coordinates (Oct '26 station 1 to Apr '27 station 7)
    const siggStartX = startX + 1 * spacing;
    const siggEndX = startX + 7 * spacing;
    const siggTrackY = spineY + 65;

    // 3. Phase Boundaries (Subtle Architectural Markers)
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
          <div class="phase-zone-label" style="left: ${p.x - 40}px;">
            ${p.name}
          </div>
        `;
      })
      .join("");

    // 4. Build SVG Graphic Tracks (One Solid Spine + SIGG Express Bypass)
    let svgHtml = `
      <svg width="${totalWidth}" height="520" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <defs>
          <filter id="beaconGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- Subtle Vertical Phase Dividers -->
        ${phases
          .map(
            (p) =>
              `<line x1="${p.x - 40}" y1="36" x2="${p.x - 40}" y2="480" stroke="rgba(255,255,255,0.04)" stroke-dasharray="3 4" stroke-width="1" />`
          )
          .join("")}

        <!-- SIGG Express Branch Line (Terracotta) -->
        <path d="M ${siggStartX - 40} ${spineY} 
                 L ${siggStartX} ${siggTrackY} 
                 L ${siggEndX} ${siggTrackY} 
                 L ${siggEndX + 40} ${spineY}" 
              fill="none" stroke="rgba(208, 135, 112, 0.4)" stroke-width="3" stroke-linejoin="round" />

        <!-- THE MAIN TRANSIT SPINE (Unvisited Track Bed) -->
        <line x1="${startX}" y1="${spineY}" x2="${startX + totalTrackLength}" y2="${spineY}" 
              stroke="rgba(255, 255, 255, 0.12)" stroke-width="6" stroke-linecap="round" />

        <!-- ACTIVE ILLUMINATED SPINE (Progress Filled to Today) -->
        ${
          currentX > startX
            ? `
          <line x1="${startX}" y1="${spineY}" x2="${currentX}" y2="${spineY}" 
                stroke="#ffffff" stroke-width="6" stroke-linecap="round" filter="url(#beaconGlow)" />
        `
            : ""
        }

        <!-- Vertical Connectors between Spine and Station Cards -->
        ${stations
          .map((station, idx) => {
            const posX = startX + idx * spacing;
            const isEven = idx % 2 === 0;
            // Even: card above spine (bottom at spineY - 45). Odd: card below spine (top at spineY + 45)
            const y1 = isEven ? spineY - 45 : spineY + 12;
            const y2 = isEven ? spineY - 12 : spineY + 45;

            return `
              <line x1="${posX}" y1="${y1}" x2="${posX}" y2="${y2}" 
                    stroke="rgba(255, 255, 255, 0.22)" stroke-width="1.5" stroke-dasharray="2 3" />
            `;
          })
          .join("")}
      </svg>
    `;

    // 5. Build HTML Station Cards & Nodes (Alternating Top & Bottom)
    let cardsHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isMajor = station.is_major;
        const isEven = idx % 2 === 0;
        const status = station.status || "upcoming";
        const isPassed = posX <= currentX;

        // Station card position:
        // Even: Top row (top = spineY - 170)
        // Odd: Bottom row (top = spineY + 45)
        const cardTop = isEven ? spineY - 165 : spineY + 45;
        const cardLeft = posX - 105; // Center 210px card on node

        // Node disc style on the spine
        let nodeContent = "";
        let nodeStyle = "background: #101216; border: 2.5px solid rgba(255,255,255,0.4);";
        if (status === "completed" || (isPassed && !isPreLaunch)) {
          nodeStyle = "background: #ffffff; border: 2.5px solid #ffffff;";
          nodeContent = `<span style="color: #08090a; font-size: 10px; font-weight: 800; line-height: 1;">✓</span>`;
        } else if (status === "active") {
          nodeStyle = "background: #ffffff; border: 2.5px solid #ffffff; box-shadow: 0 0 14px rgba(255,255,255,0.9);";
        }

        const size = isMajor ? 24 : 18;

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

        // Station card checklist progress
        const delivEntries = Object.keys(station.deliverables || {});
        const totalDelivs = delivEntries.length;
        const completedDelivs = (station.completed_deliverables || []).length;
        let checklistBadge = "";
        if (totalDelivs > 0) {
          if (completedDelivs >= totalDelivs) {
            checklistBadge = `<span class="card-checklist-badge complete">✓ ALL ${totalDelivs}</span>`;
          } else if (completedDelivs > 0) {
            checklistBadge = `<span class="card-checklist-badge">${completedDelivs}/${totalDelivs} ✓</span>`;
          } else {
            checklistBadge = `<span class="card-checklist-badge">${completedDelivs}/${totalDelivs}</span>`;
          }
        }

        return `
          <!-- Station Node On The Spine -->
          <div 
            class="spine-node-point" 
            style="left: ${posX}px; top: ${spineY}px;"
            onclick="MetroMap.selectStation('${station.id}')"
            title="${this.escapeHtml(station.name)} (${station.month_label})"
          >
            <div 
              style="width: ${size}px; height: ${size}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; ${nodeStyle}"
            >
              ${nodeContent}
            </div>
          </div>

          <!-- Clean Horizontal Station Card -->
          <div 
            class="metro-spine-card ${isMajor ? "major" : ""} ${status === "completed" ? "completed-card" : ""} ${status === "active" ? "active-card" : ""}" 
            style="left: ${cardLeft}px; top: ${cardTop}px;"
            onclick="MetroMap.selectStation('${station.id}')"
          >
            <div class="card-header-row">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="card-month-tag">${station.month_label}</span>
                ${checklistBadge}
              </div>
              ${isMajor ? '<span class="key-pill" style="border-color: rgba(197, 160, 89, 0.4); color: var(--accent-gold-dim); font-size: 8px;">MAJOR</span>' : ""}
            </div>
            <div class="card-title-text" title="${this.escapeHtml(station.name)}">
              ${this.escapeHtml(station.name)}
            </div>
            <div class="card-chips-row">
              ${chipsHtml}
            </div>
          </div>
        `;
      })
      .join("");

    // 6. Build Real-Time Day Beacon (Compass Pulse on Spine)
    const beaconHtml = `
      <div class="day-beacon-wrap" style="left: ${currentX}px; top: ${spineY}px;">
        <!-- Overhead Floating HUD Flag -->
        <div class="day-beacon-hud" style="bottom: 30px;">
          <span class="beacon-tag">${beaconTitle}</span>
          <span class="beacon-sub">${beaconSub}</span>
        </div>

        <!-- Glowing Core Pulse -->
        <div class="day-beacon-core"></div>
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

    // Deliverables interactive checklist breakdown
    const deliverablesList = document.getElementById("drawerDeliverablesList");
    if (deliverablesList && station.deliverables) {
      const allEntries = Object.entries(station.deliverables);
      const totalDelivs = allEntries.length;
      const completedList = station.completed_deliverables || [];
      const completedCount = completedList.length;
      const progressPercent = totalDelivs > 0 ? Math.round((completedCount / totalDelivs) * 100) : 0;
      const isAllComplete = totalDelivs > 0 && completedCount >= totalDelivs;

      const progressHeader = `
        <div class="deliverables-progress-box">
          <div class="deliverables-progress-header">
            <span>Deliverables Checklist (${completedCount}/${totalDelivs})</span>
            <span style="${isAllComplete ? "color: #ffffff; font-weight: 700;" : ""}">${isAllComplete ? "STATION COMPLETED ✓" : `${progressPercent}%`}</span>
          </div>
          <div class="deliverables-progress-track">
            <div class="deliverables-progress-fill" style="width: ${progressPercent}%; ${isAllComplete ? "background: #ffffff; box-shadow: 0 0 8px rgba(255,255,255,0.6);" : ""}"></div>
          </div>
        </div>
      `;

      const itemsHtml = allEntries
        .map(([key, val]) => {
          let lineBadgeColor = "var(--text-secondary)";
          if (key.toLowerCase().includes("code")) lineBadgeColor = "#8ba3c7";
          if (key.toLowerCase().includes("academic")) lineBadgeColor = "#c5a059";
          if (key.toLowerCase().includes("sigg")) lineBadgeColor = "#d08770";
          if (key.toLowerCase().includes("german")) lineBadgeColor = "#98b0a1";

          const isChecked = completedList.includes(key);

          return `
            <div 
              class="deliverable-item ${isChecked ? "checked" : ""}" 
              onclick="MetroMap.toggleDeliverable('${station.id}', '${this.escapeHtml(key)}')"
              title="Click to toggle deliverable completion"
            >
              <div class="deliverable-check-dot"></div>
              <div class="deliverable-content">
                <div class="deliverable-line-badge" style="color: ${lineBadgeColor};">
                  ${key} LINE
                </div>
                <div class="deliverable-desc">
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

        // Live re-render
        this.render();
        if (this.selectedStation && this.selectedStation.id === stationId) {
          this.openDrawer(this.selectedStation);
        }

        if (res.station_completed) {
          window.HarnessApp.showToast(`Station Completed: ${st.name}! All deliverables met.`);
        } else if (res.is_checked) {
          window.HarnessApp.showToast(`Checked: ${deliverableKey} (${res.completed_count}/${res.total_count})`);
        }
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
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};

window.MetroMap = MetroMap;
