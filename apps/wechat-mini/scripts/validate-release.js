const {isIP}=require('node:net');
const {validBase}=require('../lib/client');

function validateRelease(project,config){
 const failures=[];
 if(!/^wx[0-9a-f]{16}$/i.test(project.appid||''))failures.push('Missing verified WeChat AppID');
 if((project.appid||'').toLowerCase()==='wxae59705a7cce30f9')failures.push('The supplied sandbox AppID cannot be used for formal production review');
 let domain=false;
 if(validBase(config.baseURL)){
  try{
   const host=new URL(config.baseURL).hostname;
   domain=!isIP(host)&&host.includes('.')&&!host.includes('..')&&!host.endsWith('.')&&
    !/(^|\.)(test|invalid|example|localhost|local)$/.test(host)&&
    host.split('.').every(label=>/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(label));
  }catch(_){}
 }
 if(!domain)failures.push('Missing production HTTPS domain; IPs and reserved test hosts are not production configuration');
 if(project.setting?.urlCheck!==true)failures.push('Legal-domain validation must stay enabled');
 return failures;
}
module.exports={validateRelease};
if(require.main===module){
 const failures=validateRelease(require('../project.config.json'),require('../config'));
 if(failures.length){console.error(failures.join('\n'));process.exitCode=1;}
 else console.log('Local public configuration checks passed; domain ownership/category/filing/privacy and real-device review still require platform evidence.');
}
