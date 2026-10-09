const test=require('node:test'),assert=require('node:assert/strict');
function setup(){
 const store={'fitcrew.session':{device_token:'synthetic',created_at:Date.now()}},files=new Set(['fitcrew-private-export.json']);
 let failCleanup=true,requests=0,shares=0,definition;
 global.wx={env:{USER_DATA_PATH:'/synthetic'},getStorageSync:k=>store[k],setStorageSync:(k,v)=>store[k]=v,removeStorageSync:k=>delete store[k],getStorageInfoSync:()=>({keys:Object.keys(store)}),
  showModal:o=>o.success({confirm:true}),shareFileMessage:()=>shares++,
  getFileSystemManager:()=>({readdirSync:()=>[...files],unlinkSync:()=>{if(failCleanup)throw new Error('synthetic cleanup failure');files.clear();},writeFileSync:()=>files.add('fitcrew-private-export.json')})};
 global.getApp=()=>({api:{request:async()=>{requests++;return {export_metadata:{scope:'all'}};}}});
 global.Page=d=>definition=d;delete require.cache[require.resolve('../pages/profile/index')];require('../pages/profile/index');
 const page={...definition,data:JSON.parse(JSON.stringify(definition.data)),setData(d){Object.assign(this.data,d);}};
 page.syncBoundary();page.setData({exportPath:'/synthetic/fitcrew-private-export.json'});
 return {page,store,files,allowCleanup:()=>failCleanup=false,requests:()=>requests,shares:()=>shares};
}
test('failed replacement cleanup disables old sharing and blocks generation until retry',async()=>{
 const h=setup();await h.page.exportData();
 assert.equal(h.requests(),0);assert.equal(h.page.data.exportPath,'');assert.match(h.page.data.error,/cleanup failure/);
 await h.page.shareExport();assert.equal(h.shares(),0);assert.equal(h.files.size,1);
 h.allowCleanup();await h.page.exportData();assert.equal(h.requests(),1);assert.equal(h.page.data.exportPath,'/synthetic/fitcrew-private-export.json');
 await h.page.shareExport();assert.equal(h.shares(),1);
});
test('explicit cleanup failure hides the old file and successful retry removes it',async()=>{
 const h=setup();h.page.clearExport();assert.equal(h.page.data.exportPath,'');assert.match(h.page.data.error,/未确认清除/);
 await h.page.shareExport();assert.equal(h.shares(),0);h.allowCleanup();h.page.clearExport();assert.equal(h.files.size,0);assert.equal(h.page.data.error,'');
});
test('sharing refuses expired identity and a file replaced during confirmation',async()=>{
 const h=setup();h.store['fitcrew.session'].created_at=1;
 await h.page.shareExport();assert.equal(h.shares(),0);
 const fresh=setup();let dialog;wx.showModal=o=>dialog=o;
 const sharing=fresh.page.shareExport();fresh.page.setData({exportPath:''});dialog.success({confirm:true});await sharing;
 assert.equal(fresh.shares(),0);
 fresh.page.setData({exportPath:'/synthetic/fitcrew-private-export.json'});
 const oldConfirmation=fresh.page.shareExport(),oldDialog=dialog;
 fresh.allowCleanup();wx.showModal=o=>o.success({confirm:true});await fresh.page.exportData();
 oldDialog.success({confirm:true});await oldConfirmation;assert.equal(fresh.shares(),0);
 fresh.page.setData({exportPath:'/synthetic/fitcrew-private-export.json',busy:true});
 await fresh.page.shareExport();assert.equal(fresh.shares(),0);
});
