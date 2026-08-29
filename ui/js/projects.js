/**
 * Projects Layer: Active software and competition builds.
 */

const Projects = {
  list: [],

  async init() {
    await this.load();
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.list = await window.pywebview.api.get_projects();
      this.render();
    } catch (err) {
      console.error("Error loading projects:", err);
    }
  },

  render() {
    const container = document.getElementById("projectsContainer");
    if (!container) return;

    container.innerHTML = this.list
      .map((p) => {
        return `
          <div class="project-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div class="project-title">${this.escapeHtml(p.name)}</div>
                <span class="key-pill" style="color: var(--text-primary); text-transform: uppercase;">${p.status}</span>
              </div>
              <div class="project-desc">${this.escapeHtml(p.description)}</div>

              ${
                p.deadline
                  ? `<div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); margin-top: 6px;">
                       TARGET: ${this.escapeHtml(p.deadline)}
                     </div>`
                  : ""
              }
            </div>

            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div class="project-meta-box">
                <div class="meta-box-label">CURRENT MILESTONE</div>
                <div class="meta-box-val">${this.escapeHtml(p.current_milestone || "Define milestone")}</div>
              </div>

              <div class="project-meta-box" style="border-left: 2px solid var(--accent-white);">
                <div class="meta-box-label">IMMEDIATE NEXT ACTION</div>
                <div class="meta-box-val" style="color: var(--text-primary); font-weight: 600;">
                  ${this.escapeHtml(p.next_action || "Set next action")}
                </div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-hairline); padding-top: 10px;">
              <button 
                class="btn-ghost-icon" 
                onclick="Projects.editNextAction(${p.id}, '${this.escapeJs(p.next_action)}')"
              >
                Update Next Action
              </button>

              ${
                p.local_path
                  ? `<button 
                       class="btn-ghost-icon" 
                       title="${p.local_path}"
                       onclick="Projects.openFolder('${this.escapeJs(p.local_path)}')"
                     >
                       Open Folder &rarr;
                     </button>`
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");
  },

  async openFolder(path) {
    try {
      const opened = await window.pywebview.api.open_project_folder(path);
      if (opened) {
        window.HarnessApp.showToast("Opening workspace folder in Explorer");
      } else {
        window.HarnessApp.showToast("Folder path not found");
      }
    } catch (err) {
      console.error("Error opening folder:", err);
    }
  },

  async editNextAction(projectId, currentVal) {
    const newVal = prompt("Set the immediate next action for this project:", currentVal || "");
    if (newVal === null) return;

    try {
      await window.pywebview.api.update_project(projectId, null, null, newVal.trim());
      await this.load();
      window.HarnessApp.showToast("Next action updated");
    } catch (err) {
      console.error("Error updating project action:", err);
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

  escapeJs(str) {
    if (!str) return "";
    return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  },
};
