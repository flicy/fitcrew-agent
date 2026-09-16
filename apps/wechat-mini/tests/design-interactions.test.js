const test = require('node:test');
const assert = require('node:assert/strict');
const {base} = require('../lib/page');
const {textScale} = require('../lib/presentation');
function setup(name) {
  const storage = {};
  global.wx = {getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],getStorageInfoSync:()=>({keys:Object.keys(storage)})};
  let request;
  global.getApp=()=>({api:{request:(...args)=>request(...args)}});
  let definition=base();
  if(name){global.Page=d=>definition=d;delete require.cache[require.resolve('../pages/'+name+'/index')];require('../pages/'+name+'/index');}
  const page={...definition,data:structuredClone(definition.data),setData(d){Object.assign(this.data,d)}};
  page.onLoad();
  return {page,storage,setRequest:f=>request=f};
}
const state={logs:[],experiments:[]};
test('discrete energy controls persist draft and still lock during a pending save', async()=>{
  const {page,storage,setRequest}=setup('log');
  page.choose({currentTarget:{dataset:{field:'energy',value:'5'}}});
  assert.equal(page.data.energy,5);assert.equal(storage['fitcrew.draft'].energy,5);
  let acknowledge;
  setRequest((path,method,body)=>path==='/v3/logs'?new Promise(resolve=>acknowledge=resolve):Promise.resolve(state));
  const save=page.save();page.choose({currentTarget:{dataset:{field:'stress',value:'3'}}});
  assert.equal(page.data.stress,2);acknowledge({id:'synthetic'});await save;
  assert.equal(page.data.notice,'已保存。');assert.equal(storage['fitcrew.draft'],undefined);
});
test('success feedback requires acknowledgment, distinguishes refresh failure, and resets at boundary', async()=>{
  const {page,setRequest}=setup();setRequest(async()=>{throw Error('offline')});
  assert.equal(await page.write('a','/v3/logs',{}),false);assert.equal(page.data.notice,'');
  setRequest(async(path,method)=>{if(method==='POST')return {id:'saved'};throw Error('read failed')});
  assert.equal(await page.write('a','/v3/logs',{}),true);assert.match(page.data.notice,/已保存，最新内容暂未读到/);
  page.resetPrivate();assert.equal(page.data.notice,'');assert.equal(page.data.textScale,1);
});
test('font preferences tolerate unsupported hosts and preserve large text choices',()=>{
  assert.equal(textScale({}),1);assert.equal(textScale({getAppBaseInfo:()=>({fontSizeScaleFactor:1.6})}),1.6);
  assert.equal(textScale({getAppBaseInfo:()=>({fontSizeSetting:20.8})}),1.3);
  assert.equal(textScale({getAppBaseInfo:()=>{throw Error('unsupported')}}),1);
});
test('new goal controls cannot change selection while saving',()=>{
  const {page}=setup('journey');page.chooseGoal({currentTarget:{dataset:{index:'2'}}});assert.equal(page.data.goalIndex,2);
  page.setData({busy:true});page.chooseGoal({currentTarget:{dataset:{index:'0'}}});assert.equal(page.data.goalIndex,2);
});
test('deletion without a receipt cannot show a success notice',async()=>{
  const {page,setRequest}=setup();setRequest(async()=>({deleted:true}));
  assert.equal(await page.write('forget','/v3/memories/synthetic',{},'DELETE'),false);
  assert.equal(page.data.notice,'');assert.match(page.data.error,/删除/);
});
test('health trends preserve measured zero, suppress conflicts and clear details on refresh failure',async()=>{
 const {page,setRequest}=setup();
 const metrics=status=>({steps:{value:status==='partial'?0:999,status,unit:'步',sample_count:1,sources:['synthetic']}});
 setRequest(async()=>({...state,health_trends:{points:[{date:'one',metrics:metrics('partial')},{date:'two',metrics:metrics('source_conflict')}]}}));
 await page.refresh();page.selectHealthMetric({currentTarget:{dataset:{metric:'steps'}}});
 assert.equal(page.data.healthPoints[0].value,0);assert.equal(page.data.healthPoints[0].known,true);
 assert.equal(page.data.healthPoints[1].value,null);assert.equal(page.data.healthObservedDays,1);
 page.openHealthPoint({currentTarget:{dataset:{date:'one'}}});assert.equal(page.data.selectedHealthPoint.value,0);
 setRequest(async()=>{throw Error('offline')});await page.refresh();
 assert.deepEqual(page.data.healthPoints,[]);assert.equal(page.data.selectedHealthPoint,null);
});
test('Today separates health sample coverage from manual records and clears it at boundaries',async()=>{
 const {page,setRequest}=setup('today');
 const points=Array.from({length:9},(_,i)=>({date:'2026-09-'+String(i+1).padStart(2,'0'),metrics:{
  sleep:{status:'not_authorized',value:null,sources:[]},
  steps:{status:i===7?'source_conflict':i===8?'partial':'missing',value:i===8?0:123,sources:['synthetic']},
  hrv:{status:'missing',value:null,sources:[]}
 }}));
 setRequest(async()=>({...state,logs:[{energy:5}],health_trends:{points,window_end:'2026-09-09',timezone:'Asia/Shanghai'}}));
 await page.refresh();
 const summary=page.data.healthReadiness;
 assert.equal(summary.windowStart,'2026-09-03');
 assert.equal(summary.metrics[0].detail,'未选择上传此类数据');
 assert.equal(summary.metrics[1].observedDays,1);assert.equal(summary.metrics[1].issueDays,1);
 assert.equal(summary.metrics[1].latestDate,'2026-09-09');
 assert.equal(summary.metrics[2].detail,'近七天暂无可用数值');
 assert.equal(page.data.showHealthReadiness,false);page.toggleHealthReadiness();assert.equal(page.data.showHealthReadiness,true);
 setRequest(async()=>{throw Error('offline')});await page.refresh();assert.equal(page.data.healthReadiness,null);
 page.resetPrivate();assert.equal(page.data.showHealthReadiness,false);assert.equal(page.data.healthReadiness,null);
});
