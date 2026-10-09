const lifecycle=require('./session');
function uuid() {
 return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const n=Math.floor(Math.random()*16);return (c==='x'?n:(n&3)|8).toString(16);});
}
function validBase(value) {
 return typeof value==='string' && /^https:\/\/[a-z0-9.-]+(?::443)?(?:\/[a-z0-9_/-]*)?$/i.test(value) && !/example|localhost|127\.0\.0\.1/i.test(value);
}
function validCloud(value) {
 return !!value && typeof value==='object' &&
  typeof value.env==='string' && /^[a-z0-9][a-z0-9-]{1,62}$/i.test(value.env) &&
  typeof value.service==='string' && /^[a-z0-9][a-z0-9-]{1,62}$/i.test(value.service);
}
function validTransport(value) {
 const config=typeof value==='string'?{baseURL:value}:value||{};
 if(config.cloud)return validCloud(config.cloud) &&
  (config.baseURL==='' || config.baseURL===undefined || validBase(config.baseURL));
 return validBase(config.baseURL);
}
function makeClient(wx,value) {
 const config=typeof value==='string'?{baseURL:value}:value||{};
 function request(path,method='GET',data,anonymous=false) {
  if(!validTransport(config))return Promise.reject(new Error('服务尚未配置：需要可用的 HTTPS 服务地址；云托管还需环境 ID 和服务名。'));
  const session=lifecycle.active(wx),token=session&&session.device_token,epoch=lifecycle.epoch(wx);
  if(!anonymous&&!token)return Promise.reject(new Error('请到「我的」阅读隐私说明并登录。'));
  const header={'Content-Type':'application/json',...(token&&!anonymous?{Authorization:'Bearer '+token}:{})};
  const success=res=>{
   if(!lifecycle.current(wx,epoch))throw new Error('账户已变化，请重新操作。');
   if(res.statusCode===401&&!anonymous){lifecycle.boundary(wx);throw new Error('登录已过期，请重新登录。');}
   if(res.statusCode>=200&&res.statusCode<300)return res.data;
   const detail=res.data&&res.data.detail;
   const error=new Error((typeof detail==='string'?detail:JSON.stringify(detail||'服务请求失败'))+'（'+res.statusCode+'）');
   error.statusCode=res.statusCode;throw error;
  };
  const fail=()=>{throw new Error('网络请求未确认，请检查网络后重试；同一操作将使用原请求编号。');};
  if(config.cloud){
   if(!wx.cloud||typeof wx.cloud.callContainer!=='function')return Promise.reject(new Error('当前微信不支持云托管访问，请升级微信。'));
   return wx.cloud.callContainer({config:{env:config.cloud.env},path,method,data,header:{...header,'X-WX-SERVICE':config.cloud.service},timeout:20000}).then(success,fail);
  }
  return new Promise((resolve,reject)=>wx.request({
   url:config.baseURL.replace(/\/$/,'')+path,method,data,timeout:20000,header,
   success:res=>{try{resolve(success(res));}catch(error){reject(error);}},
   fail:()=>{try{fail();}catch(error){reject(error);}}
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
module.exports={makeClient,mutation,finish,clearPrivate,validBase,validCloud,validTransport,uuid};
