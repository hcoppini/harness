/**
 * Section 3: PROJECTS HUB CONTROLLER (Version 3.0)
 * Features:
 * - Full CRUD: Add, Edit, Delete projects with native modal
 * - Status Filters: All, Active, Completed, Paused
 * - 1-Click Launchers: VS Code, Terminal, File Explorer, GitHub
 * - Live Git Status: branch, uncommitted count, last commit
 */

const Projects = {
  list: [],
  activeFilter: "all",

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    // Add new project button
    const btnAdd = document.getElementById("btnAddNewProject");
    if (btnAdd) {
      btnAdd.addEventListener("click", () => this.openAddModal());
    }

    // Project modal form submit
    const form = document.getElementById("projectForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        await this.handleSaveProject();
      });
    }

    // Status filter buttons
    const filterBtns = document.querySelectorAll("#projectStatusFilters button");
    filterBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        filterBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeFilter = btn.getAttribute("data-filter") || "all";
        this.render();
      });
    });
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

    let filtered = this.list;
    if (this.activeFilter !== "all") {
      filtered = this.list.filter((p) => (p.status || "").toLowerCase() === this.activeFilter);
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 36px; text-align: center; background: var(--bg-card); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">No projects found in this view</div>
          <p style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Click "+ New Project" to add a build or workspace.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered
      .map((p) => {
        const git = p.git || {};
        const isGit = git.is_git;

        let statusColor = "var(--accent-purple-light)";
        if (p.status === "completed") statusColor = "var(--status-success)";
        if (p.status === "paused") statusColor = "var(--status-warning)";

        return `
          <div class="project-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                <div>
                  <div class="project-title">${this.escapeHtml(p.name)}</div>
                  <div class="project-desc">${this.escapeHtml(p.description || "No description provided.")}</div>
                </div>
                <div style="display: flex; gap: 6px; align-items: center;">
                  ${
                    isGit && git.branch
                      ? `<span class="chip-tag code" style="font-size: 10px;">
                           ⌥ ${this.escapeHtml(git.branch)}
                         </span>`
                      : ""
                  }
                  <span class="chip-tag" style="color: ${statusColor}; border-color: rgba(255,255,255,0.15); text-transform: uppercase;">${p.status}</span>
                </div>
              </div>

              ${
                p.deadline
                  ? `<div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary); margin-top: 6px;">
                       TARGET: ${this.escapeHtml(p.deadline)}
                     </div>`
                  : ""
              }

              <!-- Live Git Info Banner -->
              ${
                isGit
                  ? `
                  <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-hairline); border-radius: var(--radius-sm); padding: 6px 8px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 10px; font-family: var(--font-mono);">
                    <div style="color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 75%;">
                      ${
                        git.last_commit
                          ? `<span style="color: var(--accent-purple-light); font-weight: 600;">[GIT]</span> ${this.escapeHtml(git.last_commit)}`
                          : `<span style="color: var(--text-tertiary);">Git initialized</span>`
                      }
                    </div>
                    <div>
                      ${
                        git.uncommitted_changes > 0
                          ? `<span style="color: var(--status-warning); font-weight: 600;">* ${git.uncommitted_changes} uncommitted</span>`
                          : `<span style="color: var(--status-success);">clean</span>`
                      }
                    </div>
                  </div>
                  `
                  : ""
              }
            </div>

            <!-- Milestones & Next Action -->
            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div class="project-meta-box">
                <div class="meta-box-label">CURRENT MILESTONE</div>
                <div class="meta-box-val">${this.escapeHtml(p.current_milestone || "Define active milestone")}</div>
              </div>

              <div class="project-meta-box" style="border-left: 2px solid var(--accent-purple); background: var(--accent-purple-subtle);">
                <div class="meta-box-label" style="color: var(--accent-purple-light);">IMMEDIATE NEXT ACTION</div>
                <div class="meta-box-val" style="font-weight: 600; color: var(--text-primary);">
                  ${this.escapeHtml(p.next_action || "Set next execution action")}
                </div>
              </div>
            </div>

            <!-- Workspace Actions & Modals -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-hairline); padding-top: 10px;">
              <div style="display: flex; gap: 6px;">
                <button 
                  class="btn-ghost-icon" 
                  onclick="Projects.openEditModal(${p.id})"
                  title="Edit project details"
                >
                  Edit
                </button>
                <button 
                  class="btn-ghost-icon" 
                  onclick="Projects.confirmDelete(${p.id}, '${this.escapeJs(p.name)}')"
                  style="color: var(--status-danger);"
                  title="Delete project"
                >
                  Delete
                </button>
              </div>

              <div style="display: flex; gap: 6px;">
                ${
                  p.local_path
                    ? `
                      <button 
                        class="btn-ghost-icon" 
                        title="Open in VS Code"
                        onclick="Projects.openVsCode('${this.escapeJs(p.local_path)}')"
                        style="color: var(--accent-purple-light); font-weight: 600;"
                      >
                        VS Code
                      </button>
                      <button 
                        class="btn-ghost-icon" 
                        title="Open Terminal"
                        onclick="Projects.openTerminal('${this.escapeJs(p.local_path)}')"
                      >
                        Term
                      </button>
                      <button 
                        class="btn-ghost-icon" 
                        title="Open in File Explorer"
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
        `;
      })
      .join("");
  },

  openAddModal() {
    document.getElementById("projectModalTitle").textContent = "New Project Build";
    document.getElementById("projFormId").value = "";
    document.getElementById("projFormName").value = "";
    document.getElementById("projFormDesc").value = "";
    document.getElementById("projFormStatus").value = "active";
    document.getElementById("projFormDeadline").value = "";
    document.getElementById("projFormMilestone").value = "";
    document.getElementById("projFormNextAction").value = "";
    document.getElementById("projFormLocalPath").value = "";
    document.getElementById("projFormGithubUrl").value = "";
    document.getElementById("projFormNotes").value = "";
    document.getElementById("projectModal").classList.add("open");
  },

  openEditModal(projectId) {
    const p = this.list.find((item) => item.id === projectId);
    if (!p) return;

    document.getElementById("projectModalTitle").textContent = `Edit Project // ${p.name}`;
    document.getElementById("projFormId").value = p.id;
    document.getElementById("projFormName").value = p.name || "";
    document.getElementById("projFormDesc").value = p.description || "";
    document.getElementById("projFormStatus").value = p.status || "active";
    document.getElementById("projFormDeadline").value = p.deadline || "";
    document.getElementById("projFormMilestone").value = p.current_milestone || "";
    document.getElementById("projFormNextAction").value = p.next_action || "";
    document.getElementById("projFormLocalPath").value = p.local_path || "";
    document.getElementById("projFormGithubUrl").value = p.github_url || "";
    document.getElementById("projFormNotes").value = p.notes || "";
    document.getElementById("projectModal").classList.add("open");
  },

  closeModal() {
    document.getElementById("projectModal").classList.remove("open");
  },

  async handleSaveProject() {
    const idVal = document.getElementById("projFormId").value;
    const name = document.getElementById("projFormName").value.trim();
    const desc = document.getElementById("projFormDesc").value.trim();
    const status = document.getElementById("projFormStatus").value;
    const deadline = document.getElementById("projFormDeadline").value.trim();
    const milestone = document.getElementById("projFormMilestone").value.trim();
    const nextAction = document.getElementById("projFormNextAction").value.trim();
    const localPath = document.getElementById("projFormLocalPath").value.trim();
    const githubUrl = document.getElementById("projFormGithubUrl").value.trim();
    const notes = document.getElementById("projFormNotes").value.trim();

    try {
      if (idVal) {
        await window.pywebview.api.update_project(
          parseInt(idVal, 10),
          name,
          desc,
          status,
          milestone,
          nextAction,
          deadline,
          localPath,
          githubUrl,
          notes
        );
        window.HarnessApp.showToast("Project updated");
      } else {
        await window.pywebview.api.add_project(
          name,
          desc,
          localPath,
          githubUrl,
          milestone,
          nextAction,
          deadline,
          notes,
          status
        );
        window.HarnessApp.showToast("Project added");
      }
      this.closeModal();
      await this.load();
      if (window.Dashboard) window.Dashboard.load();
    } catch (err) {
      console.error("Error saving project:", err);
    }
  },

  async confirmDelete(projectId, name) {
    if (confirm(`Delete project "${name}" from registry?`)) {
      try {
        await window.pywebview.api.delete_project(projectId);
        await this.load();
        window.HarnessApp.showToast("Project removed");
        if (window.Dashboard) window.Dashboard.load();
      } catch (err) {
        console.error("Error deleting project:", err);
      }
    }
  },

  async openVsCode(path) {
    try {
      const opened = await window.pywebview.api.open_in_vscode(path);
      if (opened) {
        window.HarnessApp.showToast("Launching VS Code workspace");
      } else {
        window.HarnessApp.showToast("Path not found on disk");
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
        window.HarnessApp.showToast("Could not launch terminal");
      }
    } catch (err) {
      console.error("Error opening terminal:", err);
    }
  },

  async openFolder(path) {
    try {
      const opened = await window.pywebview.api.open_project_folder(path);
      if (opened) {
        window.HarnessApp.showToast("Opening folder in Explorer");
      } else {
        window.HarnessApp.showToast("Folder path not found");
      }
    } catch (err) {
      console.error("Error opening folder:", err);
    }
  },

  async openExternal(url) {
    try {
      await window.pywebview.api.open_external_url(url);
    } catch (err) {
      console.error("Error opening external link:", err);
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

window.Projects = Projects;
