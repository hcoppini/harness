/**
 * Knowledge / Memory Layer: First-principles algorithm notes, book insights, and reflections.
 */

const Knowledge = {
  items: [],
  selectedItem: null,
  activeFilter: null,
  reflectionDebounce: null,

  async init() {
    this.bindEvents();
    await this.load();
  },

  bindEvents() {
    // New Note Button
    const btnNew = document.getElementById("btnNewNote");
    if (btnNew) {
      btnNew.addEventListener("click", () => this.showEditForm(null));
    }

    // Filter Buttons
    document.getElementById("filterAllNotes")?.addEventListener("click", () => this.setFilter(null));
    document.getElementById("filterAlgoNotes")?.addEventListener("click", () => this.setFilter("algorithm"));
    document.getElementById("filterModelsNotes")?.addEventListener("click", () => this.setFilter("mental_model"));

    // Edit form buttons
    document.getElementById("btnEditNote")?.addEventListener("click", () => {
      if (this.selectedItem) this.showEditForm(this.selectedItem);
    });

    document.getElementById("btnDeleteNote")?.addEventListener("click", async () => {
      if (this.selectedItem && confirm(`Delete note "${this.selectedItem.title}"?`)) {
        await this.deleteNote(this.selectedItem.id);
      }
    });

    document.getElementById("btnCancelEditNote")?.addEventListener("click", () => {
      this.hideEditForm();
    });

    document.getElementById("noteEditForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      await this.handleSaveNote();
    });

    // Reflection inputs auto-save
    ["reflectionWorked", "reflectionSlipped", "reflectionTomorrow"].forEach((id) => {
      document.getElementById(id)?.addEventListener("input", () => {
        this.debounceSaveReflection();
      });
    });
  },

  setFilter(category) {
    this.activeFilter = category;
    this.renderList();
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
      console.error("Error loading knowledge items:", err);
    }
  },

  renderList() {
    const container = document.getElementById("knowledgeListContainer");
    if (!container) return;

    const filtered = this.activeFilter ? this.items.filter((i) => i.category === this.activeFilter) : this.items;

    if (filtered.length === 0) {
      container.innerHTML = `<div style="padding: 16px; font-size: 12px; color: var(--text-dim);">No notes found.</div>`;
      return;
    }

    container.innerHTML = filtered
      .map((item) => {
        const isSelected = this.selectedItem && this.selectedItem.id === item.id;
        return `
          <button 
            class="knowledge-item-btn ${isSelected ? "active" : ""}" 
            onclick="Knowledge.selectItemById(${item.id})"
          >
            <div style="font-weight: 700; font-size: 13px; color: var(--text-main); margin-bottom: 2px;">
              ${this.escapeHtml(item.title)}
            </div>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-dim);">
              ${item.category} ${item.tags ? `&bull; ${this.escapeHtml(item.tags)}` : ""}
            </div>
          </button>
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
      document.getElementById("editNoteCategory").value = item.category;
      document.getElementById("editNoteTags").value = item.tags || "";
      document.getElementById("editNoteContent").value = item.content;
    } else {
      document.getElementById("editNoteId").value = "";
      document.getElementById("editNoteTitle").value = "";
      document.getElementById("editNoteCategory").value = "algorithm";
      document.getElementById("editNoteTags").value = "";
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
    const category = document.getElementById("editNoteCategory").value;
    const tags = document.getElementById("editNoteTags").value.trim();
    const content = document.getElementById("editNoteContent").value.trim();

    if (!title || !content) return;

    try {
      const saved = await window.pywebview.api.save_knowledge_item(
        title,
        category,
        content,
        tags,
        idVal ? parseInt(idVal, 10) : null
      );
      await this.load();
      if (saved && saved.id) {
        this.selectItemById(saved.id);
      }
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
    const indicator = document.getElementById("reflectionSaveIndicator");
    if (indicator) indicator.textContent = "Saving...";

    this.reflectionDebounce = setTimeout(async () => {
      if (window.Today) {
        await window.Today.saveDailyLog();
      }
      if (indicator) indicator.textContent = "Saved";
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
