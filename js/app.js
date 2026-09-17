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
    this.bindSyncModal();
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
      // Render active layer (Dashboard) immediately for instant startup
      if (window.Dashboard) await window.Dashboard.init();

      // Initialize secondary layers asynchronously without blocking UI render
      Promise.allSettled([
        window.Today ? window.Today.init() : Promise.resolve(),
        window.KillListDrawer ? window.KillListDrawer.init() : Promise.resolve(),
        window.Tum ? window.Tum.init() : Promise.resolve(),
        window.Projects ? window.Projects.init() : Promise.resolve(),
        window.Body ? window.Body.init() : Promise.resolve(),
        window.Knowledge ? window.Knowledge.init() : Promise.resolve(),
      ]).catch((err) => console.warn("[App] Background layers init error:", err));

      // Non-blocking background sync initialization
      setTimeout(() => {
        this.initSync().catch((err) => console.warn("[App] Sync init error:", err));
      }, 50);
    } catch (err) {
      console.error("Error initializing layers:", err);
    }
  },

  bindNavigation() {
    const tabs = document.querySelectorAll("#navTabs .nav-tab, #mobileBottomNav .mobile-nav-tab");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const view = tab.getAttribute("data-view");
        this.switchView(view);
      });
    });
  },

  switchView(viewName) {
    if (!viewName) return;

    // Desktop nav tabs
    document.querySelectorAll("#navTabs .nav-tab").forEach((tab) => {
      if (tab.getAttribute("data-view") === viewName) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    // Mobile dock tabs
    document.querySelectorAll("#mobileBottomNav .mobile-nav-tab").forEach((tab) => {
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

    // Scroll to top on view change
    const mainContent = document.querySelector(".main-content");
    if (mainContent) mainContent.scrollTop = 0;
    window.scrollTo({ top: 0, behavior: "instant" });

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

      if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault();
        this.triggerSync(false);
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
    const tabSync = document.getElementById("btnJsonTabSync");

    if (tabSched) {
      tabSched.addEventListener("click", () => this.switchJsonTab("schedules"));
    }
    if (tabGym) {
      tabGym.addEventListener("click", () => this.switchJsonTab("gym_routines"));
    }
    if (tabRoadmap) {
      tabRoadmap.addEventListener("click", () => this.switchJsonTab("metro_roadmap"));
    }
    if (tabSync) {
      tabSync.addEventListener("click", () => this.switchJsonTab("sync_config"));
    }

    const btnSave = document.getElementById("btnSaveJsonConfig");
    if (btnSave) {
      btnSave.addEventListener("click", async () => {
        await this.saveJsonConfig();
      });
    }
  },

  async openJsonModal(initialTab = null) {
    const modal = document.getElementById("jsonModal");
    if (!modal) return;

    try {
      if (window.pywebview && window.pywebview.api) {
        this.allConfigs = await window.pywebview.api.get_all_configs();
        this.switchJsonTab(initialTab || this.activeJsonTab || "schedules");
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
    const tabSync = document.getElementById("btnJsonTabSync");
    const textarea = document.getElementById("jsonConfigTextarea");

    [tabSched, tabGym, tabRoadmap, tabSync].forEach((btn) => btn?.classList.remove("active"));

    if (tabName === "schedules" && tabSched) tabSched.classList.add("active");
    if (tabName === "gym_routines" && tabGym) tabGym.classList.add("active");
    if (tabName === "metro_roadmap" && tabRoadmap) tabRoadmap.classList.add("active");
    if (tabName === "sync_config" && tabSync) tabSync.classList.add("active");

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
        if (this.activeJsonTab === "sync_config") {
          await this.initSync();
        } else {
          await this.initAllLayers();
        }
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

  // =========================================================================
  // CROSS-DEVICE CLOUD & WEB SYNC ENGINE (Laptop <-> Desktop <-> Web)
  // =========================================================================
  syncTimer: null,
  _focusSyncBound: false,

  bindSyncModal() {
    const btnClose = document.getElementById("btnCloseSyncModal");
    const modal = document.getElementById("syncModal");
    const form = document.getElementById("syncSettingsForm");
    const btnSyncNow = document.getElementById("btnSyncNowFromModal");
    const btnUseLocal = document.getElementById("btnUseLocalSync");
    const btnOpenJson = document.getElementById("btnSyncOpenJsonHub");

    if (btnClose) {
      btnClose.addEventListener("click", () => this.closeSyncModal());
    }

    if (btnUseLocal) {
      btnUseLocal.addEventListener("click", () => {
        const input = document.getElementById("syncInputWebUrl");
        if (input) input.value = "http://localhost:5000";
      });
    }

    if (btnOpenJson) {
      btnOpenJson.addEventListener("click", () => {
        this.closeSyncModal();
        this.openJsonModal("sync_config");
      });
    }

    if (btnSyncNow) {
      btnSyncNow.addEventListener("click", async () => {
        await this.triggerSync(false);
        await this.refreshSyncModal();
      });
    }

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const webUrl = (document.getElementById("syncInputWebUrl")?.value || "").trim();
        const key = (document.getElementById("syncInputSupabaseKey")?.value || "").trim();
        const autoSync = Boolean(document.getElementById("syncInputAutoSync")?.checked);

        try {
          if (window.pywebview && window.pywebview.api) {
            if (typeof window.pywebview.api.save_sync_settings === "function") {
              await window.pywebview.api.save_sync_settings(webUrl, key, null, autoSync);
            } else {
              await window.pywebview.api.configure_web_sync(webUrl, autoSync);
            }
            this.showToast("Sync settings saved!");
            await this.triggerSync(false);
            await this.refreshSyncModal();
          }
        } catch (err) {
          console.error("Error saving sync settings:", err);
          this.showToast("Failed to save sync settings");
        }
      });
    }
  },

  async openSyncModal() {
    const modal = document.getElementById("syncModal");
    if (!modal) return;
    modal.classList.add("open");
    await this.refreshSyncModal();
  },

  closeSyncModal() {
    const modal = document.getElementById("syncModal");
    if (modal) modal.classList.remove("open");
  },

  async refreshSyncModal() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
      const status = await window.pywebview.api.get_sync_status();
      const pill = document.getElementById("syncModalStatusPill");
      const webInput = document.getElementById("syncInputWebUrl");
      const autoSyncCheck = document.getElementById("syncInputAutoSync");
      const lastTime = document.getElementById("syncModalLastTime");
      const modeText = document.getElementById("syncModalModeText");

      if (pill) {
        pill.textContent = (status.status || "ready").toUpperCase();
        pill.className = "mono-chip";
        if (status.status === "synced") pill.classList.add("lavender");
      }

      if (webInput && document.activeElement !== webInput) {
        webInput.value = status.web_url || "";
        if (!status.web_url && status.local_detected_url) {
          webInput.placeholder = `Detected local companion: ${status.local_detected_url}`;
        }
      }

      if (autoSyncCheck) {
        autoSyncCheck.checked = Boolean(status.auto_sync !== false);
      }

      if (lastTime) {
        lastTime.textContent = status.last_synced_at
          ? new Date(status.last_synced_at).toLocaleTimeString() + " (" + new Date(status.last_synced_at).toLocaleDateString() + ")"
          : "Never";
      }

      if (modeText) {
        if (status.has_web_url) {
          modeText.textContent = `Direct HTTP Sync (${status.web_url})`;
        } else if (status.local_detected_url) {
          modeText.textContent = `Local Auto-Detected (${status.local_detected_url})`;
        } else if (status.has_key) {
          modeText.textContent = "Supabase Cloud Sync";
        } else {
          modeText.textContent = "Local Only (Offline SQLite WAL)";
        }
      }
    } catch (e) {
      console.warn("Failed to refresh sync modal:", e);
    }
  },

  async initSync() {
    const badge = document.getElementById("syncStatusBadge");
    if (!badge || !window.pywebview || !window.pywebview.api) return;

    try {
      const status = await window.pywebview.api.get_sync_status();
      this.updateSyncBadge(status.status);

      // Bind click on badge to open the dedicated Sync Modal
      badge.onclick = () => {
        this.openSyncModal();
      };

      const isConfigured = Boolean(status.has_key || status.has_web_url || status.local_detected_url);

      // If configured, trigger a non-blocking background pull/push on startup
      if (isConfigured && status.auto_sync) {
        setTimeout(() => this.triggerSync(true), 300);
      }

      // Automatically sync on window focus (e.g. switching back from browser/mobile)
      if (!this._focusSyncBound) {
        this._focusSyncBound = true;
        window.addEventListener("focus", async () => {
          if (window.pywebview && window.pywebview.api) {
            const cur = await window.pywebview.api.get_sync_status();
            if ((cur.has_key || cur.has_web_url || cur.local_detected_url) && cur.auto_sync) {
              await this.triggerSync(true);
            }
          }
        });
      }

      // Schedule periodic background sync every 60 seconds
      if (this.syncTimer) clearInterval(this.syncTimer);
      this.syncTimer = setInterval(async () => {
        if (window.pywebview && window.pywebview.api) {
          const curStatus = await window.pywebview.api.get_sync_status();
          if ((curStatus.has_key || curStatus.has_web_url || curStatus.local_detected_url) && curStatus.auto_sync) {
            await this.triggerSync(true);
          }
        }
      }, 60 * 1000);
    } catch (e) {
      console.warn("[Sync] Init failed:", e);
      this.updateSyncBadge("offline");
    }
  },

  updateSyncBadge(status) {
    const dot = document.getElementById("syncDot");
    const text = document.getElementById("syncStatusText");
    const badge = document.getElementById("syncStatusBadge");
    if (!dot || !text || !badge) return;

    dot.className = "sync-dot";

    if (status === "syncing") {
      dot.classList.add("syncing");
      text.textContent = "Syncing...";
      badge.title = "Synchronizing with Cloud / Web Companion...";
    } else if (status === "synced" || status === "ready") {
      text.textContent = "Synced";
      badge.title = "Local Executable & Web in Sync (Click to configure or sync)";
    } else if (status === "unconfigured") {
      dot.classList.add("unconfigured");
      text.textContent = "Setup Sync";
      badge.title = "Click to configure Web URL or Supabase Cloud Sync";
    } else {
      dot.classList.add("offline");
      text.textContent = "Offline";
      badge.title = "Offline: Changes cached locally in SQLite (Click to configure or retry)";
    }
  },

  async triggerSync(isBackground = false) {
    if (!window.pywebview || !window.pywebview.api) return;

    this.updateSyncBadge("syncing");

    try {
      const res = await window.pywebview.api.sync_now();
      if (res.status === "synced") {
        this.updateSyncBadge("synced");
        if (!isBackground) {
          this.showToast(res.synced_count > 0 ? `Synced ${res.synced_count} updates` : "All devices in sync");
        }
        // Refresh active views if remote updates were incorporated
        if (res.synced_count > 0 || !isBackground) {
          if (this.currentView === "dashboard" && window.Dashboard) window.Dashboard.load();
          if (this.currentView === "today" && window.Today) window.Today.load();
          if (this.currentView === "tum" && window.Tum) window.Tum.load();
          if (this.currentView === "projects" && window.Projects) window.Projects.load();
          if (this.currentView === "body" && window.Body) window.Body.load();
          if (this.currentView === "knowledge" && window.Knowledge) window.Knowledge.load();
        }
      } else if (res.status === "unconfigured") {
        this.updateSyncBadge("unconfigured");
      } else {
        this.updateSyncBadge("offline");
        if (!isBackground) {
          this.showToast("Offline: changes saved locally");
        }
      }
    } catch (e) {
      this.updateSyncBadge("offline");
      if (!isBackground) {
        this.showToast("Sync unreachable (local mode)");
      }
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
