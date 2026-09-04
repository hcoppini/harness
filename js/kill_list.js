/**
 * Kill List Drawer & Execution Launcher (Harness 2.1)
 * Eliminates decision friction during SGH Library TUM Deep Work blocks.
 * Enforces the 3-Item Rule, Evening Lock, single-click launchers, and bi-directional Metro links.
 */

const KillListDrawer = {
  isOpen: false,
  dateStr: new Date().toISOString().split("T")[0],
  items: [],
  deliverables: [],
  paceVelocity: null,
  isEveningLocked: false,

  async init() {
    this.bindEvents();
  },

  bindEvents() {
    // Close button
    const closeBtn = document.getElementById("closeKillListBtn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.close());
    }

    // Backdrop click
    const backdrop = document.getElementById("killListBackdrop");
    if (backdrop) {
      backdrop.addEventListener("click", () => this.close());
    }

    // Add item form
    const form = document.getElementById("addKillItemForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleAddItem();
      });
    }

    // Quick presets when category changes
    const catSelect = document.getElementById("killItemCategory");
    if (catSelect) {
      catSelect.addEventListener("change", (e) => this.applyCategoryPresets(e.target.value));
    }

    // Keyboard ESC to close
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isOpen) {
        this.close();
      }
    });
  },

  applyCategoryPresets(category) {
    const titleInput = document.getElementById("killItemTitle");
    const specInput = document.getElementById("killItemSpec");
    const actionSelect = document.getElementById("killItemActionType");
    const pathInput = document.getElementById("killItemPath");
    const delivSelect = document.getElementById("killItemDeliverable");

    if (category === "Math R") {
      if (titleInput && !titleInput.value) titleInput.value = "Math R Diagnostic Problem Set";
      if (specInput && !specInput.value) specInput.value = "Tasks 1–5 (Zero-AI)";
      if (actionSelect) actionSelect.value = "pdf";
      if (pathInput && !pathInput.value) pathInput.value = "https://cke.gov.pl";
      if (delivSelect) delivSelect.value = "sep26_math_diag";
    } else if (category === "Algorithms") {
      if (titleInput && !titleInput.value) titleInput.value = "HackerRank Data Structures Drill";
      if (specInput && !specInput.value) specInput.value = "1 Problem Unassisted";
      if (actionSelect) actionSelect.value = "url";
      if (pathInput && !pathInput.value) pathInput.value = "https://www.hackerrank.com/domains/algorithms";
      if (delivSelect) delivSelect.value = "sep26_hackerrank_15";
    } else if (category === "SIGG") {
      if (titleInput && !titleInput.value) titleInput.value = "SIGG WIG20 Momentum Analysis";
      if (specInput && !specInput.value) specInput.value = "Scan mWIG40 liquidity";
      if (actionSelect) actionSelect.value = "workspace";
      if (pathInput && !pathInput.value) pathInput.value = "c:\\Users\\heito\\Desktop\\polish_stocks_day_trade-main";
      if (delivSelect) delivSelect.value = "sep26_sigg_setup";
    } else if (category === "German") {
      if (titleInput && !titleInput.value) titleInput.value = "A2 Nicos Weg Vocabulary & Anki";
      if (specInput && !specInput.value) specInput.value = "20 New Words";
      if (actionSelect) actionSelect.value = "url";
      if (pathInput && !pathInput.value) pathInput.value = "https://learngerman.dw.com/en/nicos-weg/c-36519789";
      if (delivSelect) delivSelect.value = "sep26_german_anki";
    }
  },

  async open(dateStr = null) {
    this.dateStr = dateStr || (window.Today ? window.Today.selectedDateStr : new Date().toISOString().split("T")[0]);
    const drawer = document.getElementById("killListDrawer");
    const backdrop = document.getElementById("killListBackdrop");
    if (!drawer) return;

    drawer.classList.add("open");
    if (backdrop) backdrop.classList.add("open");
    this.isOpen = true;

    await this.load();
  },

  close() {
    const drawer = document.getElementById("killListDrawer");
    const backdrop = document.getElementById("killListBackdrop");
    if (drawer) drawer.classList.remove("open");
    if (backdrop) backdrop.classList.remove("open");
    this.isOpen = false;
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;

      // 1. Fetch Kill List
      const res = await window.pywebview.api.get_kill_list(this.dateStr);
      this.items = res.items || [];
      this.isEveningLocked = Boolean(res.is_evening_locked);

      // 2. Fetch Active Station Deliverables (Sep '26)
      this.deliverables = await window.pywebview.api.get_station_deliverables("sep-2026") || [];

      // 3. Fetch Station Velocity Ghost Beacon
      this.paceVelocity = await window.pywebview.api.get_station_pace_velocity("sep-2026", this.dateStr);

      this.render();
    } catch (err) {
      console.error("Error loading Kill List:", err);
    }
  },

  render() {
    // 1. Header & Velocity Badge
    const dateLabel = document.getElementById("killListDateLabel");
    if (dateLabel) dateLabel.textContent = `Today // ${this.dateStr}`;

    const velocityContainer = document.getElementById("killListVelocityContainer");
    if (velocityContainer && this.paceVelocity) {
      const isBehind = this.paceVelocity.is_behind;
      const statusText = this.paceVelocity.status_text;
      const badgeStyle = isBehind
        ? "background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #f59e0b;"
        : "background: rgba(161, 161, 170, 0.08); border: 1px solid rgba(161, 161, 170, 0.2); color: #a1a1aa;";

      velocityContainer.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 10px; border-radius: 4px; font-family: var(--font-mono); font-size: 11px; ${badgeStyle}">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="width: 7px; height: 7px; border-radius: 50%; background: ${isBehind ? "#f59e0b" : "#c4b5fd"}; display: inline-block;"></span>
            <span style="font-weight: 600;">${statusText}</span>
          </div>
          <span style="font-size: 9px; opacity: 0.8;">Day ${this.paceVelocity.day_of_month}/${this.paceVelocity.total_days}</span>
        </div>
      `;
    }

    // 2. Evening Lock Banner
    const lockBanner = document.getElementById("killListLockBanner");
    if (lockBanner) {
      lockBanner.style.display = this.isEveningLocked ? "block" : "none";
    }

    // 3. Render Deliverable Dropdown in Add Form
    const delivSelect = document.getElementById("killItemDeliverable");
    if (delivSelect && this.deliverables.length > 0) {
      delivSelect.innerHTML = `
        <option value="">-- Optional: Link Deliverable --</option>
        ${this.deliverables
          .map(
            (d) =>
              `<option value="${d.deliverable_id}">[${d.stream.toUpperCase()}] ${d.title} (${d.completed_count}/${d.total_required} ${d.unit_label})</option>`
          )
          .join("")}
      `;
    }

    // 4. Render Active Items (3-Item Rule Indicator)
    const countBadge = document.getElementById("killListCountBadge");
    const count = this.items.length;
    if (countBadge) {
      countBadge.textContent = `${count} / 3 Active`;
      countBadge.className = count >= 3 ? "mono-chip done" : "mono-chip lavender";
    }

    const itemsContainer = document.getElementById("killListItemsContainer");
    if (!itemsContainer) return;

    if (count === 0) {
      itemsContainer.innerHTML = `
        <div style="background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.08); border-radius: 6px; padding: 24px 16px; text-align: center; color: var(--text-tertiary); font-size: 12px;">
          <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Zero-AI SGH Library Session Ready</div>
          <div>Queue up to 3 high-impact tasks: Math Rozszerzona, Raw CS Algorithm, and SIGG/German.</div>
        </div>
      `;
    } else {
      itemsContainer.innerHTML = this.items
        .map((item) => {
          const isDone = item.completed;
          const streamColor = this.getStreamColor(item.category);
          const actionIcon = this.getActionIcon(item.action_type);
          const delivInfo = item.deliverable;

          let burnDownHtml = "";
          if (delivInfo) {
            burnDownHtml = `
              <div style="display: flex; align-items: center; gap: 6px; margin-top: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">
                <span style="color: var(--accent-lavender); font-weight: 600;">Burn-down:</span>
                <span>${delivInfo.completed_count}/${delivInfo.total_required} ${delivInfo.unit_label}</span>
                ${delivInfo.is_completed ? '<span style="color: #6ee7b7; font-weight: 700;">(COMPLETE)</span>' : ""}
              </div>
            `;
          }

          return `
            <div class="kill-item-card ${isDone ? "done" : ""}" style="background: #0d0f12; border: 1px solid ${isDone ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.08)"}; border-radius: 6px; padding: 14px; margin-bottom: 10px; transition: all 0.15s ease;">
              <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;">
                <!-- Checkbox -->
                <div 
                  class="check-dot ${isDone ? "checked" : ""}" 
                  onclick="KillListDrawer.toggleItem('${item.id}')"
                  title="Mark kill-item completed and increment Metro deliverable"
                  style="margin-top: 3px; cursor: pointer; flex-shrink: 0;"
                ></div>

                <!-- Info Block -->
                <div style="flex: 1; min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: ${streamColor}; text-transform: uppercase; border: 1px solid rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 2px;">
                      ${this.escapeHtml(item.category)}
                    </span>
                    ${item.target_spec ? `<span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary);">${this.escapeHtml(item.target_spec)}</span>` : ""}
                  </div>

                  <div style="font-size: 13px; font-weight: 600; color: ${isDone ? "var(--text-tertiary)" : "var(--text-primary)"}; text-decoration: ${isDone ? "line-through" : "none"}; line-height: 1.4; word-break: break-word;">
                    ${this.escapeHtml(item.title)}
                  </div>

                  ${burnDownHtml}
                </div>

                <!-- Launch Button -->
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0;">
                  <button 
                    class="btn-ghost-icon launch-btn" 
                    onclick="KillListDrawer.launchItem('${item.action_type}', '${this.escapeJs(item.target_path)}')"
                    title="Launch ${item.action_type.toUpperCase()}"
                    style="padding: 4px 8px; font-size: 10px; font-family: var(--font-mono); display: flex; align-items: center; gap: 4px; border-color: rgba(255,255,255,0.12);"
                  >
                    <span>${actionIcon}</span>
                    <span>Launch</span>
                  </button>

                  <button 
                    class="btn-ghost-icon" 
                    onclick="KillListDrawer.deleteItem('${item.id}')"
                    title="Delete item"
                    style="padding: 2px 6px; font-size: 10px; color: var(--text-tertiary);"
                  >
                    &times;
                  </button>
                </div>
              </div>
            </div>
          `;
        })
        .join("");
    }

    // 5. Add Form Lock Condition (3-Item Rule Enforced)
    const addCard = document.getElementById("killListAddCard");
    const fullNotice = document.getElementById("killListFullNotice");
    if (count >= 3) {
      if (addCard) addCard.style.display = "none";
      if (fullNotice) fullNotice.style.display = "block";
    } else {
      if (addCard) addCard.style.display = "block";
      if (fullNotice) fullNotice.style.display = "none";
    }
  },

  getStreamColor(category) {
    const cat = (category || "").toLowerCase();
    if (cat.includes("math")) return "#c4b5fd"; // Lavender
    if (cat.includes("algo") || cat.includes("code")) return "#7dd3fc"; // Sky Blue
    if (cat.includes("sigg")) return "#fdba74"; // Orange
    if (cat.includes("german")) return "#6ee7b7"; // Emerald
    return "#fda4af"; // Rose
  },

  getActionIcon(actionType) {
    const act = (actionType || "").toLowerCase();
    if (act === "pdf") return "📄";
    if (act === "workspace") return "💻";
    return "🌐";
  },

  async launchItem(actionType, targetPath) {
    try {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.launch_kill_item(actionType, targetPath);
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast(`Launched: ${actionType.toUpperCase()}`);
        }
      }
    } catch (err) {
      console.error("Error launching kill item:", err);
    }
  },

  async toggleItem(itemId) {
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.toggle_kill_item(itemId);
        await this.load();
        if (window.MetroMap) window.MetroMap.load();
        if (window.Today) window.Today.load(this.dateStr);
        if (window.Dashboard) window.Dashboard.load();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Kill item updated & Metro synced");
        }
      }
    } catch (err) {
      console.error("Error toggling kill item:", err);
    }
  },

  async deleteItem(itemId) {
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.delete_kill_item(itemId);
        await this.load();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Item deleted");
        }
      }
    } catch (err) {
      console.error("Error deleting kill item:", err);
    }
  },

  async handleAddItem() {
    const catInput = document.getElementById("killItemCategory");
    const titleInput = document.getElementById("killItemTitle");
    const specInput = document.getElementById("killItemSpec");
    const actionInput = document.getElementById("killItemActionType");
    const pathInput = document.getElementById("killItemPath");
    const delivInput = document.getElementById("killItemDeliverable");

    const category = catInput ? catInput.value : "Math R";
    const title = titleInput ? titleInput.value.trim() : "";
    const spec = specInput ? specInput.value.trim() : "";
    const actionType = actionInput ? actionInput.value : "url";
    const targetPath = pathInput ? pathInput.value.trim() : "";
    const delivId = delivInput ? delivInput.value : "";

    if (!title) {
      alert("Please enter a task title.");
      return;
    }

    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.add_kill_item(
          category,
          title,
          actionType,
          targetPath,
          spec,
          delivId || null,
          this.dateStr
        );

        // Clear title and spec
        if (titleInput) titleInput.value = "";
        if (specInput) specInput.value = "";

        await this.load();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Added to Kill List");
        }
      }
    } catch (err) {
      alert(err.message || "Failed to add item (3-Item Rule)");
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

  escapeJs(str) {
    if (!str) return "";
    return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  },
};

window.KillListDrawer = KillListDrawer;
