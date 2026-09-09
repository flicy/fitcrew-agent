// Presentation only. The native navigation/tab bars keep the host's own sizing.
function textScale(host) {
  try {
    const info = host.getAppBaseInfo ? host.getAppBaseInfo() : {};
    const scale = Number(info.fontSizeScaleFactor) || Number(info.fontSizeSetting) / 16;
    return Number.isFinite(scale) && scale > 0 ? Math.max(1, scale) : 1;
  } catch (_) { return 1; }
}
module.exports = { textScale };

const healthLabels={partial:'部分样本',missing:'无样本',not_authorized:'未授权',source_conflict:'来源冲突',invalid:'数据异常'};
function healthPoints(state,metric,days){
 const points=state&&state.health_trends?state.health_trends.points.slice(-days):[];
 const mapped=points.map(p=>{const m=p.metrics[metric]||{};const known=m.status==='partial'&&Number.isFinite(m.value);return {date:p.date,...m,known,value:known?m.value:null,statusLabel:healthLabels[m.status]||'待核实',sourceText:(m.sources||[]).join('、')||'无可用来源'};});
 const maximum=Math.max(1,...mapped.filter(p=>p.known).map(p=>p.value));
 return mapped.map(p=>({...p,barHeight:p.known?p.value/maximum*100:0}));
}
module.exports.healthPoints=healthPoints;

function healthReadiness(state){
 if(!state||!state.health_trends)return null;
 const points=state.health_trends.points.slice(-7);
 const metrics=[['sleep','睡眠'],['steps','步数'],['hrv','心率变异性']].map(([key,label])=>{
  const observations=healthPoints(state,key,7),known=observations.filter(p=>p.known);
  const authorized=observations.some(p=>p.status&&p.status!=='not_authorized');
  const conflicts=observations.filter(p=>['source_conflict','invalid'].includes(p.status)).length;
  return {key,label,observedDays:known.length,issueDays:conflicts,
   detail:!authorized?'未选择上传此类数据':known.length?known.length+' / 7 天有样本':'近七天暂无可用数值',
   issue:conflicts?conflicts+' 天存在冲突或异常，已排除数值':'',
   latestDate:known.length?known[known.length-1].date:''};
 });
 return {metrics,windowStart:points.length?points[0].date:'',windowEnd:state.health_trends.window_end||'',
  timezone:state.health_trends.timezone||'',notice:state.health_trends.notice||'有样本也不代表全天完整覆盖。'};
}
module.exports.healthReadiness=healthReadiness;
