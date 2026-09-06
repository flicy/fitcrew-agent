const {mutation,finish}=require('./client');
const session=require('./session');
const labels={proposed:'待确认',running:'观察中',paused:'已暂停',stopped:'已停止',completed:'已完成'};
function confirm(title,content){return new Promise(resolve=>wx.showModal({title,content,confirmText:'确认',success:r=>resolve(r.confirm),fail:()=>resolve(false)}));}
function base(extra={}) {
 const initial={loading:false,busy:false,error:'',state:null,experiments:[],logs:[],receipt:'',...extra.data};
 return {
  resetPrivate(){this.setData({...JSON.parse(JSON.stringify(initial)),signedIn:!!wx.getStorageSync('fitcrew.session')});this._epoch=session.epoch(wx);},
  syncBoundary(){session.watch(wx,this);session.active(wx);if(this._epoch!==session.epoch(wx))this.resetPrivate();},
  onUnload(){session.unwatch(wx,this);},
  async refresh(){
   this.syncBoundary();const epoch=session.epoch(wx);this.setData({loading:true,error:''});
   try{const state=await getApp().api.request('/v3/state');if(!session.current(wx,epoch))return;this.setData({state,logs:[...state.logs].reverse(),experiments:state.experiments.map(x=>({...x,statusLabel:labels[x.status]||x.status,sourceLabel:x.source==='ai_selected'?'AI 选择 · 受约束行动':x.source==='rule_based'?'规则建议':'来源待确认',resultText:x.result?x.result.summary:''}))});}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message,state:null,logs:[],experiments:[]});}
   finally{if(session.current(wx,epoch))this.setData({loading:false});}
  },
  async write(key,path,body,method='POST'){
   this.syncBoundary();const epoch=session.epoch(wx);if(this.data.busy)return false;this.setData({busy:true,error:''});
   try{await getApp().api.request(path,method,mutation(wx,key,body));if(!session.current(wx,epoch))return false;finish(wx,key);await this.refresh();return session.current(wx,epoch);}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message});return false;}finally{if(session.current(wx,epoch))this.setData({busy:false});}
  },
  openJourney(){wx.switchTab({url:'/pages/journey/index'});},
  openLog(){wx.switchTab({url:'/pages/log/index'});},
  openExperiments(){wx.switchTab({url:'/pages/experiments/index'});},
  openProfile(){wx.switchTab({url:'/pages/profile/index'});},
  ...extra,data:JSON.parse(JSON.stringify(initial)),
  onLoad(){this.syncBoundary();if(extra.onLoad)extra.onLoad.call(this);},
  async onShow(){this.syncBoundary();if(extra.onShow)await extra.onShow.call(this);else await this.refresh();}
 };
}
module.exports={base,confirm};
