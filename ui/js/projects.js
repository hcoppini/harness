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
        const isSigg = p.name.includes("SIGG");
        const isCodeInd = p.name.includes("Independence");

        return `
          <div class="project-card" data-id="${p.id}">
            <div>
              <div class="project-top">
                <div class="project-name">${this.escapeHtml(p.name)}</div>
                <span class="badge ${p.status === "active" ? "badge-tum" : "badge-cat"}">${p.status}</span>
              </div>
              <div class="project-desc">${this.escapeHtml(p.description)}</div>

              ${
                p.deadline
                  ? `<div style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); margin-top: 8px;">
                       Target / Deadline: ${p.deadline}
                     </div>`
                  : ""
              }
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
              <!-- Current Milestone -->
              <div class="project-box">
                <div class="project-box-label">Current Milestone</div>
                <div class="project-box-val">${this.escapeHtml(p.current_milestone || "Define milestone")}</div>
              </div>

              <!-- Immediate Next Action -->
              <div class="project-box" style="border-left: 3px solid var(--accent-cyan);">
                <div class="project-box-label">Immediate Next Action</div>
                <div class="project-box-val" style="color: var(--accent-cyan);">${this.escapeHtml(p.next_action || "Set next action")}</div>
              </div>

              ${
                p.notes
                  ? `<div style="font-size: 11px; color: var(--text-dim); line-height: 1.4;">
                       <strong>Key Directive:</strong> ${this.escapeHtml(p.notes)}
                     </div>`
                  : ""
              }
            </div>

            <!-- Actions Bar -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-dim); padding-top: 12px;">
              <button 
                class="btn btn-primary" 
                style="font-size: 11px; padding: 5px 10px;"
                onclick="Projects.editNextAction(${p.id}, '${this.escapeJs(p.next_action)}')"
              >
                Update Next Action
              </button>

              ${
                p.local_path
                  ? `<button 
                       class="btn" 
                       style="font-size: 11px; padding: 5px 10px;" 
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
      window.HarnessApp.showToast("Project next action updated");
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
