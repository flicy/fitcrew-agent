const {base}=require('../../lib/page');
const lifecycle=require('../../lib/session');
Page(base({data:{choosing:false,alternatives:[{id:'brief_check',title:'只记录此刻的感受'},{id:'quiet_minute',title:'留一分钟安静休息'}]},
 async mission(e){this.syncBoundary();if(this.data.busy)return;const action=e.currentTarget.dataset.action;if(action==='lighten'){this.setData({choosing:true});return;}await this.write('mission','/v3/mission',{action});},
 cancelLighten(){if(!this.data.busy)this.setData({choosing:false});},
 async chooseLighten(e){this.syncBoundary();if(!this.data.choosing||this.data.busy)return;const epoch=lifecycle.epoch(wx);if(await this.write('mission','/v3/mission',{action:'lighten',alternative:e.currentTarget.dataset.id})&&lifecycle.current(wx,epoch))this.setData({choosing:false});}
}));
