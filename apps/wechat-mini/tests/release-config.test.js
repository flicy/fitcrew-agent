const test=require('node:test'),assert=require('node:assert/strict');
const {validateRelease,effectiveProject}=require('../scripts/validate-release');
const project={appid:'wx0123456789abcdef',setting:{urlCheck:true}};
test('private DevTools overrides cannot disable legal-domain validation',()=>{
 const effective=effectiveProject(project,{appid:'wxae59705a7cce30f9',setting:{urlCheck:false}});
 const errors=validateRelease(effective,{baseURL:'https://api.fitcrew.cn'}).join('\n');
 assert.match(errors,/validation must stay enabled/);
 assert.equal(project.setting.urlCheck,true);
 assert.equal(effectiveProject(project,{setting:{compileHotReLoad:true}}).setting.urlCheck,true);
});
test('formal release validation accepts a syntactically valid owner-confirmed AppID',()=>{
 const configured={...project,appid:'wxae59705a7cce30f9'};
 assert.deepEqual(validateRelease(configured,{baseURL:'https://api.fitcrew.cn'}),[]);
 assert.equal(configured.appid,'wxae59705a7cce30f9');
});
test('release validation refuses IP and local endpoints even with HTTPS and an AppID',()=>{
 for(const baseURL of ['https://124.156.218.104','https://2130706433','https://api.fitcrew.test','https://api.fitcrew.local','https://a..cn','https://-api.fitcrew.cn']){
  assert.match(validateRelease(project,{baseURL}).join('\n'),/production HTTPS domain/,baseURL);
 }
 assert.deepEqual(validateRelease(project,{baseURL:'https://api.fitcrew.cn'}),[]);
 assert.match(validateRelease({...project,setting:{urlCheck:false}},{baseURL:'https://api.fitcrew.cn'}).join('\n'),/validation must stay enabled/);
});
