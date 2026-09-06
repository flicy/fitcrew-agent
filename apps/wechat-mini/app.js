const {makeClient}=require('./lib/client');
const session=require('./lib/session');
const config=require('./config');
App({onLaunch(){session.active(wx);try{session.cleanExport(wx);}catch(e){/* Persistent cleanup remains accessible from Profile. */}this.api=makeClient(wx,config.baseURL);}});
