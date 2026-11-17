const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('session polling runs only while visible and stops on close', () => {
  const source = fs.readFileSync('frontend/app.js', 'utf8');
  const code = source.slice(source.indexOf('let sessionStatusPollTimer = null;'),
    source.indexOf('async function loadSessionStatuses()'));
  let tick, cleared, loads = 0;
  const context = {
    window: {setInterval: (fn, ms) => {tick = fn; assert.equal(ms, 5000); return 17;},
      clearInterval: id => {cleared = id;}},
    document: {hidden: false},
    els: {sessionStatusModal: {hidden: false}},
    state: {sessionStatusLoading: false},
    loadSessionStatuses: () => {loads++;},
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  context.startSessionStatusPolling();
  tick();
  assert.equal(loads, 1);
  context.state.sessionStatusLoading = true;
  tick();
  context.state.sessionStatusLoading = false;
  context.document.hidden = true;
  tick();
  assert.equal(loads, 1);
  context.stopSessionStatusPolling();
  assert.equal(cleared, 17);
});
