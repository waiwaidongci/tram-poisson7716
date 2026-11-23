import {el, h, p} from '../../utils/dom.js';
import {value} from '../../utils/format.js';

function shape(tag, attrs) {
  const output = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([key, val]) => output.setAttribute(key, val));
  return output;
}

export function plot(chart) {
  const series = chart.series;
  if (!series.length) return el('section', {class:'plot'}, h(3, chart.title), p('无可绘制数据', 'empty'));
  const values = series.map(item => item.value);
  const bound = Math.max(0, ...values);
  const bottom = Math.min(0, ...values);
  const span = bound - bottom || 1;
  const x = i => 28 + (i + .5) * 724 / values.length;
  const y = n => 16 + (bound - n) * 135 / span;
  const baseline = y(0);
  const svg = shape('svg', {viewBox:'0 0 780 167', role:'img', 'aria-label':chart.title});
  svg.append(shape('line', {x1:25,x2:755,y1:baseline,y2:baseline,class:'axis'}));
  if (chart.kind === 'line') {
    svg.append(shape('polyline', {points: values.map((val,i) => `${x(i)},${y(val)}`).join(' '), class:'trend'}));
  }
  series.forEach((item, i) => {
    const width = Math.min(70, 490 / values.length);
    const mark = chart.kind === 'line' ? shape('circle', {cx:x(i),cy:y(item.value),r:3.5})
      : shape('rect', {x:x(i)-width/2,y:Math.min(y(item.value),baseline),width,height:Math.max(1,Math.abs(y(item.value)-baseline))});
    const title = shape('title', {});
    title.textContent = `${item.label} · ${value(item.value)}`;
    mark.append(title);
    svg.append(mark);
  });
  const labels = el('div', {class:'plot-labels'}, ...[series[0], series.at(-1)].map(item => el('span', {}, item.label)));
  return el('section', {class:'plot'}, h(3, chart.title), svg, labels,
    el('details', {class:'series-values'}, el('summary', {}, '查看图表数值'),
      el('ul', {}, series.map(item => el('li', {}, `${item.label} · ${value(item.value)}`)))));
}
