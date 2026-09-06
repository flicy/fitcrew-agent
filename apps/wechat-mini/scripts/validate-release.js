const {validBase}=require('../lib/client');
const project=require('../project.config.json'),config=require('../config');
const failures=[];
if(!/^wx[0-9a-f]{16}$/i.test(project.appid||''))failures.push('Missing verified WeChat AppID');
if(!validBase(config.baseURL))failures.push('Missing verified production HTTPS baseURL');
if(project.setting.urlCheck!==true)failures.push('Legal-domain validation must stay enabled');
if(failures.length){console.error(failures.join('\n'));process.exitCode=1;}else console.log('Local public configuration checks passed; domain/category/filing/privacy and real-device review still required.');
