/**
 * Projects Layer: Active software and competition builds.
 * Integrated with VS Code, Terminal workspace launcher, and Git status.
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
        const git = p.git || {};
        const isGit = git.is_git;

        return `
          <div class="project-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div class="project-title">${this.escapeHtml(p.name)}</div>
                <div style="display: flex; gap: 6px; align-items: center;">
                  ${
                    isGit && git.branch
                      ? `<span class="chip-tag code" style="font-size: 10px; padding: 2px 6px;">
                           ⌥ ${this.escapeHtml(git.branch)}
                         </span>`
                      : ""
                  }
                  <span class="key-pill" style="color: var(--text-primary); text-transform: uppercase;">${p.status}</span>
                </div>
              </div>
              <div class="project-desc">${this.escapeHtml(p.description)}</div>

              ${
                p.deadline
                  ? `<div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); margin-top: 6px;">
                       TARGET: ${this.escapeHtml(p.deadline)}
                     </div>`
                  : ""
              }

              <!-- Live Git Info Banner -->
              ${
                isGit
                  ? `
                  <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-hairline); border-radius: 4px; padding: 6px 8px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 75%;">
                      ${
                        git.last_commit
                          ? `<span style="color: var(--accent-purple-light); font-weight: 600;">[GIT]</span> ${this.escapeHtml(git.last_commit)}`
                          : `<span style="color: var(--text-tertiary);">Git repository initialized</span>`
                      }
                    </div>
                    <div style="font-family: var(--font-mono); font-size: 10px;">
                      ${
                        git.uncommitted_changes > 0
                          ? `<span style="color: var(--accent-purple-light); font-weight: 600;">* ${git.uncommitted_changes} uncommitted</span>`
                          : `<span style="color: var(--text-tertiary);">clean</span>`
                      }
                    </div>
                  </div>
                  `
                  : ""
              }
            </div>

            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div class="project-meta-box">
                <div class="meta-box-label">CURRENT MILESTONE</div>
                <div class="meta-box-val">${this.escapeHtml(p.current_milestone || "Define milestone")}</div>
              </div>

              <div class="project-meta-box" style="border-left: 2px solid var(--accent-purple);">
                <div class="meta-box-label">IMMEDIATE NEXT ACTION</div>
                <div class="meta-box-val" style="color: var(--text-primary); font-weight: 600;">
                  ${this.escapeHtml(p.next_action || "Set next action")}
                </div>
              </div>
            </div>

            <!-- Workspace Dev Launchpad Actions -->
            <div style="display: flex; flex-direction: column; gap: 8px; border-top: 1px solid var(--border-hairline); padding-top: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <button 
                  class="btn-ghost-icon" 
                  onclick="Projects.editNextAction(${p.id}, '${this.escapeJs(p.next_action)}')"
                >
                  Update Action
                </button>

                <div style="display: flex; gap: 6px;">
                  ${
                    p.local_path
                      ? `
                        <button 
                          class="btn-ghost-icon" 
                          title="Open workspace in VS Code"
                          onclick="Projects.openVsCode('${this.escapeJs(p.local_path)}')"
                          style="color: var(--accent-purple-light); font-weight: 600;"
                        >
                          VS Code
                        </button>
                        <button 
                          class="btn-ghost-icon" 
                          title="Open terminal in workspace"
                          onclick="Projects.openTerminal('${this.escapeJs(p.local_path)}')"
                        >
                          Term
                        </button>
                        <button 
                          class="btn-ghost-icon" 
                          title="Open folder in File Explorer"
                          onclick="Projects.openFolder('${this.escapeJs(p.local_path)}')"
                        >
                          Dir
                        </button>
                      `
                      : ""
                  }
                  ${
                    p.github_url
                      ? `
                        <button 
                          class="btn-ghost-icon" 
                          title="Open GitHub repository"
                          onclick="Projects.openExternal('${this.escapeJs(p.github_url)}')"
                        >
                          GitHub &rarr;
                        </button>
                      `
                      : ""
                  }
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  },

  async openVsCode(path) {
    try {
      const opened = await window.pywebview.api.open_in_vscode(path);
      if (opened) {
        window.HarnessApp.showToast("Launching VS Code workspace");
      } else {
        window.HarnessApp.showToast("Could not launch VS Code for this path");
      }
    } catch (err) {
      console.error("Error opening in VS Code:", err);
    }
  },

  async openTerminal(path) {
    try {
      const opened = await window.pywebview.api.open_terminal(path);
      if (opened) {
        window.HarnessApp.showToast("Opening Terminal");
      } else {
        window.HarnessApp.showToast("Could not launch Terminal");
      }
    } catch (err) {
      console.error("Error opening terminal:", err);
    }
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

  async openExternal(url) {
    try {
      const opened = await window.pywebview.api.open_external_url(url);
      if (opened) {
        window.HarnessApp.showToast("Opening external link in browser");
      }
    } catch (err) {
      console.error("Error opening external URL:", err);
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

window.Projects = Projects;
