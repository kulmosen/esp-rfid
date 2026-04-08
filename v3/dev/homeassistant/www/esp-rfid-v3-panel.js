class EspRfidV3AdminPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._busy = false;
    this._message = "";
    this._error = "";
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set panel(panel) {
    this._panel = panel;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _registryEntityId() {
    return this._panel?.config?.registry_entity || "sensor.esp_rfid_v3_registry";
  }

  _domain() {
    return this._panel?.config?.integration_domain || "esp_rfid_v3";
  }

  _registryState() {
    return this._hass?.states?.[this._registryEntityId()] || null;
  }

  _doors() {
    return this._registryState()?.attributes?.doors || [];
  }

  _users() {
    return this._registryState()?.attributes?.users || [];
  }

  _siteName() {
    return this._registryState()?.attributes?.site_name || "ESP-RFID V3";
  }

  async _callService(service, data = {}) {
    this._busy = true;
    this._message = "";
    this._error = "";
    this._render();

    try {
      await this._hass.callService(this._domain(), service, data);
      this._message = `Action completed: ${service}`;
    } catch (error) {
      this._error = error?.message || String(error);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _onDoorSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    await this._callService("register_door", {
      device_id: String(formData.get("device_id") || "").trim(),
      name: String(formData.get("name") || "").trim(),
      base_url: String(formData.get("base_url") || "").trim(),
      api_token: String(formData.get("api_token") || "").trim(),
      allow_hold_open: formData.get("allow_hold_open") === "on",
      enabled: formData.get("enabled") === "on",
    });
    if (!this._error) {
      form.reset();
      form.querySelector("[name='allow_hold_open']").checked = true;
      form.querySelector("[name='enabled']").checked = true;
    }
  }

  async _onUserSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const selectedDoors = Array.from(
      form.querySelectorAll("input[name='door_ids']:checked")
    ).map((input) => input.value);

    await this._callService("register_user", {
      user_id: String(formData.get("user_id") || "").trim(),
      name: String(formData.get("name") || "").trim(),
      door_ids: selectedDoors,
      rfid_uid: String(formData.get("rfid_uid") || "").trim(),
      pin: String(formData.get("pin") || "").trim(),
      active: formData.get("active") === "on",
      valid_from: String(formData.get("valid_from") || "").trim(),
      valid_until: String(formData.get("valid_until") || "").trim(),
    });
    if (!this._error) {
      form.reset();
      form.querySelector("[name='active']").checked = true;
    }
  }

  _bindEvents() {
    const doorForm = this.shadowRoot.querySelector("#door-form");
    if (doorForm) {
      doorForm.addEventListener("submit", (event) => void this._onDoorSubmit(event));
    }

    const userForm = this.shadowRoot.querySelector("#user-form");
    if (userForm) {
      userForm.addEventListener("submit", (event) => void this._onUserSubmit(event));
    }

    this.shadowRoot.querySelectorAll("[data-service]").forEach((button) => {
      button.addEventListener("click", async () => {
        const service = button.dataset.service;
        const payload = button.dataset.payload
          ? JSON.parse(button.dataset.payload)
          : {};
        await this._callService(service, payload);
      });
    });
  }

  _renderDoorCard(door) {
    const actions = [
      ["pulse_unlock", "Pulse Unlock", { device_id: door.device_id, reason: "panel" }],
      ["push_snapshot", "Push Snapshot", { device_id: door.device_id }],
      ["resync_door", "Resync", { device_id: door.device_id }],
      ["reboot_door", "Reboot", { device_id: door.device_id }],
      ["remove_door", "Remove", { device_id: door.device_id }],
    ];

    if (door.allow_hold_open) {
      actions.splice(1, 0, [
        "hold_unlock",
        "Hold Open",
        { device_id: door.device_id, reason: "panel" },
      ]);
      actions.splice(2, 0, [
        "cancel_hold",
        "Cancel Hold",
        { device_id: door.device_id, reason: "panel" },
      ]);
    }

    return `
      <section class="card">
        <div class="card-header">
          <div>
            <h3>${door.name}</h3>
            <p class="muted">${door.device_id}</p>
          </div>
          <span class="badge ${door.available ? "ok" : "warn"}">
            ${door.available ? "Online" : "Offline"}
          </span>
        </div>
        <dl class="meta">
          <div><dt>Lock state</dt><dd>${door.lock_state || "unknown"}</dd></div>
          <div><dt>Health</dt><dd>${door.health_state || "unknown"}</dd></div>
          <div><dt>Snapshot</dt><dd>${door.snapshot_version || "none"}</dd></div>
          <div><dt>Credentials</dt><dd>${door.credential_count ?? 0}</dd></div>
          <div><dt>Queue</dt><dd>${door.event_queue_depth ?? 0}</dd></div>
          <div><dt>Last sync</dt><dd>${door.last_sync_at || "never"}</dd></div>
        </dl>
        ${door.last_error ? `<p class="error">${door.last_error}</p>` : ""}
        <div class="button-row">
          ${actions
            .map(
              ([service, label, payload]) => `
                <button
                  data-service="${service}"
                  data-payload='${JSON.stringify(payload)}'
                  ${this._busy ? "disabled" : ""}
                >${label}</button>
              `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  _renderUserCard(user) {
    return `
      <section class="card compact">
        <div class="card-header">
          <div>
            <h3>${user.name}</h3>
            <p class="muted">${user.user_id}</p>
          </div>
          <span class="badge ${user.active ? "ok" : "warn"}">
            ${user.active ? "Active" : "Inactive"}
          </span>
        </div>
        <dl class="meta">
          <div><dt>Doors</dt><dd>${(user.door_ids || []).join(", ") || "none"}</dd></div>
          <div><dt>RFID</dt><dd>${user.has_tag ? "Yes" : "No"}</dd></div>
          <div><dt>PIN</dt><dd>${user.has_pin ? "Yes" : "No"}</dd></div>
          <div><dt>Valid from</dt><dd>${user.valid_from || "always"}</dd></div>
          <div><dt>Valid until</dt><dd>${user.valid_until || "no expiry"}</dd></div>
        </dl>
        <div class="button-row">
          <button
            data-service="remove_user"
            data-payload='${JSON.stringify({ user_id: user.user_id })}'
            ${this._busy ? "disabled" : ""}
          >Remove User</button>
        </div>
      </section>
    `;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) {
      return;
    }

    const registry = this._registryState();
    const doors = this._doors();
    const users = this._users();

    const doorOptions = doors
      .map(
        (door) => `
          <label class="checkbox">
            <input type="checkbox" name="door_ids" value="${door.device_id}" />
            <span>${door.name}</span>
          </label>
        `
      )
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 24px;
          color: var(--primary-text-color);
          background:
            radial-gradient(circle at top left, rgba(49, 109, 181, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(255, 176, 0, 0.14), transparent 22%),
            var(--primary-background-color);
          min-height: 100vh;
          box-sizing: border-box;
          font-family: var(--primary-font-family, sans-serif);
        }

        h1, h2, h3, p {
          margin: 0;
        }

        .layout {
          display: grid;
          gap: 20px;
        }

        .hero {
          padding: 24px;
          border-radius: 20px;
          background: linear-gradient(135deg, rgba(34, 59, 92, 0.95), rgba(18, 33, 53, 0.88));
          color: white;
          box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
        }

        .hero p {
          margin-top: 8px;
          color: rgba(255, 255, 255, 0.82);
        }

        .status {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 16px;
        }

        .pill {
          padding: 10px 14px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.12);
          font-size: 14px;
        }

        .message {
          padding: 14px 16px;
          border-radius: 14px;
          background: rgba(65, 184, 131, 0.12);
          color: var(--success-color, #2e7d32);
        }

        .error {
          padding: 14px 16px;
          border-radius: 14px;
          background: rgba(211, 47, 47, 0.12);
          color: var(--error-color, #c62828);
        }

        .grid {
          display: grid;
          gap: 20px;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        }

        .card {
          padding: 18px;
          border-radius: 18px;
          background: var(--card-background-color);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.08));
          border: 1px solid rgba(127, 140, 141, 0.18);
        }

        .compact {
          padding: 16px;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 16px;
        }

        .muted {
          color: var(--secondary-text-color);
          margin-top: 4px;
          font-size: 13px;
        }

        .badge {
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 600;
          white-space: nowrap;
        }

        .badge.ok {
          background: rgba(65, 184, 131, 0.14);
          color: var(--success-color, #2e7d32);
        }

        .badge.warn {
          background: rgba(255, 152, 0, 0.16);
          color: var(--warning-color, #b26a00);
        }

        .meta {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }

        .meta div {
          padding: 10px 12px;
          border-radius: 12px;
          background: rgba(127, 140, 141, 0.08);
        }

        .meta dt {
          color: var(--secondary-text-color);
          font-size: 12px;
          margin-bottom: 4px;
        }

        .meta dd {
          margin: 0;
          font-weight: 600;
          font-size: 14px;
          word-break: break-word;
        }

        .button-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        button {
          border: 0;
          border-radius: 12px;
          padding: 10px 14px;
          background: var(--primary-color);
          color: white;
          cursor: pointer;
          font: inherit;
        }

        button[disabled] {
          opacity: 0.6;
          cursor: default;
        }

        .secondary {
          background: var(--card-background-color);
          color: var(--primary-text-color);
          border: 1px solid rgba(127, 140, 141, 0.3);
        }

        form {
          display: grid;
          gap: 12px;
        }

        label {
          display: grid;
          gap: 6px;
          font-size: 14px;
        }

        input {
          border: 1px solid rgba(127, 140, 141, 0.35);
          border-radius: 12px;
          padding: 10px 12px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .checkbox-group {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .checkbox {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 10px;
          background: rgba(127, 140, 141, 0.08);
        }

        .empty {
          padding: 18px;
          border-radius: 16px;
          border: 1px dashed rgba(127, 140, 141, 0.35);
          color: var(--secondary-text-color);
          background: rgba(127, 140, 141, 0.04);
        }

        @media (max-width: 800px) {
          :host {
            padding: 16px;
          }

          .hero {
            padding: 18px;
          }
        }
      </style>
      <div class="layout">
        <section class="hero">
          <h1>${this._siteName()}</h1>
          <p>Central control plane for door nodes, users, snapshots and manual actions.</p>
          <div class="status">
            <div class="pill">${doors.length} door nodes</div>
            <div class="pill">${users.length} central users</div>
            <div class="pill">Registry entity: ${this._registryEntityId()}</div>
          </div>
        </section>

        ${this._message ? `<div class="message">${this._message}</div>` : ""}
        ${this._error ? `<div class="error">${this._error}</div>` : ""}

        ${
          !registry
            ? `<div class="empty">
                 The registry entity was not found yet. Finish Home Assistant onboarding,
                 add the ESP-RFID V3 integration, and wait for the first refresh.
               </div>`
            : ""
        }

        <section class="grid">
          <section class="card">
            <div class="card-header">
              <div>
                <h2>Doors</h2>
                <p class="muted">Register nodes and run live actions.</p>
              </div>
              <div class="button-row">
                <button
                  data-service="sync_all"
                  data-payload="{}"
                  ${this._busy ? "disabled" : ""}
                >Refresh All</button>
                <button
                  data-service="push_all_snapshots"
                  data-payload="{}"
                  ${this._busy ? "disabled" : ""}
                >Push All Snapshots</button>
              </div>
            </div>

            <form id="door-form">
              <label>
                Device ID
                <input name="device_id" placeholder="frontdoor" required />
              </label>
              <label>
                Name
                <input name="name" placeholder="Front Door" required />
              </label>
              <label>
                Base URL
                <input name="base_url" placeholder="http://esp_rfid_v3_frontdoor:18101" required />
              </label>
              <label>
                API Token
                <input name="api_token" placeholder="frontdoor-dev-token" required />
              </label>
              <label class="checkbox">
                <input type="checkbox" name="allow_hold_open" checked />
                <span>Allow hold open</span>
              </label>
              <label class="checkbox">
                <input type="checkbox" name="enabled" checked />
                <span>Enabled</span>
              </label>
              <div class="button-row">
                <button type="submit" ${this._busy ? "disabled" : ""}>Save Door</button>
              </div>
            </form>
          </section>

          <section class="card">
            <div class="card-header">
              <div>
                <h2>Users</h2>
                <p class="muted">Create central access users and assign them to doors.</p>
              </div>
            </div>

            <form id="user-form">
              <label>
                User ID
                <input name="user_id" placeholder="dennis" required />
              </label>
              <label>
                Name
                <input name="name" placeholder="Dennis" required />
              </label>
              <label>
                RFID UID
                <input name="rfid_uid" placeholder="A1B2C3D4" />
              </label>
              <label>
                PIN
                <input name="pin" placeholder="1234" />
              </label>
              <label>
                Valid From
                <input name="valid_from" placeholder="2026-04-08T12:00:00+00:00" />
              </label>
              <label>
                Valid Until
                <input name="valid_until" placeholder="2026-12-31T23:59:59+00:00" />
              </label>
              <label class="checkbox">
                <input type="checkbox" name="active" checked />
                <span>Active</span>
              </label>
              <div>
                <p class="muted">Door assignments</p>
                <div class="checkbox-group">
                  ${doorOptions || '<span class="muted">Register at least one door first.</span>'}
                </div>
              </div>
              <div class="button-row">
                <button type="submit" ${this._busy ? "disabled" : ""}>Save User</button>
              </div>
            </form>
          </section>
        </section>

        <section>
          <h2>Door Nodes</h2>
          <div class="grid">
            ${doors.length ? doors.map((door) => this._renderDoorCard(door)).join("") : '<div class="empty">No door nodes have been registered yet.</div>'}
          </div>
        </section>

        <section>
          <h2>Users</h2>
          <div class="grid">
            ${users.length ? users.map((user) => this._renderUserCard(user)).join("") : '<div class="empty">No central users yet. Add one above.</div>'}
          </div>
        </section>
      </div>
    `;

    this._bindEvents();
  }
}

customElements.define("esp-rfid-v3-admin", EspRfidV3AdminPanel);
