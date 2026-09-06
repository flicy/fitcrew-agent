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
