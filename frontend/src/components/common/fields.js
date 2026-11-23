import {el} from '../../utils/dom.js';

export function field(config, current = config.default) {
  const id = `field-${config.key}`;
  const attrs = {id, name:config.key, required:config.required !== false, 'aria-describedby': config.help ? `${id}-help` : undefined};
  const options = config.type === 'bool' ? [['true', '是'], ['false', '否']]
    : config.options?.map(option => [String(option), String(option)]);
  const type = {int:'number', number:'number', date:'date', string:'text'}[config.type] || config.type;
  const input = options
    ? el('select', attrs, options.map(([value, label]) => el('option', {value, selected:value === String(current)}, label)))
    : el('input', {...attrs, type, step:config.type === 'int' ? '1' : config.type === 'number' ? 'any' : undefined,
      min: config.min, max:config.max, maxlength:config.max_length, value:current, autocomplete:config.autocomplete});
  return el('label', {for:id, class:'field'}, el('span', {}, config.label), input,
    config.help && el('small', {id:`${id}-help`}, config.help));
}

export function datasetField(datasets, selected) {
  return el('label', {for:'dataset-id', class:'field'}, el('span', {}, '数据批次'),
    el('select', {id:'dataset-id', name:'dataset_id', required:true}, datasets.map(item =>
      el('option', {value:item.id, selected:String(item.id) === String(selected)}, `${item.name} · ${item.row_count} 行`))));
}

export const feedback = () => el('p', {class:'feedback', 'aria-live':'polite', 'data-testid':'feedback'});
