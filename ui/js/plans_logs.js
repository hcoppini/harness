/**
 * Harness A2UI Renderer & Plans/Logs Controller (v1.0)
 * Renders strict declarative A2UI JSON surfaces (`agent_to_renderer`) using
 * Harness's native Obsidian monochrome component catalog, alongside the AI Diary
 * and Confirmed Outings ledger.
 */

const PlansLogs = {
  stance: "coach",
  messages: [],
  outings: [],
  providerStatus: null,
  activeSurface: null,
  activeDataModel: {},
  activeComponents: [],
  isSending: false,

  async init() {
    this.bindEvents();
  },

  bindEvents() {
    const input = document.getElementById("plansChatInput");
    const sendBtn = document.getElementById("btnPlansChatSend");
    const synthBtn = document.getElementById("btnPlansSynthesize");

    if (sendBtn && !sendBtn.dataset.bound) {
      sendBtn.dataset.bound = "1";
      sendBtn.addEventListener("click", () => this.sendMessage());
    }

    if (input && !input.dataset.bound) {
      input.dataset.bound = "1";
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    if (synthBtn && !synthBtn.dataset.bound) {
      synthBtn.dataset.bound = "1";
      synthBtn.addEventListener("click", () => this.synthesizeLog());
    }

    document.querySelectorAll("#plansStanceBar .plans-stance-btn").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        this.stance = btn.getAttribute("data-stance") || "coach";
        document.querySelectorAll("#plansStanceBar .plans-stance-btn").forEach((b) => {
          b.classList.toggle("active", b === btn);
        });
      });
    });
  },

  getTodayIso() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  },

  async load() {
    this.bindEvents();
    const api = window.pywebview && window.pywebview.api;
    if (!api) return;

    try {
      const [status, outings, conv] = await Promise.all([
        api.get_a2ui_status ? api.get_a2ui_status() : Promise.resolve(null),
        api.get_a2ui_outings ? api.get_a2ui_outings() : Promise.resolve([]),
        api.get_diary_conversation ? api.get_diary_conversation(this.getTodayIso()) : Promise.resolve(null),
      ]);

      this.providerStatus = status;
      this.outings = Array.isArray(outings) ? outings : [];
      this.messages = (conv && Array.isArray(conv.messages)) ? conv.messages : [];
      if (conv && conv.stance) {
        this.stance = conv.stance;
        document.querySelectorAll("#plansStanceBar .plans-stance-btn").forEach((b) => {
          b.classList.toggle("active", b.getAttribute("data-stance") === this.stance);
        });
      }

      this.renderProviderBadge();
      this.renderChat();
      this.renderOutingsList();
      if (!this.activeSurface) {
        this.renderEmptySurface();
      }
    } catch (err) {
      console.error("Failed to load Plans / Logs:", err);
    }
  },

  renderProviderBadge() {
    const badge = document.getElementById("a2uiProviderBadge");
    if (!badge || !this.providerStatus) return;
    const label = this.providerStatus.provider_label || "LOCAL PARSER";
    const isLive = Boolean(
      this.providerStatus.ollama_running ||
      this.providerStatus.has_gemini_fallback ||
      this.providerStatus.has_groq_fallback
    );
    badge.textContent = label;
    badge.className = `mono-chip ${isLive ? "lavender" : ""}`;
    badge.title = this.providerStatus.ollama_running
      ? `Local Ollama connected (${(this.providerStatus.ollama_models || []).join(", ")})`
      : "Ollama not running locally — using free cloud fallback or deterministic A2UI parser";
  },

  useQuickPrompt(text) {
    const input = document.getElementById("plansChatInput");
    if (!input) return;
    input.value = text;
    input.focus();
  },

  async sendMessage(overrideText = null) {
    if (this.isSending) return;
    const input = document.getElementById("plansChatInput");
    const msg = (overrideText !== null ? overrideText : (input ? input.value : "")).trim();
    if (!msg) return;

    const api = window.pywebview && window.pywebview.api;
    if (!api || !api.send_a2ui_message) return;

    this.isSending = true;
    const sendBtn = document.getElementById("btnPlansChatSend");
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.textContent = "Thinking...";
    }
    if (input && overrideText === null) input.value = "";

    // Optimistic user bubble
    this.messages.push({ role: "user", content: msg, timestamp: "now" });
    this.renderChat();

    try {
      const res = await api.send_a2ui_message(msg, this.stance, this.getTodayIso());
      if (res && res.conversation && Array.isArray(res.conversation.messages)) {
        this.messages = res.conversation.messages;
      } else if (res && res.reply) {
        this.messages.push({ role: "assistant", stance: this.stance, content: res.reply, timestamp: "now" });
      }

      if (res && Array.isArray(res.outings)) {
        this.outings = res.outings;
        this.renderOutingsList();
      }

      this.renderChat();

      if (res && res.agent_to_renderer) {
        this.applyA2UIEnvelope(res.agent_to_renderer);
      }
    } catch (err) {
      console.error("A2UI send failed:", err);
      if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast("Failed to process plan message");
      }
    } finally {
      this.isSending = false;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
      }
    }
  },

  async synthesizeLog() {
    const api = window.pywebview && window.pywebview.api;
    if (!api || !api.synthesize_diary_session) return;
    try {
      const res = await api.synthesize_diary_session(this.getTodayIso(), true);
      if (window.HarnessApp && window.HarnessApp.showToast) {
        const msg = res && res.status === "success"
          ? `Log synthesized (${res.actions_created || 0} tasks extracted)`
          : (res && res.message) || "No conversation to synthesize";
        window.HarnessApp.showToast(msg);
      }
      if (window.Today && typeof window.Today.load === "function") window.Today.load();
      if (window.Dashboard && typeof window.Dashboard.load === "function") window.Dashboard.load();
    } catch (err) {
      console.error("Synthesize diary failed:", err);
    }
  },

  renderChat() {
    const container = document.getElementById("plansChatMessages");
    if (!container) return;

    if (!this.messages || this.messages.length === 0) {
      container.innerHTML = `
        <div class="plans-chat-empty">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--accent-lavender); letter-spacing: 0.06em; margin-bottom: 6px;">
            A2UI PLANNER &amp; AI DIARY READY
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
            Announce any trip, outing, or school break (e.g. <strong>"I have a trip Dec 23–27 to Krakow"</strong>) to dynamically rearrange your schedule, or log daily reflections directly.
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = this.messages.map((m) => {
      const isUser = m.role === "user";
      const meta = isUser
        ? `YOU • ${this.escapeHtml(m.timestamp || "")}`
        : `${this.escapeHtml((m.stance || "coach").toUpperCase())}${m.provider ? ` • ${this.escapeHtml(m.provider)}` : ""} • ${this.escapeHtml(m.timestamp || "")}`;
      return `
        <div class="plans-msg ${isUser ? "is-user" : "is-assistant"}">
          <div class="plans-msg-meta">${meta}</div>
          <div class="plans-msg-body">${this.escapeHtml(m.content || "")}</div>
          ${m.surfaceId ? `<div class="plans-msg-surface-tag">Rendered A2UI Surface &rarr;</div>` : ""}
        </div>
      `;
    }).join("");

    container.scrollTop = container.scrollHeight;
  },

  // =========================================================================
  // A2UI v1.0 Protocol Interpreter & Native Obsidian Renderer
  // =========================================================================
  resolvePath(pathExpr) {
    if (typeof pathExpr !== "string" || !pathExpr.startsWith("@path:/")) return pathExpr;
    const parts = pathExpr.slice(7).split("/").filter(Boolean);
    let cur = this.activeDataModel;
    for (const p of parts) {
      if (cur && typeof cur === "object" && p in cur) {
        cur = cur[p];
      } else {
        return "";
      }
    }
    return cur;
  },

  setPath(pathExpr, value) {
    if (typeof pathExpr !== "string" || !pathExpr.startsWith("@path:/")) return;
    const parts = pathExpr.slice(7).split("/").filter(Boolean);
    if (parts.length === 0) return;
    let cur = this.activeDataModel;
    for (let i = 0; i < parts.length - 1; i++) {
      const key = parts[i];
      if (!cur[key] || typeof cur[key] !== "object") cur[key] = {};
      cur = cur[key];
    }
    cur[parts[parts.length - 1]] = value;
  },

  applyA2UIEnvelope(envelope) {
    if (!envelope || !Array.isArray(envelope.messages)) return;
    this.activeSurface = {
      surfaceId: envelope.surfaceId || "a2ui_surface",
      provider: envelope.provider || "local_parser",
      title: "Dynamic Plan Surface",
    };

    for (const msg of envelope.messages) {
      if (msg.createSurface) {
        this.activeSurface.title = msg.createSurface.title || this.activeSurface.title;
      } else if (msg.updateDataModel && msg.updateDataModel.data) {
        this.activeDataModel = JSON.parse(JSON.stringify(msg.updateDataModel.data));
      } else if (msg.updateComponents && Array.isArray(msg.updateComponents.components)) {
        this.activeComponents = msg.updateComponents.components;
      } else if (msg.deleteSurface) {
        this.activeSurface = null;
        this.activeDataModel = {};
        this.activeComponents = [];
      }
    }

    if (this.activeSurface) {
      this.renderA2UISurface();
    } else {
      this.renderEmptySurface();
    }
  },

  renderEmptySurface() {
    const mount = document.getElementById("a2uiSurfaceMount");
    if (!mount) return;
    mount.innerHTML = `
      <div class="monotone-card a2ui-surface a2ui-surface-idle">
        <div class="card-label" style="margin-bottom: 6px;">A2UI DYNAMIC SURFACE // STANDBY</div>
        <div style="font-size: 12px; color: var(--text-tertiary); line-height: 1.5;">
          Announce a trip, outing, or vacation window in the chatbox on the left. Harness will render an interactive preview here—showing exam conflicts and day-by-day schedule changes—before anything touches your plan.
        </div>
      </div>
    `;
  },

  renderA2UISurface() {
    const mount = document.getElementById("a2uiSurfaceMount");
    if (!mount) return;

    const nodesHtml = (this.activeComponents || []).map((comp) => this.renderCatalogNode(comp)).join("");
    mount.innerHTML = `
      <div class="monotone-card a2ui-surface" data-surface-id="${this.escapeHtml(this.activeSurface?.surfaceId || "")}">
        ${nodesHtml}
      </div>
    `;
  },

  renderCatalogNode(comp) {
    if (!comp || !comp["@catalogId"]) return "";
    const kind = comp["@catalogId"];

    if (kind === "Heading") {
      const tone = comp.badgeTone === "lavender" ? "lavender" : (comp.badgeTone === "optimal" ? "green" : "");
      return `
        <div class="a2ui-heading">
          <div>
            ${comp.eyebrow ? `<div class="a2ui-eyebrow">${this.escapeHtml(comp.eyebrow)}</div>` : ""}
            <h3 class="a2ui-title">${this.escapeHtml(comp.title || "")}</h3>
          </div>
          ${comp.badge ? `<span class="mono-chip ${tone}" style="font-size: 9.5px;">${this.escapeHtml(comp.badge)}</span>` : ""}
        </div>
      `;
    }

    if (kind === "OutingSummaryCard") {
      const outing = this.activeDataModel.outing || {};
      const name = this.resolvePath(comp.namePath || "@path:/outing/name") || outing.name || "Outing";
      const dest = this.resolvePath(comp.destinationPath || "@path:/outing/destination") || outing.destination || "";
      const desc = this.resolvePath(comp.descriptionPath || "@path:/outing/description") || outing.description || "";
      return `
        <div class="a2ui-block a2ui-summary-box">
          <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 8px; flex-wrap: wrap;">
            <strong style="font-size: 13px; color: var(--text-primary);">${this.escapeHtml(name)}</strong>
            ${dest ? `<span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">${this.escapeHtml(dest)}</span>` : ""}
          </div>
          ${desc ? `<div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 4px; line-height: 1.45;">${this.escapeHtml(desc)}</div>` : ""}
        </div>
      `;
    }

    if (kind === "DateRangeField") {
      const startPath = comp.startPath || "@path:/outing/start_date";
      const endPath = comp.endPath || "@path:/outing/end_date";
      const startVal = this.resolvePath(startPath) || "";
      const endVal = this.resolvePath(endPath) || "";
      return `
        <div class="a2ui-block">
          <div class="card-label" style="margin-bottom: 6px;">${this.escapeHtml(comp.label || "Dates")}</div>
          <div class="a2ui-date-grid">
            <label class="a2ui-field-wrap">
              <span class="a2ui-field-lbl">START</span>
              <input type="date" class="a2ui-input" value="${this.escapeHtml(startVal)}" onchange="PlansLogs.handleModelEdit('${this.escapeJs(startPath)}', this.value)" />
            </label>
            <label class="a2ui-field-wrap">
              <span class="a2ui-field-lbl">END</span>
              <input type="date" class="a2ui-input" value="${this.escapeHtml(endVal)}" onchange="PlansLogs.handleModelEdit('${this.escapeJs(endPath)}', this.value)" />
            </label>
          </div>
        </div>
      `;
    }

    if (kind === "ModeSelector") {
      const valPath = comp.valuePath || "@path:/outing/mode";
      const curVal = this.resolvePath(valPath) || "travel";
      const opts = Array.isArray(comp.options) ? comp.options : [];
      return `
        <div class="a2ui-block">
          <div class="card-label" style="margin-bottom: 6px;">${this.escapeHtml(comp.label || "Mode")}</div>
          <div class="day-mode-segmented" style="width: 100%;">
            ${opts.map((o) => `
              <button
                type="button"
                class="day-mode-btn ${curVal === o.value ? "active" : ""}"
                style="flex: 1;"
                onclick="PlansLogs.handleModelEdit('${this.escapeJs(valPath)}', '${this.escapeJs(o.value)}')"
              >${this.escapeHtml(o.label)}</button>
            `).join("")}
          </div>
        </div>
      `;
    }

    if (kind === "ConflictAlert") {
      const items = this.resolvePath(comp.itemsPath || "@path:/affected_exams") || [];
      if (!Array.isArray(items) || items.length === 0) return "";
      return `
        <div class="a2ui-block a2ui-conflict-box">
          <div style="font-family: var(--font-mono); font-size: 10px; font-weight: 700; color: #fca5a5; margin-bottom: 4px;">
            ${this.escapeHtml(comp.title || "Overlapping Tests")}
          </div>
          ${items.map((ex) => `
            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
              <strong>[${this.escapeHtml(ex.exam_date || "")}] ${this.escapeHtml(ex.subject || "")}:</strong> ${this.escapeHtml(ex.title || "")}
            </div>
          `).join("")}
        </div>
      `;
    }

    if (kind === "ScheduleDiff") {
      const days = this.resolvePath(comp.daysPath || "@path:/schedule_diff") || [];
      if (!Array.isArray(days) || days.length === 0) return "";
      return `
        <div class="a2ui-block">
          <div class="card-label" style="margin-bottom: 6px;">${this.escapeHtml(comp.title || "Rearranged Plan")}</div>
          <div class="a2ui-diff-list">
            ${days.slice(0, 10).map((d) => `
              <div class="a2ui-diff-row">
                <div class="a2ui-diff-date">
                  <span>${this.escapeHtml(d.date || "")}</span>
                  <small>${this.escapeHtml((d.weekday || "").slice(0, 3).toUpperCase())}</small>
                </div>
                <div class="a2ui-diff-body">
                  <div class="a2ui-diff-before">${this.escapeHtml(d.before || "")}</div>
                  <div class="a2ui-diff-after">&rarr; ${this.escapeHtml(d.after || "")}</div>
                </div>
                <span class="mono-chip ${d.badge === "BREAK SPRINT" ? "lavender" : ""}" style="font-size: 8.5px; padding: 1px 6px;">${this.escapeHtml(d.badge || "")}</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    if (kind === "ActionBar") {
      const actions = Array.isArray(comp.actions) ? comp.actions : [];
      return `
        <div class="a2ui-action-bar">
          ${actions.map((a) => `
            <button
              type="button"
              class="${a.style === "primary" ? "btn-primary" : "btn-ghost-icon"}"
              onclick="PlansLogs.invokeAction('${this.escapeJs(a["@call"] || "")}')"
            >${this.escapeHtml(a.label || "Action")}</button>
          `).join("")}
        </div>
      `;
    }

    return "";
  },

  async handleModelEdit(pathExpr, value) {
    this.setPath(pathExpr, value);
    const api = window.pywebview && window.pywebview.api;
    if (api && api.apply_a2ui_action) {
      try {
        const res = await api.apply_a2ui_action("recompute_preview", this.activeDataModel);
        if (res && res.success) {
          this.activeDataModel.affected_exams = res.affected_exams || [];
          this.activeDataModel.schedule_diff = res.schedule_diff || [];
        }
      } catch (_) {}
    }
    this.renderA2UISurface();
  },

  async invokeAction(actionName) {
    if (actionName === "cancel_surface") {
      this.activeSurface = null;
      this.activeDataModel = {};
      this.activeComponents = [];
      this.renderEmptySurface();
      return;
    }

    const api = window.pywebview && window.pywebview.api;
    if (!api || !api.apply_a2ui_action) return;

    try {
      const res = await api.apply_a2ui_action(actionName, this.activeDataModel);
      if (res && res.success) {
        if (Array.isArray(res.outings)) {
          this.outings = res.outings;
          this.renderOutingsList();
        }
        if (actionName === "apply_outing") {
          this.activeSurface = null;
          this.activeDataModel = {};
          this.activeComponents = [];
          this.renderEmptySurface();
          if (window.HarnessApp && window.HarnessApp.showToast) {
            window.HarnessApp.showToast(`Applied outing: ${res.outing?.name || "Saved"}`);
          }
          if (window.Dashboard && typeof window.Dashboard.load === "function") window.Dashboard.load();
          if (window.Today && typeof window.Today.load === "function") window.Today.load();
          if (window.MetroMap && typeof window.MetroMap.load === "function") window.MetroMap.load();
        }
      } else if (window.HarnessApp && window.HarnessApp.showToast) {
        window.HarnessApp.showToast((res && res.error) || "Action failed");
      }
    } catch (err) {
      console.error("A2UI action failed:", err);
    }
  },

  async deleteOuting(outingId) {
    const api = window.pywebview && window.pywebview.api;
    if (!api || !api.apply_a2ui_action) return;
    try {
      const res = await api.apply_a2ui_action("delete_outing", { outing_id: outingId });
      if (res && res.success) {
        this.outings = res.outings || [];
        this.renderOutingsList();
        if (window.HarnessApp && window.HarnessApp.showToast) {
          window.HarnessApp.showToast("Outing removed from plan");
        }
        if (window.Dashboard && typeof window.Dashboard.load === "function") window.Dashboard.load();
        if (window.Today && typeof window.Today.load === "function") window.Today.load();
      }
    } catch (err) {
      console.error("Delete outing failed:", err);
    }
  },

  renderOutingsList() {
    const host = document.getElementById("plansOutingsList");
    if (!host) return;
    if (!this.outings || this.outings.length === 0) {
      host.innerHTML = `<div style="font-size: 11.5px; color: var(--text-tertiary);">No outings or break windows logged yet.</div>`;
      return;
    }

    host.innerHTML = this.outings.map((w) => {
      const isConfirmed = w.confirmed !== false;
      const isBreak = w.type === "break";
      return `
        <div class="plans-outing-item">
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <strong style="font-size: 12.5px; color: var(--text-primary);">${this.escapeHtml(w.name || "Outing")}</strong>
              <span class="mono-chip ${isBreak ? "lavender" : ""}" style="font-size: 8.5px; padding: 1px 5px;">${isBreak ? "BREAK SPRINT" : "TRAVEL"}</span>
              <span class="mono-chip ${isConfirmed ? "green" : ""}" style="font-size: 8.5px; padding: 1px 5px;">${isConfirmed ? "CONFIRMED" : "TENTATIVE"}</span>
            </div>
            <div style="font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary); margin-top: 2px;">
              ${this.escapeHtml(w.start_date || "")} &rarr; ${this.escapeHtml(w.end_date || "")}${w.destination ? ` &bull; ${this.escapeHtml(w.destination)}` : ""}
            </div>
          </div>
          <button
            type="button"
            class="btn-ghost-icon"
            style="font-size: 10px; padding: 3px 8px;"
            onclick="PlansLogs.deleteOuting('${this.escapeJs(w.id || "")}')"
            title="Remove outing window"
          >Remove</button>
        </div>
      `;
    }).join("");
  },

  escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  escapeJs(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/\\/g, "\\\\")
      .replace(/'/g, "\\'")
      .replace(/"/g, '\\"')
      .replace(/\r|\n/g, " ");
  },
};

window.PlansLogs = PlansLogs;
