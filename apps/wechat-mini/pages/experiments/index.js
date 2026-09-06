const lifecycle=require('../../lib/session');
const {base,confirm}=require('../../lib/page');
Page(base({
 async propose(){await this.write('propose','/v3/experiments/propose',{});},
 async transition(e){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);
  const item=this.data.experiments.find(x=>x.id===e.currentTarget.dataset.id),action=e.currentTarget.dataset.action;if(!item)return;
  if(action==='accept'){
   const scope=[item.hypothesis,'行动：'+item.intervention,'观察 '+item.duration_days+' 天','指标：'+item.metrics.join('、'),'判断标准：'+item.success_criteria.join('；'),'停止条件：'+item.stop_conditions.join('；'),'使用数据：'+item.data_categories.join('、'),'自愿参加，可暂停或停止。结果只描述相关变化，不证明因果。'].join('\n');
   if(!await confirm('确认实验范围与数据使用',scope))return;
  }
  if(action==='stop'&&!await confirm('停止这次实验？','保留已有记录和实验历史，不再继续观察。'))return;
  if(!lifecycle.current(wx,epoch))return;
  await this.write('transition.'+item.id,'/v3/experiments/'+item.id+'/transition',{action,revision:item.revision});
 }
}));
