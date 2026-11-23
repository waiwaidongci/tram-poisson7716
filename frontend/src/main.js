import {ROLE} from './constants/enums.js';
import {deliveryPage} from './pages/delivery.js';
import {reviewPage} from './pages/review.js';
import {inputs} from './pages/inputs.js';
import {login} from './pages/login.js';
import {overview} from './pages/overview.js';
import {results} from './pages/results.js';
import {runPage} from './pages/run.js';
import {pages, route} from './router/routes.js';
import {session} from './stores/session.js';
import {workspace} from './stores/workspace.js';
import {button, el, h, link, p} from './utils/dom.js';

const app = document.getElementById('app');
const views = {overview, inputs, run:runPage, results, review:reviewPage, delivery:deliveryPage};
let revision = 0;

function shell(state, content) {
  const {spec} = workspace;
  const index = pages.indexOf(state.page);
  return el('div',{class:'shell'},el('aside',{class:'rail'},
    link(spec.title,'#overview',{class:'brand'}),
    el('nav',{'aria-label':'业务模块'},pages.map((page,i)=>link(spec.pages[i],`#${page}`,{class:'nav-link',
      'aria-current':page===state.page ? 'page' : undefined}))),
    el('div',{class:'account'},p(`${ROLE[session.actor.role]} · ${session.actor.username}`),
      button('退出',{class:'quiet',onClick:()=>{session.signOut();render();}}))),
    el('main',{class:'main',id:'main'},el('header',{class:'header'},h(1,spec.pages[index]),p(spec.title)), content));
}

async function render() {
  const current = ++revision;
  const state = route();
  const {spec} = workspace;
  if (!session.actor) {
    document.body.dataset.page = 'login';
    app.replaceChildren(login(spec,render));
    return;
  }
  try {
    await workspace.refresh();
    const content = await views[state.page](state,render);
    if (revision !== current) return;
    document.body.dataset.page = state.page;
    app.replaceChildren(shell(state,content));
    if (state.page !== 'inputs') window.scrollTo(0,0);
  } catch (error) {
    if (revision !== current) return;
    if (error.status === 401) {
      session.signOut();
      await render();
      return;
    }
    document.body.dataset.page = state.page;
    app.replaceChildren(shell(state,el('div',{class:'empty',role:'alert'},p(error.message),
      button('重试',{class:'quiet',onClick:render}))));
  }
}

async function init() {
  try {
    await Promise.all([workspace.init(),session.restore()]);
    document.title = workspace.spec.title;
    await render();
  } catch (error) {
    app.replaceChildren(el('main',{class:'boot',role:'alert'},h(1,'连接工作台失败'),p(error.message),
      button('重试',{class:'quiet',onClick:init})));
  }
}

window.addEventListener('hashchange',render);
init();
