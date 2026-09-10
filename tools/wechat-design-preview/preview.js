(async()=>{
  const fixtureScript=await fetch('/fixtures.js').then(r=>r.text());
  const {makeFixture,makePreviewCapabilities,makePreviewDevices}=Function(fixtureScript+';return {makeFixture,makePreviewCapabilities,makePreviewDevices};')();
  const metadata=await fetch('/meta').then(r=>r.json());
  document.getElementById('revision').textContent='当前源码 / Current source: '+metadata.revision+' · 合成验收 / Synthetic acceptance';
  const scenes=new Map(), mounted=new Map();
  const bundles=await Promise.all(['before','after'].map(version=>fetch('/bundle?version='+version).then(r=>r.json())));
  const ids=['page','scenario','step','width','scale'],controls=Object.fromEntries(ids.map(id=>[id,document.getElementById(id)]));
  const query=new URLSearchParams(location.search);ids.forEach(id=>{if(query.has(id))controls[id].value=query.get(id);});
  function mount(frame,bundle){
    const route=controls.page.value,scenario=controls.scenario.value,width=Number(controls.width.value),scale=Number(controls.scale.value);
    const previous=mounted.get(frame.id);if(previous){previous.onHide?.();previous.onUnload?.();}
    const sceneKey=frame.id+':'+scenario+':'+controls.step.value;
    if(!scenes.has(sceneKey))scenes.set(sceneKey,{state:makeFixture(scenario,controls.step.value),caps:makePreviewCapabilities(scenario),devices:makePreviewDevices(scenario),storage:{}});
    const scene=scenes.get(sceneKey),storage=scene.storage,state=scene.state;let page,schedule=false;
    const formatModule={exports:{}};Function('module',bundle.formatter||'')(formatModule);const fmt=formatModule.exports;
    frame.style.width=width+'px';frame.style.height='874px';
    const d=frame.contentDocument;d.open();d.write('<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style></style></head><body><div class="preview-nav">FitCrew · 合成预览 <span>•••　◉</span></div><main id="app"></main><nav id="tabs"></nav></body></html>');d.close();
    const css=bundle.css[route].replace(/(^|[\s}])page\s*\{/g,'$1body{').replace(/(^|[\s,>])view(?=[\s,{])/g,'$1div').replace(/(-?\d*\.?\d+)rpx/g,(_,v)=>Number(v)*width/750+'px');
    d.querySelector('style').textContent='body{margin:0;padding-bottom:72px}button,input,textarea,select{font-family:inherit}button{cursor:pointer;width:100%;box-sizing:border-box}view,scroll-view{display:block}#app{min-width:0} .preview-nav{position:relative;display:flex;justify-content:center;padding:14px 20px;font:600 15px -apple-system;background:#F8F7FA;min-height:48px}.preview-nav span{position:absolute;right:16px;font-size:12px;border:1px solid #ddd;border-radius:20px;padding:3px 8px;top:11px}#tabs{position:fixed;bottom:0;left:0;right:0;background:#fff;display:flex;border-top:1px solid #eee;z-index:10;padding:6px 8px 10px;gap:2px}#tabs button{flex:1;min-width:44px;min-height:50px;margin:0;padding:4px 0;background:none;border:0;color:#756A81;font-size:11px;display:flex;flex-direction:column;gap:4px}#tabs img{width:24px;height:24px}#tabs .active{color:#6544A3}dialog{border:0;border-radius:22px;padding:24px;max-width:calc(100% - 24px);width:360px;max-height:85vh;overflow:auto;color:#292333;font:16px/1.6 -apple-system}dialog::backdrop{background:#22192f66}dialog button{width:100%}select{width:100%;color:inherit}'+css;
    if(scenario!=='restricted'&&!scene.loggedOut)storage['fitcrew.session']={device_token:'synthetic-local-preview',created_at:Date.now()};
    async function modal(title,content,items){return new Promise(resolve=>{const el=d.createElement('dialog');const h=d.createElement('h3');h.textContent=title;el.append(h);const p=d.createElement('div');p.textContent=content;p.style.whiteSpace='pre-wrap';el.append(p);items.forEach((text,i)=>{const b=d.createElement('button');b.textContent=text;b.onclick=()=>{el.close();el.remove();resolve(i)};el.append(b)});el.oncancel=()=>{el.remove();resolve(-1)};d.body.append(el);el.showModal()})}
    const wx={getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],getStorageInfoSync:()=>({keys:Object.keys(storage)}),getAppBaseInfo:()=>({fontSizeScaleFactor:scale}),env:{USER_DATA_PATH:'/synthetic-local-preview'},getFileSystemManager:()=>({readdirSync:()=>[],unlinkSync:()=>{},writeFileSync:()=>{}}),switchTab:({url})=>{controls.page.value=url.split('/')[2];update()},showModal:async o=>{const i=await modal(o.title,o.content,['取消',o.confirmText||'确认']);o.success({confirm:i===1})},showActionSheet:async o=>{const i=await modal('保存方式','仅在本地预览中模拟。',[...o.itemList,'取消']);if(i<0||i===o.itemList.length)o.fail();else o.success({tapIndex:i})},setClipboardData:o=>{document.getElementById('actions').textContent='仅模拟复制，不改系统剪贴板；此链接无法连接真实账号。';o.success?.();},openPrivacyContract:()=>modal('隐私指引','本地预览不连接微信隐私平台。',['关闭'])};
    async function request(path,method='GET',body){
      if(scenario==='restricted')throw Error('请先登录后使用。');
      if(scenario==='failed')throw Error('连接暂时中断，请重新读取。');
      if(method!=='GET'&&scenario==='offline')throw Error('网络连接失败，所选内容已保留。');
      if(path==='/v3/capabilities')return structuredClone(scene.caps);
      if(path==='/v3/ai-consent'&&method==='POST'){scene.caps.ai_consent_granted=body.granted;return structuredClone(scene.caps);}
      if(path==='/v3/device-pairing/devices')return {devices:structuredClone(scene.devices)};
      if(path.startsWith('/v3/device-pairing/devices/')&&method==='DELETE'){const id=path.split('/').at(-1);scene.devices=scene.devices.filter(d=>d.id!==id);return {disconnected:true,device_id:id};}
      if(path==='/v3/device-pairing'&&method==='POST')return {pairing_url:'fitcrew-health://configure?payload=synthetic-preview-not-redeemable',expires_at:new Date(Date.now()+15*60*1000).toISOString()};
      if(path==='/v3/device-pairing'&&method==='DELETE')return {cancelled:true};
      if(path==='/v3/state'){if(scene.loggedOut)throw Error('合成账号已注销；切换状态可重新开始预览。');return structuredClone(state);}
      if(path==='/v3/logs'&&method==='POST'){state.logs.push({...body,id:'preview-'+Date.now(),created_at:'2026-09-08T10:00:00+08:00'});return {id:state.logs.at(-1).id};}
      if(path==='/v3/journey'){state.journey={title:{sleep:'睡得更好',energy:'精力更稳',activity:'动得更多'}[body.goal],days:90,start_date:'2026-09-08'};return state.journey;}
      if(path==='/v3/mission'){if(body.action==='lighten'){state.mission.title=body.alternative==='quiet_minute'?'留一分钟安静休息':'只记录此刻的感受';state.mission.adjusted_at='2026-09-08T10:00:00+08:00';state.mission.revision++;}else state.mission.status=body.action==='done'?'done':'skipped';return state.mission;}
      if(path==='/v3/onboarding'){state.onboarding.step++;return state.onboarding;}
      if(path==='/v3/experiments/propose'){const template=state.experiments[0]||makeFixture('ready',7).experiments[0];state.experiments.unshift({...template,id:'preview-proposal-'+Date.now(),status:'proposed',result:null,health_observation:null,source:scene.caps.ai_consent_granted?'ai_selected':'rule_based'});return state.experiments[0];}
      if(path.endsWith('/feedback')){const item=state.experiments.find(e=>e.id===path.split('/')[3]);item.user_feedback={assessment:body.assessment};if(body.confirm_memory&&body.assessment!=='uncertain'){state.confirmed_memories.push({id:'synthetic-feedback-'+Date.now(),text:'我主观觉得这次行动'+(body.assessment==='fits'?'适合':'不适合')+'自己。',experiment_title:item.title,confirmed_at:new Date().toISOString()});}return item;}
      if(path.endsWith('/transition')){const item=state.experiments.find(e=>e.id===path.split('/')[3]);item.status={accept:'running',pause:'paused',resume:'running',stop:'stopped',evaluate:'completed'}[body.action];return item;}
      if(method==='GET'&&path.startsWith('/v3/export?'))return {synthetic:true,export_metadata:{scope:new URLSearchParams(path.split('?')[1]).get('scope'),receipt_id:'synthetic-receipt'}};
      if(method==='DELETE'){
        if(path.startsWith('/v3/memories/'))state.confirmed_memories=state.confirmed_memories.filter(m=>m.id!==path.split('/').at(-1));
        else if(path.startsWith('/v3/milestones/'))state.milestones=state.milestones.filter(m=>m.id!==path.split('/').at(-1));
        else if(path.startsWith('/v3/logs/'))state.logs=state.logs.filter(m=>m.id!==path.split('/').at(-1));
        else if(path==='/v3/data'||path==='/v3/account'){state.logs=[];state.confirmed_memories=[];state.milestones=[];if(body.scope!=='logs')Object.assign(state,makeFixture('empty',7));if(path==='/v3/account')scene.loggedOut=true;}
        else throw Error('此操作尚未实现合成预览：'+method+' '+path);
        return {deleted:true,receipt_id:'synthetic-receipt'};
      }
      throw Error('此操作尚未实现合成预览：'+method+' '+path);
    }
    const cache={};
    function requireModule(path){if(cache[path])return cache[path].exports;const module={exports:{}};cache[path]=module;const req=name=>{let parts=(path.slice(0,path.lastIndexOf('/')+1)+name).split('/'),normalized=[];parts.forEach(p=>{if(p==='..')normalized.pop();else if(p!=='.')normalized.push(p)});let key=normalized.join('/');if(!key.endsWith('.js'))key+='.js';return requireModule(key)};Function('require','module','exports','Page','wx','getApp',bundle.modules[path]||'')(req,module,module.exports,definition=>{page=definition;mounted.set(frame.id,page);},wx,()=>({api:{request}}));return module.exports;}
    requireModule('pages/'+route+'/index.js');
    page.data=structuredClone(page.data);page.setData=function(data){Object.assign(this.data,data);if(d.activeElement?.tagName==='TEXTAREA')return;if(!schedule){schedule=true;queueMicrotask(()=>{schedule=false;render()})}};
    const app=d.getElementById('app');
    function val(expr,scope){try{return Function('s','with(s){return ('+expr+')}')(scope)}catch(_){return undefined}}
    function interpolate(str,scope){return String(str).replace(/\{\{([\s\S]*?)\}\}/g,(_,expr)=>val(expr,scope)??'')}
    function expression(str,scope){return val(str.replace(/^\{\{|\}\}$/g,''),scope)}
    const template=bundle.status.children.find(n=>typeof n!=='string'&&n.tag==='template');
    function children(nodes,parent,scope){let chain=false;for(const node of nodes){if(typeof node==='string'){if(node.trim())parent.append(d.createTextNode(interpolate(node,scope)));continue;}const a=node.attrs;
      if(a['wx:for']){const arr=expression(a['wx:for'],scope)||[];arr.forEach((item,index)=>{const local={...scope,[a['wx:for-item']||'item']:item,[a['wx:for-index']||'index']:index};const copy={...node,attrs:{...a}};delete copy.attrs['wx:for'];children([copy],parent,local)});continue;}
      if(a['wx:if']!==undefined){chain=!!expression(a['wx:if'],scope);if(!chain)continue;}
      else if(a['wx:elif']!==undefined){if(chain)continue;chain=!!expression(a['wx:elif'],scope);if(!chain)continue;}
      else if(a['wx:else']!==undefined){if(chain)continue;chain=true;}
      else chain=false;
      if(['import','wxs'].includes(node.tag))continue;
      if(node.tag==='template'){children(template.children,parent,scope);continue;}
      if(['root','block'].includes(node.tag)){children(node.children,parent,scope);continue;}
      let tag={view:'div',text:'span','scroll-view':'div',picker:'select',slider:'input'}[node.tag]||node.tag;
      const el=d.createElement(tag);Object.entries(a).forEach(([k,v])=>{if(k==='class'||k==='style'||k.startsWith('aria-')||k==='role'||k.startsWith('data-'))el.setAttribute(k,interpolate(v,scope));});
      if(a.disabled&&expression(a.disabled,scope))el.disabled=true;
      if(a['scroll-x']!==undefined){el.style.overflowX='auto';el.style.maxWidth='100%';if(a['scroll-left'])el.dataset.initialScroll=expression(a['scroll-left'],scope)}
      if(a['scroll-y']!==undefined)el.style.overflowY='auto';
      if(node.tag==='picker'){const items=expression(a.range,scope)||[];items.forEach((item,i)=>{let opt=d.createElement('option');opt.value=i;opt.textContent=item;el.append(opt)});el.value=expression(a.value,scope);el.classList.add('input');}
      else if(node.tag==='slider'){el.type='range';['min','max','step'].forEach(k=>el[k]=a[k]);el.value=expression(a.value,scope);el.style.width='100%';el.style.minHeight='44px';}
      else if(node.tag==='textarea'){el.value=expression(a.value,scope)||'';el.placeholder=a.placeholder||'';el.maxLength=Number(a.maxlength||500);el.onblur=()=>render();}
      else children(node.children,el,scope);
      for(const [event,handler] of Object.entries(a)){const events={bindtap:'click',bindchange:'change',bindinput:'input'};if(events[event])el.addEventListener(events[event],async()=>{if(!page[handler])throw Error('Unbound handler '+handler);await page[handler]({currentTarget:{dataset:{...el.dataset}},detail:{value:el.value}});if(event!=='bindinput')render();});}
      parent.append(el);
    }}
    function render(){const old=app.querySelector('.trend-scroll'),pos=old&&old.dataset.initialScroll===String(page.data.trendDays*62)?old.scrollLeft:null;app.replaceChildren();children(bundle.pages[route].children,app,{...page.data,fmt});const next=app.querySelector('.trend-scroll');if(next)next.scrollLeft=pos??Number(next.dataset.initialScroll||0);}
    const tabs=d.getElementById('tabs');bundle.config.tabBar.list.forEach(item=>{let b=d.createElement('button'),name=item.pagePath.split('/')[1];b.className=name===route?'active':'';if(item.iconPath){const img=d.createElement('img');img.src='/'+(name===route?item.selectedIconPath:item.iconPath);b.append(img)}const span=d.createElement('span');span.textContent=item.text;b.append(span);b.onclick=()=>{controls.page.value=name;update()};tabs.append(b)});
    page.onLoad();page.onShow().then(()=>{if(scenario==='busy')page.setData({busy:true});if(scenario==='offline')page.setData({error:'网络连接失败，所选内容已保留。'});render()});
  }
  function update(){bundles.forEach((bundle,i)=>mount(document.getElementById(i?'after':'before'),bundle));}
  ids.forEach(id=>controls[id].onchange=update);document.getElementById('single').onclick=()=>document.body.classList.toggle('single');if(query.get('capture')==='1'){document.body.classList.add('capture');if(query.get('version')==='before')document.body.classList.add('before-only');}if(query.get('single')==='1')document.body.classList.add('single');update();
})();
