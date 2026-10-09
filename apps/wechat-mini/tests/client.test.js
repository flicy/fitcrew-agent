const test=require('node:test'),assert=require('node:assert/strict');
const {makeClient,mutation,finish,clearPrivate,validBase,validCloud}=require('../lib/client');
function platform(){const store={};return {store,getStorageSync:k=>store[k],setStorageSync:(k,v)=>store[k]=v,removeStorageSync:k=>delete store[k],getStorageInfoSync:()=>({keys:Object.keys(store)})};}
test('fails closed for missing production config and missing identity',async()=>{const wx=platform();await assert.rejects(makeClient(wx,'').request('/v3/state'));await assert.rejects(makeClient(wx,'https://api.fitcrew.test').request('/v3/state'));assert.equal(validBase('http://localhost'),false);});
test('login has no authorization; private mutations serialize bearer and exact body',async()=>{const wx=platform();let sent;wx.request=o=>{sent=o;o.success({statusCode:200,data:{ok:true}});};const api=makeClient(wx,'https://api.fitcrew.test');await api.request('/v3/auth/wechat','POST',{code:'synthetic-code',privacy_version:'2026-09-07'},true);assert.equal(sent.header.Authorization,undefined);wx.setStorageSync('fitcrew.session',{device_token:'synthetic-token',created_at:Date.now()});const body=mutation(wx,'log',{energy:3});await api.request('/v3/logs','POST',body);assert.equal(sent.header.Authorization,'Bearer synthetic-token');assert.deepEqual(sent.data,body);assert.equal(sent.url,'https://api.fitcrew.test/v3/logs');});
test('transport and non-2xx failures never produce synthetic success',async()=>{const wx=platform();wx.setStorageSync('fitcrew.session',{device_token:'synthetic-token',created_at:Date.now()});const api=makeClient(wx,'https://api.fitcrew.test');wx.request=o=>o.fail({});await assert.rejects(api.request('/v3/state'),/网络/);wx.request=o=>o.success({statusCode:409,data:{detail:'stale revision'}});await assert.rejects(api.request('/v3/state'),/stale revision/);});
test('retry ID survives relaunch; changed content gets new UUID; acknowledged completion clears intent',()=>{const wx=platform();const a=mutation(wx,'log',{energy:3});assert.match(a.request_id,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);assert.deepEqual(mutation(wx,'log',{energy:3}),a);assert.notEqual(mutation(wx,'log',{energy:4}).request_id,a.request_id);finish(wx,'log');assert.equal(wx.getStorageSync('fitcrew.pending.log'),undefined);});
test('account cleanup clears scoped secrets/drafts/intents only',()=>{const wx=platform();wx.setStorageSync('fitcrew.session',{device_token:'synthetic',created_at:Date.now()});wx.setStorageSync('fitcrew.draft',{});wx.setStorageSync('unrelated','keep');clearPrivate(wx);assert.deepEqual(wx.store,{unrelated:'keep'});});
test('cloud transport keeps the same authenticated API contract without a request domain',async()=>{
 const wx=platform();let sent;
 wx.cloud={callContainer:o=>{sent=o;return Promise.resolve({statusCode:200,data:{ok:true}});}};
 const config={baseURL:'https://fitcrew-123.tcloudbaseapp.com',cloud:{env:'fitcrew-prod-123',service:'fitcrew-api'}};
 assert.equal(validCloud(config.cloud),true);
 await makeClient(wx,config).request('/v3/auth/wechat','POST',{code:'synthetic',privacy_version:'2026-09-07'},true);
 assert.equal(sent.header.Authorization,undefined);
 assert.equal(sent.header['X-WX-SERVICE'],'fitcrew-api');
 assert.equal(sent.config.env,'fitcrew-prod-123');
 assert.equal(sent.path,'/v3/auth/wechat');
 wx.setStorageSync('fitcrew.session',{device_token:'synthetic-token',created_at:Date.now()});
 await makeClient(wx,config).request('/v3/state');
 assert.equal(sent.header.Authorization,'Bearer synthetic-token');
 assert.equal(sent.path,'/v3/state');
});
test('cloud transport fails closed for incomplete settings and treats 401 as logout',async()=>{
 const wx=platform();wx.cloud={callContainer:()=>Promise.resolve({statusCode:401,data:{detail:'expired'}})};
 const config={baseURL:'https://fitcrew-123.tcloudbaseapp.com',cloud:{env:'fitcrew-prod-123',service:'fitcrew-api'}};
 assert.equal(validCloud({env:'',service:'fitcrew-api'}),false);
 await assert.rejects(makeClient(wx,{...config,cloud:{env:'',service:'fitcrew-api'}}).request('/v3/auth/wechat','POST',{},true),/服务尚未配置/);
 wx.setStorageSync('fitcrew.session',{device_token:'synthetic-token',created_at:Date.now()});
 await assert.rejects(makeClient(wx,config).request('/v3/state'),/登录已过期/);
 assert.equal(wx.getStorageSync('fitcrew.session'),undefined);
});
