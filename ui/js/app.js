/**
 * Master Application Controller, Navigation, and JSON Hub (Version 3.0)
 */

window.HarnessApp = {
  currentView: "dashboard",
  activeJsonTab: "schedules",
  allConfigs: null,
  initialized: false,

  init() {
    this.bindNavigation();
    this.bindKeybindings();
    this.bindModals();
    this.bindJsonModal();
    this.startClock();

    const startBridge = async () => {
      if (this.initialized) return;
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_today === "function") {
        this.initialized = true;
        await this.initAllLayers();
      }
    };

    window.addEventListener("pywebviewready", startBridge);

    // If bridge is already available (e.g. browser polyfill), start immediately
    if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_today === "function") {
      startBridge();
    }

    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      if (this.initialized || attempts > 60) {
        clearInterval(interval);
        return;
      }
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_today === "function") {
        clearInterval(interval);
        await startBridge();
      }
    }, 100);
  },

  async initAllLayers() {
    try {
      if (window.FocusTimer) window.FocusTimer.init();
      if (window.CommandPalette) window.CommandPalette.init();
      if (window.Dashboard) await window.Dashboard.init();
      if (window.Today) await window.Today.init();
      if (window.KillListDrawer) await window.KillListDrawer.init();
      if (window.Tum) await window.Tum.init();
      if (window.Projects) await window.Projects.init();
      if (window.Body) await window.Body.init();
      if (window.Knowledge) await window.Knowledge.init();
    } catch (err) {
      console.error("Error initializing layers:", err);
    }
  },

  bindNavigation() {
    const tabs = document.querySelectorAll("#navTabs .nav-tab");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const view = tab.getAttribute("data-view");
        this.switchView(view);
      });
    });
  },

  switchView(viewName) {
    if (!viewName || viewName === this.currentView) return;

    document.querySelectorAll("#navTabs .nav-tab").forEach((tab) => {
      if (tab.getAttribute("data-view") === viewName) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    document.querySelectorAll(".view-section").forEach((sec) => {
      if (sec.id === `view-${viewName}`) {
        sec.classList.add("active");
      } else {
        sec.classList.remove("active");
      }
    });

    this.currentView = viewName;

    // Refresh view data
    if (viewName === "dashboard" && window.Dashboard) window.Dashboard.load();
    if (viewName === "today" && window.Today) window.Today.load();
    if (viewName === "tum" && window.Tum) {
      window.Tum.load();
      if (window.MetroMap) window.MetroMap.load();
    }
    if (viewName === "projects" && window.Projects) window.Projects.load();
    if (viewName === "body" && window.Body) window.Body.load();
    if (viewName === "knowledge" && window.Knowledge) window.Knowledge.load();
  },

  bindModals() {
    // Universal backdrop click to close any modal overlay
    document.querySelectorAll(".modal-overlay").forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.classList.remove("open");
        }
      });
    });
  },

  bindKeybindings() {
    window.addEventListener("keydown", (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      const isInput = activeTag === "input" || activeTag === "textarea" || activeTag === "select";

      if (isInput) {
        if (e.key === "Escape") {
          document.activeElement.blur();
          this.closeAllModals();
        }
        return;
      }

      if (e.key === "0" || e.key === "`") {
        e.preventDefault();
        this.switchView("dashboard");
      } else if (e.key === "1") {
        e.preventDefault();
        this.switchView("today");
      } else if (e.key === "2") {
        e.preventDefault();
        this.switchView("tum");
      } else if (e.key === "3") {
        e.preventDefault();
        this.switchView("projects");
      } else if (e.key === "4") {
        e.preventDefault();
        this.switchView("body");
      } else if (e.key === "5") {
        e.preventDefault();
        this.switchView("knowledge");
      }

      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        this.switchView("today");
        const quickInput = document.getElementById("quickTaskInput");
        if (quickInput) quickInput.focus();
      }

      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        if (window.Today) window.Today.handleRollover();
      }

      if (e.key === "Escape") {
        this.closeAllModals();
      }
    });
  },

  closeAllModals() {
    document.querySelectorAll(".modal-overlay").forEach((m) => m.classList.remove("open"));
    if (window.MetroMap) window.MetroMap.closeDrawer();
  },

  bindJsonModal() {
    const btnOpen = document.getElementById("btnOpenJsonModal");
    const btnClose = document.getElementById("btnCloseJsonModal");
    const modal = document.getElementById("jsonModal");

    if (btnOpen) {
      btnOpen.addEventListener("click", async () => {
        await this.openJsonModal();
      });
    }

    if (btnClose) {
      btnClose.addEventListener("click", () => this.closeJsonModal());
    }

    const tabSched = document.getElementById("btnJsonTabSchedules");
    const tabGym = document.getElementById("btnJsonTabGym");
    const tabRoadmap = document.getElementById("btnJsonTabRoadmap");

    if (tabSched) {
      tabSched.addEventListener("click", () => this.switchJsonTab("schedules"));
    }
    if (tabGym) {
      tabGym.addEventListener("click", () => this.switchJsonTab("gym_routines"));
    }
    if (tabRoadmap) {
      tabRoadmap.addEventListener("click", () => this.switchJsonTab("metro_roadmap"));
    }

    const btnSave = document.getElementById("btnSaveJsonConfig");
    if (btnSave) {
      btnSave.addEventListener("click", async () => {
        await this.saveJsonConfig();
      });
    }
  },

  async openJsonModal() {
    const modal = document.getElementById("jsonModal");
    if (!modal) return;

    try {
      if (window.pywebview && window.pywebview.api) {
        this.allConfigs = await window.pywebview.api.get_all_configs();
        this.switchJsonTab(this.activeJsonTab || "schedules");
      }
      modal.classList.add("open");
    } catch (err) {
      console.error("Error opening JSON modal:", err);
    }
  },

  closeJsonModal() {
    const modal = document.getElementById("jsonModal");
    if (modal) modal.classList.remove("open");
  },

  switchJsonTab(tabName) {
    this.activeJsonTab = tabName;
    const tabSched = document.getElementById("btnJsonTabSchedules");
    const tabGym = document.getElementById("btnJsonTabGym");
    const tabRoadmap = document.getElementById("btnJsonTabRoadmap");
    const textarea = document.getElementById("jsonConfigTextarea");

    [tabSched, tabGym, tabRoadmap].forEach((btn) => btn?.classList.remove("active"));

    if (tabName === "schedules" && tabSched) tabSched.classList.add("active");
    if (tabName === "gym_routines" && tabGym) tabGym.classList.add("active");
    if (tabName === "metro_roadmap" && tabRoadmap) tabRoadmap.classList.add("active");

    if (textarea && this.allConfigs) {
      const data = this.allConfigs[tabName] || {};
      textarea.value = JSON.stringify(data, null, 2);
    }
  },

  async saveJsonConfig() {
    const textarea = document.getElementById("jsonConfigTextarea");
    const statusEl = document.getElementById("jsonImportStatus");
    if (!textarea) return;

    const raw = textarea.value.trim();
    try {
      JSON.parse(raw);
    } catch (e) {
      if (statusEl) statusEl.textContent = `JSON Error: ${e.message}`;
      return;
    }

    try {
      const success = await window.pywebview.api.import_config(this.activeJsonTab, raw);
      if (success) {
        if (statusEl) statusEl.textContent = "Saved & Applied.";
        this.showToast("Configuration saved");
        await this.initAllLayers();
        setTimeout(() => {
          if (statusEl) statusEl.textContent = "";
        }, 2000);
      } else {
        if (statusEl) statusEl.textContent = "Failed to write file.";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = `Error: ${err}`;
    }
  },

  startClock() {
    const dateEl = document.getElementById("currentDatePill");
    const timeEl = document.getElementById("currentTimePill");

    const updateTime = () => {
      const now = new Date();
      if (dateEl) {
        dateEl.textContent = now.toLocaleDateString("en-US", {
          weekday: "short",
          month: "short",
          day: "numeric",
        });
      }
      if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
      }
    };

    updateTime();
    setInterval(updateTime, 1000);
  },

  showToast(message, durationMs = 2400) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.style.cssText = `
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-medium);
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 500;
      color: var(--text-primary);
      box-shadow: var(--shadow-dropdown);
      animation: fadeIn 0.15s ease-out;
    `;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(10px)";
      toast.style.transition = "all 0.15s ease";
      setTimeout(() => toast.remove(), 150);
    }, durationMs);
  },
};

document.addEventListener("DOMContentLoaded", () => {
  window.HarnessApp.init();
});
