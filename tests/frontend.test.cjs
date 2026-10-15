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
