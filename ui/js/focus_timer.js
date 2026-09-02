/**
 * Focus HUD: Deep Work & Sprint Timer for TUM/Matura sprints.
 * Provides 60m Math R, 60m CS Code, 25m Pomodoro, and custom timers.
 * Synthesizes audio completion tones via Web Audio API.
 */

const FocusTimer = {
  durationSeconds: 60 * 60, // Default 60 minutes
  remainingSeconds: 60 * 60,
  timerInterval: null,
  isRunning: false,
  currentPresetName: "60m Math R",

  presets: [
    { name: "60m Math R", seconds: 60 * 60 },
    { name: "60m CS Code", seconds: 60 * 60 },
    { name: "25m Sprint", seconds: 25 * 60 },
    { name: "50m Lift", seconds: 50 * 60 },
  ],

  init() {
    this.createDom();
    this.bindEvents();
    this.updateDisplay();
  },

  createDom() {
    // Header HUD Pill
    const headerRight = document.querySelector(".header-right");
    if (!headerRight || document.getElementById("focusTimerPill")) return;

    const timerPill = document.createElement("div");
    timerPill.id = "focusTimerPill";
    timerPill.className = "streak-pill";
    timerPill.style.cursor = "pointer";
    timerPill.title = "Focus Deep Work Timer (Click to open controls, Space to start/pause)";
    timerPill.innerHTML = `
      <span style="color: var(--accent-purple-light); font-size: 11px;">⏱</span>
      <span id="focusTimeDisplay" style="font-family: var(--font-mono); font-weight: 700; color: var(--text-primary);">60:00</span>
      <span id="focusPresetLabel" style="font-size: 9px; color: var(--text-tertiary); text-transform: uppercase;">Math R</span>
    `;
    headerRight.insertBefore(timerPill, headerRight.firstChild);

    timerPill.addEventListener("click", () => this.toggleDrawer());

    // Drawer overlay for controls
    const modal = document.createElement("div");
    modal.id = "focusTimerModal";
    modal.className = "modal-overlay";
    modal.style.display = "none";
    modal.innerHTML = `
      <div class="modal-card" style="max-width: 440px; text-align: center; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <span class="card-label">TUM Deep Work Timer</span>
          <button id="btnCloseFocusModal" class="drawer-close-btn">&times;</button>
        </div>

        <div style="margin: 20px 0;">
          <div id="focusModalBigTime" style="font-size: 48px; font-weight: 800; font-family: var(--font-mono); color: var(--text-primary); letter-spacing: -1px;">
            60:00
          </div>
          <div id="focusModalPresetName" style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-purple-light); text-transform: uppercase; margin-top: 4px;">
            60m Math R Focus Sprint
          </div>
        </div>

        <!-- Presets Row -->
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; margin-bottom: 20px;">
          ${this.presets
            .map(
              (p, idx) => `
            <button 
              class="btn-ghost-icon ${idx === 0 ? "active" : ""}" 
              style="font-size: 10px; padding: 6px 2px; justify-content: center;"
              onclick="FocusTimer.selectPreset(${idx})"
            >
              ${p.name}
            </button>
          `
            )
            .join("")}
        </div>

        <!-- Actions -->
        <div style="display: flex; justify-content: center; gap: 10px;">
          <button id="btnToggleFocusTimer" class="btn-ghost-icon" style="padding: 8px 24px; font-weight: 600; color: var(--text-primary); border-color: var(--accent-purple);">
            Start Focus
          </button>
          <button id="btnResetFocusTimer" class="btn-ghost-icon" style="padding: 8px 16px;">
            Reset
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener("click", (e) => {
      if (e.target === modal) this.closeDrawer();
    });

    document.getElementById("btnCloseFocusModal").addEventListener("click", () => this.closeDrawer());
    document.getElementById("btnToggleFocusTimer").addEventListener("click", () => this.toggleTimer());
    document.getElementById("btnResetFocusTimer").addEventListener("click", () => this.resetTimer());
  },

  bindEvents() {
    document.addEventListener("keydown", (e) => {
      // Hotkey 'T' to open timer HUD (if not in an input/textarea)
      const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea") return;

      if (e.key.toLowerCase() === "t" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        this.toggleDrawer();
      }
    });
  },

  toggleDrawer() {
    const modal = document.getElementById("focusTimerModal");
    if (!modal) return;
    if (modal.style.display === "none" || !modal.style.display) {
      modal.style.display = "flex";
    } else {
      modal.style.display = "none";
    }
  },

  closeDrawer() {
    const modal = document.getElementById("focusTimerModal");
    if (modal) modal.style.display = "none";
  },

  selectPreset(index) {
    const preset = this.presets[index];
    if (!preset) return;
    this.pauseTimer();
    this.durationSeconds = preset.seconds;
    this.remainingSeconds = preset.seconds;
    this.currentPresetName = preset.name;

    // Update preset buttons active state
    const buttons = document.querySelectorAll("#focusTimerModal .btn-ghost-icon");
    buttons.forEach((btn, idx) => {
      if (idx < this.presets.length) {
        if (idx === index) btn.classList.add("active");
        else btn.classList.remove("active");
      }
    });

    this.updateDisplay();
  },

  toggleTimer() {
    if (this.isRunning) {
      this.pauseTimer();
    } else {
      this.startTimer();
    }
  },

  startTimer() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.updateControls();

    this.timerInterval = setInterval(() => {
      if (this.remainingSeconds > 0) {
        this.remainingSeconds--;
        this.updateDisplay();
      } else {
        this.completeTimer();
      }
    }, 1000);
  },

  pauseTimer() {
    this.isRunning = false;
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    this.updateControls();
  },

  resetTimer() {
    this.pauseTimer();
    this.remainingSeconds = this.durationSeconds;
    this.updateDisplay();
  },

  completeTimer() {
    this.pauseTimer();
    this.playTone();
    window.HarnessApp.showToast(`Focus block completed: ${this.currentPresetName}!`);

    // Auto-mark completed block in daily log if Today is loaded
    if (window.Today) {
      const activeIdx = "0";
      window.Today.completedBlocks.add(activeIdx);
      window.Today.saveDailyLog();
      window.Today.render();
    }
  },

  updateDisplay() {
    const mins = Math.floor(this.remainingSeconds / 60);
    const secs = this.remainingSeconds % 60;
    const formatted = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

    const pillDisplay = document.getElementById("focusTimeDisplay");
    const modalDisplay = document.getElementById("focusModalBigTime");
    const presetLabel = document.getElementById("focusPresetLabel");
    const modalPresetLabel = document.getElementById("focusModalPresetName");

    if (pillDisplay) pillDisplay.textContent = formatted;
    if (modalDisplay) modalDisplay.textContent = formatted;
    if (presetLabel) presetLabel.textContent = this.currentPresetName.replace("60m ", "").replace("25m ", "");
    if (modalPresetLabel) modalPresetLabel.textContent = `${this.currentPresetName} Focus Sprint`;
  },

  updateControls() {
    const btn = document.getElementById("btnToggleFocusTimer");
    if (btn) {
      btn.textContent = this.isRunning ? "Pause Focus" : "Start Focus";
      btn.style.borderColor = this.isRunning ? "var(--text-primary)" : "var(--accent-purple)";
    }
  },

  playTone() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.setValueAtTime(880.0, audioCtx.currentTime + 0.15); // A5

      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.6);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start();
      osc.stop(audioCtx.currentTime + 0.6);
    } catch (e) {
      console.log("Audio not supported or permitted");
    }
  },
};

window.FocusTimer = FocusTimer;
