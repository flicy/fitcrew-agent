const {base}=require('../../lib/page');Page(base({async mission(e){await this.write('mission','/v3/mission',{action:e.currentTarget.dataset.action});}}));
