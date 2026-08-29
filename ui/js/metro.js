/**
 * Section 2: TUM ROADMAP & ICONIC METRO TRANSIT ENGINE
 * - Authentic 5-line parallel transit corridor (Trunk, CS, Academics, SIGG, German).
 * - Real-Time Day Beacon: Daily moving train that advances day by day from Sep '26 to Jul '28.
 * - Dynamic track illumination: Track fills up to today's exact position.
 * - Alternating 35° angled transit typography: Zero label overlap, 100% legibility.
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
      if (e.target.closest(".station-node-v2") || e.target.closest(".station-drawer")) return;
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
    const spacing = 160;
    const startX = 160;
    const totalTrackLength = (stations.length - 1) * spacing;
    const totalWidth = startX + totalTrackLength + 320;

    canvasWrap.style.minWidth = `${totalWidth}px`;

    // 1. Parallel Track Corridor Coordinates (Strict Beck angles)
    const trackCS = 150;       // Line 1: CS & Code Independence (Glacier Blue)
    const trackAca = 185;      // Line 2: Academics & GPA (Champagne Gold)
    const trackTrunk = 230;    // Line 3: TUM Central Trunk (Pure White)
    const trackSIGG = 275;     // Line 4: SIGG GPW (Terracotta)
    const trackGerman = 310;   // Line 5: German Goethe (Sage Green)

    // 2. Real-Time Day Progress Calculation (Advances day by day)
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
      currentX = startX - 50;
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
      beaconTitle = `▲ YOU ARE HERE • DAY ${elapsedDays + 1} OF ${totalDays}`;
      beaconSub = `${dateStr} // Real-time position`;
    }

    this.currentBeaconX = currentX;

    // 3. Render SVG Tracks (Background Guide Rails + Illuminated Active Beams)
    const siggStartIdx = 1; // Oct '26
    const siggEndIdx = 7;   // Apr '27 (Warsaw GPW Finals)
    const siggStartX = startX + siggStartIdx * spacing;
    const siggEndX = startX + siggEndIdx * spacing;

    let svgHtml = `
      <svg width="${totalWidth}" height="480" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <defs>
          <filter id="beaconGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- ================= BACKGROUND GUIDE TRACKS ================= -->
        <!-- Track 1: CS & Code Independence -->
        <line x1="${startX}" y1="${trackCS}" x2="${startX + totalTrackLength}" y2="${trackCS}" 
              stroke="rgba(122, 162, 247, 0.2)" stroke-width="3" stroke-linecap="round" />

        <!-- Track 2: Academics & GPA -->
        <line x1="${startX}" y1="${trackAca}" x2="${startX + totalTrackLength}" y2="${trackAca}" 
              stroke="rgba(224, 175, 104, 0.2)" stroke-width="3" stroke-linecap="round" />

        <!-- Track 3: TUM Central Trunk (Projected Track Bed) -->
        <line x1="${startX}" y1="${trackTrunk}" x2="${startX + totalTrackLength}" y2="${trackTrunk}" 
              stroke="rgba(255, 255, 255, 0.18)" stroke-width="7" stroke-linecap="round" />

        <!-- Track 4: SIGG GPW Branch (Oct '26 to Apr '27 Finals) -->
        <path d="M ${siggStartX - 30} ${trackTrunk} 
                 L ${siggStartX} ${trackSIGG} 
                 L ${siggEndX} ${trackSIGG} 
                 L ${siggEndX + 30} ${trackTrunk}" 
              fill="none" stroke="rgba(247, 118, 142, 0.25)" stroke-width="3" stroke-linejoin="round" />

        <!-- Track 5: German Goethe Ladder -->
        <line x1="${startX}" y1="${trackGerman}" x2="${startX + totalTrackLength}" y2="${trackGerman}" 
              stroke="rgba(115, 218, 202, 0.2)" stroke-width="3" stroke-linecap="round" />

        <!-- ================= ACTIVE ILLUMINATED TRACKS (Filled up to today) ================= -->
        ${
          currentX > startX
            ? `
          <!-- Illuminated Central Trunk -->
          <line x1="${startX}" y1="${trackTrunk}" x2="${currentX}" y2="${trackTrunk}" 
                stroke="#ffffff" stroke-width="7" stroke-linecap="round" filter="url(#beaconGlow)" />

          <!-- Illuminated CS Branch -->
          <line x1="${startX}" y1="${trackCS}" x2="${currentX}" y2="${trackCS}" 
                stroke="#7aa2f7" stroke-width="3" stroke-linecap="round" />

          <!-- Illuminated Academics Branch -->
          <line x1="${startX}" y1="${trackAca}" x2="${currentX}" y2="${trackAca}" 
                stroke="#e0af68" stroke-width="3" stroke-linecap="round" />

          <!-- Illuminated German Branch -->
          <line x1="${startX}" y1="${trackGerman}" x2="${currentX}" y2="${trackGerman}" 
                stroke="#73daca" stroke-width="3" stroke-linecap="round" />
        `
            : ""
        }

        <!-- ================= STATION INTERCHANGE CONNECTORS & TICKS ================= -->
        ${stations
          .map((station, idx) => {
            const posX = startX + idx * spacing;
            const isMajor = station.is_major;
            const isEven = idx % 2 === 0;

            // Vertical capsule or transfer connector
            const topY = trackCS - 4;
            const bottomY = station.branches?.includes("sigg") ? trackSIGG + 4 : trackGerman + 4;

            return `
              <!-- Interchange capsule connecting active tracks -->
              <line x1="${posX}" y1="${topY}" x2="${posX}" y2="${bottomY}" 
                    stroke="${isMajor ? "rgba(255,255,255,0.45)" : "rgba(255,255,255,0.18)"}" 
                    stroke-width="${isMajor ? "4" : "2"}" stroke-linecap="round" />

              <!-- Label Leader Tick -->
              <line x1="${posX}" y1="${isEven ? topY : bottomY}" x2="${posX}" y2="${isEven ? topY - 20 : bottomY + 20}" 
                    stroke="rgba(255,255,255,0.3)" stroke-width="1.5" />
            `;
          })
          .join("")}
      </svg>
    `;

    // 4. Build HTML Station Nodes & 35° Angled Typography
    let nodesHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const isMajor = station.is_major;
        const isEven = idx % 2 === 0;
        const status = station.status || "upcoming";
        const isPassed = posX <= currentX;

        // Visual style for station center dot
        let dotStyle = "";
        let dotContent = "";
        if (status === "completed" || (isPassed && !isPreLaunch)) {
          dotStyle = "background: #ffffff; border-color: #ffffff;";
          dotContent = `<span style="color: #08090a; font-size: 10px; font-weight: 800; line-height: 1;">✓</span>`;
        } else if (status === "active") {
          dotStyle = "background: #ffffff; border-color: #ffffff; box-shadow: 0 0 16px rgba(255,255,255,0.9);";
        }

        return `
          <!-- Station Click Target on Trunk Track -->
          <div 
            class="station-node-v2" 
            style="left: ${posX}px; top: ${trackTrunk}px; transform: translate(-50%, -50%);"
            onclick="MetroMap.selectStation('${station.id}')"
            title="${this.escapeHtml(station.name)} (${station.month_label})"
          >
            <!-- Central Trunk Station Disc -->
            <div 
              style="width: ${isMajor ? "22px" : "16px"}; height: ${isMajor ? "22px" : "16px"}; border-radius: 50%; border: 3px solid #ffffff; background: #101216; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; ${dotStyle}"
            >
              ${dotContent}
            </div>

            <!-- Alternating Angled Typography (Prevents any overlap) -->
            <div class="${isEven ? "station-label-angled-up" : "station-label-angled-down"}">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="key-pill" style="font-size: 9px; font-weight: 700; ${isMajor ? "border-color: rgba(255,255,255,0.4); color: #ffffff;" : ""}">
                  ${station.month_label}
                </span>
                ${isMajor ? '<span style="font-size: 8px; text-transform: uppercase; color: var(--accent-gold-dim); font-weight: 700; letter-spacing: 0.5px;">MAJOR</span>' : ""}
              </div>
              <div style="font-size: 12px; font-weight: 600; color: ${isMajor ? "#ffffff" : "var(--text-primary)"}; margin-top: 3px;">
                ${this.escapeHtml(station.name)}
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    // 5. Build Real-Time Day Beacon Indicator (Moving Train on Trunk Line)
    const beaconHtml = `
      <div class="day-beacon-wrap" style="left: ${currentX}px; top: ${trackTrunk}px;">
        <!-- Overhead Floating HUD Flag -->
        <div class="day-beacon-hud">
          <span class="beacon-tag">${beaconTitle}</span>
          <span class="beacon-sub">${beaconSub}</span>
        </div>

        <!-- Glowing Core Pulse -->
        <div class="day-beacon-core"></div>
      </div>
    `;

    canvasWrap.innerHTML = svgHtml + nodesHtml + beaconHtml;
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
      deliverablesList.innerHTML = Object.entries(station.deliverables)
        .map(([key, val]) => {
          let lineBadgeColor = "var(--text-secondary)";
          if (key.toLowerCase().includes("code")) lineBadgeColor = "#7aa2f7";
          if (key.toLowerCase().includes("academic")) lineBadgeColor = "#e0af68";
          if (key.toLowerCase().includes("sigg")) lineBadgeColor = "#f7768e";
          if (key.toLowerCase().includes("german")) lineBadgeColor = "#73daca";

          return `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-hairline); border-radius: 4px; padding: 8px 10px; margin-bottom: 6px;">
              <div style="font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: ${lineBadgeColor}; font-weight: 700; margin-bottom: 2px;">
                ${key} LINE
              </div>
              <div style="font-size: 12px; color: var(--text-primary); line-height: 1.4;">
                ${this.escapeHtml(val)}
              </div>
            </div>
          `;
        })
        .join("");
    }

    drawer.classList.add("open");
  },

  closeDrawer() {
    const drawer = document.getElementById("stationDrawer");
    if (drawer) drawer.classList.remove("open");
    this.selectedStation = null;
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
