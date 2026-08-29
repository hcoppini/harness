/**
 * Harness Metro Map Engine:
 * Horizontal, draggable, interactive metro-line roadmap for TUM Heilbronn journey.
 */

const MetroMap = {
  data: null,
  isDragging: false,
  startX: 0,
  scrollLeft: 0,
  selectedStation: null,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    const container = document.getElementById("metroScrollContainer");
    if (!container) return;

    // Mouse drag scrolling with grab/grabbing
    container.addEventListener("mousedown", (e) => {
      // Don't drag if clicking inside station node or drawer
      if (e.target.closest(".station-node") || e.target.closest(".station-drawer")) return;
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
      const walk = (x - this.startX) * 1.5; // Smooth multiplier
      container.scrollLeft = this.scrollLeft - walk;
    });

    // Horizontal wheel navigation
    container.addEventListener("wheel", (e) => {
      if (e.deltaY !== 0) {
        e.preventDefault();
        container.scrollLeft += e.deltaY;
      }
    }, { passive: false });

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

    // Jump to current station
    const btnJump = document.getElementById("btnJumpCurrentStation");
    if (btnJump) {
      btnJump.addEventListener("click", () => this.scrollToCurrent());
    }
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.data = await window.pywebview.api.get_metro_roadmap();
      this.render();
    } catch (err) {
      console.error("Error loading Metro Roadmap:", err);
    }
  },

  render() {
    if (!this.data || !this.data.stations) return;

    const canvasWrap = document.getElementById("metroCanvasWrap");
    if (!canvasWrap) return;

    const stations = this.data.stations;
    const spacing = 145; // Horizontal distance between monthly stations
    const startX = 120;
    const trunkY = 220;
    const totalWidth = startX + stations.length * spacing + 250;

    canvasWrap.style.minWidth = `${totalWidth}px`;

    // 1. Build SVG tracks for Main line and Branches
    let svgHtml = `
      <svg width="${totalWidth}" height="460" style="position: absolute; top: 0; left: 0; pointer-events: none;">
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <!-- Main Trunk Track Backbone -->
        <line x1="${startX}" y1="${trunkY}" x2="${startX + (stations.length - 1) * spacing}" y2="${trunkY}" 
              stroke="rgba(255, 255, 255, 0.25)" stroke-width="6" stroke-linecap="round" />
        
        <!-- Active Progress Line -->
        <line x1="${startX}" y1="${trunkY}" x2="${startX + spacing * 1.5}" y2="${trunkY}" 
              stroke="#ffffff" stroke-width="6" stroke-linecap="round" />

        <!-- Branch Line 1: Academics (Top) -->
        <path d="M ${startX} ${trunkY} Q ${startX + 50} 130, ${startX + 120} 130 L ${startX + (stations.length - 1) * spacing} 130" 
              fill="none" stroke="rgba(197, 160, 89, 0.35)" stroke-width="2.5" stroke-dasharray="4 4" />
        
        <!-- Branch Line 2: Code Independence -->
        <path d="M ${startX} ${trunkY} Q ${startX + 60} 175, ${startX + 140} 175 L ${startX + 14 * spacing} 175 Q ${startX + 15 * spacing} 175, ${startX + 15 * spacing} ${trunkY}" 
              fill="none" stroke="rgba(139, 163, 199, 0.4)" stroke-width="2.5" />

        <!-- Branch Line 3: German Ladder (Bottom) -->
        <path d="M ${startX} ${trunkY} Q ${startX + 60} 290, ${startX + 130} 290 L ${startX + 18 * spacing} 290 Q ${startX + 19 * spacing} 290, ${startX + 20 * spacing} ${trunkY}" 
              fill="none" stroke="rgba(152, 176, 161, 0.4)" stroke-width="2.5" stroke-dasharray="5 3" />

        <!-- Branch Line 4: SIGG Contest (Bottom 2) -->
        <path d="M ${startX + spacing} ${trunkY} Q ${startX + 1.5 * spacing} 350, ${startX + 2 * spacing} 350 L ${startX + 7 * spacing} 350 Q ${startX + 7.5 * spacing} 350, ${startX + 8 * spacing} ${trunkY}" 
              fill="none" stroke="rgba(208, 135, 112, 0.45)" stroke-width="2.5" />
      </svg>
    `;

    // 2. Build HTML station nodes
    let nodesHtml = stations
      .map((station, idx) => {
        const posX = startX + idx * spacing;
        const posY = trunkY;
        const isMajor = station.is_major;
        const statusClass = station.status || "upcoming";

        return `
          <div 
            class="station-node ${isMajor ? "major" : ""} ${statusClass}" 
            style="left: ${posX}px; top: ${posY}px;"
            onclick="MetroMap.selectStation('${station.id}')"
            title="${station.name} (${station.month_label})"
          >
            <div class="station-dot"></div>
            <div class="station-label">
              <div class="station-month">${station.month_label}</div>
              <div class="station-name">${this.escapeHtml(station.name)}</div>
            </div>
          </div>
        `;
      })
      .join("");

    canvasWrap.innerHTML = svgHtml + nodesHtml;
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
          return `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-hairline); border-radius: 4px; padding: 8px 10px; margin-bottom: 6px;">
              <div style="font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 2px;">
                ${key}
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
      window.HarnessApp.showToast(`Station updated to ${newStatus}`);
    } catch (err) {
      console.error("Error updating station status:", err);
    }
  },

  scrollToCurrent() {
    const container = document.getElementById("metroScrollContainer");
    if (container) {
      container.scrollTo({ left: 0, behavior: "smooth" });
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
