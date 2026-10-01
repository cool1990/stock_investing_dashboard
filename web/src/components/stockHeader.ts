import type { ConsensusPage } from '../lib/types';
import { el } from './segmented';

function metric(label: string, value: string, sub: string): HTMLElement {
  return el('div', { className: 'metric' }, [
    el('div', { className: 'metric__label', text: label }),
    el('div', { className: 'metric__value', text: value }),
    el('div', { className: 'metric__sub', text: sub }),
  ]);
}

function placeholder(v: unknown, fallback = '[ ]'): string {
  if (v === null || v === undefined || v === '') return fallback;
  return String(v);
}

export function renderStockHeader(data: ConsensusPage, activeTab: string): HTMLElement {
  const m = data.meta;
  const h = m.header;
  const section = el('section', { className: 'stock-header' });
  const inner = el('div', { className: 'stock-header__inner page-shell' });

  const timing = m.release_timing === 'after_close' ? '盘后发布' : '盘前发布';
  const titleRow = el('div', { className: 'stock-header__title-row' }, [
    el('div', { className: 'stock-header__names' }, [
      el('h1', { text: m.ticker }),
      el('span', { className: 'name', text: `${m.name_en} ${m.name_zh}` }),
      el('span', { className: 'chip', text: `${m.exchange} · ${m.sector}` }),
    ]),
    el('div', { className: 'stock-header__meta' }, [
      document.createTextNode(`最新财报 `),
      el('b', { text: m.latest_report }),
      document.createTextNode(` · ${m.latest_report_date} ${timing}`),
      el('br'),
      document.createTextNode(`数据更新 [${m.updated_at_bj} 北京]`),
    ]),
  ]);

  const grid = el('div', { className: 'metrics-grid' }, [
    metric('股价', placeholder(h.price, '[$xxx.xx]'), `1D ${placeholder(h.price_1d, '[±x%]')} · YTD ${placeholder(h.price_ytd, '[±x%]')}`),
    metric('市值', placeholder(h.market_cap, '[$xxxB]'), '股价 × 总股本'),
    metric('EV 企业价值', placeholder(h.ev, '[$xxxB]'), `市值 − 净现金 $${h.net_cash_b ?? '[ ]'}B`),
    metric('Forward PE（NTM）', placeholder(h.forward_pe_ntm, '[x.x]'), '股价 ÷ 未来 4 季共识 EPS'),
    metric('做空比例', placeholder(h.short_interest, '[x.x%]'), '占流通股 · 半月更新'),
    metric('下次财报', placeholder(h.next_earnings, '[2026-12-xx]'), `隐含波动 ${placeholder(h.implied_move, '[±x%]')}`),
  ]);

  const more = el('details', { className: 'more-metrics' });
  more.appendChild(el('summary', { text: '更多指标 ▾' }));
  const panel = el('div', { className: 'more-metrics__panel' }, [
    metric('52 周区间', placeholder(h.week52, '[xx – xxx]'), '距高点 [−x%]'),
    metric('EV / EBITDA（NTM）', placeholder(h.ev_ebitda_ntm, '[x.x]'), ''),
    metric('股息', h.dividend_quarterly != null ? `$${h.dividend_quarterly} / 季` : '[ ]', `股息率 ${placeholder(h.dividend_yield, '[x.x%]')}`),
    metric('分析师目标价', placeholder(h.target_price, '[$xxx]'), placeholder(h.ratings, '买入 [x] · 持有 [x] · 卖出 [x]')),
    metric('机构 / 内部人持股', placeholder(h.inst_insider, '[xx%] / [x%]'), '90 天内部人净买入 [ ]'),
    metric('空头回补天数', placeholder(h.days_to_cover, '[x.x]'), '上期 [x.x]'),
  ]);
  const tip = el('div', {
    className: 'footnote',
    style: 'grid-column:1/-1;padding:8px 14px 4px;border-top:1px solid var(--line-2);margin-top:4px',
    text: '字段在 config/companies/MU.yaml 中增减',
  });
  panel.appendChild(tip);
  more.appendChild(panel);
  grid.appendChild(more);

  const tabs = [
    { id: 'overview', label: '财报解读', href: `#/${m.ticker}/overview` },
    { id: 'statements', label: '财务报表', href: `#/${m.ticker}/statements` },
    { id: 'call', label: '电话会', href: `#/${m.ticker}/call` },
    { id: 'consensus', label: '分析师预期', href: `#/${m.ticker}/consensus` },
    { id: 'price', label: '股价反应', href: `#/${m.ticker}/price` },
  ];
  const nav = el('nav', { className: 'stock-tabs', 'aria-label': '个股页面' });
  for (const t of tabs) {
    nav.appendChild(
      el('a', {
        href: t.href,
        ...(activeTab === t.id ? { 'aria-current': 'page' } : {}),
        text: t.label,
      }),
    );
  }

  inner.append(
    el('div', { className: 'breadcrumb' }, [
      el('a', { href: '#/', text: '观察池' }),
      document.createTextNode(' / '),
      document.createTextNode(m.ticker),
    ]),
    titleRow,
    grid,
    nav,
  );
  section.appendChild(inner);
  return section;
}
