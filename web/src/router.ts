export type Route =
  | { name: 'watchlist' }
  | { name: 'sources' }
  | { name: 'consensus'; ticker: string }
  | { name: 'placeholder'; ticker: string; tab: string }
  | { name: 'notfound' };

export function parseHash(hash: string = location.hash): Route {
  const raw = (hash || '#/').replace(/^#/, '') || '/';
  const parts = raw.split('/').filter(Boolean);
  if (parts.length === 0) return { name: 'watchlist' };
  if (parts[0] === 'sources') return { name: 'sources' };
  if (parts.length === 1) {
    return { name: 'consensus', ticker: parts[0].toUpperCase() };
  }
  const ticker = parts[0].toUpperCase();
  const tab = parts[1];
  if (tab === 'consensus') return { name: 'consensus', ticker };
  if (['overview', 'statements', 'call', 'price'].includes(tab)) {
    return { name: 'placeholder', ticker, tab };
  }
  return { name: 'notfound' };
}

export function onRouteChange(handler: () => void): void {
  window.addEventListener('hashchange', handler);
}
