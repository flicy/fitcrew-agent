const {base,confirm}=require('../../lib/page');
const lifecycle=require('../../lib/session');
const {validBase}=require('../../lib/client');
const config=require('../../config');
Page(base({
 data:{signedIn:false,caps:null,receipt:'',exportPath:''},
 async onShow(){this.setData({signedIn:!!wx.getStorageSync('fitcrew.session')});await this.refresh();if(this.data.signedIn)await this.capabilities();},
 async capabilities(){const epoch=lifecycle.epoch(wx);try{const caps=await getApp().api.request('/v3/capabilities');if(lifecycle.current(wx,epoch))this.setData({caps});}catch(e){if(lifecycle.current(wx,epoch))this.setData({caps:null,error:e.message});}},
 openPrivacy(){if(wx.openPrivacyContract)wx.openPrivacyContract({fail:()=>this.setData({error:'平台隐私保护指引尚未配置，请由运营者在小程序后台补全后再登录。'})});},
 async login(){
  this.syncBoundary();let epoch=lifecycle.epoch(wx);if(this.data.busy)return;
  if(!await confirm('FitCrew 隐私说明 · 2026-09-07','登录将使用微信临时凭证创建私有账户。你主动提交的目标、身体感受与实验记录用于个人生活方式观察，支持导出、删除及注销；不向群聊公开。AI 使用需另行同意。请先阅读平台隐私保护指引。'))return;
  if(!lifecycle.current(wx,epoch))return;this.setData({busy:true,error:''});
  try{
   if(!validBase(config.baseURL))throw new Error('服务地址尚未配置，暂时无法登录。');
   if(!wx.requirePrivacyAuthorize)throw new Error('请升级微信后使用隐私授权。');
   await new Promise((resolve,reject)=>wx.requirePrivacyAuthorize({success:resolve,fail:()=>reject(new Error('未完成微信隐私授权。'))}));
   if(!lifecycle.current(wx,epoch))return;
   const code=await new Promise((resolve,reject)=>wx.login({success:r=>r.code?resolve(r.code):reject(new Error('微信未返回登录凭证')),fail:()=>reject(new Error('微信登录失败，请重试'))}));
   if(!lifecycle.current(wx,epoch))return;
   const session=await getApp().api.request('/v3/auth/wechat','POST',{code,privacy_version:'2026-09-07'},true);
   if(!lifecycle.current(wx,epoch))return;
   if(!session.device_token||!session.device_binding_id)throw new Error('登录响应缺少设备凭据。');
   // Never forward the bearer to a server-selected different origin.
   if(session.base_url&&session.base_url.replace(/\/$/,'')!==config.baseURL.replace(/\/$/,''))throw new Error('登录返回的服务地址与已配置地址不一致，请联系运营者。');
   lifecycle.install(wx,{device_token:session.device_token,device_binding_id:session.device_binding_id,consent_ids:session.consent_ids});epoch=lifecycle.epoch(wx);
   this.setData({signedIn:true});await this.refresh();await this.capabilities();
  }catch(e){if(lifecycle.current(wx,epoch))this.setData({error:e.message});}finally{if(lifecycle.current(wx,epoch))this.setData({busy:false});}
 },
 async ai(){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);const caps=this.data.caps;if(!caps||this.data.busy)return;
  const granted=!caps.ai_consent_granted;
  if(granted&&!await confirm('单独同意 AI 使用','服务商：'+caps.ai_provider+'\n'+caps.ai_notice+'\n版本：'+caps.ai_notice_version))return;
  if(!lifecycle.current(wx,epoch))return;this.setData({busy:true,error:''});
  try{const result=await getApp().api.request('/v3/ai-consent','POST',{granted,provider_notice_version:caps.ai_notice_version});if(lifecycle.current(wx,epoch))this.setData({caps:result});}catch(e){if(lifecycle.current(wx,epoch))this.setData({error:e.message});}finally{if(lifecycle.current(wx,epoch))this.setData({busy:false});}
 },
 async exportData(){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);
  if(this.data.busy||!await confirm('导出私有数据？','将把账户记录和健康数据写入本机小程序沙箱。文件包含敏感信息，请妥善保管；不会自动发送给他人。'))return;
  if(!lifecycle.current(wx,epoch))return;this.setData({busy:true,error:''});
  try{
   const data=await getApp().api.request('/v3/export'),filePath=wx.env.USER_DATA_PATH+'/fitcrew-private-export.json';
   if(!lifecycle.current(wx,epoch))return;
   wx.getFileSystemManager().writeFileSync(filePath,JSON.stringify(data,null,2),'utf8');
   this.setData({exportPath:filePath});
  }catch(e){if(lifecycle.current(wx,epoch))this.setData({error:e.message});}finally{if(lifecycle.current(wx,epoch))this.setData({busy:false});}
 },
 async shareExport(){
  const epoch=lifecycle.epoch(wx);
  if(!this.data.exportPath||!await confirm('选择导出接收位置','即将打开微信文件发送界面。文件包含你的私有健康数据，仅选择你信任的接收方。'))return;
  if(!lifecycle.current(wx,epoch))return;
  if(wx.shareFileMessage)wx.shareFileMessage({filePath:this.data.exportPath,fileName:'FitCrew-private-export.json',fail:()=>this.setData({error:'文件未发送，可重试或清除导出。'})});
  else this.setData({error:'当前微信不支持发送文件，请升级微信；文件仍保留在本机沙箱。'});
 },
 clearExport(){try{lifecycle.cleanExport(wx);this.setData({exportPath:''});}catch(e){this.setData({error:'本机导出文件未确认清除，请重试。'});}},
 async erase(e){
  this.syncBoundary();let epoch=lifecycle.epoch(wx);
  const account=e.currentTarget.dataset.kind==='account';
  if(this.data.busy||!await confirm(account?'永久注销账户？':'永久删除私有数据？',account?'删除全部私有记录、健康数据和账户，并撤销登录凭据。无法撤销。':'删除旅程、实验、身体记录及健康数据；账户保留。无法撤销。'))return;
  if(!lifecycle.current(wx,epoch))return;this.setData({busy:true,error:''});
  try{
   const result=await getApp().api.request(account?'/v3/account':'/v3/data','DELETE',{confirmation:'DELETE'});
   if(!lifecycle.current(wx,epoch))return;
   if(!result.deleted||!result.receipt_id)throw new Error('服务未确认删除完成。');
   const cleanupError=lifecycle.boundary(wx,!account);epoch=lifecycle.epoch(wx);
   this.setData({receipt:result.receipt_id,state:null,logs:[],experiments:[],signedIn:!account,caps:null});
   if(!account){await this.refresh();await this.capabilities();}
   if(cleanupError)this.setData({error:cleanupError});
  }catch(e){if(lifecycle.current(wx,epoch))this.setData({error:e.message});}finally{if(lifecycle.current(wx,epoch))this.setData({busy:false});}
 }
}));
