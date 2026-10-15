/* Bundled with the integration. Uses HA services, never the Windows API token. */
const CONTROLS = [
  ["toggle", "Питание Plex", "mdi:power", "power"],
  ["home", "Главная", "mdi:home-outline", "home"],
  ["info", "Информация", "mdi:information-outline", "info"],
  ["up", "Вверх", "mdi:chevron-up", "up"],
  ["left", "Влево", "mdi:chevron-left", "left"],
  ["select", "OK", "mdi:circle-outline", "ok"],
  ["right", "Вправо", "mdi:chevron-right", "right"],
  ["down", "Вниз", "mdi:chevron-down", "down"],
  ["back", "Назад · Esc", "mdi:keyboard-return", "back"],
  ["fullscreen", "Полный экран", "mdi:fullscreen", "fullscreen"],
  ["seek_backward", "−10 секунд", "mdi:rewind-10", "rewind"],
  ["play_pause", "Пуск / Пауза", "mdi:play-pause", "playpause"],
  ["seek_forward", "+10 секунд", "mdi:fast-forward-10", "forward"],
  ["previous", "Предыдущий", "mdi:skip-previous", "previous"],
  ["stop", "Стоп", "mdi:stop", "stop"],
  ["next", "Следующий", "mdi:skip-next", "next"],
  ["volume_down", "Тише", "mdi:volume-minus", "quieter"],
  ["mute", "Без звука", "mdi:volume-mute", "mute"],
  ["volume_up", "Громче", "mdi:volume-plus", "louder"],
  ["subtitles", "Субтитры", "mdi:subtitles-outline", "subtitles"],
  ["audio", "Аудиодорожка", "mdi:translate", "audio"],
  ["focus", "Показать Plex", "mdi:monitor", "focus"],
];

class PlexRemoteCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._busy = false;
    this._selected = "";
  }
  static getStubConfig() { return {}; }
  setConfig(config) {
    if (config.entity && !config.entity.startsWith("remote.")) {
      throw new Error("Выберите remote-сущность Plex PC Remote, а не media_player");
    }
    this._config = config;
    this._selected = config.entity || "";
    this._update();
  }
  set hass(value) { this._hass = value; this._update(); }
  getCardSize() { return 10; }
  connectedCallback() { this._build(); this._update(); }
  _build() {
    if (this.shadowRoot.querySelector(".remote")) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; color:var(--primary-text-color, #20252b); }
        * { box-sizing:border-box; }
        .remote { padding:20px; background:var(--ha-card-background,var(--card-background-color,#fff));
          border:1px solid var(--divider-color,#dedede); border-radius:24px; }
        header {display:flex; align-items:center; gap:12px; margin-bottom:16px;}
        header ha-icon {color:#c78b00; --mdc-icon-size:32px;}
        h2 {font-size:22px; margin:0;} .status {font-size:13px; opacity:.75; margin-top:4px;}
        select {width:100%; padding:10px; margin-bottom:14px; border-radius:10px;
          background:var(--secondary-background-color,#f4f5f6); color:inherit; border:1px solid var(--divider-color,#ddd);}
        .keys {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px;
          grid-template-areas:'power home info' '. up .' 'left ok right' 'back down fullscreen'
          'rewind playpause forward' 'previous stop next' 'quieter mute louder' 'subtitles audio focus';}
        button {font:inherit; color:inherit; cursor:pointer; border:0; border-radius:14px;
          background:var(--secondary-background-color,#f1f3f5); min-height:60px;
          padding:10px 4px; touch-action:manipulation; display:flex; flex-direction:column;
          gap:5px; align-items:center; justify-content:center; -webkit-tap-highlight-color:transparent;}
        button span {font-size:11px; line-height:1.2; text-align:center;}
        button ha-icon {--mdc-icon-size:27px;}
        button:active {transform:scale(.96);} button:hover {filter:brightness(.95);}
        button:focus-visible {outline:3px solid var(--primary-color,#168ada); outline-offset:2px;}
        button:disabled {opacity:.35; cursor:default; transform:none;}
        [data-command=select], [data-command=play_pause] {background:#e5ad30; color:#16191e;}
        [data-command=toggle] {color:var(--error-color,#bc283d);}
        .message {font-size:13px; line-height:1.5; margin:12px 0 0; overflow-wrap:anywhere;}
        .error {color:var(--error-color,#bc283d);}
        .homekit {width:100%; margin-top:16px; flex-direction:row; min-height:48px; gap:10px;}
        .homekit span {font-size:14px;}
        .note {font-size:12px; opacity:.7; margin:12px 0 0; line-height:1.5;}
        [hidden] {display:none!important;}
      </style>
      <section class="remote">
        <header><ha-icon icon="mdi:remote-tv"></ha-icon><div><h2>Plex пульт</h2><div class="status" aria-live="polite"></div></div></header>
        <select aria-label="Компьютер Plex"></select>
        <div class="keys"></div>
        <p class="message warning" role="status"></p>
        <p class="message error" role="alert" hidden></p>
        <button class="homekit"><ha-icon icon="mdi:home-automation"></ha-icon><span>Добавить в Apple Home</span></button>
        <p class="message pairing" role="status" hidden></p>
        <p class="note">Питание запускает или закрывает только Plex. Компьютер остаётся включённым.</p>
      </section>`;
    const grid = this.shadowRoot.querySelector(".keys");
    for (const [command, title, icon, area] of CONTROLS) {
      const button = document.createElement("button");
      button.dataset.command = command;
      button.style.gridArea = area;
      button.setAttribute("aria-label", title);
      button.title = title;
      const glyph = document.createElement("ha-icon");
      glyph.setAttribute("icon", icon);
      const label = document.createElement("span");
      label.textContent = title;
      button.append(glyph, label);
      button.addEventListener("click", () => this._send(command));
      grid.append(button);
    }
    this.shadowRoot.querySelector("select").addEventListener("change", (event) => {
      this._selected = event.target.value;
      this._update();
    });
    this.shadowRoot.querySelector(".homekit").addEventListener("click", () => this._homekit());
  }
  _state() { return this._hass?.states[this._selected]; }
  _update() {
    if (!this.isConnected || !this._hass) return;
    this._build();
    const entities = Object.entries(this._hass.states).filter(([id, state]) =>
      id.startsWith("remote.") && (id === this._config.entity || state.attributes.integration === "plex_pc_remote"));
    if (!this._selected || (!this._config.entity && !this._hass.states[this._selected])) {
      this._selected = entities[0]?.[0] || "";
    }
    const select = this.shadowRoot.querySelector("select");
    const signature = JSON.stringify(entities.map(([id,s]) => [id,s.attributes.friendly_name]));
    if (this._options !== signature) {
      select.replaceChildren();
      for (const [id,state] of entities) {
        const option = document.createElement("option");
        option.value = id; option.textContent = state.attributes.friendly_name || id;
        select.append(option);
      }
      this._options = signature;
    }
    select.value = this._selected;
    select.hidden = entities.length < 2 || Boolean(this._config.entity);
    select.disabled = this._busy;
    const state = this._state();
    const available = state && !["unavailable", "unknown"].includes(state.state);
    const on = state?.state === "on";
    const compatible = typeof state?.attributes.input_ready === "boolean";
    const ready = state?.attributes.input_ready === true;
    this.shadowRoot.querySelector(".status").textContent = !state ? "Пульт не найден — добавьте интеграцию Plex PC Remote"
      : !available ? "Сервер недоступен" : on ? "Plex открыт" : "Plex закрыт";
    const warning = this.shadowRoot.querySelector(".warning");
    warning.textContent = !available ? "" : !compatible
      ? "Обновите Windows-сервер до 1.1.0. Обновление только HACS не исправляет клавиши."
      : !ready ? "Раскладка обновлена. Выключите и снова включите Plex кнопкой питания, чтобы он её загрузил." : "";
    warning.hidden = !warning.textContent;
    for (const button of this.shadowRoot.querySelectorAll("[data-command]")) {
      button.disabled = this._busy || !available || (button.dataset.command !== "toggle" && (!on || !ready));
    }
    this.shadowRoot.querySelector(".homekit").hidden = !this._hass.user?.is_admin;
    this.shadowRoot.querySelector(".homekit").disabled = this._busy || !available || !state?.attributes.tv_entity_id;
    this.shadowRoot.querySelector("h2").textContent = this._config.name || "Plex пульт";
  }
  async _call(domain, service, data) {
    if (this._busy || !this._hass) return false;
    this._busy = true;
    const error = this.shadowRoot.querySelector(".error");
    error.hidden = true;
    this._update();
    try {
      await this._hass.callService(domain, service, data);
      return true;
    } catch (err) {
      error.textContent = err.message || String(err);
      error.hidden = false;
      return false;
    } finally {
      this._busy = false;
      this._update();
    }
  }
  async _send(command) {
    const button = this.shadowRoot.querySelector(`[data-command="${command}"]`);
    if (!button || button.disabled) return;
    // Always toggle actual playback. Never infer play/pause from process on/off.
    return this._call("remote", "send_command", { entity_id: this._selected, command });
  }
  async _homekit() {
    const entity = this._state()?.attributes.tv_entity_id;
    if (!entity || this.shadowRoot.querySelector(".homekit").disabled) return;
    if (await this._call("plex_pc_remote", "expose_homekit", { entity_id: entity })) {
      const message = this.shadowRoot.querySelector(".pairing");
      message.textContent = "Откройте уведомления HA: HomeKit покажет QR-код. На iPhone: Дом → + → Добавить аксессуар. После сопряжения выберите Plex в пульте Apple TV в Пункте управления.";
      message.hidden = false;
    }
  }
}

class PlexRemotePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this.shadowRoot.innerHTML = `<style>:host{display:block;height:100%;overflow:auto;background:var(--primary-background-color,#fafafa)}
      header{height:56px;display:flex;align-items:center;gap:16px;padding:0 16px;background:var(--app-header-background-color,#1675b9);color:var(--app-header-text-color,white)}
      button{font:inherit;background:none;border:0;color:inherit;font-size:24px;cursor:pointer;padding:8px}
      main{max-width:460px;margin:20px auto;padding:0 12px 24px}</style>
      <header><button aria-label="Открыть меню">☰</button><span>Plex пульт</span></header><main></main>`;
    this._card = document.createElement("plex-pc-remote-card");
    this._card.setConfig({});
    this.shadowRoot.querySelector("main").append(this._card);
    this.shadowRoot.querySelector("button").addEventListener("click", () =>
      this.dispatchEvent(new Event("hass-toggle-menu", {bubbles:true, composed:true})));
  }
  set hass(value) { this._card.hass = value; }
}

if (!customElements.get("plex-pc-remote-card")) customElements.define("plex-pc-remote-card", PlexRemoteCard);
if (!customElements.get("plex-pc-remote-panel")) customElements.define("plex-pc-remote-panel", PlexRemotePanel);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "plex-pc-remote-card")) {
  window.customCards.push({type:"plex-pc-remote-card", name:"Plex PC Remote", preview:true,
    description:"Полный пульт Plex: стрелки, Esc, Play/Pause, громкость и HomeKit. Устройство определяется автоматически."});
}
