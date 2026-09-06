const lifecycle=require('./session');
function uuid() {
 return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const n=Math.floor(Math.random()*16);return (c==='x'?n:(n&3)|8).toString(16);});
}
function validBase(value) {
 return typeof value==='string' && /^https:\/\/[a-z0-9.-]+(?::443)?(?:\/[a-z0-9_/-]*)?$/i.test(value) && !/example|localhost|127\.0\.0\.1/i.test(value);
}
function makeClient(wx,baseURL) {
 function request(path,method='GET',data,anonymous=false) {
  if(!validBase(baseURL))return Promise.reject(new Error('服务尚未配置：需要已备案并加入微信合法域名的 HTTPS API。'));
  const session=lifecycle.active(wx),token=session&&session.device_token,epoch=lifecycle.epoch(wx);
  if(!anonymous&&!token)return Promise.reject(new Error('请到「我的」阅读隐私说明并登录。'));
  return new Promise((resolve,reject)=>wx.request({
   url:baseURL.replace(/\/$/,'')+path,method,data,timeout:20000,
   header:{'Content-Type':'application/json',...(token&&!anonymous?{Authorization:'Bearer '+token}:{})},
   success:res=>{if(!lifecycle.current(wx,epoch)){reject(new Error('账户已变化，请重新操作。'));return;}if(res.statusCode===401&&!anonymous){lifecycle.boundary(wx);reject(new Error('登录已过期，请重新登录。'));return;}if(res.statusCode>=200&&res.statusCode<300)resolve(res.data);else{const detail=res.data&&res.data.detail;reject(new Error((typeof detail==='string'?detail:JSON.stringify(detail||'服务请求失败'))+'（'+res.statusCode+'）'));}},
   fail:()=>reject(new Error('网络请求未确认，请检查网络后重试；同一操作将使用原请求编号。'))
  }));
 }
 return {request};
}
function mutation(wx,key,body) {
 const storage='fitcrew.pending.'+key,fingerprint=JSON.stringify(body),old=wx.getStorageSync(storage);
 if(old&&old.fingerprint===fingerprint)return old.body;
 const value={...body,request_id:uuid()};wx.setStorageSync(storage,{fingerprint,body:value});return value;
}
function finish(wx,key){wx.removeStorageSync('fitcrew.pending.'+key);}
function clearPrivate(wx){return lifecycle.boundary(wx);}
module.exports={makeClient,mutation,finish,clearPrivate,validBase,uuid};
