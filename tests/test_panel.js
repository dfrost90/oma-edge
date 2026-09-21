// Exercise the panel's actual profile-editing functions without a running desktop.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const qml = fs.readFileSync(__dirname + '/../Panel.qml', 'utf8');
const context = {config: {version:1, enabled:true, profiles:[{monitor:'DP-1',workspace:'1',enabled:true,width:12,side:'right',fullBar:true,slots:[{id:'telegram',class:'telegram',weight:1}]}]}, draft:null, profileIndex:0, dirty:false, message:''};
context.root = context;
vm.createContext(context);
for (const name of ['clone','groupedProfiles','chooseWorkspaces','edit','save','addWindow']) {
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
context.windows.forEach((_, i) => context.addWindow(i));
assert.equal(context.draft.slots.map(s => s.label).join(','), 'Cliamp,Nvim,kitty');
assert.ok(context.draft.slots.every(s => s.class === 'kitty'));
assert.equal(context.draft.slots.map(s => s.preferred).join(','), '11,12,13');
console.log('Workspace editing and window title label checks passed');
