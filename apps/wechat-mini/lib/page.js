const {mutation,finish}=require('./client');
const session=require('./session');
const labels={proposed:'待确认',running:'观察中',paused:'已暂停',stopped:'已停止',completed:'已完成'};
function confirm(title,content){return new Promise(resolve=>wx.showModal({title,content,confirmText:'确认',success:r=>resolve(r.confirm),fail:()=>resolve(false)}));}
function base(extra={}) {
 const initial={loading:false,busy:false,error:'',state:null,experiments:[],logs:[],trendPoints:[],trendDays:30,selectedTrend:null,observedDays:0,receipt:'',...extra.data};
 return {
  resetPrivate(){this.setData({...JSON.parse(JSON.stringify(initial)),signedIn:!!wx.getStorageSync('fitcrew.session')});this._epoch=session.epoch(wx);},
  syncBoundary(){session.watch(wx,this);session.active(wx);if(this._epoch!==session.epoch(wx))this.resetPrivate();},
  onUnload(){session.unwatch(wx,this);},
  async refresh(){
   this.syncBoundary();const epoch=session.epoch(wx);this.setData({loading:true,error:''});
   try{const state=await getApp().api.request('/v3/state');if(!session.current(wx,epoch))return;this.setData({state,logs:[...state.logs].reverse(),experiments:state.experiments.map(x=>({...x,statusLabel:labels[x.status]||x.status,sourceLabel:x.source==='ai_selected'?'AI 选择 · 受约束行动':x.source==='rule_based'?'规则建议':'来源待确认',resultText:x.result?x.result.summary:''}))});this.updateTrends();}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message,state:null,logs:[],experiments:[],trendPoints:[],selectedTrend:null,observedDays:0});}
   finally{if(session.current(wx,epoch))this.setData({loading:false});}
  },
  async write(key,path,body,method='POST'){
   this.syncBoundary();const epoch=session.epoch(wx);if(this.data.busy)return false;this.setData({busy:true,error:''});
   try{await getApp().api.request(path,method,mutation(wx,key,body));if(!session.current(wx,epoch))return false;finish(wx,key);await this.refresh();return session.current(wx,epoch);}
   catch(e){if(session.current(wx,epoch))this.setData({error:e.message});return false;}finally{if(session.current(wx,epoch))this.setData({busy:false});}
  },
  updateTrends(){const points=this.data.state&&this.data.state.trends?this.data.state.trends.points.slice(-this.data.trendDays):[];this.setData({selectedTrend:null,trendPoints:points.map(p=>({...p,barHeight:p.energy===null?0:p.energy*20})),observedDays:points.filter(p=>p.count>0).length});},
  openTrendPoint(e){this.syncBoundary();const point=this.data.trendPoints.find(p=>p.date===e.currentTarget.dataset.date);if(point)this.setData({selectedTrend:point});},
  closeTrendPoint(){this.setData({selectedTrend:null});},
  selectTrend(e){this.setData({trendDays:Number(e.currentTarget.dataset.days)});this.updateTrends();},
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
