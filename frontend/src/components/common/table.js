import {button, el, p} from '../../utils/dom.js';
import {value} from '../../utils/format.js';

export function table(columns, rows, {caption, empty = '暂无记录', pageSize = 12} = {}) {
  if (!rows.length) return p(empty, 'empty');
  const body = el('tbody');
  const grid = el('table', {}, caption && el('caption', {class:'sr'}, caption),
    el('thead', {}, el('tr', {}, columns.map(col => el('th', {scope:'col'}, col.label)))), body);
  const count = el('span', {'aria-live':'polite'});
  let offset = 0;
  const prev = button('上一页', {class:'quiet', onClick: () => { offset -= pageSize; paint(); }});
  const next = button('下一页', {class:'quiet', onClick: () => { offset += pageSize; paint(); }});
  function paint() {
    const end = Math.min(rows.length, offset + pageSize);
    body.replaceChildren(...rows.slice(offset, end).map(row =>
      el('tr', {}, columns.map(col => el('td', {}, col.render ? col.render(row) : value(row[col.key]))))));
    count.textContent = `${offset + 1}–${end} / ${rows.length}`;
    prev.disabled = offset === 0;
    next.disabled = end === rows.length;
  }
  paint();
  return el('div', {}, el('div', {class:'table-wrap', tabindex:'0', role:'region', 'aria-label':caption || '数据表'}, grid),
    rows.length > pageSize && el('div', {class:'pagination'}, prev, count, next));
}
