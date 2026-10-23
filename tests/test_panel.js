// Exercise the panel's actual profile-editing functions without a running desktop.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ProfileModel = require('../ProfileModel.js');
const qml = fs.readFileSync(__dirname + '/../Panel.qml', 'utf8');
const context = {config: {version:1, enabled:true, profiles:[{monitor:'DP-1',workspace:'1',enabled:true,width:12,side:'right',fullBar:true,slots:[{id:'telegram',class:'telegram',weight:1}]}]}, draft:null, profileIndex:0, dirty:false, message:''};
context.root = context;
context.ProfileModel = ProfileModel;
context.clone = ProfileModel.clone;
context.groupedProfiles = () => ProfileModel.groupedProfiles(context.config);
context.rpc = {running: false};
context.pendingSelection = '';
context.savedSelection = '';
context.state = {reload() {}, text: () => JSON.stringify(context.snapshot)};
vm.createContext(context);
for (const name of ['chooseWorkspaces','edit','save','addWindow','windowKey','selectProfile','finishRequest','readState']) {
  const start = qml.indexOf('    function ' + name + '(');
  const end = qml.indexOf('\n    }', start) + 6;
  vm.runInContext(qml.slice(start,end), context);
}
Object.defineProperty(context, 'profiles', {get: () => context.groupedProfiles()});
context.send = data => { context.sent = data; };
context.draft = context.clone(context.profiles[0]);
context.chooseWorkspaces(['1','2']);
context.save(false);
assert.equal(context.sent.config.profiles.length, 2);
const ids = context.sent.config.profiles.flatMap(p => p.slots.map(s => s.id));
assert.equal(new Set(ids).size, ids.length);
context.config = context.sent.config;
assert.equal(context.profiles.length, 1);
assert.equal(context.profiles[0].workspaces.join(','), '1,2');
context.draft = context.clone(context.profiles[0]);
context.chooseWorkspaces(['2']);
context.save(false);
assert.equal(context.sent.config.profiles.length, 1);
assert.equal(context.sent.config.profiles[0].workspace, '2');
context.chooseWorkspaces(['2','*']);
assert.equal(context.draft.workspaces.join(','), '*');
context.chooseWorkspaces(['*','3']);
assert.equal(context.draft.workspaces.join(','), '3');
context.chooseWorkspaces([]);
context.sent = null;
context.save(false);
assert.equal(context.sent, null);
assert.match(context.message, /Select at least/);
context.config.profiles.push({monitor:'DP-1',workspace:'4',slots:[]});
context.chooseWorkspaces(['4']);
context.save(false);
assert.equal(context.sent, null);
assert.match(context.message, /already has a profile/);
context.draft = {slots: []};
context.windows = [
  {class: 'kitty', title: 'Cliamp', stableId: '11'},
  {class: 'kitty', title: 'Nvim', stableId: '12'},
  {class: 'kitty', title: '', stableId: '13'}
];
const selectedKeys = context.windows.map(c => context.windowKey(c));
context.windows.reverse(); // Snapshot order can change while the picker is open.
selectedKeys.forEach(key => context.addWindow(key));
assert.equal(context.draft.slots.map(s => s.label).join(','), 'Cliamp,Nvim,kitty');
assert.ok(context.draft.slots.every(s => s.class === 'kitty'));
assert.equal(context.draft.slots.map(s => s.preferred).join(','), '11,12,13');
console.log('Workspace editing and window title label checks passed');

assert.equal(context.draft.slots[0].windowTitle, 'Cliamp');
context.windows = [];
context.addWindow(selectedKeys[0]);
assert.equal(context.draft.slots.length, 3);
assert.match(context.message, /closed/);

// Execute the real sender and Process startup handler: payload must use stdin.
const sendStart = qml.indexOf('    function send(data) {');
const sendEnd = qml.indexOf('\n    }', sendStart) + 6;
context.rpc = {running: false};
context.backend = '/plugin/backend.py';
vm.runInContext(qml.slice(sendStart, sendEnd), context);
const privateRequest = {action: 'save', config: {title: 'Private title\nКиїв'}};
context.send(privateRequest);
assert.deepEqual(Array.from(context.rpc.command), ['python3', '/plugin/backend.py', 'request-stdin']);
assert.equal(context.rpc.payload, JSON.stringify(privateRequest));
const rpcBlock = qml.slice(qml.indexOf('        id: rpc'));
assert.match(rpcBlock, /stdinEnabled: true/);
context.payload = context.rpc.payload;
context.write = data => { context.pipeData = data; };
vm.runInContext(rpcBlock.match(/onStarted: \{([\s\S]*?)\n        \}/)[1], context);
assert.equal(context.pipeData, JSON.stringify(privateRequest) + '\n');
assert.equal(context.payload, '');
console.log('Private panel requests use stdin, not command-line arguments');

// A failed request must preserve the selected profile and the editable draft.
context.config = {version:1, enabled:true, profiles:[1,2,3].map(n => ({
  monitor:'DP-1', workspace:String(n), enabled:true, side:'right', width:20, slots:[]
}))};
context.rpc.running = false;
context.send = data => { context.sent = data; };
context.selectProfile(0);
context.edit('width', 25);
context.save(false);
context.finishRequest({ok:false, error:'Reservation timed out'});
assert.equal(context.profileIndex, 0);
assert.equal(context.draft.width, 25);
assert.equal(context.dirty, true);
context.selectProfile(context.profileIndex);
assert.equal(context.draft.workspaces[0], '1');
assert.equal(context.draft.width, 20);

// A successful save selects the same logical profile after serialization reorders it.
context.edit('width', 30);
context.save(false);
context.finishRequest({ok:true});
context.snapshot = {config: context.sent.config};
context.readState();
assert.equal(context.draft.workspaces[0], '1');
assert.equal(context.draft.width, 30);
assert.equal(context.dirty, false);

// Slot IDs survive workspace additions/removals, app reordering and weight edits.
let config = {version:1, enabled:true, profiles:[{
  monitor:'DP-1', workspace:'1', enabled:true, side:'right', width:20,
  slots:[{id:'first', class:'chat', weight:1}, {id:'second', class:'browser', weight:1}]
}]};
let draft = ProfileModel.groupedProfiles(config)[0];
draft.workspaces.push('2');
config = ProfileModel.saveProfile(config, draft, false).config;
const original = JSON.parse(JSON.stringify(config));
const idsByWorkspace = Object.fromEntries(config.profiles.map(p => [p.workspace, p.slots.map(s=>s.id)]));
assert.deepEqual(idsByWorkspace['1'], ['first','second']);
assert.equal(new Set(config.profiles.flatMap(p=>p.slots.map(s=>s.id))).size, 4);
draft = ProfileModel.groupedProfiles(config)[0];
draft.slots.reverse();
draft.slots[0].weight = 3;
draft.workspaces = ['2','1','3'];
config = ProfileModel.saveProfile(config, draft, false).config;
for (const p of config.profiles.filter(p=>p.workspace!=='3')) {
  assert.deepEqual(p.slots.map(s=>s.id), idsByWorkspace[p.workspace].slice().reverse());
}
assert.equal(new Set(config.profiles.flatMap(p=>p.slots.map(s=>s.id))).size, 6);
assert.ok(config.profiles.every(p=>p.slots.every(s=>!('sourceIds' in s))));
assert.equal(original.profiles[0].slots[0].weight, 1);
draft = ProfileModel.groupedProfiles(config)[0];
draft.workspaces = ['2'];
const reduced = ProfileModel.saveProfile(config, draft, false).config;
assert.deepEqual(reduced.profiles[0].slots.map(s=>s.id), idsByWorkspace['2'].slice().reverse());
console.log('Failed-save selection, successful-save selection and stable slot IDs passed');
