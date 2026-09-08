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
