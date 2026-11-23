import {el, h, link, p} from '../../utils/dom.js';
import {value} from '../../utils/format.js';

export const panel = (title, ...children) => el('section', {class:'panel'}, title && h(2, title), children);
export const empty = (message, href, text) => el('div', {class:'empty'}, p(message), href && link(text, href, {class:'quiet'}));
export const pill = (text, state) => el('span', {class:'pill', 'data-state':state}, text);
export const metrics = entries => el('dl', {class:'metrics'}, entries.map(item =>
  el('div', {}, el('dt', {}, item.label), el('dd', {}, value(item.value)), item.detail && p(item.detail, 'subtle'))));
