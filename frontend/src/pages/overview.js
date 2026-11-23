import {panel, metrics, pill, empty} from '../components/common/panels.js';
import {table} from '../components/common/table.js';
import {STATUS} from '../constants/enums.js';
import {session} from '../stores/session.js';
import {workspace} from '../stores/workspace.js';
import {el, h, link, p} from '../utils/dom.js';
import {date} from '../utils/format.js';

export async function overview() {
  const {spec, datasets, runs} = workspace;
  const latest = runs[0];
  const feed = session.canReview ? await workspace.audit() : [];
  return el('div', {class:'overview'},
    el('div', {class:'overview-main'},
      el('section', {class:'hero'}, p(spec.organization,'eyeline'), h(2,spec.subtitle), p(spec.workflow,'intro-copy'),
        el('div',{class:'actions'}, link(spec.pages[1], '#inputs', {class:'primary'}), link(spec.pages[2], '#run',{class:'quiet'}))),
      panel('业务处理步骤', el('ol', {class:'work-steps'}, spec.steps.map(text => el('li', {}, text)))),
      feed.length && panel('最近审计事件',table([
        {key:'actor',label:'操作者'}, {key:'event',label:'动作'}, {key:'target',label:'关联记录'},
        {label:'时间',render:row=>date(row.created_at)},
      ],feed.slice(0,8),{caption:'最近审计事件'}))),
    el('aside', {class:'sidebar-panel'},
      panel('当前批次', metrics([{label:'数据批次',value:datasets.length},{label:'运行记录',value:runs.length}]),
        datasets[0] && p(datasets[0].filename,'filename')),
      panel('最近运行', latest ? el('div',{class:'activity'},link(latest.name,`#results/${latest.id}`),
        pill(STATUS[latest.status],latest.status),p(date(latest.created_at),'subtle'))
        : empty('进入运行页，使用演示数据执行首次分析。','#run','前往运行')),
      panel('现场问题', el('ul', {class:'method-list'}, spec.pains.map(text => el('li',{},text))))));
}
