import { el } from './segmented';

export function renderBanner(text: string): HTMLElement {
  return el('div', { className: 'banner', role: 'note' }, [
    el('span', {
      className: 'banner__icon',
      'aria-hidden': 'true',
      text: 'i',
    }),
    el('span', { text }),
  ]);
}
