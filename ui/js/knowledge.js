/**
 * Knowledge Layer: First-principles algorithm ledger and evening reflection audit.
 */

const Knowledge = {
  items: [],
  selectedItem: null,
  reflectionDebounce: null,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    // New Note
    document.getElementById("btnNewNote")?.addEventListener("click", () => this.showEditForm(null));

    // Edit & Delete
    document.getElementById("btnEditNote")?.addEventListener("click", () => {
      if (this.selectedItem) this.showEditForm(this.selectedItem);
    });

    document.getElementById("btnDeleteNote")?.addEventListener("click", async () => {
      if (this.selectedItem && confirm(`Delete note "${this.selectedItem.title}"?`)) {
        await this.deleteNote(this.selectedItem.id);
      }
    });

    document.getElementById("btnCancelEditNote")?.addEventListener("click", () => this.hideEditForm());

    document.getElementById("noteEditForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      await this.handleSaveNote();
    });

    // Reflection inputs auto-save
    ["reflectionWorked", "reflectionSlipped", "reflectionTomorrow"].forEach((id) => {
      document.getElementById(id)?.addEventListener("input", () => this.debounceSaveReflection());
    });
  },

  async load() {
    try {
      if (!window.pywebview || !window.pywebview.api) return;
      this.items = await window.pywebview.api.get_knowledge();
      this.renderList();
      if (this.items.length > 0 && !this.selectedItem) {
        this.selectItem(this.items[0]);
      }
    } catch (err) {
      console.error("Error loading knowledge notes:", err);
    }
  },

  renderList() {
    const container = document.getElementById("knowledgeListContainer");
    if (!container) return;

    if (this.items.length === 0) {
      container.innerHTML = `<div style="padding: 14px; font-size: 11px; color: var(--text-tertiary);">No notes saved.</div>`;
      return;
    }

    container.innerHTML = this.items
      .map((item) => {
        const isSelected = this.selectedItem && this.selectedItem.id === item.id;
        return `
          <div 
            style="padding: 10px 12px; border-bottom: 1px solid var(--border-hairline); cursor: pointer; background: ${isSelected ? "var(--bg-surface-active)" : "transparent"}; transition: background 0.15s ease;"
            onclick="Knowledge.selectItemById(${item.id})"
          >
            <div style="font-weight: 500; font-size: 12px; color: var(--text-primary); margin-bottom: 2px;">
              ${this.escapeHtml(item.title)}
            </div>
            <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary); text-transform: uppercase;">
              ${item.category} ${item.tags ? `&bull; ${this.escapeHtml(item.tags)}` : ""}
            </div>
          </div>
        `;
      })
      .join("");
  },

  selectItemById(id) {
    const item = this.items.find((i) => i.id === id);
    if (item) this.selectItem(item);
  },

  selectItem(item) {
    this.selectedItem = item;
    this.renderList();
    this.hideEditForm();

    const titleEl = document.getElementById("noteTitle");
    const metaEl = document.getElementById("noteMeta");
    const contentEl = document.getElementById("noteContentView");
    const btnEdit = document.getElementById("btnEditNote");
    const btnDelete = document.getElementById("btnDeleteNote");

    if (titleEl) titleEl.textContent = item.title;
    if (metaEl) metaEl.textContent = `CATEGORY: ${item.category.toUpperCase()} | TAGS: ${item.tags || "NONE"}`;
    if (contentEl) contentEl.textContent = item.content;
    if (btnEdit) btnEdit.style.display = "inline-flex";
    if (btnDelete) btnDelete.style.display = "inline-flex";
  },

  showEditForm(item) {
    document.getElementById("noteDisplayView").style.display = "none";
    const form = document.getElementById("noteEditForm");
    form.style.display = "flex";

    if (item) {
      document.getElementById("editNoteId").value = item.id;
      document.getElementById("editNoteTitle").value = item.title;
      document.getElementById("editNoteContent").value = item.content;
    } else {
      document.getElementById("editNoteId").value = "";
      document.getElementById("editNoteTitle").value = "";
      document.getElementById("editNoteContent").value = "";
    }
  },

  hideEditForm() {
    document.getElementById("noteDisplayView").style.display = "block";
    document.getElementById("noteEditForm").style.display = "none";
  },

  async handleSaveNote() {
    const idVal = document.getElementById("editNoteId").value;
    const title = document.getElementById("editNoteTitle").value.trim();
    const content = document.getElementById("editNoteContent").value.trim();

    if (!title || !content) return;

    try {
      const saved = await window.pywebview.api.save_knowledge_item(
        title,
        "algorithm",
        content,
        "first-principles",
        idVal ? parseInt(idVal, 10) : null
      );
      await this.load();
      if (saved && saved.id) this.selectItemById(saved.id);
      window.HarnessApp.showToast("Note saved");
    } catch (err) {
      console.error("Error saving note:", err);
    }
  },

  async deleteNote(id) {
    try {
      await window.pywebview.api.delete_knowledge_item(id);
      this.selectedItem = null;
      await this.load();
      window.HarnessApp.showToast("Note deleted");
    } catch (err) {
      console.error("Error deleting note:", err);
    }
  },

  debounceSaveReflection() {
    clearTimeout(this.reflectionDebounce);
    const pill = document.getElementById("reflectionSavePill");
    if (pill) pill.textContent = "Saving...";

    this.reflectionDebounce = setTimeout(async () => {
      if (window.Today) {
        await window.Today.saveDailyLog();
      }
      if (pill) pill.textContent = "Saved";
    }, 400);
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
};
