/**
 * Kill List Drawer & Execution Launcher (Harness 3.0 / Executive OS)
 * Eliminates decision friction during SGH Library / TUM Deep Work blocks.
 * Enforces the 3-Item Rule, Evening Lock, single-click sequential Metro progression,
 * 1-click School Exam prep (Vulcan UONET+), and single-click quick burndowns.
 */

const KillListDrawer = {
  isOpen: false,
  getLocalDateStr(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  },
  dateStr: (() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  })(),
  items: [],
  deliverables: [],
  workload: null,
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

    // Quick add custom item form (single input)
    const quickForm = document.getElementById("quickAddKillItemForm");
    if (quickForm) {
      quickForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleQuickAdd();
      });
    }

    // Fallback for legacy form if present
    const legacyForm = document.getElementById("addKillItemForm");
    if (legacyForm) {
      legacyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleQuickAdd();
      });
    }

    // Keyboard ESC to close
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isOpen) {
        this.close();
      }
    });
  },

  async open(dateStr = null) {
    this.dateStr = dateStr || (window.Today ? window.Today.selectedDateStr : this.getLocalDateStr());
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
      this.items = (res && res.items) || [];
      this.isEveningLocked = Boolean(res && res.is_evening_locked);

      // 2. Fetch Active Station Deliverables (Sep '26)
      this.deliverables = (await window.pywebview.api.get_station_deliverables("sep-2026")) || [];

      // 3. Fetch Station Velocity Ghost Beacon
      try {
        this.paceVelocity = await window.pywebview.api.get_station_pace_velocity("sep-2026", this.dateStr);
      } catch (e) {
        this.paceVelocity = null;
      }

      // 4. Fetch Workload Governor Analysis
      try {
        if (typeof window.pywebview.api.get_workload_analysis === "function") {
          this.workload = await window.pywebview.api.get_workload_analysis(this.dateStr);
        }
      } catch (e) {
        this.workload = null;
      }

      this.render();

      // Sync inline kill list card on Today view
      if (window.Today && typeof window.Today.renderInlineKillList === "function") {
        window.Today.renderInlineKillList(this.items);
      }
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
      let statusText = this.paceVelocity.status_text;
      if (isBehind && this.paceVelocity.deficit_item_title) {
        statusText = `Pace Deficit: ${this.paceVelocity.deficit_item_title} (-${this.paceVelocity.max_deficit} ${this.paceVelocity.deficit_unit})`;
      }
      const badgeStyle = isBehind
        ? "background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); color: #f59e0b;"
        : "background: rgba(110, 231, 183, 0.08); border: 1px solid rgba(110, 231, 183, 0.25); color: #6ee7b7;";

      velocityContainer.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 10px; border-radius: 4px; font-family: var(--font-mono); font-size: 11px; ${badgeStyle}">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="width: 7px; height: 7px; border-radius: 50%; background: ${isBehind ? "#f59e0b" : "#6ee7b7"}; display: inline-block;"></span>
            <span style="font-weight: 600;">${statusText}</span>
          </div>
          <span style="font-size: 9px; opacity: 0.8;">Day ${this.paceVelocity.day_of_month || 1}/${this.paceVelocity.total_days || 30}</span>
        </div>
      `;
    }

    // 2. Evening Lock Banner
    const lockBanner = document.getElementById("killListLockBanner");
    if (lockBanner) {
      lockBanner.style.display = this.isEveningLocked ? "block" : "none";
    }

    // 3. Render Active Items (3-Item Rule Indicator)
    const count = this.items.length;
    const completedCount = this.items.filter((i) => i.completed).length;

    const countBadge = document.getElementById("killListCountBadge");
    if (countBadge) {
      countBadge.textContent = `${completedCount} / ${count} Done`;
      countBadge.className = count >= 3 ? "mono-chip done" : "mono-chip lavender";
    }

    const todayBadge = document.getElementById("todayKillListBadge");
    if (todayBadge) {
      todayBadge.textContent = `${completedCount}/${count}`;
    }

    const inlineBadge = document.getElementById("todayInlineKillCountBadge");
    if (inlineBadge) {
      inlineBadge.textContent = `${completedCount} / ${count} Active`;
    }

    const itemsContainer = document.getElementById("killListItemsContainer");
    if (itemsContainer) {
      if (count === 0) {
        itemsContainer.innerHTML = `
          <div style="background: rgba(196, 181, 253, 0.03); border: 1px dashed rgba(196, 181, 253, 0.25); border-radius: 6px; padding: 22px 16px; text-align: center;">
            <div style="font-weight: 700; color: var(--accent-lavender); font-size: 13px; margin-bottom: 6px;">Zero Decision Mode • Session Ready</div>
            <div style="color: var(--text-secondary); font-size: 11px; margin-bottom: 14px; line-height: 1.4;">
              Don't waste cognitive energy deciding what to do. Auto-populate your 3 optimal deep work targets instantly.
            </div>
            <button type="button" class="btn-primary" onclick="KillListDrawer.autoPopulate()" style="padding: 8px 18px; font-size: 12px; font-weight: 700; margin: 0 auto; display: inline-flex; align-items: center; gap: 6px;">
              <span>⚡</span><span>Auto-Populate 3 Targets</span>
            </button>
          </div>
        `;
      } else {
        itemsContainer.innerHTML = this.items
          .map((item) => {
            const isDone = item.completed;
            const streamColor = this.getStreamColor(item.category);
            const actionIcon = this.getActionIcon(item.action_type);
            const delivInfo = item.deliverable;
            const qtyBadge = item.quantity && item.quantity > 1 ? `<span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: var(--accent-lavender); background: rgba(196, 181, 253, 0.12); padding: 1px 5px; border-radius: 2px;">+${item.quantity} reps</span>` : "";

            let burnDownHtml = "";
            if (delivInfo) {
              const paceItem = (this.paceVelocity && Array.isArray(this.paceVelocity.deliverables))
                ? this.paceVelocity.deliverables.find((p) => p.deliverable_id === item.station_deliverable_id)
                : null;

              let pacePill = "";
              if (paceItem) {
                if (paceItem.is_behind) {
                  pacePill = `<span style="color: #f59e0b; font-weight: 600; margin-left: 6px;">[Deficit: -${paceItem.deficit} ${paceItem.unit_label}]</span>`;
                } else {
                  pacePill = `<span style="color: #6ee7b7; font-weight: 600; margin-left: 6px;">[Optimal: +${Math.max(0, paceItem.pace_delta)} ${paceItem.unit_label}]</span>`;
                }
              }

              burnDownHtml = `
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin-top: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">
                  <span style="color: var(--accent-lavender); font-weight: 600;">Burn-down:</span>
                  <span>${delivInfo.completed_count}/${delivInfo.total_required} ${delivInfo.unit_label}</span>
                  ${delivInfo.is_completed ? '<span style="color: #6ee7b7; font-weight: 700; margin-left: 6px;">(COMPLETE)</span>' : pacePill}
                </div>
              `;
            }

            return `
              <div class="kill-item-card ${isDone ? "done" : ""}" style="background: #0d0f12; border: 1px solid ${isDone ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.08)"}; border-radius: 6px; padding: 12px 14px; margin-bottom: 8px; transition: all 0.15s ease;">
                <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;">
                  <!-- Checkbox -->
                  <div 
                    class="check-dot ${isDone ? "checked" : ""}" 
                    onclick="KillListDrawer.toggleItem('${item.id}')"
                    title="Mark kill-item completed and advance progressive Metro counter"
                    style="margin-top: 3px; cursor: pointer; flex-shrink: 0;"
                  ></div>

                  <!-- Info Block -->
                  <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                      <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: ${streamColor}; text-transform: uppercase; border: 1px solid rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 2px;">
                        ${this.escapeHtml(item.category)}
                      </span>
                      ${qtyBadge}
                      ${item.target_spec ? `<span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary);">${this.escapeHtml(item.target_spec)}</span>` : ""}
                    </div>

                    <div style="font-size: 13px; font-weight: 600; color: ${isDone ? "var(--text-tertiary)" : "var(--text-primary)"}; text-decoration: ${isDone ? "line-through" : "none"}; line-height: 1.4; word-break: break-word;">
                      ${this.escapeHtml(item.title)}
                    </div>

                    ${burnDownHtml}
                  </div>

                  <!-- Launch & Delete Buttons -->
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
    }

    // 4. Render 1-Click Metro Deliverables Sequential Queue (Compact Single-line)
    const metroContainer = document.getElementById("killListMetroDeliverablesQueue");
    if (metroContainer) {
      if (!this.deliverables || this.deliverables.length === 0) {
        metroContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-tertiary); padding: 8px;">No active Metro deliverables found.</div>`;
      } else {
        const canEnqueue = count < 3;
        metroContainer.innerHTML = this.deliverables
          .map((d) => {
            const nextSpec = d.next_spec;
            const isCompleted = d.is_completed || d.completed_count >= d.total_required;
            const streamColor = this.getStreamColor(d.stream);
            const targetSpecLabel = nextSpec ? nextSpec.target_spec : "";

            return `
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 10px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 4px;">
                <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;">
                  <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: ${streamColor}; text-transform: uppercase; width: 62px; flex-shrink: 0;">${this.escapeHtml(d.stream)}</span>
                  <div style="flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px;">
                    <span style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(d.title)}</span>
                    ${targetSpecLabel ? `<span style="font-family: var(--font-mono); color: var(--accent-lavender); margin-left: 6px; font-size: 10px;">[${this.escapeHtml(targetSpecLabel)}]</span>` : ""}
                  </div>
                  <span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); flex-shrink: 0;">${d.completed_count}/${d.total_required}</span>
                </div>

                <div style="flex-shrink: 0;">
                  ${
                    isCompleted
                      ? `<span class="mono-chip done" style="font-size: 9px; padding: 1px 6px;">DONE</span>`
                      : canEnqueue
                      ? `<button type="button" class="btn-primary" onclick="KillListDrawer.enqueueProgressive('${d.deliverable_id}')" style="font-size: 9px; padding: 3px 8px; white-space: nowrap; font-weight: 600;">+ Enqueue</button>`
                      : `<button type="button" class="btn-ghost-icon" disabled style="font-size: 9px; padding: 2px 6px; opacity: 0.4;">Full</button>`
                  }
                </div>
              </div>
            `;
          })
          .join("");
      }
    }

    // 5. Render 1-Click Upcoming School Exams Prep Queue (Acute only <= 10 days)
    const examSection = document.getElementById("killListExamQueueSection");
    const examContainer = document.getElementById("killListUpcomingExamsQueue");
    if (examSection && examContainer) {
      const allUpcomingExams = (this.workload && this.workload.upcoming_exams) || [];
      const acuteExams = allUpcomingExams.filter((ex) => ex.days_left !== undefined && ex.days_left <= 10);
      if (acuteExams.length === 0) {
        examSection.style.display = "none";
      } else {
        examSection.style.display = "block";
        const canEnqueue = count < 3;
        examContainer.innerHTML = acuteExams
          .map((ex) => {
            const daysLeft = ex.days_left;
            const daysColor = daysLeft <= 2 ? "#fda4af" : daysLeft <= 4 ? "#fdba74" : "#c4b5fd";
            const urgencyBadge = `<span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: ${daysColor}; background: rgba(255,255,255,0.05); padding: 1px 5px; border-radius: 2px;">${daysLeft === 0 ? "TODAY" : daysLeft === 1 ? "TOMORROW" : `IN ${daysLeft} DAYS`}</span>`;
            const tierBadge = `<span style="font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary);">Tier ${ex.tier || 1}</span>`;

            return `
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 10px; background: rgba(254, 202, 202, 0.02); border: 1px solid rgba(254, 202, 202, 0.15); border-radius: 4px;">
                <div style="flex: 1; min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 10px; font-weight: 700; color: #fda4af;">${this.escapeHtml(ex.subject)}</span>
                    ${urgencyBadge}
                    ${tierBadge}
                  </div>
                  <div style="font-size: 11px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;">
                    ${this.escapeHtml(ex.title)}
                  </div>
                </div>

                <div>
                  ${
                    canEnqueue
                      ? `<button type="button" class="btn-ghost-icon" onclick="KillListDrawer.enqueueExamPrep(${ex.id})" style="font-size: 9px; padding: 3px 7px; color: #fda4af; border-color: rgba(254, 202, 202, 0.3); font-weight: 600; white-space: nowrap;">+ Prep</button>`
                      : `<button type="button" class="btn-ghost-icon" disabled style="font-size: 9px; padding: 2px 6px; opacity: 0.4;">Full</button>`
                  }
                </div>
              </div>
            `;
          })
          .join("");
      }
    }

    // 6. 3-Item Rule Capacity Notice & Quick Add Visibility
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
    if (act === "pdf") return "PDF";
    if (act === "workspace") return "CODE";
    return "URL";
  },

  async launchItem(actionType, targetPath) {
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.launch_kill_item(actionType, targetPath);
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
        if (window.Today) window.Today.load(this.dateStr);
        if (window.Dashboard) window.Dashboard.load();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Item deleted");
        }
      }
    } catch (err) {
      console.error("Error deleting kill item:", err);
    }
  },

  async autoPopulate() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      await window.pywebview.api.auto_populate_kill_list(this.dateStr);
      await this.load();
      if (window.Today) await window.Today.load(this.dateStr);
      if (window.Dashboard) await window.Dashboard.load();
      if (window.MetroMap) await window.MetroMap.load();
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast("⚡ 3 High-Impact Targets Auto-Populated");
      }
    } catch (err) {
      console.error("Error auto-populating kill list:", err);
    }
  },

  async enqueueProgressive(deliverableId) {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      await window.pywebview.api.enqueue_progressive_deliverable(deliverableId, this.dateStr);
      await this.load();
      if (window.Today) await window.Today.load(this.dateStr);
      if (window.Dashboard) await window.Dashboard.load();
      if (window.MetroMap) await window.MetroMap.load();
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast("Enqueued auto-advancing Metro deliverable");
      }
    } catch (err) {
      alert(err.message || "Failed to enqueue deliverable");
    }
  },

  async enqueueExamPrep(examId) {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      await window.pywebview.api.enqueue_exam_prep(examId, this.dateStr);
      await this.load();
      if (window.Today) await window.Today.load(this.dateStr);
      if (window.Dashboard) await window.Dashboard.load();
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast("Enqueued exam prep to Kill List");
      }
    } catch (err) {
      alert(err.message || "Failed to enqueue exam prep");
    }
  },

  async quickLogStudy(deliverableId, count = 1, notes = "") {
    try {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.log_study_reps(deliverableId, count, notes);
        await this.load();
        if (window.MetroMap) await window.MetroMap.load();
        if (window.Today) await window.Today.load(this.dateStr);
        if (window.Dashboard) await window.Dashboard.load();

        if (window.HarnessApp && window.HarnessApp.showToast) {
          const title = res && res.deliverable ? res.deliverable.title : "Study session";
          const progress = res && res.deliverable ? ` (${res.deliverable.completed_count}/${res.deliverable.total_required})` : "";
          window.HarnessApp.showToast(`+${count} reps logged for ${title}${progress}`);
        }
      }
    } catch (err) {
      console.error("Error logging study reps:", err);
    }
  },

  async handleQuickAdd() {
    const titleInput = document.getElementById("quickKillItemTitle") || document.getElementById("killItemTitle");
    const text = titleInput ? titleInput.value.trim() : "";
    if (!text) return;

    let cat = "Secondary";
    let actionType = "url";
    let targetPath = text;
    let spec = "";

    const lower = text.toLowerCase();
    if (lower.includes("math") || lower.includes("matemat") || lower.includes("cke")) {
      cat = "Math R";
      actionType = "pdf";
      targetPath = "https://cke.gov.pl";
    } else if (lower.includes("leet") || lower.includes("algo") || lower.includes("code")) {
      cat = "Algorithms";
      actionType = "url";
      targetPath = "https://leetcode.com";
    } else if (lower.includes("german") || lower.includes("deutsch") || lower.includes("anki")) {
      cat = "German";
      actionType = "url";
      targetPath = "https://learngerman.dw.com";
    } else if (lower.includes("sigg") || lower.includes("gpw")) {
      cat = "SIGG";
      actionType = "workspace";
      targetPath = "c:\\Users\\heito\\Desktop\\polish_stocks_day_trade-main";
    } else if (text.startsWith("http://") || text.startsWith("https://")) {
      actionType = "url";
    } else if (text.toLowerCase().endsWith(".pdf")) {
      actionType = "pdf";
    } else {
      actionType = "url";
      targetPath = "";
    }

    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.add_kill_item(
          cat,
          text,
          actionType,
          targetPath,
          spec,
          null,
          1,
          this.dateStr
        );

        if (titleInput) titleInput.value = "";
        await this.load();
        if (window.Today) await window.Today.load(this.dateStr);
        if (window.Dashboard) await window.Dashboard.load();
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
