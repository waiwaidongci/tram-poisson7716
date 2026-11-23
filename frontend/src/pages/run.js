import {datasetField, feedback, field} from '../components/common/fields.js';
import {empty, panel, pill} from '../components/common/panels.js';
import {table} from '../components/common/table.js';
import {STATUS} from '../constants/enums.js';
import {handler} from '../hooks/action.js';
import {session} from '../stores/session.js';
import {workspace} from '../stores/workspace.js';
import {button, el, link, p} from '../utils/dom.js';
import {date} from '../utils/format.js';

function runRequest(data, spec) {
  return {dataset_id:Number(data.get('dataset_id')),name:data.get('name'),
    params:Object.fromEntries(spec.params.map(param=>[param.key,data.get(param.key)]))};
}

export async function runPage(route, refresh) {
  const {spec,datasets,runs} = workspace;
  const scheduling = spec.scheduled && route.scheduling;
  const plans = scheduling ? await workspace.schedules() : [];
  const error = feedback();
  const submit = button(`执行${spec.run}`,{type:'submit',class:'primary','data-testid':'start-run'});
  const plan = button('保存定时计划',{type:'button',class:'primary','data-testid':'save-schedule'});
  const scheduleFields = scheduling && session.canReview && el('details',{class:'schedule-fields'},
    el('summary',{},'定时站内分发'),
    p('单次执行锁定所选批次。每日计划读取最新导入的批次，报告日逐日推进。通过发布门槛后进入站内收件箱。','subtle'),
    field({key:'recipient',label:'收件团队',type:'string',required:false,max_length:100}),
    field({key:'first_at',label:'首次执行时间（北京时间）',type:'datetime-local',required:false}),
    el('label',{class:'check'},el('input',{name:'repeat_daily',type:'checkbox'}),'每日同一时间运行'), plan);
  const form = el('form',{class:'fields','data-testid':'run-form',
    onSubmit:handler(submit,error,async event=>{
      const item = await workspace.start(runRequest(new FormData(event.target),spec));
      location.hash = `#results/${item.id}`;
    })}, datasetField(datasets,route.id),field({key:'name',label:'运行名称',type:'string',max_length:120},`样本${spec.run}`),
    el('div',{class:'form-grid'},spec.params.map(param=>field(param))),el('div',{class:'actions'},submit),scheduleFields,error);
  plan.addEventListener('click',handler(plan,error,async()=>{
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const recipient = data.get('recipient'), start = data.get('first_at');
    if (!recipient?.trim() || !start) throw new Error('请填写收件团队和首次执行时间');
    await workspace.schedule({...runRequest(data,spec),recipient,first_at:`${start}:00+08:00`,repeat_daily:data.has('repeat_daily')});
    await refresh();
  }));
  const runList = table([
    {label:'运行',render:item=>link(item.name,`#results/${item.id}`)},
    {label:'状态',render:item=>pill(STATUS[item.status],item.status)},
    {label:'时间',render:item=>date(item.created_at)},
  ],runs,{caption:'运行记录',empty:'首次运行后将在此显示后台状态。'});
  const scheduleList = scheduling && panel('定时计划',table([
    {key:'name',label:'计划'}, {key:'recipient',label:'收件团队'},
    {label:'下次执行（北京时间）',render:row=>row.enabled ? date(row.next_at) : '—'},
    {key:'next_report_day',label:'下次报告日'},
    {label:'状态',render:row=>row.enabled ? '启用' : '已结束'},
    {label:'操作',render:row=>{
      if (!row.enabled || !session.canReview) return '—';
      const action = button('停止计划',{class:'quiet'});
      action.addEventListener('click',handler(action,error,async()=>{await workspace.disable(row.id);await refresh();}));
      return action;
    }},
  ],plans,{caption:'定时计划',empty:'还未配置定时计划。'}));
  return el('div',{class:'two-col'}, el('div',{class:'wide-panel'},
    panel(spec.run,session.canWrite ? (datasets.length ? form : empty('请先导入数据。','#inputs','前往导入'))
      : p('只读角色可以查看上方业务流程的历史运行。','empty')),
    !scheduling && panel('运行记录',runList),scheduleList),
    el('aside',{class:'sidebar-panel'},panel('计算口径',el('ul',{class:'method-list'},spec.methodology.map(text=>el('li',{},text))))));
}
