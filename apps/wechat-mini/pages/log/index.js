const lifecycle=require('../../lib/session');
const {base,confirm}=require('../../lib/page');
Page(base({data:{energy:3,stress:2,feelingIndex:1,feelings:['充沛','正常','有点累','很累','不适'],note:'',sleepIndex:0,trainingIndex:0,sourceIndex:0,sleepFeelings:['暂不记录','醒后清爽','一般','醒后疲惫'],trainingFeelings:['暂不记录','完成','偏累','恢复良好'],stressSources:['暂不记录','工作','学习','人际','其他']},
 onLoad(){const draft=wx.getStorageSync('fitcrew.draft');if(draft)this.setData(draft);},
 edit(e){this.syncBoundary();if(this.data.busy)return;const field=e.currentTarget.dataset.field,value=field==='note'?e.detail.value:Number(e.detail.value);this.setData({[field]:value});wx.setStorageSync('fitcrew.draft',this.draft());},
 draft(){const {energy,stress,feelingIndex,note,sleepIndex,trainingIndex,sourceIndex}=this.data;return {energy,stress,feelingIndex,note,sleepIndex,trainingIndex,sourceIndex};},
 async save(){this.syncBoundary();const epoch=lifecycle.epoch(wx);const {energy,stress,feelingIndex,feelings,note}=this.data;if(note.length>500)return this.setData({error:'备注最多 500 字'});
 const {sleepIndex,trainingIndex,sourceIndex,sleepFeelings,trainingFeelings,stressSources}=this.data;
 const body={energy,stress,feeling:feelings[feelingIndex],note,sleep_feeling:sleepIndex?sleepFeelings[sleepIndex]:null,training_feeling:trainingIndex?trainingFeelings[trainingIndex]:null,stress_source:sourceIndex?stressSources[sourceIndex]:null};
 if(await this.write('log','/v3/logs',body)&&lifecycle.current(wx,epoch)){wx.removeStorageSync('fitcrew.draft');this.setData({note:'',sleepIndex:0,trainingIndex:0,sourceIndex:0});}},
 async remove(e){this.syncBoundary();const epoch=lifecycle.epoch(wx);if(this.data.busy||!await confirm('删除这条记录？','这会永久删除记录，并使相关实验评估失效。'))return;if(!lifecycle.current(wx,epoch))return;this.setData({busy:true,error:''});try{const receipt=await getApp().api.request('/v3/logs/'+e.currentTarget.dataset.id,'DELETE');if(!lifecycle.current(wx,epoch))return;this.setData({receipt:receipt.receipt_id});await this.refresh();}catch(e){if(lifecycle.current(wx,epoch))this.setData({error:e.message});}finally{if(lifecycle.current(wx,epoch))this.setData({busy:false});}}
}));
