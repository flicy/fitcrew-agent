const lifecycle=require('../../lib/session');
const {base,confirm}=require('../../lib/page');
Page(base({
 data:{expandedExperiment:''},
 toggleDetails(e){this.syncBoundary();const id=e.currentTarget.dataset.id;this.setData({expandedExperiment:this.data.expandedExperiment===id?'':id});},
 async feedback(e){
  this.syncBoundary();if(this.data.busy)return;const epoch=lifecycle.epoch(wx);
  const item=this.data.experiments.find(x=>x.id===e.currentTarget.dataset.id),assessment=e.currentTarget.dataset.assessment;if(!item)return;
  const choice=await new Promise(resolve=>wx.showActionSheet({itemList:assessment==='uncertain'?['仅保存反馈']:['仅保存反馈','保存并确认为记忆'],success:r=>resolve(r.tapIndex),fail:()=>resolve(-1)}));
  if(choice<0||!lifecycle.current(wx,epoch))return;
  if(choice===1&&!await confirm('确认这条主观记忆？','保存到私人账号，可在我的页面撤回；不是疗效结论，不会自动发送给 AI。'))return;
  if(!lifecycle.current(wx,epoch))return;
  await this.write('feedback.'+item.id,'/v3/experiments/'+item.id+'/feedback',{revision:item.revision,assessment,confirm_memory:choice===1});
 },
 async propose(){await this.write('propose','/v3/experiments/propose',{});},
 async transition(e){
  this.syncBoundary();const epoch=lifecycle.epoch(wx);
  const item=this.data.experiments.find(x=>x.id===e.currentTarget.dataset.id),action=e.currentTarget.dataset.action;if(!item)return;
  if(action==='accept'){
   const scope=[item.purpose||'开始前七天为基线，开始后七天为观察期，两窗各至少四个记录日才比较均值；不判断疗效。',item.hypothesis,'行动：'+item.intervention,'观察 '+item.duration_days+' 天','指标：'+item.metrics.join('、'),'判断标准：'+item.success_criteria.join('；'),'停止条件：'+item.stop_conditions.join('；'),'使用数据：'+item.data_categories.join('、'),'自愿参加，可暂停或停止。结果只描述相关变化，不证明因果。'].join('\n');
   if(!await confirm('确认实验范围与数据使用',scope))return;
  }
  if(action==='stop'&&!await confirm('停止这次实验？','保留已有记录和实验历史，不再继续观察。'))return;
  if(!lifecycle.current(wx,epoch))return;
  await this.write('transition.'+item.id,'/v3/experiments/'+item.id+'/transition',{action,revision:item.revision});
 }
}));
