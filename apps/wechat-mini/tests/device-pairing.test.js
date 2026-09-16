const test=require('node:test'),assert=require('node:assert/strict');
const lifecycle=require('../lib/session'),{base}=require('../lib/page'),actions=require('../lib/device-pairing');
function setup(){
 const storage={},copies=[];
 global.wx={getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],getStorageInfoSync:()=>({keys:Object.keys(storage)}),showModal:o=>o.success({confirm:true}),setClipboardData:o=>{copies.push(o.data);o.success();}};
 lifecycle.install(wx,{device_token:'synthetic'});
 const p=base({...actions,data:{pairingURL:'',pairingExpires:'',pairingBusy:false}});
 p.setData=function(v){Object.assign(this.data,v);};p.syncBoundary();
 return {p,storage,copies};
}
const result=()=>({pairing_url:'fitcrew-health://configure?payload=synthetic-secret',expires_at:new Date(Date.now()+900000).toISOString()});
test('connection needs confirmation; never copies or stores the link automatically',async()=>{
 const {p,storage,copies}=setup();let calls=0;
 global.getApp=()=>({api:{request:async()=>{calls++;return result();}}});
 wx.showModal=o=>o.success({confirm:false});await p.createPairing();assert.equal(calls,0);
 wx.showModal=o=>o.success({confirm:true});await p.createPairing();assert.equal(calls,1);
 assert.equal(copies.length,0);assert.ok(!JSON.stringify(storage).includes('synthetic-secret'));
 p.copyPairing();assert.equal(copies.length,1);
 p.clearPairingView();assert.equal(p.data.pairingURL,'');
});
test('unconfirmed network response retries with the same request id',async()=>{
 const {p}=setup();const ids=[];
 global.getApp=()=>({api:{request:async(path,method,body)=>{ids.push(body.request_id);if(ids.length===1)throw Error('offline');return result();}}});
 await p.createPairing();assert.match(p.data.error,/offline/);await p.createPairing();
 assert.equal(ids[0],ids[1]);assert.ok(p.data.pairingURL);
});
test('hidden page and changed account discard delayed pairing secrets',async()=>{
 for(const change of ['hide','account']){
  const {p}=setup();let resolve;
  global.getApp=()=>({api:{request:()=>new Promise(r=>resolve=r)}});
  const pending=p.createPairing();await Promise.resolve();
  if(change==='hide')p.clearPairingView();else lifecycle.install(wx,{device_token:'another'});
  resolve(result());await pending;assert.equal(p.data.pairingURL,'');assert.equal(p.data.pairingBusy,false);
 }
});
test('expired links cannot copy and cancellation requires a server acknowledgment',async()=>{
 const {p,copies}=setup();p.setData({...{pairingURL:result().pairing_url,pairingExpires:new Date(0).toISOString()}});p.copyPairing();assert.equal(copies.length,0);
 global.getApp=()=>({api:{request:async()=>({})}});await p.cancelPairing();assert.match(p.data.error,/未确认撤销/);
 global.getApp=()=>({api:{request:async()=>({cancelled:true})}});await p.cancelPairing();assert.match(p.data.notice,/已撤销/);
});
test('terminal connection conflict starts a new request instead of retrying forever',async()=>{
 const {p}=setup(),ids=[];
 global.getApp=()=>({api:{request:async(path,method,body)=>{ids.push(body.request_id);if(ids.length===1)throw Object.assign(Error('used'),{statusCode:409});return result();}}});
 await p.createPairing();await p.createPairing();assert.notEqual(ids[0],ids[1]);assert.ok(p.data.pairingURL);
});
test('disconnect acknowledges only its device and hides stale completion on page exit',async()=>{
 const {p}=setup();p.setData({pairedDevices:[{id:'one'},{id:'two'}]});
 global.getApp=()=>({api:{request:async()=>({disconnected:true,device_id:'one'})}});
 await p.disconnectDevice({currentTarget:{dataset:{id:'one'}}});assert.deepEqual(p.data.pairedDevices,[{id:'two'}]);
 let resolve;global.getApp=()=>({api:{request:()=>new Promise(r=>resolve=r)}});
 const pending=p.disconnectDevice({currentTarget:{dataset:{id:'two'}}});await Promise.resolve();p.clearPairingView();p.setData({notice:'new page'});resolve({disconnected:true,device_id:'two'});await pending;
 assert.equal(p.data.notice,'new page');
});
