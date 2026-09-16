const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {module:{exports:{}}};
vm.runInNewContext(fs.readFileSync(require.resolve('../templates/format.wxs'),'utf8'),context);
const {time} = context.module.exports;
test('UTC pairing expiry keeps its timezone instead of appearing local',()=>{
  assert.equal(time('2026-09-10T18:24:32.123Z'),'2026-09-10 18:24 UTC');
  assert.equal(time('2026-09-10T18:24:32+00:00'),'2026-09-10 18:24 UTC');
});
test('offset timestamps retain date, clock and positive or negative offset',()=>{
  assert.equal(time('2026-09-11T02:24:00+08:00'),'2026-09-11 02:24 UTC+08:00');
  assert.equal(time('2026-09-10T13:24:00-05:00'),'2026-09-10 13:24 UTC-05:00');
});
test('absent timezone is explicit and missing values remain empty-state copy',()=>{
  assert.equal(time('2026-09-10T18:24:00'),'2026-09-10 18:24（时区未注明）');
  assert.equal(time(null),'尚无记录');
  assert.equal(time(''),'尚无记录');
});
