export function createSegmented(
  ariaLabel: string,
  options: Array<{ value: string; label: string }>,
  selected: string,
  onChange: (value: string) => void,
): HTMLElement {
  const group = document.createElement('div');
  group.className = 'seg';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', ariaLabel);

  for (const opt of options) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = opt.label;
    btn.setAttribute('aria-pressed', String(opt.value === selected));
    btn.addEventListener('click', () => onChange(opt.value));
    group.appendChild(btn);
  }
  return group;
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Record<string, string | boolean | undefined> = {},
  children: Array<Node | string | HTMLElement> = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === undefined || v === false) continue;
    if (k === 'className') node.className = String(v);
    else if (k === 'text') node.textContent = String(v);
    else if (k === 'value' && (tag === 'input' || tag === 'textarea')) {
      (node as HTMLInputElement).value = String(v);
    } else if (v === true) node.setAttribute(k, '');
    else node.setAttribute(k, String(v));
  }
  for (const child of children) {
    if (child === '' || child == null) continue;
    node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return node;
}
