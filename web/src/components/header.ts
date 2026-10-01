import { el } from './segmented';

export function renderSiteHeader(active: 'watchlist' | 'sources' | 'none' = 'none'): HTMLElement {
  const header = el('header', { className: 'site-header' });
  const inner = el('div', { className: 'site-header__inner page-shell' });

  const brand = el('a', { className: 'site-header__brand', href: '#/' }, ['财报台']);
  const nav = el('nav', { className: 'site-header__nav', 'aria-label': '全站' }, [
    el('a', {
      href: '#/',
      ...(active === 'watchlist' ? { 'aria-current': 'page' } : {}),
    }, ['观察池']),
    el('a', {
      href: '#/sources',
      ...(active === 'sources' ? { 'aria-current': 'page' } : {}),
    }, ['数据说明']),
  ]);

  const search = el('label', { className: 'site-header__search' });
  search.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8A93A0" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>`;
  const input = el('input', {
    type: 'text',
    placeholder: '输入代码进入个股，如 NVDA',
    'aria-label': '搜索股票代码',
  }) as HTMLInputElement;
  input.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter') return;
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;
    location.hash = `#/${ticker}/consensus`;
  });
  search.appendChild(input);

  inner.append(brand, nav, el('div', { className: 'site-header__spacer' }), search);
  header.appendChild(inner);
  return header;
}
