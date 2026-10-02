import { el } from './segmented';
import { colorClass, displayValue, isPlaceholder } from './placeholder';

export function renderKpiCard(opts: {
  label: string;
  value: string | number | null | undefined;
  sub?: string | null;
  why?: string | null;
  color?: string | null;
  large?: boolean;
}): HTMLElement {
  const card = el('div', { className: 'kpi-card' });
  card.appendChild(el('div', { className: 'kpi-card__label', text: opts.label }));
  const val = displayValue(opts.value);
  const v = el('div', {
    className: `kpi-card__value mono${opts.large ? ' lg' : ''}${isPlaceholder(opts.value) ? ' faint' : ''} ${colorClass(opts.color)}`,
    text: val,
  });
  card.appendChild(v);
  if (opts.sub) {
    card.appendChild(el('div', { className: 'kpi-card__sub', text: opts.sub }));
  }
  if (opts.why) {
    card.appendChild(el('div', { className: 'kpi-card__why', text: opts.why }));
  }
  return card;
}
