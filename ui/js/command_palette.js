/**
 * Global Command Palette (Ctrl+K) for Harness OS.
 * Instant launcher for views, workspaces, and quick actions.
 */

const CommandPalette = {
  isOpen: false,
  selectedIndex: 0,
  items: [],

  init() {
    this.createDom();
    this.bindEvents();
  },

  createDom() {
    if (document.getElementById("commandPaletteModal")) return;

    const modal = document.createElement("div");
    modal.id = "commandPaletteModal";
    modal.className = "modal-overlay";
    modal.style.display = "none";
    modal.innerHTML = `
      <div class="modal-card" style="max-width: 580px; padding: 14px; background: var(--bg-card); border: 1px solid var(--border-hairline); box-shadow: 0 16px 36px rgba(0,0,0,0.7);">
        <div style="position: relative; margin-bottom: 10px;">
          <input 
            type="text" 
            id="paletteSearchInput" 
            class="scratchpad-input" 
            placeholder="Type a command, project, or layer (Esc to exit)..."
            style="width: 100%; padding: 10px 12px; font-size: 13px; background: var(--bg-surface); border: 1px solid var(--border-hairline); border-radius: 6px;"
            autocomplete="off"
          />
        </div>
        <div id="paletteResultsList" style="max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;">
          <!-- Items rendered dynamically -->
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-hairline); font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">
          <span>&uarr; &darr; to navigate &bull; Enter to select</span>
          <span>Ctrl + K</span>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener("click", (e) => {
      if (e.target === modal) this.close();
    });

    const input = document.getElementById("paletteSearchInput");
    input.addEventListener("input", () => this.filter());
    input.addEventListener("keydown", (e) => this.handleKeydown(e));
  },

  bindEvents() {
    document.addEventListener("keydown", (e) => {
      // Ctrl + K or Cmd + K
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        this.toggle();
      }
      if (this.isOpen && e.key === "Escape") {
        e.preventDefault();
        this.close();
      }
    });
  },

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  },

  open() {
    this.isOpen = true;
    const modal = document.getElementById("commandPaletteModal");
    const input = document.getElementById("paletteSearchInput");
    if (!modal || !input) return;

    modal.style.display = "flex";
    input.value = "";
    this.selectedIndex = 0;
    this.buildItems();
    this.render();
    setTimeout(() => input.focus(), 50);
  },

  close() {
    this.isOpen = false;
    const modal = document.getElementById("commandPaletteModal");
    if (modal) modal.style.display = "none";
  },

  buildItems() {
    const defaultActions = [
      {
        category: "Navigation",
        title: "Go to Cockpit",
        shortcut: "0",
        action: () => window.HarnessApp.switchView("dashboard"),
      },
      {
        category: "Navigation",
        title: "Go to Daily Execution",
        shortcut: "1",
        action: () => window.HarnessApp.switchView("today"),
      },
      {
        category: "Navigation",
        title: "Go to Study & Exams",
        shortcut: "2",
        action: () => window.HarnessApp.switchView("study"),
      },
      {
        category: "Navigation",
        title: "Go to TUM '28 Roadmap",
        shortcut: "3",
        action: () => window.HarnessApp.switchView("tum"),
      },
      {
        category: "Actions",
        title: "Open Focus Timer",
        shortcut: "T",
        action: () => window.FocusTimer && window.FocusTimer.openSetup(),
      },
      {
        category: "Actions",
        title: "Carry Over Incomplete Tasks",
        shortcut: "R",
        action: () => {
          if (window.Today) window.Today.rolloverTasks();
        },
      },
      {
        category: "Actions",
        title: "Sync School Timetable (TM1)",
        shortcut: "S",
        action: () => {
          if (window.Today) window.Today.refreshSchoolPlan();
        },
      },
      {
        category: "Actions",
        title: "Add Quick Bookmark",
        action: () => {
          if (window.Today && window.Today.openAddLinkModal) window.Today.openAddLinkModal();
        },
      },
    ];

    // Dynamic Quick Links from Today / EasyLinks
    const portalActions = [];
    const easyLinks = (window.Today && Array.isArray(window.Today.easyLinks) && window.Today.easyLinks.length > 0)
      ? window.Today.easyLinks
      : [
          { name: "TM1 Official Portal", url: "https://tm1.edu.pl/", desc: "School homepage" },
          { name: "TM1 Live Plan (Optivum)", url: "https://tm1.edu.pl/plan/", desc: "Class schedule" },
          { name: "Vulcan UONET+ E-Dziennik", url: "https://uonetplus.vulcan.net.pl/", desc: "Grades & exams" },
          { name: "SIGG Platform (GPW)", url: "https://sigg.gpw.pl/", desc: "Trading challenge" },
          { name: "TUM Heilbronn Portal", url: "https://www.tum.de/en/campus-heilbronn/", desc: "Admissions & info" },
          { name: "CKE Matura Portal", url: "https://cke.gov.pl/", desc: "Past papers & keys" },
        ];
    easyLinks.forEach((link) => {
      if (link && link.url) {
        portalActions.push({
          category: "Portals",
          title: link.name,
          detail: link.desc || link.url,
          action: () => window.pywebview && window.pywebview.api && window.pywebview.api.open_external_url(link.url),
        });
      }
    });

    this.allItems = [...defaultActions, ...portalActions];
    this.filteredItems = [...this.allItems];
  },

  filter() {
    const input = document.getElementById("paletteSearchInput");
    const q = (input.value || "").trim().toLowerCase();

    if (!q) {
      this.filteredItems = [...this.allItems];
    } else {
      this.filteredItems = this.allItems.filter((item) => {
        return (
          item.title.toLowerCase().includes(q) ||
          item.category.toLowerCase().includes(q) ||
          (item.detail && item.detail.toLowerCase().includes(q))
        );
      });
    }

    this.selectedIndex = 0;
    this.render();
  },

  render() {
    const list = document.getElementById("paletteResultsList");
    if (!list) return;

    if (this.filteredItems.length === 0) {
      list.innerHTML = `
        <div style="padding: 16px; text-align: center; color: var(--text-tertiary); font-size: 12px;">
          No matching commands found
        </div>
      `;
      return;
    }

    list.innerHTML = this.filteredItems
      .map((item, idx) => {
        const isSelected = idx === this.selectedIndex;
        const bg = isSelected ? "var(--bg-surface-hover)" : "transparent";
        const border = isSelected ? "1px solid var(--accent-purple)" : "1px solid transparent";

        return `
          <div 
            class="palette-item"
            data-index="${idx}"
            style="display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-radius: 4px; background: ${bg}; border: ${border}; cursor: pointer; transition: all 0.1s ease;"
            onclick="CommandPalette.select(${idx})"
            onmouseenter="CommandPalette.setIndex(${idx})"
          >
            <div>
              <span style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-purple-light); text-transform: uppercase; margin-right: 6px;">[${item.category}]</span>
              <span style="font-size: 12px; color: var(--text-primary); font-weight: ${isSelected ? '600' : '400'};">${this.escapeHtml(item.title)}</span>
              ${
                item.detail
                  ? `<div style="font-size: 10px; font-family: var(--font-mono); color: var(--text-tertiary); margin-top: 2px;">${this.escapeHtml(item.detail)}</div>`
                  : ""
              }
            </div>
            ${
              item.shortcut
                ? `<span class="key-pill" style="font-size: 10px;">${item.shortcut}</span>`
                : ""
            }
          </div>
        `;
      })
      .join("");

    // Ensure selected item is scrolled into view
    const selectedEl = list.children[this.selectedIndex];
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: "nearest" });
    }
  },

  setIndex(idx) {
    this.selectedIndex = idx;
    this.render();
  },

  handleKeydown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex + 1) % this.filteredItems.length;
      this.render();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this.selectedIndex = (this.selectedIndex - 1 + this.filteredItems.length) % this.filteredItems.length;
      this.render();
    } else if (e.key === "Enter") {
      e.preventDefault();
      this.select(this.selectedIndex);
    }
  },

  select(idx) {
    const item = this.filteredItems[idx];
    if (item && item.action) {
      this.close();
      item.action();
    }
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  },
};

window.CommandPalette = CommandPalette;
