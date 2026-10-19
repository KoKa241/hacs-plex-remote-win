const {test, before} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
let window;
before(async () => {
  const {Window} = await import('happy-dom');
  window = new Window();
  window.eval(fs.readFileSync('custom_components/plex_pc_remote/www/plex-remote.js', 'utf8'));
});
function mount(overrides = {}) {
  const calls = [];
  const element = window.document.createElement('plex-pc-remote-card');
  element.setConfig({});
  window.document.body.append(element);
  const hass = {user:{is_admin:true}, states:{'remote.actual_name':{
    state:'on', attributes:{integration:'plex_pc_remote',input_ready:true,tv_entity_id:'media_player.actual_tv',friendly_name:'Living room'},
  }}, callService:async (...args)=>calls.push(args), ...overrides};
  element.hass = hass;
  return {element,calls,hass};
}
test('renders all arrows, Esc, seeking, volume and true toggle independently of media-player state', async () => {
  const {element,calls} = mount();
  for (const command of ['up','down','left','right','select','back','seek_forward','seek_backward','volume_up','volume_down','play_pause']) {
    assert.equal(element.shadowRoot.querySelector(`[data-command="${command}"]`).disabled, false);
    await element._send(command);
    assert.deepEqual(JSON.parse(JSON.stringify(calls.at(-1))), ['remote','send_command',{entity_id:'remote.actual_name',command}]);
  }
  await element._send('play_pause');
  assert.equal(calls.at(-1)[2].command, 'play_pause');
  assert.equal(calls.at(-2)[2].command, 'play_pause');
});
test('power works while closed; navigation is disabled', async () => {
  const {element,hass,calls} = mount();
  hass.states['remote.actual_name'].state='off'; element.hass=hass;
  await element._send('up'); assert.equal(calls.length,0);
  await element._send('toggle'); assert.equal(calls.at(-1)[2].command,'toggle');
});
test('old server is detected rather than sending F11 again', async () => {
  const {element,hass,calls} = mount();
  hass.states['remote.actual_name'].attributes.input_ready=null; element.hass=hass;
  assert.match(element.shadowRoot.querySelector('.warning').textContent, /Обновите Windows/);
  await element._send('volume_up'); assert.equal(calls.length,0);
});
test('pending profile restart disables keys and leaves power available', async () => {
  const {element,hass} = mount();
  hass.states['remote.actual_name'].attributes.input_ready=false; element.hass=hass;
  assert.equal(element.shadowRoot.querySelector('[data-command="volume_up"]').disabled,true);
  assert.equal(element.shadowRoot.querySelector('[data-command="toggle"]').disabled,false);
});
test('HomeKit creation uses actual linked TV entity, not a hardcoded name', async () => {
  const {element,calls}=mount(); await element._homekit();
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0])), ['plex_pc_remote','expose_homekit',{entity_id:'media_player.actual_tv'}]);
  assert.equal(element.shadowRoot.querySelector('.pairing').hidden,false);
});
test('service errors appear and buttons recover', async () => {
  const {element}=mount({callService:async()=>{throw new Error('Windows denied focus');}});
  await element._send('play_pause');
  assert.match(element.shadowRoot.querySelector('.error').textContent,/Windows denied focus/);
  assert.equal(element.shadowRoot.querySelector('.error').hidden,false);
  assert.equal(element.shadowRoot.querySelector('[data-command="play_pause"]').disabled,false);
});
test('unavailable server blocks power too', async () => {
  const {element,hass,calls}=mount(); hass.states['remote.actual_name'].state='unavailable';element.hass=hass;
  await element._send('toggle');assert.equal(calls.length,0);
});
test('multiple computers can be selected and entity names are not interpreted as markup', async () => {
  const {element,hass,calls}=mount();
  hass.states['remote.second']={state:'on',attributes:{integration:'plex_pc_remote',input_ready:true,friendly_name:'<img src=x onerror=alert(1)>'}};
  element.hass=hass;
  const select=element.shadowRoot.querySelector('select');
  assert.equal(select.hidden,false);assert.equal(select.querySelector('img'),null);
  select.value='remote.second';select.dispatchEvent(new window.Event('change'));
  await element._send('up');assert.equal(calls[0][2].entity_id,'remote.second');
});
test('panel mounts the same complete remote', () => {
  const panel=window.document.createElement('plex-pc-remote-panel');window.document.body.append(panel);
  assert.ok(panel.shadowRoot.querySelector('plex-pc-remote-card'));
});

function pointer(pad,type,id,x,y){pad[type]({pointerId:id,clientX:x,clientY:y,button:0,preventDefault(){}});}
async function flushPad(pad){clearTimeout(pad.timer);pad.timer=null;await pad.drain();}
function padFixture(){
  const f=mount();f.ws=[];f.hass.callWS=async m=>f.ws.push(m);
  f.hass.states['remote.actual_name'].attributes.desktop_input=true;f.element.hass=f.hass;
  f.pad=f.element.shadowRoot.querySelector('plex-touchpad');f.pad.setMode('plex');return f;
}
test('Plex down swipe emits down once, never OK or desktop input',async()=>{
  const {pad,calls,ws}=padFixture();pointer(pad,'down',1,50,50);pointer(pad,'move',1,52,90);pointer(pad,'move',1,52,160);pointer(pad,'up',1,52,160);await flushPad(pad);
  assert.deepEqual(calls.map(x=>x[2].command),['down']);assert.equal(ws.length,0);
});
test('Plex tap = select; two-finger tap = back',async()=>{
  const {pad,calls}=padFixture();pointer(pad,'down',1,50,50);pointer(pad,'up',1,51,51);
  pointer(pad,'down',1,50,50);pointer(pad,'down',2,80,50);pointer(pad,'up',1,50,50);pointer(pad,'up',2,80,50);await flushPad(pad);
  assert.deepEqual(calls.map(x=>x[2].command),['select','back']);
});
test('sub-threshold drag never becomes accidental OK; cancelled gestures send nothing',async()=>{
  const {pad,calls}=padFixture();pointer(pad,'down',1,0,0);pointer(pad,'move',1,20,0);pointer(pad,'up',1,20,0);
  pointer(pad,'down',1,0,0);pad.cancel();pointer(pad,'up',1,0,0);await flushPad(pad);assert.equal(calls.length,0);
});
test('mouse sends relative movement while Plex is off and does not focus Plex',async()=>{
  const {pad,hass,element,ws,calls}=padFixture();hass.states['remote.actual_name'].state='off';element.hass=hass;pad.setMode('mouse');
  pointer(pad,'down',1,50,50);pointer(pad,'move',1,70,60);pointer(pad,'up',1,70,60);await flushPad(pad);
  assert.equal(calls.length,0);assert.equal(ws[0].payload.kind,'move');assert.equal(ws[0].payload.dx,30);assert.equal(ws[0].payload.dy,15);
});
test('mouse two-finger scroll does not click or move cursor',async()=>{
  const {pad,ws}=padFixture();pad.setMode('mouse');pointer(pad,'down',1,50,50);pointer(pad,'down',2,80,50);
  pointer(pad,'move',1,50,100);pointer(pad,'move',2,80,100);pointer(pad,'up',1,50,100);pointer(pad,'up',2,80,100);await flushPad(pad);
  assert.ok(ws.length>0);assert.ok(ws.every(m=>m.payload.kind==='scroll'));
});
test('changing mode drops unsent actions',async()=>{
  const {pad,calls,ws}=padFixture();pointer(pad,'down',1,0,0);pointer(pad,'move',1,60,0);pad.setMode('mouse');await flushPad(pad);assert.equal(calls.length+ws.length,0);
});
test('Unicode text sent exactly once and cleared only after acknowledgement',async()=>{
  const {pad,ws}=padFixture();pad.setMode('mouse');const box=pad.shadowRoot.querySelector('textarea');box.value='Привет 🙂';
  const pending=pad.sendText();await flushPad(pad);await pending;
  assert.equal(ws.length,1);assert.equal(ws[0].payload.text,'Привет 🙂');assert.equal(box.value,'');
});
test('failed text retained and never automatically retried',async()=>{
  const {pad,hass}=padFixture();let attempts=0;hass.callWS=async()=>{attempts++;throw new Error('blocked');};pad.setMode('mouse');const box=pad.shadowRoot.querySelector('textarea');box.value='text';
  const pending=pad.sendText();await flushPad(pad);await pending;assert.equal(attempts,1);assert.equal(box.value,'text');assert.match(pad.shadowRoot.querySelector('.notice').textContent,/blocked/);
});
test('shortcuts are explicit desktop packets, not Plex keys',async()=>{
  const {pad,ws}=padFixture();pad.setMode('mouse');
  for(const key of ['escape','alt_f4','task_manager']){pad.shadowRoot.querySelector(`[data-shortcut="${key}"]`).click();await flushPad(pad);assert.equal(ws.at(-1).payload.key,key);}
});

test('original button remote remains visible without expanding a section',()=>{
  const {element}=mount();
  assert.equal(element.shadowRoot.querySelector('details'),null);
  assert.ok(element.shadowRoot.querySelector('.keys [data-command="up"]'));
});
test('Plex pad provides independent controls and can power on a closed Plex',async()=>{
  const {pad,hass,calls,element}=padFixture();
  for(const command of ['back','volume_down','mute','volume_up','play_pause','stop','fullscreen','toggle']){
    const b=pad.shadowRoot.querySelector(`[data-plex="${command}"]`);
    assert.equal(b.disabled,false);b.click();await flushPad(pad);
    assert.equal(calls.at(-1)[2].command,command);
  }
  hass.states['remote.actual_name'].state='off';element.hass=hass;
  assert.equal(pad.shadowRoot.querySelector('[data-plex="back"]').disabled,true);
  const power=pad.shadowRoot.querySelector('[data-plex="toggle"]');
  assert.equal(power.disabled,false);power.click();await flushPad(pad);
  assert.equal(calls.at(-1)[2].command,'toggle');
});

test('tabs show only one control surface and clear pending pointer input',async()=>{
  const {element,hass}=mount();
  const root=element.shadowRoot,pad=root.querySelector('plex-touchpad');
  hass.states['remote.actual_name'].attributes.desktop_input=true;
  element.hass=hass;
  assert.equal(root.querySelector('#plex-panel').hidden,false);
  assert.equal(root.querySelector('#mouse-panel').hidden,true);
  assert.equal(pad.mode,'mouse');
  root.querySelector('[data-tab="mouse"]').click();
  assert.equal(root.querySelector('#plex-panel').hidden,true);
  assert.equal(root.querySelector('#mouse-panel').hidden,false);
  pad.enqueue('desktop',{kind:'move',dx:10,dy:5});
  root.querySelector('[data-tab="plex"]').click();
  assert.equal(pad.queue.length,0);
  assert.equal(root.querySelector('#mouse-panel').hidden,true);
});
test('Windows key and shortcuts belong to the mouse keyboard section',async()=>{
  const {pad,ws}=padFixture();pad.setMode('mouse');
  const win=pad.shadowRoot.querySelector('.desktop [data-shortcut="windows"]');
  assert.ok(win);assert.equal(pad.shadowRoot.querySelector('.plex-controls [data-shortcut]'),null);
  win.click();await flushPad(pad);
  assert.equal(ws.at(-1).payload.key,'windows');
});
