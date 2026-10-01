import './styles/tokens.css';
import { renderSiteHeader } from './components/header';
import { renderStockHeader } from './components/stockHeader';
import { renderConsensusPage } from './pages/consensus';
import { el } from './components/segmented';
import type { ConsensusPage } from './lib/types';
import { onRouteChange, parseHash } from './router';

const app = document.querySelector<HTMLDivElement>('#app')!;

async function loadConsensus(ticker: string): Promise<ConsensusPage> {
  const url = `./data/pages/${ticker}/consensus.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`无法加载 ${url}（${res.status}）`);
  return res.json();
}

function renderWatchlist(): HTMLElement {
  const main = el('main', { className: 'main' });
  main.appendChild(
    el('div', { className: 'placeholder-page' }, [
      el('h2', { text: '观察池' }),
      el('p', {
        text: '当前已接入美光（MU）。点击下方进入分析师预期页，或在顶栏搜索框输入代码。',
      }),
      el('p', {}, [
        el('a', { href: '#/MU/consensus', text: 'MU · Micron Technology 美光科技 →' }),
      ]),
    ]),
  );
  return main;
}

function renderSources(): HTMLElement {
  const main = el('main', { className: 'main' });
  main.appendChild(
    el('div', { className: 'placeholder-page' }, [
      el('h2', { text: '数据说明' }),
      el('p', {
        text: '浏览器只读同源 JSON。每日由 GitHub Actions 抓取 Yahoo / SEC 等免费源，写入 data/ 并构建本站。抓取状态见 data/_status.json。',
      }),
      el('ul', {}, [
        el('li', { text: '未来共识：Yahoo earnings_estimate / revenue_estimate / eps_trend' }),
        el('li', { text: '已公布 EPS：Yahoo Reported EPS（Non-GAAP），新闻稿可 YAML 覆盖' }),
        el('li', { text: '已公布营收：SEC EDGAR XBRL' }),
        el('li', { text: '指引：config/companies/<TICKER>.yaml 手工录入' }),
        el('li', { text: '缺失字段显示 [ ]，禁止插值或编造' }),
      ]),
    ]),
  );
  return main;
}

function renderPlaceholder(ticker: string, tab: string): HTMLElement {
  const labels: Record<string, string> = {
    overview: '财报解读',
    statements: '财务报表',
    call: '电话会',
    price: '股价反应',
  };
  const main = el('main', { className: 'main' });
  main.appendChild(
    el('div', { className: 'placeholder-page' }, [
      el('h2', { text: `${labels[tab] ?? tab}（占位）` }),
      el('p', { text: `${ticker} 的此页面尚未实现。请先查看分析师预期。` }),
      el('p', {}, [el('a', { href: `#/${ticker}/consensus`, text: '前往分析师预期 →' })]),
    ]),
  );
  return main;
}

async function render() {
  const route = parseHash();
  app.replaceChildren();

  if (route.name === 'watchlist') {
    app.append(renderSiteHeader('watchlist'), renderWatchlist());
    return;
  }
  if (route.name === 'sources') {
    app.append(renderSiteHeader('sources'), renderSources());
    return;
  }
  if (route.name === 'notfound') {
    app.append(
      renderSiteHeader(),
      el('div', { className: 'error-box', text: '页面不存在。返回观察池。' }),
    );
    return;
  }

  app.append(renderSiteHeader(), el('div', { className: 'loading-box', text: '加载中…' }));
  try {
    const data = await loadConsensus(route.ticker);
    app.replaceChildren();
    app.append(renderSiteHeader(), renderStockHeader(data, route.name === 'consensus' ? 'consensus' : route.tab));
    if (route.name === 'consensus') {
      app.append(renderConsensusPage(data));
    } else {
      app.append(renderPlaceholder(route.ticker, route.tab));
    }
  } catch (err) {
    app.replaceChildren();
    app.append(
      renderSiteHeader(),
      el('div', {
        className: 'error-box',
        text: err instanceof Error ? err.message : '加载失败',
      }),
      el('div', { className: 'placeholder-page' }, [
        el('p', { text: '目前样例数据仅覆盖 MU。' }),
        el('a', { href: '#/MU/consensus', text: '打开 MU 分析师预期' }),
      ]),
    );
  }
}

if (!location.hash || location.hash === '#') {
  location.hash = '#/MU/consensus';
}

onRouteChange(() => {
  void render();
});
void render();
