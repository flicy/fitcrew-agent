const {makeClient,validCloud}=require('./lib/client');
const session=require('./lib/session');
const config=require('./config');
App({onLaunch(){session.active(wx);try{session.cleanExport(wx);}catch(e){/* Persistent cleanup remains accessible from Profile. */}if(validCloud(config.cloud)&&wx.cloud&&wx.cloud.init)wx.cloud.init({env:config.cloud.env});this.api=makeClient(wx,config);}});
