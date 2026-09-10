// Entirely synthetic, developer-only fixtures. Not bundled in the mini program.
function makeFixture(scenario, step) {
  const points=Array.from({length:90},(_,i)=>{const date=new Date(Date.UTC(2026,5,11+i)).toISOString().slice(0,10),count=i>70&&i%3?1:0;return {date,count,energy:count?2+i%4:null,stress:count?2:null,events:i===82?['开始了合成观察实验']:[]};});
  const logs=[{id:'synthetic-log',created_at:'2026-09-08T08:30:00+08:00',feeling:'正常',energy:3,stress:2,note:'合成测试记录，不含真实健康数据。',sleep_feeling:'一般',training_feeling:'完成',stress_source:'工作'}];
  const common={source:'rule_based',purpose:'用于本人的生活方式观察。开始前七天为基线、开始后七天为观察期；两窗各至少四个记录日才比较。',hypothesis:'留一点放松时间，是否更适合自己的日常节奏？',intervention:'睡前留一分钟安静休息。',duration_days:7,metrics:['手动记录的精力与压力'],success_criteria:['比较两窗的记录均值，描述观察到的变化'],stop_conditions:['感觉不适或不愿继续时停止'],data_categories:['手动身体记录的结构化感受'],revision:1};
  const experiments=[{...common,id:'synthetic-running',title:'睡前留一点放松时间',status:'running',baseline_start:'2026-08-25',accepted_at:'2026-09-01T08:00:00+08:00',ends_at:'2026-09-08T08:00:00+08:00'}, {...common,id:'synthetic-completed',title:'留意自己的放松节奏',status:'completed',result:{status:scenario==='invalidated'?'invalidated':'insufficient_data',summary:scenario==='invalidated'?'来源记录已删除，本次结果已失效。':'记录天数不足，暂不能比较两个时间窗。请以自己的感受为准。'}}];
  const state={onboarding:{step:scenario==='onboarding'?Number(step):7},journey:{title:'睡得更好',days:90,start_date:'2026-08-25'},journey_progress:{title:'建立记录',day:15,total_days:90,window_end:'2026-09-08',observed_days:8,missing_days:7,notice:'阶段仅按日历时间划分，不代表健康改善。'},health:{sample_count:0,last_sync_at:null},today_context:{title:'从已有感受，慢慢了解自己',detail:'目前只有手动记录，尚无可用的 Apple 健康数据。',source:'手动身体记录',window_start:'2026-09-02',window_end:'2026-09-08'},mission:{id:'synthetic-mission',title:'留一分钟，安静休息',why:'从轻量行动开始，继续留意精力与压力的变化。',status:'proposed',revision:1},next_check:{title:'下一次身体记录后再看看',detail:'记下此刻感受，为这段观察留下一条线索。',action:'log'},logs,experiments,trends:{points,window_end:'2026-09-08'},confirmed_memories:[{id:'synthetic-memory',text:'我主观觉得这次行动适合自己。',experiment_title:'合成观察案例',confirmed_at:'2026-09-08T09:00:00+08:00'}],milestones:[{id:'synthetic-milestone',date:'2026-09-08',status:'available',title:'一次观察已结束',action:'睡前留一分钟安静休息',evidence:'这是合成预览的观察过程记录，不代表健康改善。'}]};
  if(scenario==='empty'){state.journey=null;state.journey_progress=null;state.mission=null;state.logs=[];state.experiments=[];state.confirmed_memories=[];state.milestones=[];state.trends.points=points.map(p=>({...p,count:0,energy:null,stress:null,events:[]}));state.today_context.title='从第一条感受开始';state.next_check={title:'选一个你在意的方向',detail:'先设定旅程，再慢慢记录。',action:'journey'};}
  if(['health','connected'].includes(scenario)){
    state.health_trends={window_end:'2026-09-08',timezone:'Asia/Shanghai',notice:'合成测试健康样本；不保证全天覆盖，不用于诊断或证明行动效果。',points:points.map((p,i)=>({date:p.date,metrics:Object.fromEntries(['sleep','steps','hrv'].map((key,j)=>{const status=i%7===0?'source_conflict':i%4===0?'missing':'partial';return [key,{status,value:status==='partial'?(key==='sleep'?6+i%3:key==='steps'?(i%9===0?0:4000+i*20):35+i%11):null,unit:['小时','步','毫秒'][j],sample_count:status==='missing'?0:2,sources:status==='missing'?[]:['synthetic.test.source']}];}))}))};
    state.today_context.detail='以下健康记录仅为合成测试数据。';
    state.health={sample_count:42,last_sync_at:'2026-09-08T08:30:00+08:00'};
    state.experiments[1].health_observation={timezone:'Asia/Shanghai',notice:'合成验收样本。仅描述部分样本，不代表健康改善或行动效果。',metrics:[
      {key:'sleep',label:'睡眠',summary:'基线 4 天有样本，平均 6.5 小时；观察期 4 天，平均 7 小时。仅为合成数据的描述性比较。',source_text:'synthetic.test.sleep'},
      {key:'steps',label:'步数',summary:'观察期可用日期不足，来源冲突的日期已排除，暂不能比较。',source_text:'synthetic.test.phone、synthetic.test.watch'},
      {key:'hrv',label:'心率变异性',summary:'当前授权范围无可用样本，暂不能比较。',source_text:'无可用来源'}]};
  }
  return state;
}

function makePreviewCapabilities(scenario) {
  const available=scenario==='connected';
  return {ai_available:available,ai_consent_granted:false,ai_provider:available?'合成服务商（无外部调用）':'',ai_notice_version:available?'synthetic-feedback-v1':'',ai_notice:'AI 需要另行同意。最多使用同一目标下十条已确认反馈的类别信息，不发送笔记、身份或原始健康数据。此服务商及所有响应均为合成预览。'};
}
function makePreviewDevices(scenario) {
  return scenario==='connected'?[{id:'synthetic-device',connected_at:'2026-09-08T08:00:00+08:00',last_sync_at:'2026-09-08T08:30:00+08:00',expires_at:'2026-10-08T08:00:00+08:00'}]:[];
}
