import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@4.1.1/lit-element.js?module";

class HashPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _data: { type: Object, state: true },
      _loading: { type: Boolean, state: true },
      _showAddForm: { type: Boolean, state: true },
      _addForm: { type: Object, state: true },
      _completingChore: { type: String, state: true },
      _areas: { type: Array, state: true },
      _activeTab: { type: String, state: true },
    };
  }

  constructor() {
    super();
    this._data = null;
    this._loading = true;
    this._showAddForm = false;
    this._addForm = { name: "", room: "", interval: 14, assigned_person: "" };
    this._completingChore = null;
    this._areas = [];
    this._activeTab = "mine";
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
    this._refreshInterval = setInterval(() => this._fetchData(), 30000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._refreshInterval) {
      clearInterval(this._refreshInterval);
    }
  }

  async _fetchData() {
    if (!this.hass) return;
    try {
      const result = await this.hass.callWS({ type: "hash/dashboard" });
      this._data = result;
      this._loading = false;

      // Fetch areas for the add form
      const areaReg = await this.hass.callWS({
        type: "config/area_registry/list",
      });
      this._areas = areaReg || [];
    } catch (e) {
      console.error("HASH: Failed to fetch dashboard data", e);
      this._loading = false;
    }
  }

  _getCurrentPersonEntityId() {
    if (!this.hass || !this.hass.user) return null;
    const userId = this.hass.user.id;
    const states = this.hass.states;
    for (const entityId of Object.keys(states)) {
      if (!entityId.startsWith("person.")) continue;
      const state = states[entityId];
      if (state.attributes && state.attributes.user_id === userId) {
        return entityId;
      }
    }
    // Fallback: match by name
    const userName = this.hass.user.name;
    for (const entityId of Object.keys(states)) {
      if (!entityId.startsWith("person.")) continue;
      const state = states[entityId];
      if (
        state.attributes &&
        state.attributes.friendly_name &&
        state.attributes.friendly_name.toLowerCase() === userName.toLowerCase()
      ) {
        return entityId;
      }
    }
    return null;
  }

  _getChoresForTab(tab) {
    if (!this._data || !this._data.chores) return [];
    const myPersonId = this._getCurrentPersonEntityId();
    const chores = Object.values(this._data.chores);

    let filtered;
    switch (tab) {
      case "mine":
        filtered = chores.filter(
          (c) => myPersonId && c.assigned_to === myPersonId
        );
        break;
      case "others":
        filtered = chores.filter(
          (c) => c.assigned_to && (!myPersonId || c.assigned_to !== myPersonId)
        );
        break;
      case "all":
      default:
        filtered = chores;
        break;
    }

    return this._sortByDue(filtered);
  }

  _sortByDue(chores) {
    const now = Date.now();
    return [...chores].sort((a, b) => {
      const dueA = a.next_due ? new Date(a.next_due).getTime() : Infinity;
      const dueB = b.next_due ? new Date(b.next_due).getTime() : Infinity;
      return dueA - dueB;
    });
  }

  _getDaysLeft(chore) {
    if (!chore.next_due) return null;
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const due = new Date(chore.next_due);
    return Math.round((due - now) / 86400000);
  }

  _groupByRoom(chores) {
    const groups = new Map();
    for (const chore of chores) {
      const room = chore.room || "No Room";
      if (!groups.has(room)) groups.set(room, []);
      groups.get(room).push(chore);
    }
    return groups;
  }

  _getPersonName(entityId) {
    if (!this.hass || !this.hass.states[entityId]) return entityId;
    return (
      this.hass.states[entityId].attributes.friendly_name ||
      entityId.replace("person.", "")
    );
  }

  _getStatusColor(status) {
    switch (status) {
      case "Great":
        return "var(--success-color, #4caf50)";
      case "Fine":
        return "var(--info-color, #2196f3)";
      case "Dirty":
        return "var(--warning-color, #ff9800)";
      case "Urgent":
        return "var(--error-color, #f44336)";
      default:
        return "var(--secondary-text-color)";
    }
  }

  async _completeChore(choreId) {
    this._completingChore = choreId;
    try {
      await this.hass.callWS({
        type: "hash/complete_chore",
        chore_id: choreId,
      });
      await new Promise((r) => setTimeout(r, 600));
      await this._fetchData();
    } catch (e) {
      console.error("HASH: Failed to complete chore", e);
    }
    this._completingChore = null;
  }

  async _addChore() {
    const form = this._addForm;
    if (!form.name || !form.interval) return;
    try {
      await this.hass.callWS({
        type: "hash/add_chore",
        name: form.name,
        room: form.room,
        interval: parseInt(form.interval, 10),
        assigned_person: form.assigned_person,
      });
      this._addForm = { name: "", room: "", interval: 14, assigned_person: "" };
      this._showAddForm = false;
      await this._fetchData();
    } catch (e) {
      console.error("HASH: Failed to add chore", e);
    }
  }

  _closeAddForm() {
    this._showAddForm = false;
  }

  _setTab(tab) {
    this._activeTab = tab;
  }

  _renderTabs() {
    const mineCount = this._getChoresForTab("mine").length;
    const othersCount = this._getChoresForTab("others").length;
    const allCount = this._getChoresForTab("all").length;

    const tabs = [
      { id: "mine", label: "My Tasks", count: mineCount },
      { id: "others", label: "Others", count: othersCount },
      { id: "all", label: "All Tasks", count: allCount },
    ];

    return html`
      <div class="tab-bar">
        ${tabs.map(
          (t) => html`
            <button
              class="tab ${this._activeTab === t.id ? "active" : ""}"
              @click=${() => this._setTab(t.id)}
            >
              ${t.label}
              <span class="tab-badge">${t.count}</span>
            </button>
          `
        )}
      </div>
    `;
  }

  _renderTabContent() {
    const showAssignee = this._activeTab !== "mine";
    const chores = this._getChoresForTab(this._activeTab);

    if (chores.length === 0) {
      const msg =
        this._activeTab === "mine"
          ? "You're all caught up!"
          : this._activeTab === "others"
            ? "No tasks assigned to others."
            : "No tasks yet.";
      return html`<div class="empty-state">${msg}</div>`;
    }

    return this._renderChoreList(chores, showAssignee);
  }

  _renderChoreList(chores, showAssignee) {
    const groups = this._groupByRoom(chores);
    return html`
      ${[...groups.entries()].map(
        ([room, roomChores]) =>
          html`${this._renderRoomGroup(room, roomChores, showAssignee)}`
      )}
    `;
  }

  _renderRoomGroup(roomName, chores, showAssignee) {
    return html`
      <div class="room-group">
        <div class="room-header">${roomName}</div>
        <div class="room-cards">
          ${chores.map((c, i) =>
            this._renderChoreCard(c, showAssignee, i === 0, i === chores.length - 1)
          )}
        </div>
      </div>
    `;
  }

  _renderDueMeta(chore) {
    const daysLeft = this._getDaysLeft(chore);
    if (daysLeft === null) {
      return html`${chore.interval_display} · paused`;
    }
    if (daysLeft < 0) {
      return html`<span class="due-overdue">overdue by ${Math.abs(daysLeft)}d</span> · ${chore.interval_display}`;
    }
    if (daysLeft === 0) {
      return html`<span class="due-today">due today</span> · ${chore.interval_display}`;
    }
    return html`${daysLeft}d left · ${chore.interval_display}`;
  }

  _renderChoreCard(chore, showAssignee, isFirst, isLast) {
    const isCompleting = this._completingChore === chore.chore_id;
    const color = this._getStatusColor(chore.status);
    const pct = Math.round(chore.cleanliness);

    let assigneeLabel = "";
    if (showAssignee && chore.assigned_to) {
      assigneeLabel = this._getPersonName(chore.assigned_to);
    }

    return html`
      <div
        class="chore-card ${isCompleting ? "completing" : ""} ${isFirst ? "first" : ""} ${isLast ? "last" : ""}"
      >
        <div class="status-stripe" style="background:${color}"></div>
        <div class="card-body">
          <div class="card-row-main">
            <span class="chore-name">${chore.name}</span>
            ${assigneeLabel
              ? html`<span class="assignee-tag">${assigneeLabel}</span>`
              : ""}
            <span class="chore-status" style="color:${color}">${chore.status}</span>
            <div class="progress-bar">
              <div
                class="progress-fill"
                style="width:${pct}%;background:${color}"
              ></div>
            </div>
            <span class="pct">${pct}%</span>
            <button
              class="complete-btn"
              @click=${() => this._completeChore(chore.chore_id)}
              ?disabled=${isCompleting}
              title="Mark as completed"
            >
              ${isCompleting ? "..." : "\u2713"}
            </button>
          </div>
          <div class="card-row-meta">
            ${this._renderDueMeta(chore)}
          </div>
        </div>
      </div>
    `;
  }

  _renderAddForm() {
    const persons = Object.keys(this.hass.states).filter((e) =>
      e.startsWith("person.")
    );

    return html`
      <div class="add-form-overlay" @click=${this._closeAddForm}>
        <div class="add-form" @click=${(e) => e.stopPropagation()}>
          <h3>Add Chore</h3>
          <label>
            Name
            <input
              type="text"
              .value=${this._addForm.name}
              @input=${(e) =>
                (this._addForm = { ...this._addForm, name: e.target.value })}
            />
          </label>
          <label>
            Area
            <select
              .value=${this._addForm.room}
              @change=${(e) =>
                (this._addForm = { ...this._addForm, room: e.target.value })}
            >
              <option value="">None</option>
              ${this._areas.map(
                (a) =>
                  html`<option value=${a.area_id}>${a.name}</option>`
              )}
            </select>
          </label>
          <label>
            Interval (days)
            <input
              type="number"
              min="1"
              max="730"
              .value=${String(this._addForm.interval)}
              @input=${(e) =>
                (this._addForm = {
                  ...this._addForm,
                  interval: e.target.value,
                })}
            />
          </label>
          <label>
            Assigned Person
            <select
              .value=${this._addForm.assigned_person}
              @change=${(e) =>
                (this._addForm = {
                  ...this._addForm,
                  assigned_person: e.target.value,
                })}
            >
              <option value="">Unassigned</option>
              ${persons.map(
                (p) => html`
                  <option value=${p}>
                    ${this.hass.states[p].attributes.friendly_name ||
                    p.replace("person.", "")}
                  </option>
                `
              )}
            </select>
          </label>
          <div class="form-actions">
            <button class="cancel-btn" @click=${this._closeAddForm}>
              Cancel
            </button>
            <button class="save-btn" @click=${() => this._addChore()}>
              Add
            </button>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    const isAdmin = !this._loading && this.hass && this.hass.user && this.hass.user.is_admin;
    const globalPause = !this._loading && this._data && this._data.global_pause;

    return html`
      <div class="header">
        <ha-menu-button
          .hass=${this.hass}
          .narrow=${this.narrow}
        ></ha-menu-button>
        <span class="header-title">HASH</span>
        ${isAdmin
          ? html`
              <button
                class="add-btn"
                @click=${() => (this._showAddForm = true)}
                title="Add Chore"
              >
                +
              </button>
            `
          : ""}
      </div>
      ${this._loading
        ? html`<div class="container"><p class="loading">Loading...</p></div>`
        : html`
            <div class="page">
              ${globalPause
                ? html`<div class="pause-banner">
                    Global Pause Active — no schedules generated
                  </div>`
                : ""}
              ${this._renderTabs()}
              <div class="container ${this.narrow ? "narrow" : ""}">
                ${this._renderTabContent()}
              </div>
            </div>
          `}

      ${this._showAddForm ? this._renderAddForm() : ""}
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        --hash-card-bg: var(--card-background-color, #fff);
        --hash-text: var(--primary-text-color, #212121);
        --hash-secondary: var(--secondary-text-color, #727272);
        --hash-divider: var(--divider-color, #e0e0e0);
        --hash-surface: var(
          --ha-card-background,
          var(--card-background-color, #fff)
        );
        --hash-primary: var(--primary-color, #03a9f4);
        --hash-radius: 10px;
      }

      /* ---- Header ---- */
      .header {
        display: flex;
        align-items: center;
        height: 56px;
        padding: 0 8px;
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
        box-sizing: border-box;
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .header-title {
        flex: 1;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-left: 4px;
      }
      .add-btn {
        background: none;
        border: 2px solid var(--app-header-text-color, #fff);
        color: var(--app-header-text-color, #fff);
        width: 34px;
        height: 34px;
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 4px;
        line-height: 1;
        padding: 0;
        transition: background 0.2s;
      }
      .add-btn:hover {
        background: rgba(255, 255, 255, 0.15);
      }

      /* ---- Page ---- */
      .page {
        display: flex;
        flex-direction: column;
        min-height: 100%;
      }

      /* ---- Pause Banner ---- */
      .pause-banner {
        background: var(--warning-color, #ff9800);
        color: #fff;
        text-align: center;
        padding: 10px 16px;
        font-weight: 500;
        font-size: 14px;
      }

      /* ---- Tab Bar ---- */
      .tab-bar {
        position: sticky;
        top: 0;
        z-index: 5;
        display: flex;
        background: var(--hash-surface);
        border-bottom: 1px solid var(--hash-divider);
        padding: 0 16px;
        max-width: 800px;
        margin: 0 auto;
        width: 100%;
        box-sizing: border-box;
      }
      .tab {
        flex: 1;
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 12px 8px 10px;
        font-size: 14px;
        font-weight: 500;
        color: var(--hash-secondary);
        cursor: pointer;
        transition: color 0.2s, border-color 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .tab:hover {
        color: var(--hash-text);
      }
      .tab.active {
        color: var(--hash-primary);
        border-bottom-color: var(--hash-primary);
        font-weight: 600;
      }
      .tab-badge {
        background: var(--hash-divider);
        color: var(--hash-secondary);
        font-size: 11px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 10px;
        min-width: 18px;
        text-align: center;
      }
      .tab.active .tab-badge {
        background: var(--hash-primary);
        color: #fff;
      }

      /* ---- Container ---- */
      .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px 16px 32px;
        width: 100%;
        box-sizing: border-box;
      }
      .container.narrow {
        padding: 12px 8px 24px;
      }

      .loading {
        text-align: center;
        padding: 48px 0;
        color: var(--hash-secondary);
      }

      /* ---- Empty State ---- */
      .empty-state {
        text-align: center;
        color: var(--hash-secondary);
        font-style: italic;
        padding: 48px 16px;
        font-size: 15px;
      }

      /* ---- Room Group ---- */
      .room-group {
        margin-bottom: 24px;
      }
      .room-header {
        color: var(--hash-secondary);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 0 4px 8px;
      }
      .room-cards {
        border-radius: var(--hash-radius);
        overflow: hidden;
        box-shadow: var(
          --ha-card-box-shadow,
          0 1px 3px rgba(0, 0, 0, 0.08),
          0 2px 8px rgba(0, 0, 0, 0.06)
        );
      }

      /* ---- Chore Card ---- */
      .chore-card {
        display: flex;
        background: var(--hash-card-bg);
        border-bottom: 1px solid var(--hash-divider);
        transition: opacity 0.4s ease, transform 0.4s ease,
          background 0.15s ease;
      }
      .chore-card:last-child {
        border-bottom: none;
      }
      .chore-card:hover {
        background: var(
          --ha-card-background,
          color-mix(in srgb, var(--hash-card-bg), var(--hash-text) 3%)
        );
      }
      .chore-card.completing {
        opacity: 0.3;
        transform: scale(0.97);
      }

      .status-stripe {
        width: 4px;
        flex-shrink: 0;
      }

      .card-body {
        flex: 1;
        min-width: 0;
        padding: 12px 14px;
      }

      .card-row-main {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }

      .chore-name {
        color: var(--hash-text);
        font-size: 14px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
      }

      .assignee-tag {
        font-size: 11px;
        font-weight: 500;
        color: var(--hash-primary);
        background: color-mix(in srgb, var(--hash-primary) 12%, transparent);
        padding: 1px 7px;
        border-radius: 4px;
        white-space: nowrap;
      }

      .chore-status {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        white-space: nowrap;
        margin-left: auto;
      }

      .progress-bar {
        width: 80px;
        height: 6px;
        background: var(--hash-divider);
        border-radius: 3px;
        overflow: hidden;
        flex-shrink: 0;
      }
      .progress-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
      }

      .pct {
        color: var(--hash-secondary);
        font-size: 11px;
        min-width: 30px;
        text-align: right;
        font-variant-numeric: tabular-nums;
      }

      .complete-btn {
        background: none;
        border: 2px solid var(--hash-divider);
        color: var(--hash-secondary);
        width: 30px;
        height: 30px;
        border-radius: 50%;
        font-size: 15px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition: all 0.2s ease;
        flex-shrink: 0;
      }
      .complete-btn:hover {
        border-color: var(--success-color, #4caf50);
        color: var(--success-color, #4caf50);
        background: rgba(76, 175, 80, 0.08);
      }
      .complete-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .card-row-meta {
        color: var(--hash-secondary);
        font-size: 11px;
        margin-top: 4px;
        padding-left: 0;
      }
      .due-overdue {
        color: var(--error-color, #f44336);
        font-weight: 600;
      }
      .due-today {
        color: var(--warning-color, #ff9800);
        font-weight: 600;
      }

      /* ---- Responsive: narrow cards ---- */
      @media (max-width: 600px) {
        .card-row-main {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 4px 8px;
        }
        .chore-name {
          grid-column: 1;
          grid-row: 1;
        }
        .chore-status {
          grid-column: 2;
          grid-row: 1;
          margin-left: 0;
        }
        .assignee-tag {
          grid-column: 1;
          grid-row: 2;
          justify-self: start;
        }
        .progress-bar {
          width: auto;
          flex: 1;
          grid-column: 1;
          grid-row: 3;
        }
        .pct {
          grid-row: 3;
        }
        .complete-btn {
          grid-column: 2;
          grid-row: 2 / 4;
          align-self: center;
        }
      }

      /* ---- Add Chore Form Overlay ---- */
      .add-form-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
      }
      .add-form {
        background: var(--hash-card-bg);
        border-radius: 16px;
        padding: 24px;
        width: 90%;
        max-width: 400px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
      }
      .add-form h3 {
        margin: 0 0 20px 0;
        color: var(--hash-text);
        font-size: 18px;
        font-weight: 600;
      }
      .add-form label {
        display: block;
        margin-bottom: 14px;
        color: var(--hash-secondary);
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.3px;
      }
      .add-form input,
      .add-form select {
        display: block;
        width: 100%;
        margin-top: 4px;
        padding: 10px 12px;
        border: 1px solid var(--hash-divider);
        border-radius: 8px;
        background: var(--input-fill-color, var(--hash-card-bg));
        color: var(--hash-text);
        font-size: 14px;
        box-sizing: border-box;
        transition: border-color 0.2s;
      }
      .add-form input:focus,
      .add-form select:focus {
        outline: none;
        border-color: var(--hash-primary);
        box-shadow: 0 0 0 2px
          color-mix(in srgb, var(--hash-primary) 20%, transparent);
      }
      .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 20px;
      }
      .cancel-btn {
        background: none;
        border: 1px solid var(--hash-divider);
        color: var(--hash-secondary);
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.15s;
      }
      .cancel-btn:hover {
        background: var(--hash-divider);
      }
      .save-btn {
        background: var(--hash-primary);
        border: none;
        color: var(--text-primary-color, #fff);
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        transition: opacity 0.15s;
      }
      .save-btn:hover {
        opacity: 0.9;
      }
    `;
  }
}

customElements.define("hash-panel", HashPanel);
