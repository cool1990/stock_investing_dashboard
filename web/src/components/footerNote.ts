import { el } from './segmented';

export function renderFooterNote(lines: string[]): HTMLElement {
  const foot = el('footer', { className: 'page-footer' });
  for (const line of lines) {
    foot.appendChild(el('p', { text: line }));
  }
  return foot;
}
