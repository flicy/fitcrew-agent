const states=new WeakMap();
function state(wx){if(!states.has(wx))states.set(wx,{epoch:0,pages:new Set()});return states.get(wx);}
function epoch(wx){return state(wx).epoch;}
function current(wx,value){return epoch(wx)===value;}
function watch(wx,page){state(wx).pages.add(page);}
function unwatch(wx,page){state(wx).pages.delete(page);}
function exportPath(wx){return wx.env.USER_DATA_PATH+'/fitcrew-private-export.json';}
function cleanExport(wx){
 if(!wx.getFileSystemManager||!wx.env)return;
 const fs=wx.getFileSystemManager(),path=exportPath(wx);
 const names=fs.readdirSync(wx.env.USER_DATA_PATH);
 if(names.includes("fitcrew-private-export.json"))fs.unlinkSync(path);
}
function boundary(wx,keepSession=false){
 const session=keepSession?wx.getStorageSync('fitcrew.session'):null;
 state(wx).epoch++;
 wx.getStorageInfoSync().keys.filter(k=>k.startsWith('fitcrew.')).forEach(k=>wx.removeStorageSync(k));
 if(session)wx.setStorageSync('fitcrew.session',session);
 let cleanupError='';
 try{cleanExport(wx);}catch(e){cleanupError='本机导出未能清除，请在「我的」重试清除。';}
 for(const page of state(wx).pages){page.resetPrivate();if(cleanupError)page.setData({error:cleanupError});}
 return cleanupError;
}
function active(wx){
 const session=wx.getStorageSync('fitcrew.session');
 if(session&&(!session.created_at||Date.now()-session.created_at>=30*24*60*60*1000)){boundary(wx);return null;}
 return session||null;
}
function install(wx,session){const error=boundary(wx);if(error)throw new Error(error);wx.setStorageSync('fitcrew.session',{...session,created_at:Date.now()});for(const page of state(wx).pages)page.resetPrivate();}
module.exports={epoch,current,watch,unwatch,boundary,active,install,exportPath,cleanExport};
