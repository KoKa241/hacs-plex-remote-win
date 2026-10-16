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

class PlexTouchpad extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:"open"});
    this.mode="plex"; this.points=new Map(); this.queue=[]; this.epoch=0;
    this.shadowRoot.innerHTML=`
    <style>
      :host{display:block;margin:0 0 18px;font:inherit;color:inherit}*{box-sizing:border-box}
      .modes,.clicks{display:flex;gap:8px;margin:10px 0}button{font:inherit;cursor:pointer;border:0;border-radius:12px;
      padding:12px;background:var(--secondary-background-color,#eef0f3);color:inherit;min-height:44px;touch-action:manipulation}
      .modes button,.clicks button{flex:1}button[aria-pressed=true]{background:#e5ad30;color:#16191e}
      button:disabled{opacity:.4;cursor:default}button:focus-visible,.pad:focus-visible{outline:3px solid var(--primary-color,#168ada)}
      .pad{height:225px;border:2px solid var(--divider-color,#d3d7dc);border-radius:20px;display:flex;align-items:center;
      justify-content:center;text-align:center;padding:24px;touch-action:none;user-select:none;-webkit-user-select:none;
      background:radial-gradient(circle,var(--divider-color,#ddd) 1px,transparent 1px);background-size:18px 18px}
      .pad[aria-disabled=true]{opacity:.4}.pad span{background:var(--card-background-color,#fff);border-radius:12px;padding:12px;pointer-events:none;line-height:1.6}
      .hint,.notice{font-size:12px;line-height:1.5;margin:8px 0}.notice{color:var(--error-color,#b92333)}
      textarea{font:inherit;font-size:16px;width:100%;min-height:85px;resize:vertical;border:1px solid var(--divider-color,#ccc);
      background:var(--card-background-color,#fff);color:inherit;border-radius:12px;padding:10px;margin-top:10px}
      .shortcuts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px}.shortcuts button{font-size:12px}
      .send{width:100%;margin-top:6px}.notice:empty{display:none}[hidden]{display:none!important}
    </style>
    <div class="modes" role="group" aria-label="Режим площадки"><button data-mode="plex" aria-pressed="true">Жесты Plex</button><button data-mode="mouse" aria-pressed="false">Мышь Windows</button></div>
    <div class="pad" tabindex="0" role="group" aria-label="Сенсорная площадка"><span></span></div>
    <p class="hint"></p><p class="notice" role="status" aria-live="polite"></p>
    <div class="desktop" hidden>
      <div class="clicks"><button data-click="left">Левый клик</button><button data-click="right">Правый клик</button></div>
      <label>Текст в активное окно Windows<textarea maxlength="2000" placeholder="Введите текст и нажмите «Отправить»" aria-label="Текст в Windows"></textarea></label>
      <button class="send">Отправить текст</button>
      <div class="shortcuts"></div>
      <p class="hint">Alt+F4 закрывает активное окно. Текст и сочетания отправляются в окно, выбранное на компьютере.</p>
    </div>`;
    for(const button of this.shadowRoot.querySelectorAll('[data-mode]')) button.addEventListener('click',()=>this.setMode(button.dataset.mode));
    for(const button of this.shadowRoot.querySelectorAll('[data-click]')) button.addEventListener('click',()=>this.desktop({kind:'click',button:button.dataset.click}));
    const shortcuts=[['escape','Esc'],['enter','Enter'],['backspace','⌫ Backspace'],['tab','Tab'],['delete','Delete'],['alt_tab','Alt+Tab'],['alt_f4','Закрыть · Alt+F4'],['task_manager','Диспетчер задач'],['show_desktop','Рабочий стол'],['select_all','Выделить всё'],['copy','Копировать'],['paste','Вставить']];
    for(const [key,title] of shortcuts){const b=document.createElement('button');b.textContent=title;b.dataset.shortcut=key;
      b.addEventListener('click',()=>this.desktop({kind:'shortcut',key}));this.shadowRoot.querySelector('.shortcuts').append(b);}
    this.shadowRoot.querySelector('.send').addEventListener('click',()=>this.sendText());
    const pad=this.shadowRoot.querySelector('.pad');
    pad.addEventListener('pointerdown',e=>this.down(e));pad.addEventListener('pointermove',e=>this.move(e));
    pad.addEventListener('pointerup',e=>this.up(e));pad.addEventListener('pointercancel',()=>this.cancel());
    pad.addEventListener('lostpointercapture',e=>{if(this.points.has(e.pointerId))this.cancel();});
    pad.addEventListener('contextmenu',e=>e.preventDefault());
    pad.addEventListener('keydown',e=>{if(this.mode==='plex'&&this.enabled){const c={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',Enter:'select',Escape:'back'}[e.key];if(c){e.preventDefault();this.plex(c);}}});
    this._blur=()=>this.cancel();this._visibility=()=>{if(document.hidden)this.cancel();};
  }
  connectedCallback(){window.addEventListener('blur',this._blur);document.addEventListener('visibilitychange',this._visibility);this.render();}
  disconnectedCallback(){window.removeEventListener('blur',this._blur);document.removeEventListener('visibilitychange',this._visibility);this.cancel();this.shadowRoot.querySelector('textarea').value='';}
  configure(hass,entity){
    if(entity!==this.entity){this.cancel();this.shadowRoot.querySelector('textarea').value='';}
    this.hass=hass;this.entity=entity;this.render();
  }
  setMode(mode){if(!['plex','mouse'].includes(mode)||mode===this.mode)return;this.cancel();this.mode=mode;this.shadowRoot.querySelector('.notice').textContent='';this.render();}
  render(){
    const s=this.hass?.states[this.entity]; const online=s&&!['unavailable','unknown'].includes(s.state);
    this.enabled=Boolean(online&&(this.mode==='mouse'?s.attributes.desktop_input===true:s.state==='on'&&s.attributes.input_ready===true));
    if(!this.enabled&&(this.points.size||this.queue.length))this.cancel();
    for(const b of this.shadowRoot.querySelectorAll('[data-mode]'))b.setAttribute('aria-pressed',String(b.dataset.mode===this.mode));
    this.shadowRoot.querySelector('.desktop').hidden=this.mode!=='mouse';
    this.shadowRoot.querySelector('.pad').setAttribute('aria-disabled',String(!this.enabled));
    this.shadowRoot.querySelector('.pad span').textContent=this.mode==='plex'?'↑  ←  OK  →  ↓':'Тачпад Windows';
    this.shadowRoot.querySelector('.hint').textContent=this.mode==='plex'?'Свайп — стрелка · касание — OK · два пальца — Esc'
      :online&&!s.attributes.desktop_input?'Для мыши обновите Windows-сервер до 1.2.0.':'Один палец — курсор · касание — клик · два пальца — прокрутка / правый клик';
    for(const b of this.shadowRoot.querySelectorAll('.desktop button'))b.disabled=!this.enabled||Boolean(this.sendingText);
  }
  cancel(){this.points.clear();this.gesture=null;this.epoch++;clearTimeout(this.timer);this.timer=null;for(const item of this.queue)item.resolve(false);this.queue=[];}
  center(){const a=[...this.points.values()];return{x:a.reduce((s,p)=>s+p.x,0)/a.length,y:a.reduce((s,p)=>s+p.y,0)/a.length};}
  down(e){
    if(!this.enabled||e.button>0)return;e.preventDefault();
    if(!this.points.size)this.gesture={time:Date.now(),max:0,multi:false,swiped:false,scroll:0,blocked:false};
    this.points.set(e.pointerId,{x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY});
    const g=this.gesture;g.multi ||= this.points.size>1;g.blocked ||= this.points.size>2;
    g.last=this.center();if(this.points.size===1)g.start=g.last;
    try{this.shadowRoot.querySelector('.pad').setPointerCapture(e.pointerId);}catch{/* Synthetic tests/older browsers. */}
  }
  move(e){
    if(!this.points.has(e.pointerId)||!this.gesture)return;e.preventDefault();
    const p=this.points.get(e.pointerId);p.x=e.clientX;p.y=e.clientY;
    const g=this.gesture;g.max=Math.max(g.max,Math.hypot(p.x-p.sx,p.y-p.sy));
    const c=this.center(),dx=c.x-g.last.x,dy=c.y-g.last.y;g.last=c;
    if(g.blocked)return;
    if(this.mode==='plex'){
      if(g.multi||g.swiped)return;
      const x=c.x-g.start.x,y=c.y-g.start.y;
      if(Math.max(Math.abs(x),Math.abs(y))>=32){g.swiped=true;this.plex(Math.abs(x)>Math.abs(y)?(x>0?'right':'left'):(y>0?'down':'up'));}
    }else if(this.points.size===2){
      g.scroll+=dy;const steps=Math.trunc(g.scroll/24);if(steps){g.scroll-=steps*24;this.desktop({kind:'scroll',steps:-steps});}
    }else if(!g.multi&&(dx||dy))this.desktop({kind:'move',dx:Math.round(dx*1.5),dy:Math.round(dy*1.5)});
  }
  up(e){
    if(!this.points.has(e.pointerId)||!this.gesture)return;
    this.move(e);const g=this.gesture;this.points.delete(e.pointerId);
    if(this.points.size){g.last=this.center();return;}
    this.gesture=null;
    if(g.blocked||g.swiped||g.max>10||Date.now()-g.time>600)return;
    if(this.mode==='plex')this.plex(g.multi?'back':'select');
    else this.desktop({kind:'click',button:g.multi?'right':'left'});
  }
  plex(command){if(!this.enabled||this.mode!=='plex')return Promise.resolve(false);navigator.vibrate?.(12);return this.enqueue('plex',{command});}
  desktop(payload){if(!this.enabled||this.mode!=='mouse')return Promise.resolve(false);return this.enqueue('desktop',payload);}
  enqueue(route,payload){
    if(this.queue.length>=16){this.shadowRoot.querySelector('.notice').textContent='Соединение не успевает. Повторите после завершения команды.';return Promise.resolve(false);}
    const previous=this.queue.at(-1);
    if(payload.kind==='move'&&previous?.payload.kind==='move'){
      previous.payload.dx=Math.max(-500,Math.min(500,previous.payload.dx+payload.dx));
      previous.payload.dy=Math.max(-500,Math.min(500,previous.payload.dy+payload.dy));return Promise.resolve(true);
    }
    if(payload.kind==='move'){payload.dx=Math.max(-500,Math.min(500,payload.dx));payload.dy=Math.max(-500,Math.min(500,payload.dy));}
    if(payload.kind==='scroll')payload.steps=Math.max(-10,Math.min(10,payload.steps));
    const result=new Promise(resolve=>this.queue.push({route,payload,entity:this.entity,epoch:this.epoch,resolve}));
    if(!this.running&&!this.timer)this.timer=setTimeout(()=>{this.timer=null;this.drain();},35);
    return result;
  }
  async drain(){
    if(this.running)return;this.running=true;
    try{while(this.queue.length){const item=this.queue.shift();
      if(item.epoch!==this.epoch){item.resolve(false);continue;}
      try{
        if(item.route==='plex')await this.hass.callService('remote','send_command',{entity_id:item.entity,...item.payload});
        else await this.hass.callWS({type:'plex_pc_remote/input',entity_id:item.entity,payload:item.payload});
        item.resolve(true);
      }catch(err){item.resolve(false);if(item.epoch===this.epoch){this.cancel();this.shadowRoot.querySelector('.notice').textContent=err.message||String(err);}break;}
    }}finally{this.running=false;if(this.queue.length)this.drain();}
  }
  async sendText(){
    if(this.sendingText)return;const box=this.shadowRoot.querySelector('textarea'),text=box.value;
    if(!text)return;const epoch=this.epoch;this.sendingText=true;this.render();
    try{const ok=await this.desktop({kind:'text',text});if(ok&&epoch===this.epoch&&box.value===text)box.value='';}
    finally{this.sendingText=false;this.render();}
  }
}

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
        <plex-touchpad></plex-touchpad>
        <details><summary style="cursor:pointer;padding:12px 0">Кнопки пульта Plex</summary><div class="keys"></div></details>
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
    this.shadowRoot.querySelector("plex-touchpad").configure(this._hass, this._selected);
    const state = this._state();
    const available = state && !["unavailable", "unknown"].includes(state.state);
    const on = state?.state === "on";
    const compatible = typeof state?.attributes.input_ready === "boolean";
    const ready = state?.attributes.input_ready === true;
    this.shadowRoot.querySelector(".status").textContent = !state ? "Пульт не найден — добавьте интеграцию Plex PC Remote"
      : !available ? "Сервер недоступен" : on ? "Plex открыт" : "Plex закрыт";
    const warning = this.shadowRoot.querySelector(".warning");
    warning.textContent = !available ? "" : !compatible
      ? "Обновите Windows-сервер до 1.2.0. Обновление только HACS не исправляет клавиши."
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

if (!customElements.get("plex-touchpad")) customElements.define("plex-touchpad", PlexTouchpad);
if (!customElements.get("plex-pc-remote-card")) customElements.define("plex-pc-remote-card", PlexRemoteCard);
if (!customElements.get("plex-pc-remote-panel")) customElements.define("plex-pc-remote-panel", PlexRemotePanel);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "plex-pc-remote-card")) {
  window.customCards.push({type:"plex-pc-remote-card", name:"Plex PC Remote", preview:true,
    description:"Полный пульт Plex: стрелки, Esc, Play/Pause, громкость и HomeKit. Устройство определяется автоматически."});
}
