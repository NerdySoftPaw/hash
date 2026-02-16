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

  _groupChores() {
    if (!this._data || !this._data.chores) {
      return { mine: {}, unassigned: [], others: {} };
    }

    const myPersonId = this._getCurrentPersonEntityId();
    const chores = Object.values(this._data.chores);
    const mine = {};
    const unassigned = [];
    const others = {};

    for (const chore of chores) {
      const assignee = chore.assigned_to;

      if (!assignee) {
        unassigned.push(chore);
      } else if (myPersonId && assignee === myPersonId) {
        const room = chore.room || "No Room";
        if (!mine[room]) mine[room] = [];
        mine[room].push(chore);
      } else {
        const personName = this._getPersonName(assignee);
        if (!others[personName]) others[personName] = [];
        others[personName].push(chore);
      }
    }

    return { mine, unassigned, others };
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
      // Brief delay then refresh for animation feel
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

  _renderChoreCard(chore) {
    const isCompleting = this._completingChore === chore.chore_id;
    const color = this._getStatusColor(chore.status);
    const pct = Math.round(chore.cleanliness);

    return html`
      <div
        class="chore-card ${isCompleting ? "completing" : ""}"
        style="border-left: 3px solid ${color}"
      >
        <div class="chore-info">
          <span class="chore-name">${chore.name}</span>
          <span class="chore-status" style="color: ${color}"
            >${chore.status}</span
          >
        </div>
        <div class="chore-bar-row">
          <div class="progress-bar">
            <div
              class="progress-fill"
              style="width: ${pct}%; background-color: ${color}"
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
        <div class="chore-meta">
          ${chore.interval_display} &middot; last ${chore.days_since}d ago
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

  _closeAddForm() {
    this._showAddForm = false;
  }

  render() {
    if (this._loading) {
      return html`
        <ha-app-layout>
          <app-header slot="header" fixed>
            <app-toolbar>
              <ha-menu-button
                .hass=${this.hass}
                .narrow=${this.narrow}
              ></ha-menu-button>
              <div main-title>HASH Dashboard</div>
            </app-toolbar>
          </app-header>
          <div class="container">
            <p class="loading">Loading...</p>
          </div>
        </ha-app-layout>
      `;
    }

    const { mine, unassigned, others } = this._groupChores();
    const isAdmin = this.hass && this.hass.user && this.hass.user.is_admin;
    const globalPause = this._data && this._data.global_pause;

    return html`
      <ha-app-layout>
        <app-header slot="header" fixed>
          <app-toolbar>
            <ha-menu-button
              .hass=${this.hass}
              .narrow=${this.narrow}
            ></ha-menu-button>
            <div main-title>HASH Dashboard</div>
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
          </app-toolbar>
        </app-header>
        <div class="container ${this.narrow ? "narrow" : ""}">
          ${globalPause
            ? html`<div class="pause-banner">Global Pause Active</div>`
            : ""}

          <section>
            <h2>My Tasks</h2>
            ${Object.keys(mine).length === 0
              ? html`<p class="empty">No tasks assigned to you.</p>`
              : Object.entries(mine).map(
                  ([room, chores]) => html`
                    <div class="room-group">
                      <h3 class="room-name">${room}</h3>
                      ${chores.map((c) => this._renderChoreCard(c))}
                    </div>
                  `
                )}
          </section>

          ${unassigned.length > 0
            ? html`
                <section>
                  <h2>Unassigned Tasks</h2>
                  ${unassigned.map((c) => this._renderChoreCard(c))}
                </section>
              `
            : ""}

          ${Object.keys(others).length > 0
            ? html`
                <section>
                  <h2>Other People</h2>
                  ${Object.entries(others).map(
                    ([person, chores]) => html`
                      <div class="person-group">
                        <h3 class="person-name">${person}</h3>
                        ${chores.map((c) => this._renderChoreCard(c))}
                      </div>
                    `
                  )}
                </section>
              `
            : ""}
        </div>

        ${this._showAddForm ? this._renderAddForm() : ""}
      </ha-app-layout>
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
      }

      app-header {
        background-color: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
      }

      app-toolbar {
        display: flex;
        align-items: center;
      }

      app-toolbar [main-title] {
        flex: 1;
        margin-left: 16px;
        font-size: 20px;
      }

      .add-btn {
        background: none;
        border: 2px solid var(--app-header-text-color, #fff);
        color: var(--app-header-text-color, #fff);
        width: 36px;
        height: 36px;
        border-radius: 50%;
        font-size: 22px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 8px;
        line-height: 1;
        padding: 0;
      }
      .add-btn:hover {
        background: rgba(255, 255, 255, 0.15);
      }

      .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 16px;
      }
      .container.narrow {
        padding: 8px;
      }

      .loading {
        text-align: center;
        padding: 48px 0;
        color: var(--hash-secondary);
      }

      .pause-banner {
        background: var(--warning-color, #ff9800);
        color: #fff;
        text-align: center;
        padding: 8px;
        border-radius: 8px;
        margin-bottom: 16px;
        font-weight: 500;
      }

      section {
        margin-bottom: 24px;
      }

      h2 {
        color: var(--hash-text);
        font-size: 18px;
        font-weight: 500;
        margin: 0 0 12px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid var(--hash-divider);
      }

      .room-group,
      .person-group {
        margin-bottom: 16px;
      }

      h3.room-name,
      h3.person-name {
        color: var(--hash-secondary);
        font-size: 14px;
        font-weight: 500;
        margin: 0 0 8px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .chore-card {
        background: var(--hash-card-bg);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        box-shadow: var(
          --ha-card-box-shadow,
          0 2px 4px rgba(0, 0, 0, 0.1)
        );
        transition: opacity 0.3s ease, transform 0.3s ease;
      }
      .chore-card.completing {
        opacity: 0.5;
        transform: scale(0.98);
      }

      .chore-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
      }
      .chore-name {
        color: var(--hash-text);
        font-size: 15px;
        font-weight: 500;
      }
      .chore-status {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
      }

      .chore-bar-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }
      .progress-bar {
        flex: 1;
        height: 8px;
        background: var(--hash-divider);
        border-radius: 4px;
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
      }
      .pct {
        color: var(--hash-secondary);
        font-size: 12px;
        min-width: 36px;
        text-align: right;
      }

      .complete-btn {
        background: none;
        border: 2px solid var(--hash-divider);
        color: var(--hash-secondary);
        width: 32px;
        height: 32px;
        border-radius: 50%;
        font-size: 16px;
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

      .chore-meta {
        color: var(--hash-secondary);
        font-size: 12px;
      }

      .empty {
        color: var(--hash-secondary);
        font-style: italic;
        padding: 8px 0;
      }

      /* Add chore form overlay */
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
        border-radius: 12px;
        padding: 24px;
        width: 90%;
        max-width: 400px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      }
      .add-form h3 {
        margin: 0 0 16px 0;
        color: var(--hash-text);
        font-size: 18px;
      }
      .add-form label {
        display: block;
        margin-bottom: 12px;
        color: var(--hash-secondary);
        font-size: 13px;
      }
      .add-form input,
      .add-form select {
        display: block;
        width: 100%;
        margin-top: 4px;
        padding: 8px 12px;
        border: 1px solid var(--hash-divider);
        border-radius: 6px;
        background: var(--input-fill-color, var(--hash-card-bg));
        color: var(--hash-text);
        font-size: 14px;
        box-sizing: border-box;
      }
      .add-form input:focus,
      .add-form select:focus {
        outline: none;
        border-color: var(--primary-color);
      }
      .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 16px;
      }
      .cancel-btn {
        background: none;
        border: 1px solid var(--hash-divider);
        color: var(--hash-secondary);
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
      }
      .save-btn {
        background: var(--primary-color);
        border: none;
        color: var(--text-primary-color, #fff);
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
      }
      .save-btn:hover {
        opacity: 0.9;
      }
    `;
  }
}

customElements.define("hash-panel", HashPanel);
