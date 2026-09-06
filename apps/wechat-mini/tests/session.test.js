const test=require('node:test'),assert=require('node:assert/strict');
const lifecycle=require('../lib/session'),{makeClient}=require('../lib/client'),{base}=require('../lib/page');
function setup(){
 const storage={},files=new Set(['/sandbox/fitcrew-private-export.json']);
 const wx={env:{USER_DATA_PATH:'/sandbox'},getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],getStorageInfoSync:()=>({keys:Object.keys(storage)}),getFileSystemManager:()=>({readdirSync:()=>[...files].map(p=>p.split('/').pop()),unlinkSync:p=>files.delete(p)})};
 global.wx=wx;return {wx,storage,files};
}
function page(){const p=base({data:{note:'',caps:null,exportPath:''}});p.setData=function(v){Object.assign(this.data,v);};p.syncBoundary();return p;}
test('401 clears credentials and cached tabs, exposes login, removes export',async()=>{
 const {wx,storage,files}=setup();lifecycle.install(wx,{device_token:'old'});const p=page();p.setData({signedIn:true,note:'private',state:{logs:['private']}});files.add(lifecycle.exportPath(wx));
 wx.request=o=>o.success({statusCode:401,data:{detail:'expired'}});
 await assert.rejects(makeClient(wx,'https://api.fitcrew.test').request('/v3/state'),/过期/);
 assert.equal(storage['fitcrew.session'],undefined);assert.equal(p.data.signedIn,false);assert.equal(p.data.note,'');assert.equal(p.data.state,null);assert.equal(files.size,0);
});
test('30-day expiry invalidates old tabs and missing timestamps fail closed',()=>{
 const {wx}=setup();wx.setStorageSync('fitcrew.session',{device_token:'old',created_at:Date.now()-30*86400000});
 const p=page();assert.equal(lifecycle.active(wx),null);assert.equal(p.data.signedIn,false);
 wx.setStorageSync('fitcrew.session',{device_token:'legacy'});assert.equal(lifecycle.active(wx),null);
});
test('delayed old response cannot populate new account or invalidate its token',async()=>{
 const {wx}=setup();lifecycle.install(wx,{device_token:'old'});const p=page();let callback;
 wx.request=o=>callback=o;const api=makeClient(wx,'https://api.fitcrew.test');global.getApp=()=>({api});
 const pending=p.refresh();lifecycle.install(wx,{device_token:'new'});callback.success({statusCode:200,data:{logs:[{note:'old private'}],experiments:[]}});
 await pending;assert.equal(p.data.state,null);assert.equal(wx.getStorageSync('fitcrew.session').device_token,'new');
 const other=api.request('/v3/state');lifecycle.install(wx,{device_token:'newer'});callback.success({statusCode:401,data:{}});
 await assert.rejects(other,/账户已变化/);assert.equal(wx.getStorageSync('fitcrew.session').device_token,'newer');
});
test('data deletion keeps identity but resets hidden tab draft and invalidates pending write',async()=>{
 const {wx,files}=setup();lifecycle.install(wx,{device_token:'same'});const p=page();p.setData({note:'old note'});wx.setStorageSync('fitcrew.draft',{note:'old note'});
 let resolve;global.getApp=()=>({api:{request:()=>new Promise(r=>resolve=r)}});const write=p.write('log','/v3/logs',{note:'old note'});
 files.add(lifecycle.exportPath(wx));lifecycle.boundary(wx,true);resolve({id:'old-write'});
 assert.equal(await write,false);assert.equal(p.data.note,'');assert.equal(wx.getStorageSync('fitcrew.draft'),undefined);assert.equal(files.size,0);assert.equal(wx.getStorageSync('fitcrew.session').device_token,'same');
});
test('export cleanup is independent of volatile page.exportPath and login fails closed if unlink fails',()=>{
 const {wx,files}=setup();assert.equal(files.size,1);lifecycle.cleanExport(wx);assert.equal(files.size,0);
 wx.getFileSystemManager=()=>({readdirSync:()=>['fitcrew-private-export.json'],unlinkSync:()=>{throw Error('disk');}});
 assert.throws(()=>lifecycle.install(wx,{device_token:'new'}),/未能清除/);assert.equal(wx.getStorageSync('fitcrew.session'),undefined);
});
