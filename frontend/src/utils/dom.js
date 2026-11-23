export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'style') Object.assign(node.style, value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child !== null && child !== undefined && child !== false) node.append(child);
  }
  return node;
}

export const p = (text, className) => el('p', {class: className}, text);
export const h = (level, text) => el(`h${level}`, {}, text);
export const button = (text, attributes = {}) => el('button', {type:'button', ...attributes}, text);
export const link = (text, href, attributes = {}) => el('a', {href, ...attributes}, text);
