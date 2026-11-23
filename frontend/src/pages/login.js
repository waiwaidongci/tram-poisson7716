import {ROLE} from '../constants/enums.js';
import {feedback, field} from '../components/common/fields.js';
import {handler} from '../hooks/action.js';
import {session} from '../stores/session.js';
import {button, el, h, p} from '../utils/dom.js';

export function login(spec, refresh) {
  const error = feedback();
  const submit = button('登录', {type:'submit', class:'primary'});
  const form = el('form', {class:'login-form', 'data-testid':'login-form', onSubmit:handler(submit,error,async event => {
    const data = new FormData(event.target);
    await session.signIn(data.get('username'), data.get('password'));
    await refresh();
  })}, field({key:'username',label:'账号', type:'string', autocomplete:'username',max_length:64}),
    field({key:'password',label:'密码',type:'password',autocomplete:'current-password',max_length:128}), submit,error);
  const samples = el('div', {class:'login-roles'}, Object.entries(ROLE).map(([name, label]) =>
    button(label, {class:'quiet', onClick:() => {
      form.elements.username.value = name;
      form.elements.password.value = `${name}-demo-2611`;
    }})));
  return el('main', {class:'login'},
    el('div', {class:'login-intro'}, p(spec.organization, 'eyeline'), h(1,spec.title), p(spec.subtitle,'intro-copy'),
      el('div', {class:'login-index'}, spec.pages.slice(1).map(label => el('span', {}, label)))),
    el('section', {class:'login-box'}, h(2,'登录工作台'), form,
      el('div', {class:'test-roles'}, p('填入演示账号', 'subtle'), samples)));
}
