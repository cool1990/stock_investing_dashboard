import './styles/tokens.css';
import './styles/base.css';
import { renderSiteHeader } from './components/header';
import { renderStockHeader } from './components/stockHeader';
import { renderConsensusPage } from './pages/consensus';
import { renderWatchlistPage } from './pages/watchlist';
import { renderReviewPage } from './pages/review';
import { renderFinancialsPage } from './pages/financials';
import { renderCallPage } from './pages/call';
import { renderPricePage } from './pages/price';
import { renderSourcesPage } from './pages/sources';
import { loadJson, sampleOrPage } from './lib/load';
import type { ConsensusPage, StockMeta } from './lib/types';
import { el } from './components/segmented';
import { onRouteChange, parseHash, routeTab, type Route } from './router';

const app = document.querySelector<HTMLDivElement>('#app')!;

let watchlistFilter = '';

async function loadStockMeta(ticker: string, fallback?: StockMeta): Promise<StockMeta> {
  try {
    const h = await loadJson<StockMeta>(sampleOrPage('stockHeader', ticker));
    return { ...h, ticker: h.ticker || ticker };
  } catch {
    if (fallback) return { ...fallback, ticker };
    throw new Error(`无法加载 ${ticker} 的页头数据`);
  }
}

async function loadRouteData(route: Route): Promise<unknown> {
  switch (route.name) {
    case 'watchlist':
      return loadJson(sampleOrPage('watchlist'));
    case 'sources':
      return loadJson(sampleOrPage('sources'));
    case 'review':
      return loadJson(sampleOrPage('review', route.ticker));
    case 'financials':
      return loadJson(sampleOrPage('financials', route.ticker));
    case 'call':
      return loadJson(sampleOrPage('call', route.ticker));
    case 'consensus':
      return loadJson<ConsensusPage>(sampleOrPage('consensus', route.ticker));
    case 'price':
      return loadJson(sampleOrPage('price', route.ticker));
    default:
      return null;
  }
}

function renderPage(route: Route, data: unknown): HTMLElement {
  switch (route.name) {
    case 'watchlist':
      return renderWatchlistPage(data as Parameters<typeof renderWatchlistPage>[0], {
        filterQuery: watchlistFilter,
      });
    case 'sources':
      return renderSourcesPage(data as Parameters<typeof renderSourcesPage>[0]);
    case 'review':
      return renderReviewPage(data as Parameters<typeof renderReviewPage>[0], route.ticker);
    case 'financials':
      return renderFinancialsPage(data as Parameters<typeof renderFinancialsPage>[0]);
    case 'call':
      return renderCallPage(data as Parameters<typeof renderCallPage>[0], route.ticker);
    case 'consensus':
      return renderConsensusPage(data as ConsensusPage);
    case 'price':
      return renderPricePage(data as Parameters<typeof renderPricePage>[0]);
    default:
      return el('div', { className: 'error-box', text: '页面不存在' });
  }
}

async function render() {
  const route = parseHash();
  app.replaceChildren();

  if (route.name === 'notfound') {
    app.append(
      renderSiteHeader(),
      el('div', { className: 'error-box', text: '页面不存在。返回观察池。' }),
      el('div', { className: 'placeholder-page' }, [el('a', { href: '#/', text: '观察池' })]),
    );
    return;
  }

  const isStock = routeTab(route) != null;
  const siteActive =
    route.name === 'watchlist' ? 'watchlist' : route.name === 'sources' ? 'sources' : 'none';

  if (!isStock) {
    if (route.name === 'watchlist' || route.name === 'sources') {
      try {
        const data = await loadRouteData(route);
        app.append(
          renderSiteHeader(siteActive, {
            onWatchlistFilter: (q) => {
              watchlistFilter = q;
              if (route.name === 'watchlist') void render();
            },
          }),
          renderPage(route, data),
        );
      } catch (err) {
        app.append(
          renderSiteHeader(siteActive),
          el('div', {
            className: 'error-box',
            text: err instanceof Error ? err.message : '加载失败',
          }),
        );
      }
      return;
    }
  }

  app.append(renderSiteHeader(siteActive), el('div', { className: 'loading-box', text: '加载中…' }));
  try {
    if (route.name === 'watchlist' || route.name === 'sources') return;
    const stockRoute = route as Extract<Route, { ticker: string }>;
    const data = await loadRouteData(stockRoute);
    let meta: StockMeta | undefined;
    if (stockRoute.name === 'consensus') {
      meta = (data as ConsensusPage).meta;
    }
    const stockMeta = await loadStockMeta(stockRoute.ticker, meta);
    const tab = routeTab(stockRoute)!;
    app.replaceChildren();
    app.append(
      renderSiteHeader(siteActive),
      renderStockHeader(stockMeta, tab),
      renderPage(stockRoute, data),
    );
  } catch (err) {
    app.replaceChildren();
    app.append(
      renderSiteHeader(siteActive),
      el('div', {
        className: 'error-box',
        text: err instanceof Error ? err.message : '加载失败',
      }),
      el('div', { className: 'placeholder-page' }, [
        el('p', { text: '目前样例数据主要覆盖 MU。' }),
        el('a', { href: '#/MU', text: '打开 MU 财报解读' }),
      ]),
    );
  }
}

if (!location.hash || location.hash === '#') {
  location.hash = '#/';
}

onRouteChange(() => {
  void render();
});
void render();
