export const number = new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 4});
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

export function value(input) {
  if (input === null || input === undefined || input === '') return '—';
  if (typeof input === 'number') return number.format(input);
  if (typeof input === 'boolean') return input ? '是' : '否';
  return Array.isArray(input) ? input.join('、') : String(input);
}
export const date = input => input ? dateFormatter.format(new Date(input)) : '—';
