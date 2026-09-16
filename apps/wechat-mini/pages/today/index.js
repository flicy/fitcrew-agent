const {base}=require('../../lib/page');
const lifecycle=require('../../lib/session');
Page(base({data:{showHealthReadiness:false,choosing:false,missionSnapshot:null,alternatives:[{id:'brief_check',title:'只记录此刻的感受'},{id:'quiet_minute',title:'留一分钟安静休息'}]},
 toggleHealthReadiness(){this.syncBoundary();this.setData({showHealthReadiness:!this.data.showHealthReadiness});},
 async mission(e){this.syncBoundary();if(this.data.busy)return;const action=e.currentTarget.dataset.action;if(action==='lighten'){const mission=this.data.state&&this.data.state.mission;this.setData({choosing:true,missionSnapshot:mission?{mission_id:mission.id,revision:mission.revision}:null});return;}await this.write('mission','/v3/mission',{action,...(this.data.state&&this.data.state.mission?{mission_id:this.data.state.mission.id,revision:this.data.state.mission.revision}:{})});},
 cancelLighten(){if(!this.data.busy)this.setData({choosing:false});},
 async chooseLighten(e){this.syncBoundary();if(!this.data.choosing||this.data.busy)return;const epoch=lifecycle.epoch(wx);if(await this.write('mission','/v3/mission',{action:'lighten',alternative:e.currentTarget.dataset.id,...this.data.missionSnapshot})&&lifecycle.current(wx,epoch))this.setData({choosing:false});}
}));
