const {mutation,finish}=require('./client');
const session=require('./session');
const {textScale}=require('./presentation');
const labels={proposed:'待确认',running:'观察中',paused:'已暂停',stopped:'已停止',completed:'已完成'};
function confirm(title,content){return new Promise(resolve=>wx.showModal({title,content,confirmText:'确认',success:r=>resolve(r.confirm),fail:()=>resolve(false)}));}
function base(extra={}) {
 const initial={textScale:1,notice:'',loading:false,busy:false,error:'',state:null,experiments:[],logs:[],trendPoints:[],trendDays:30,selectedTrend:null,observedDays:0,receipt:'',...extra.data};
 return {
  resetPrivate(){this.setData({...JSON.parse(JSON.stringify(initial)),signedIn:!!wx.getStorageSync('fitcrew.session')});this._epoch=session.epoch(wx);},
  syncBoundary(){session.watch(wx,this);session.active(wx);if(this._epoch!==session.epoch(wx))this.resetPrivate();},
  onUnload(){session.unwatch(wx,this);},
  async refresh(){
   this.syncBoundary();const epoch=session.epoch(wx);this.setData({loading:true,error:'',notice:''});
   try{const state=await getApp().api.request('/v3/state');if(!session.current(wx,epoch))return;this.setData({state,logs:[...state.logs].reverse(),experiments:state.experiments.map(x=>({...x,statusLabel:labels[x.status]||x.status,sourceLabel:x.source==='ai_selected'?'AI 选择 · 受约束行动':x.source==='rule_based'?'规则建议':'来源待确认',resultText:x.result?x.result.summary:''}))});this.updateTrends();}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message,state:null,logs:[],experiments:[],trendPoints:[],selectedTrend:null,observedDays:0});}
   finally{if(session.current(wx,epoch))this.setData({loading:false});}
  },
  async write(key,path,body,method='POST'){
   this.syncBoundary();const epoch=session.epoch(wx);if(this.data.busy)return false;this.setData({busy:true,error:'',notice:''});
   try{const result=await getApp().api.request(path,method,mutation(wx,key,body));if(!session.current(wx,epoch))return false;if(method==='DELETE'){if(!result.deleted||!result.receipt_id)throw new Error('服务器未确认删除，请重试');this.setData({receipt:result.receipt_id});}finish(wx,key);await this.refresh();if(session.current(wx,epoch))this.setData({notice:method==='DELETE'?'已删除，服务回执见下方。':this.data.error?'已保存，最新内容暂未读到，请重新读取。':'已保存。'});return session.current(wx,epoch);}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message});return false;}finally{if(session.current(wx,epoch))this.setData({busy:false});}
  },
  updateTrends(){const points=this.data.state&&this.data.state.trends?this.data.state.trends.points.slice(-this.data.trendDays):[];this.setData({selectedTrend:null,trendPoints:points.map(p=>({...p,barHeight:p.energy===null?0:p.energy*20})),observedDays:points.filter(p=>p.count>0).length});},
  openTrendPoint(e){this.syncBoundary();const point=this.data.trendPoints.find(p=>p.date===e.currentTarget.dataset.date);if(point)this.setData({selectedTrend:point});},
  preventTouchMove(){},
  closeTrendPoint(){this.setData({selectedTrend:null});},
  selectTrend(e){this.setData({trendDays:Number(e.currentTarget.dataset.days)});this.updateTrends();},
  async advanceOnboarding(e){const progress=this.data.state&&this.data.state.onboarding;if(!progress)return;const route=e.currentTarget.dataset.route;await this.write('onboarding','/v3/onboarding',{step:progress.step,...(route?{route}:{})});},
  openNextCheck(){const next=this.data.state&&this.data.state.next_check;if(!next)return;if(next.action==='log')this.openLog();else if(next.action==='journey')this.openJourney();else this.openExperiments();},
  openJourney(){wx.switchTab({url:'/pages/journey/index'});},
  openLog(){wx.switchTab({url:'/pages/log/index'});},
  openExperiments(){wx.switchTab({url:'/pages/experiments/index'});},
  openProfile(){wx.switchTab({url:'/pages/profile/index'});},
  ...extra,data:JSON.parse(JSON.stringify(initial)),
  onLoad(){this.syncBoundary();if(extra.onLoad)extra.onLoad.call(this);},
  async onShow(){this.syncBoundary();this.setData({textScale:textScale(wx)});if(extra.onShow)await extra.onShow.call(this);else await this.refresh();}
 };
}
module.exports={base,confirm};
