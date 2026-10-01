export type StockTab = 'review' | 'financials' | 'call' | 'consensus' | 'price';

export type Route =
  | { name: 'watchlist' }
  | { name: 'sources' }
  | { name: 'review'; ticker: string; period?: string }
  | { name: 'financials'; ticker: string }
  | { name: 'call'; ticker: string; period?: string }
  | { name: 'consensus'; ticker: string }
  | { name: 'price'; ticker: string }
  | { name: 'notfound' };

const LEGACY_TAB: Record<string, StockTab> = {
  overview: 'review',
  statements: 'financials',
};

export function parseHash(hash: string = location.hash): Route {
  const raw = (hash || '#/').replace(/^#/, '') || '/';
  const parts = raw.split('/').filter(Boolean);
  if (parts.length === 0) return { name: 'watchlist' };
  if (parts[0].toLowerCase() === 'sources') return { name: 'sources' };

  const ticker = parts[0].toUpperCase();
  if (parts.length === 1) {
    return { name: 'review', ticker };
  }

  let tab = parts[1].toLowerCase();
  tab = LEGACY_TAB[tab] ?? tab;

  if (tab === 'review') {
    const period = parts[2] || undefined;
    return { name: 'review', ticker, period };
  }
  if (tab === 'financials') return { name: 'financials', ticker };
  if (tab === 'call') {
    return { name: 'call', ticker, period: parts[2] || undefined };
  }
  if (tab === 'consensus') return { name: 'consensus', ticker };
  if (tab === 'price') return { name: 'price', ticker };

  return { name: 'notfound' };
}

export function routeTab(route: Route): StockTab | null {
  if (route.name === 'review') return 'review';
  if (route.name === 'financials') return 'financials';
  if (route.name === 'call') return 'call';
  if (route.name === 'consensus') return 'consensus';
  if (route.name === 'price') return 'price';
  return null;
}

export function onRouteChange(handler: () => void): void {
  window.addEventListener('hashchange', handler);
}
