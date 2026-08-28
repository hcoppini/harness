/**
 * Master Application Controller & Keyboard Router for Harness.
 */

window.HarnessApp = {
  currentView: "today",

  init() {
    this.bindNavigation();
    this.bindKeybindings();
    this.startClock();

    // Listen for PyWebView ready event
    window.addEventListener("pywebviewready", async () => {
      console.log("PyWebView API bridge connected");
      await this.initAllLayers();
      const statusText = document.getElementById("appStatusText");
      if (statusText) {
        statusText.textContent = "Harness Engine Connected (Local SQLite WAL)";
      }
    });

    // Fallback if pywebview is already attached or in browser test mode
    if (window.pywebview && window.pywebview.api) {
      this.initAllLayers();
    }
  },

  async initAllLayers() {
    if (window.Today) await window.Today.init();
    if (window.Tum) await window.Tum.init();
    if (window.Projects) await window.Projects.init();
    if (window.Body) await window.Body.init();
    if (window.Knowledge) await window.Knowledge.init();
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

    // Update nav tab styling
    document.querySelectorAll("#navTabs .nav-tab").forEach((tab) => {
      if (tab.getAttribute("data-view") === viewName) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    // Update view sections
    document.querySelectorAll(".view-section").forEach((sec) => {
      if (sec.id === `view-${viewName}`) {
        sec.classList.add("active");
      } else {
        sec.classList.remove("active");
      }
    });

    this.currentView = viewName;

    // Refresh view data upon focus
    if (viewName === "today" && window.Today) window.Today.load();
    if (viewName === "tum" && window.Tum) window.Tum.load();
    if (viewName === "projects" && window.Projects) window.Projects.load();
    if (viewName === "body" && window.Body) window.Body.load();
    if (viewName === "knowledge" && window.Knowledge) window.Knowledge.load();
  },

  bindKeybindings() {
    window.addEventListener("keydown", (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      const isInput = activeTag === "input" || activeTag === "textarea" || activeTag === "select";

      // If user is actively typing in a form field, don't trigger global navigation shortcuts
      if (isInput) {
        if (e.key === "Escape") {
          document.activeElement.blur();
        }
        return;
      }

      // View switching hotkeys [1 - 5]
      if (e.key === "1") {
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

      // Action hotkeys: [N] for new task, [R] for rollover
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        this.switchView("today");
        const taskInput = document.getElementById("taskTitleInput");
        if (taskInput) {
          taskInput.focus();
        }
      }

      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        if (window.Today) {
          window.Today.handleRollover();
        }
      }
    });
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
          year: "numeric",
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
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      toast.style.transition = "all 0.2s ease";
      setTimeout(() => toast.remove(), 200);
    }, durationMs);
  },
};

document.addEventListener("DOMContentLoaded", () => {
  window.HarnessApp.init();
});
