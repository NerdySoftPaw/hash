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

  /* ---- Render helpers ---- */

  _renderHeader(isAdmin) {
    return html`
      <div class="hero">
        <div class="hero-inner">
          <ha-menu-button
            .hass=${this.hass}
            .narrow=${this.narrow}
          ></ha-menu-button>
          <div class="hero-text">
            <div class="hero-title">HASH</div>
            <div class="hero-sub">Home Assistant Sweeping Hub</div>
          </div>
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
      </div>
    `;
  }

  _renderTabs() {
    const mineCount = this._getChoresForTab("mine").length;
    const othersCount = this._getChoresForTab("others").length;
    const allCount = this._getChoresForTab("all").length;

    const tabs = [
      { id: "mine", label: "My Tasks", count: mineCount, icon: "\u2709" },
      { id: "others", label: "Others", count: othersCount, icon: "\uD83D\uDC65" },
      { id: "all", label: "All", count: allCount, icon: "\uD83D\uDCCB" },
    ];

    return html`
      <div class="tab-bar-wrap">
        <div class="tab-bar">
          ${tabs.map(
            (t) => html`
              <button
                class="tab ${this._activeTab === t.id ? "active" : ""}"
                @click=${() => this._setTab(t.id)}
              >
                <span class="tab-label">${t.label}</span>
                <span class="tab-count">${t.count}</span>
              </button>
            `
          )}
        </div>
      </div>
    `;
  }

  _renderTabContent() {
    const showAssignee = this._activeTab !== "mine";
    const chores = this._getChoresForTab(this._activeTab);

    if (chores.length === 0) {
      const emoji =
        this._activeTab === "mine"
          ? "\uD83C\uDF89"
          : this._activeTab === "others"
            ? "\uD83D\uDE4C"
            : "\uD83D\uDDC2\uFE0F";
      const msg =
        this._activeTab === "mine"
          ? "You're all caught up!"
          : this._activeTab === "others"
            ? "No tasks assigned to others."
            : "No tasks created yet.";
      return html`
        <div class="empty-state">
          <div class="empty-icon">${emoji}</div>
          <div class="empty-msg">${msg}</div>
          <div class="empty-hint">Tasks will appear here once created.</div>
        </div>
      `;
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
          ${chores.map((c) => this._renderChoreCard(c, showAssignee))}
        </div>
      </div>
    `;
  }

  _renderDueMeta(chore) {
    const daysLeft = this._getDaysLeft(chore);
    if (daysLeft === null) {
      return html`${chore.interval_display} \u00b7 paused`;
    }
    if (daysLeft < 0) {
      return html`<span class="due-overdue">overdue ${Math.abs(daysLeft)}d</span> \u00b7 ${chore.interval_display}`;
    }
    if (daysLeft === 0) {
      return html`<span class="due-today">due today</span> \u00b7 ${chore.interval_display}`;
    }
    return html`${daysLeft}d left \u00b7 ${chore.interval_display}`;
  }

  _renderChoreCard(chore, showAssignee) {
    const isCompleting = this._completingChore === chore.chore_id;
    const color = this._getStatusColor(chore.status);
    const pct = Math.round(chore.cleanliness);

    let assigneeLabel = "";
    if (showAssignee && chore.assigned_to) {
      assigneeLabel = this._getPersonName(chore.assigned_to);
    }

    return html`
      <div class="chore-card ${isCompleting ? "completing" : ""}">
        <div class="status-stripe" style="background:${color}"></div>
        <div class="card-body">
          <div class="card-top">
            <span class="chore-name">${chore.name}</span>
            ${assigneeLabel
              ? html`<span class="assignee-tag">${assigneeLabel}</span>`
              : ""}
            <span class="spacer"></span>
            <span class="status-badge" style="background:${color}">${chore.status}</span>
          </div>
          <div class="card-mid">
            <div class="progress-track">
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
              ${isCompleting ? "\u2026" : "\u2713"}
            </button>
          </div>
          <div class="card-meta">${this._renderDueMeta(chore)}</div>
        </div>
      </div>
    `;
  }

  _renderAddForm() {
    const persons = Object.keys(this.hass.states).filter((e) =>
      e.startsWith("person.")
    );

    return html`
      <div class="modal-overlay" @click=${this._closeAddForm}>
        <div class="modal" @click=${(e) => e.stopPropagation()}>
          <div class="modal-header">
            <span class="modal-title">New Chore</span>
            <button class="modal-close" @click=${this._closeAddForm}>\u00d7</button>
          </div>
          <div class="modal-body">
            <div class="field">
              <label class="field-label">Name</label>
              <input
                type="text"
                placeholder="e.g. Vacuum living room"
                .value=${this._addForm.name}
                @input=${(e) =>
                  (this._addForm = { ...this._addForm, name: e.target.value })}
              />
            </div>
            <div class="field-row">
              <div class="field">
                <label class="field-label">Area</label>
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
              </div>
              <div class="field field-small">
                <label class="field-label">Interval</label>
                <div class="input-suffix">
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
                  <span class="suffix">days</span>
                </div>
              </div>
            </div>
            <div class="field">
              <label class="field-label">Assigned Person</label>
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
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click=${this._closeAddForm}>Cancel</button>
            <button class="btn-save" @click=${() => this._addChore()}>Add Chore</button>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    const isAdmin =
      !this._loading && this.hass && this.hass.user && this.hass.user.is_admin;
    const globalPause =
      !this._loading && this._data && this._data.global_pause;

    return html`
      ${this._renderHeader(isAdmin)}

      ${this._loading
        ? html`<div class="wrap"><p class="loading">Loading...</p></div>`
        : html`
            ${globalPause
              ? html`<div class="pause-banner">
                  \u26A0 Global Pause Active — no schedules generated
                </div>`
              : ""}
            ${this._renderTabs()}
            <div class="wrap ${this.narrow ? "narrow" : ""}">
              ${this._renderTabContent()}
            </div>
          `}

      ${this._showAddForm ? this._renderAddForm() : ""}
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        background: var(--secondary-background-color, #f5f5f5);
        min-height: 100vh;
        --hash-card-bg: var(--card-background-color, #fff);
        --hash-text: var(--primary-text-color, #212121);
        --hash-secondary: var(--secondary-text-color, #727272);
        --hash-divider: var(--divider-color, #e0e0e0);
        --hash-surface: var(
          --ha-card-background,
          var(--card-background-color, #fff)
        );
        --hash-primary: var(--primary-color, #03a9f4);
        --hash-radius: 12px;
      }

      /* ======== Hero Header ======== */
      .hero {
        background: linear-gradient(
          135deg,
          var(--primary-color, #03a9f4) 0%,
          color-mix(in srgb, var(--primary-color, #03a9f4) 70%, #000) 100%
        );
        color: #fff;
        padding: 0;
      }
      .hero-inner {
        display: flex;
        align-items: center;
        gap: 4px;
        max-width: 832px;
        margin: 0 auto;
        padding: 12px 16px 16px;
      }
      .hero-text {
        flex: 1;
        min-width: 0;
      }
      .hero-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 1.5px;
        line-height: 1.2;
      }
      .hero-sub {
        font-size: 12px;
        opacity: 0.75;
        font-weight: 400;
        margin-top: 1px;
      }
      .add-btn {
        background: rgba(255, 255, 255, 0.18);
        border: none;
        color: #fff;
        width: 38px;
        height: 38px;
        border-radius: 12px;
        font-size: 22px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        padding: 0;
        transition: background 0.2s;
        flex-shrink: 0;
      }
      .add-btn:hover {
        background: rgba(255, 255, 255, 0.3);
      }

      /* ======== Pause Banner ======== */
      .pause-banner {
        background: var(--warning-color, #ff9800);
        color: #fff;
        text-align: center;
        padding: 10px 16px;
        font-weight: 600;
        font-size: 13px;
      }

      /* ======== Tab Bar ======== */
      .tab-bar-wrap {
        background: var(--hash-surface);
        border-bottom: 1px solid var(--hash-divider);
        position: sticky;
        top: 0;
        z-index: 5;
      }
      .tab-bar {
        display: flex;
        gap: 4px;
        max-width: 800px;
        margin: 0 auto;
        padding: 10px 16px;
      }
      .tab {
        flex: 1;
        background: transparent;
        border: 1px solid var(--hash-divider);
        border-radius: 10px;
        padding: 9px 6px;
        font-size: 13px;
        font-weight: 500;
        color: var(--hash-secondary);
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .tab:hover {
        background: var(--hash-divider);
        color: var(--hash-text);
      }
      .tab.active {
        background: var(--hash-primary);
        border-color: var(--hash-primary);
        color: #fff;
        font-weight: 600;
      }
      .tab-label {
        white-space: nowrap;
      }
      .tab-count {
        font-size: 11px;
        font-weight: 700;
        background: rgba(0, 0, 0, 0.1);
        padding: 1px 7px;
        border-radius: 8px;
        min-width: 14px;
        text-align: center;
      }
      .tab.active .tab-count {
        background: rgba(255, 255, 255, 0.25);
      }

      /* ======== Content Wrap ======== */
      .wrap {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px 16px 40px;
        width: 100%;
        box-sizing: border-box;
      }
      .wrap.narrow {
        padding: 12px 8px 32px;
      }

      .loading {
        text-align: center;
        padding: 64px 0;
        color: var(--hash-secondary);
        font-size: 15px;
      }

      /* ======== Empty State ======== */
      .empty-state {
        text-align: center;
        padding: 56px 24px;
      }
      .empty-icon {
        font-size: 48px;
        line-height: 1;
        margin-bottom: 12px;
      }
      .empty-msg {
        font-size: 17px;
        font-weight: 600;
        color: var(--hash-text);
        margin-bottom: 4px;
      }
      .empty-hint {
        font-size: 13px;
        color: var(--hash-secondary);
      }

      /* ======== Room Group ======== */
      .room-group {
        margin-bottom: 24px;
      }
      .room-header {
        color: var(--hash-secondary);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 0 4px 8px;
      }
      .room-cards {
        border-radius: var(--hash-radius);
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06),
          0 4px 12px rgba(0, 0, 0, 0.04);
      }

      /* ======== Chore Card ======== */
      .chore-card {
        display: flex;
        background: var(--hash-card-bg);
        border-bottom: 1px solid var(--hash-divider);
        transition: opacity 0.4s, transform 0.4s, background 0.15s;
      }
      .chore-card:last-child {
        border-bottom: none;
      }
      .chore-card:hover {
        background: color-mix(
          in srgb,
          var(--hash-card-bg) 96%,
          var(--hash-text)
        );
      }
      .chore-card.completing {
        opacity: 0.25;
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

      .card-top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .chore-name {
        color: var(--hash-text);
        font-size: 14px;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
      }
      .assignee-tag {
        font-size: 10px;
        font-weight: 600;
        color: var(--hash-primary);
        background: color-mix(
          in srgb,
          var(--hash-primary) 12%,
          transparent
        );
        padding: 2px 8px;
        border-radius: 6px;
        white-space: nowrap;
        text-transform: uppercase;
        letter-spacing: 0.3px;
      }
      .spacer {
        flex: 1;
      }
      .status-badge {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        color: #fff;
        padding: 3px 8px;
        border-radius: 6px;
        white-space: nowrap;
      }

      .card-mid {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .progress-track {
        flex: 1;
        height: 6px;
        background: var(--hash-divider);
        border-radius: 3px;
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
      }
      .pct {
        color: var(--hash-secondary);
        font-size: 11px;
        min-width: 32px;
        text-align: right;
        font-weight: 600;
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
        transition: all 0.2s;
        flex-shrink: 0;
      }
      .complete-btn:hover {
        border-color: var(--success-color, #4caf50);
        color: var(--success-color, #4caf50);
        background: rgba(76, 175, 80, 0.1);
      }
      .complete-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .card-meta {
        color: var(--hash-secondary);
        font-size: 11px;
        margin-top: 6px;
      }
      .due-overdue {
        color: var(--error-color, #f44336);
        font-weight: 700;
      }
      .due-today {
        color: var(--warning-color, #ff9800);
        font-weight: 700;
      }

      /* ======== Responsive ======== */
      @media (max-width: 600px) {
        .hero-title {
          font-size: 18px;
        }
        .hero-sub {
          font-size: 11px;
        }
        .tab {
          padding: 8px 4px;
          font-size: 12px;
        }
        .card-top {
          flex-wrap: wrap;
        }
        .card-mid {
          flex-wrap: wrap;
        }
      }

      /* ======== Modal ======== */
      .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
        padding: 16px;
        box-sizing: border-box;
      }
      .modal {
        background: var(--hash-card-bg);
        border-radius: 20px;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }
      .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px 16px;
        border-bottom: 1px solid var(--hash-divider);
      }
      .modal-title {
        font-size: 18px;
        font-weight: 700;
        color: var(--hash-text);
      }
      .modal-close {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--hash-secondary);
        cursor: pointer;
        padding: 0;
        line-height: 1;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        transition: background 0.15s;
      }
      .modal-close:hover {
        background: var(--hash-divider);
      }
      .modal-body {
        padding: 20px 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex: 1;
        min-width: 0;
      }
      .field-label {
        font-size: 11px;
        font-weight: 700;
        color: var(--hash-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .field-row {
        display: flex;
        gap: 12px;
      }
      .field-small {
        flex: 0 0 120px;
      }
      .modal-body input,
      .modal-body select {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--hash-divider);
        border-radius: 10px;
        background: var(
          --input-fill-color,
          var(--secondary-background-color, #f5f5f5)
        );
        color: var(--hash-text);
        font-size: 14px;
        box-sizing: border-box;
        transition: border-color 0.2s, box-shadow 0.2s;
      }
      .modal-body input::placeholder {
        color: var(--hash-secondary);
        opacity: 0.6;
      }
      .modal-body input:focus,
      .modal-body select:focus {
        outline: none;
        border-color: var(--hash-primary);
        box-shadow: 0 0 0 3px
          color-mix(in srgb, var(--hash-primary) 15%, transparent);
      }
      .input-suffix {
        position: relative;
        display: flex;
        align-items: center;
      }
      .input-suffix input {
        padding-right: 44px;
      }
      .suffix {
        position: absolute;
        right: 12px;
        font-size: 12px;
        color: var(--hash-secondary);
        pointer-events: none;
      }
      .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        padding: 16px 24px 20px;
        border-top: 1px solid var(--hash-divider);
      }
      .btn-cancel {
        background: none;
        border: 1px solid var(--hash-divider);
        color: var(--hash-secondary);
        padding: 10px 20px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.15s, color 0.15s;
      }
      .btn-cancel:hover {
        background: var(--hash-divider);
        color: var(--hash-text);
      }
      .btn-save {
        background: var(--hash-primary);
        border: none;
        color: #fff;
        padding: 10px 24px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        transition: opacity 0.15s, transform 0.1s;
      }
      .btn-save:hover {
        opacity: 0.92;
      }
      .btn-save:active {
        transform: scale(0.97);
      }
    `;
  }
}

customElements.define("hash-panel", HashPanel);
