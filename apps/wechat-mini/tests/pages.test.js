const test=require('node:test'),assert=require('node:assert/strict');
const {base}=require('../lib/page');
function setup(){
 const storage={},wx={getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],getStorageInfoSync:()=>({keys:Object.keys(storage)})};
 global.wx=wx;let request;global.getApp=()=>({api:{request:(...args)=>request(...args)}});
 return {wx,setRequest:f=>request=f,storage};
}
function mount(definition){return {...definition,data:JSON.parse(JSON.stringify(definition.data)),setData(data){Object.assign(this.data,data);}};}
test('failed write preserves input and intent; retry sends same UUID',async()=>{
 const h=setup(),page=mount(base({data:{note:'draft'}})),sent=[];
 h.setRequest(async(path,method,body)=>{sent.push(body);throw new Error('offline');});
 assert.equal(await page.write('log','/v3/logs',{note:'draft'}),false);
 assert.equal(page.data.note,'draft');assert.equal(page.data.error,'offline');
 await page.write('log','/v3/logs',{note:'draft'});assert.equal(sent[0].request_id,sent[1].request_id);
 assert.equal(page.data.busy,false);
});
test('state is server-only and ascending logs display newest first',async()=>{
 const h=setup(),page=mount(base());h.setRequest(async()=>({journey:null,mission:null,health:{sample_count:0,last_sync_at:null},logs:[{id:'a'},{id:'b'}],experiments:[{id:'x',source:'rule_based',status:'proposed'}]}));
 await page.refresh();assert.equal(page.data.logs[0].id,'b');assert.equal(page.data.experiments[0].sourceLabel,'规则建议');
 h.setRequest(async()=>{throw new Error('401');});await page.refresh();assert.equal(page.data.state,null);assert.deepEqual(page.data.logs,[]);
});
test('account DELETE failure retains token; server receipt clears token',async()=>{
 const h=setup();h.wx.showModal=o=>o.success({confirm:true});h.wx.env={USER_DATA_PATH:'/synthetic-sandbox'};
 h.wx.getFileSystemManager=()=>({readdirSync:()=>[],unlinkSync:()=>{}});let definition;global.Page=d=>definition=d;
 require('../pages/profile/index');const page=mount(definition);h.wx.setStorageSync('fitcrew.session',{device_token:'synthetic',created_at:Date.now()});
 h.setRequest(async()=>{throw new Error('server rejected');});await page.erase({currentTarget:{dataset:{kind:'account'}}});
 assert.equal(h.storage['fitcrew.session'].device_token,'synthetic');assert.equal(page.data.receipt,'');
 let body;h.setRequest(async(path,method,data)=>{assert.equal(path,'/v3/account');assert.equal(method,'DELETE');body=data;return {deleted:true,receipt_id:'receipt-test'};});
 await page.erase({currentTarget:{dataset:{kind:'account'}}});assert.deepEqual(body,{confirmation:'DELETE'});assert.equal(h.storage['fitcrew.session'],undefined);assert.equal(page.data.receipt,'receipt-test');
});
test('pending log save locks edits so a newer draft cannot be silently discarded',async()=>{
 const h=setup();let definition;global.Page=d=>definition=d;
 require('../pages/log/index');const page=mount(definition);page.syncBoundary();
 page.edit({currentTarget:{dataset:{field:'note'}},detail:{value:'draft A'}});
 let resolveWrite,submitted;
 h.setRequest((path,method,body)=>{
  if(path==='/v3/logs'){submitted=body;return new Promise(resolve=>resolveWrite=resolve);}
  return Promise.resolve({logs:[],experiments:[],journey:null,mission:null});
 });
 const saving=page.save();assert.equal(page.data.busy,true);
 page.edit({currentTarget:{dataset:{field:'note'}},detail:{value:'draft B'}});
 page.edit({currentTarget:{dataset:{field:'energy'}},detail:{value:5}});
 assert.equal(page.data.note,'draft A');assert.equal(page.data.energy,3);
 assert.equal(h.storage['fitcrew.draft'].note,'draft A');assert.equal(submitted.note,'draft A');
 resolveWrite({id:'saved'});await saving;assert.equal(page.data.note,'');assert.equal(page.data.busy,false);
 page.edit({currentTarget:{dataset:{field:'note'}},detail:{value:'draft B'}});
 assert.equal(page.data.note,'draft B');assert.equal(h.storage['fitcrew.draft'].note,'draft B');
});
test('optional signals survive offline retry and clear only after acknowledgment',async()=>{
 const h=setup();let definition;global.Page=d=>definition=d;
 delete require.cache[require.resolve('../pages/log/index')];require('../pages/log/index');
 const page=mount(definition);page.onLoad();
 for(const [field,value] of Object.entries({sleepIndex:3,trainingIndex:2,sourceIndex:1,feelingIndex:4}))page.edit({currentTarget:{dataset:{field}},detail:{value}});
 const sent=[];h.setRequest(async(path,method,body)=>{sent.push(body);throw new Error('offline');});
 await page.save();assert.equal(page.data.sleepIndex,3);assert.equal(h.storage['fitcrew.draft'].trainingIndex,2);
 h.setRequest(async(path,method,body)=>{if(path==='/v3/logs'){sent.push(body);return {id:'saved'};}return {logs:[],experiments:[]};});
 await page.save();assert.equal(sent[0].request_id,sent[1].request_id);
 assert.equal(sent[1].sleep_feeling,'醒后疲惫');assert.equal(sent[1].training_feeling,'偏累');assert.equal(sent[1].stress_source,'工作');assert.equal(sent[1].feeling,'不适');
 assert.equal(page.data.sleepIndex,0);assert.equal(page.data.trainingIndex,0);assert.equal(page.data.sourceIndex,0);assert.equal(h.storage['fitcrew.draft'],undefined);
 await page.save();assert.equal(sent[2].sleep_feeling,null);assert.equal(sent[2].training_feeling,null);assert.equal(sent[2].stress_source,null);
 let destination;h.wx.switchTab=({url})=>destination=url;page.openExperiments();assert.equal(destination,'/pages/experiments/index');
});
test('lighten selection and cancel never write; confirmed choice retries unchanged',async()=>{
 const h=setup();let definition;global.Page=d=>definition=d;require('../pages/today/index');const page=mount(definition);page.onLoad();
 const sent=[];h.setRequest(async(path,method,body)=>{sent.push(body);throw new Error('offline');});
 await page.mission({currentTarget:{dataset:{action:'lighten'}}});assert.equal(page.data.choosing,true);assert.equal(sent.length,0);
 page.cancelLighten();assert.equal(page.data.choosing,false);assert.equal(sent.length,0);
 page.setData({state:{mission:{id:'2026-09-08',revision:2}}});
 await page.mission({currentTarget:{dataset:{action:'lighten'}}});
 page.setData({state:{mission:{id:'2026-09-09',revision:0}}});
 const choice={currentTarget:{dataset:{id:'quiet_minute'}}};await page.chooseLighten(choice);assert.equal(page.data.choosing,true);
 h.setRequest(async(path,method,body)=>{if(path==='/v3/mission'){sent.push(body);return {id:'saved'};}return {logs:[],experiments:[]};});
 await page.chooseLighten(choice);assert.equal(page.data.choosing,false);assert.equal(sent[0].alternative,'quiet_minute');assert.equal(sent[0].mission_id,'2026-09-08');assert.equal(sent[0].revision,2);assert.equal(sent[0].request_id,sent[1].request_id);
});
test('trend windows retain gaps and clear on failed refresh',async()=>{
 const h=setup(),page=mount(base());
 const points=Array.from({length:90},(_,i)=>({date:String(i),count:i===89?1:0,energy:i===89?4:null,stress:i===89?2:null}));
 h.setRequest(async()=>({logs:[],experiments:[],trends:{points}}));await page.refresh();
 assert.equal(page.data.trendPoints.length,30);assert.equal(page.data.observedDays,1);assert.equal(page.data.trendPoints[0].energy,null);
 page.selectTrend({currentTarget:{dataset:{days:60}}});assert.equal(page.data.trendPoints.length,60);
 page.selectTrend({currentTarget:{dataset:{days:90}}});assert.equal(page.data.trendPoints.length,90);
 page.openTrendPoint({currentTarget:{dataset:{date:'89'}}});assert.equal(page.data.selectedTrend.energy,4);
 h.setRequest(async()=>{throw new Error('offline');});await page.refresh();assert.deepEqual(page.data.trendPoints,[]);assert.equal(page.data.observedDays,0);assert.equal(page.data.selectedTrend,null);
});
test('experiment feedback cancel does not write and feedback-only does not confirm memory',async()=>{
 const h=setup();let definition;global.Page=d=>definition=d;delete require.cache[require.resolve('../pages/experiments/index')];require('../pages/experiments/index');const page=mount(definition);page.onLoad();
 page.setData({experiments:[{id:'experiment',revision:3,status:'completed'}]});
 const sent=[];h.setRequest(async(path,method,body)=>{if(method==='POST'){sent.push(body);return {id:'experiment'};}return {logs:[],experiments:[]};});
 h.wx.showActionSheet=o=>o.fail();const event={currentTarget:{dataset:{id:'experiment',assessment:'fits'}}};await page.feedback(event);assert.equal(sent.length,0);
 h.wx.showActionSheet=o=>o.success({tapIndex:0});await page.feedback(event);assert.equal(sent.length,1);assert.equal(sent[0].confirm_memory,false);assert.equal(sent[0].assessment,'fits');
});
