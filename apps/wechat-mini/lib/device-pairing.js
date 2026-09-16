const {mutation,finish}=require('./client');
const lifecycle=require('./session');
const {confirm}=require('./page');
module.exports={
 async loadPairedDevices(){
  const epoch=lifecycle.epoch(wx),revision=(this._devicesRevision||0)+1;this._devicesRevision=revision;
  try{const result=await getApp().api.request('/v3/device-pairing/devices');if(lifecycle.current(wx,epoch)&&revision===this._devicesRevision)this.setData({pairedDevices:result.devices||[]});}
  catch(e){if(lifecycle.current(wx,epoch)&&revision===this._devicesRevision)this.setData({pairedDevices:[],error:e.message});}
 },
 async disconnectDevice(e){
  this.syncBoundary();const epoch=lifecycle.epoch(wx),id=e.currentTarget.dataset.id;
  if(this.data.busy||this.data.pairingBusy||!await confirm('断开这台 iPhone？','停止这台设备之后的账号访问与上传，保留已上传的记录。设备可能保留已查看的本机内容；重新连接需生成新链接。'))return;
  if(!lifecycle.current(wx,epoch)||this.data.busy||this.data.pairingBusy)return;
  const revision=(this._pairingRevision||0)+1;this._pairingRevision=revision;const current=()=>lifecycle.current(wx,epoch)&&revision===this._pairingRevision;this._devicesRevision=(this._devicesRevision||0)+1;this.setData({pairingBusy:true,error:''});
  try{const result=await getApp().api.request('/v3/device-pairing/devices/'+id,'DELETE');if(!current())return;if(result.disconnected!==true||result.device_id!==id)throw new Error('未确认断开，请重试。');this.setData({pairedDevices:this.data.pairedDevices.filter(d=>d.id!==id),notice:'设备已断开，云端记录保留。'});}
  catch(e){if(current())this.setData({error:e.message});}finally{if(current())this.setData({pairingBusy:false});}
 },
 clearPairingView(){this._pairingRevision=(this._pairingRevision||0)+1;this.setData({pairingURL:'',pairingExpires:'',pairingBusy:false});},
 async createPairing(){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);
  if(this.data.busy||this.data.pairingBusy||!this.data.signedIn)return;
  if(!await confirm('连接自己的 iPhone','连接将让 FitCrew iOS 访问当前账号的私人记录。链接 15 分钟有效、只能使用一次，请勿发送给他人。健康上传仍需在 iOS 单独选择并授权。已有 Apple 登录账号的数据不会自动合并。'))return;
  if(!lifecycle.current(wx,epoch)||this.data.busy||this.data.pairingBusy)return;
  const revision=(this._pairingRevision||0)+1;this._pairingRevision=revision;
  const current=()=>lifecycle.current(wx,epoch)&&this._pairingRevision===revision;
  this.setData({pairingBusy:true,pairingURL:'',pairingExpires:'',error:''});
  try{
   const result=await getApp().api.request('/v3/device-pairing','POST',mutation(wx,'device-pairing',{privacy_version:'2026-09-07'}));
   if(!current())return;
   finish(wx,'device-pairing');
   if(typeof result.pairing_url!=='string'||!result.pairing_url.startsWith('fitcrew-health://configure?payload=')||!(Date.parse(result.expires_at)>Date.now()))throw new Error('连接响应无效，请重新生成。');
   this.setData({pairingURL:result.pairing_url,pairingExpires:result.expires_at});
  }catch(e){if(current()){if(e.statusCode===409)finish(wx,'device-pairing');this.setData({error:e.statusCode===409?'连接已过期、撤销或用过，请重新生成。':e.message});}}finally{if(current())this.setData({pairingBusy:false});}
 },
 copyPairing(){
  this.syncBoundary();const epoch=lifecycle.epoch(wx),revision=this._pairingRevision,url=this.data.pairingURL;
  if(this.data.busy||this.data.pairingBusy||!url)return;
  if(!(Date.parse(this.data.pairingExpires)>Date.now())){this.clearPairingView();this.setData({error:'连接已过期，请重新生成。'});return;}
  wx.setClipboardData({data:url,success:()=>{if(lifecycle.current(wx,epoch)&&revision===this._pairingRevision)this.setData({notice:'已复制。打开 FitCrew iOS，在「我的」粘贴并确认连接；使用后请清除剪贴板中的链接。'});},fail:()=>{if(lifecycle.current(wx,epoch)&&revision===this._pairingRevision)this.setData({error:'未能复制，请重试。'});}});
 },
 async cancelPairing(){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);if(this.data.busy||this.data.pairingBusy||!this.data.signedIn)return;
  this.clearPairingView();const revision=this._pairingRevision,current=()=>lifecycle.current(wx,epoch)&&revision===this._pairingRevision;
  this.setData({pairingBusy:true,error:''});
  try{const result=await getApp().api.request('/v3/device-pairing','DELETE');if(!current())return;if(result.cancelled!==true)throw new Error('未确认撤销，请重试。');finish(wx,'device-pairing');this.setData({notice:'未使用的连接已撤销；已连接设备不受影响。'});}
  catch(e){if(current())this.setData({error:e.message});}finally{if(current())this.setData({pairingBusy:false});}
 }
};
