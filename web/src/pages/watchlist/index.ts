import { createSegmented, el } from '../../components/segmented';
import { renderKpiCard } from '../../components/kpiCard';
import { renderDataTable } from '../../components/dataTable';
import { renderAddStockLink } from '../../components/header';
import { displayValue } from '../../components/placeholder';
import { formatRatioChange } from '../../lib/fmt';
import { renderFooterNote } from '../../components/footerNote';

export interface WatchlistPage {
  as_of_bj: string;
  groups: Array<{ id: string; label: string }>;
  kpi: {
    red7d: { n: number | null; tickers: number | null };
    earn30d: { n: number | null; next: { t: string; d: string | null } | null };
    rev30d: { up: number | null; down: number | null };
    todo: number | null;
  };
  stocks: Array<{
    t: string;
    name: string;
    group: string;
    sub: string;
    has_page: boolean;
    price: number | null;
    d1: number | null;
    d1_tone: string;
    ytd: number | null;
    ytd_tone: string;
    mcap: string | null;
    ntm_eps: number | null;
    rev30: number | null;
    rev30_tone: string;
    fpe: number | null;
    short: number | null;
    short_date: string | null;
    last: { d: string | null; q: string | null; eps_surp: number | null; eps_surp_tone: string };
    react: number | null;
    react_tone: string;
    next: { d: string | null; approx: string | null };
    red7d: number | null;
  }>;
  news: Array<{
    d: string | null;
    t: string;
    type: string;
    title: string | null;
    why: string | null;
    red: boolean;
    url: string | null;
  }>;
  calendar: Array<{
    d: string | null;
    t: string;
    timing: string;
    q: string;
    cons_eps: number | null;
    iv: number | null;
  }>;
  recent: Array<{
    d: string;
    t: string;
    q: string;
    eps_surp: number | null;
    eps_surp_tone: string;
    rev_surp: number | null;
    rev_surp_tone: string;
  }>;
}

export function renderWatchlistPage(
  data: WatchlistPage,
  opts: { filterQuery?: string; onFilter?: (q: string) => void } = {},
): HTMLElement {
  let group = 'all';
  let newsMode: 'red' | 'all' = 'red';
  let filterQuery = opts.filterQuery ?? '';

  const root = el('main', { className: 'main watchlist-page' });

  const paint = () => {
    root.replaceChildren();

    const head = el('div', { className: 'watchlist-head' });
    const titleRow = el('div', { className: 'watchlist-head__row' }, [
      el('div', {}, [
        el('h1', { className: 'watchlist-title', text: '观察池' }),
        el('div', {
          className: 'section__sub',
          text: `${data.stocks.length} 只股票 · 数据截至 ${data.as_of_bj} 北京`,
        }),
      ]),
      el('div', { className: 'watchlist-head__actions' }, [
        createSegmented(
          '分组',
          data.groups.map((g) => ({ value: g.id, label: g.label })),
          group,
          (v) => {
            group = v;
            paint();
          },
        ),
        renderAddStockLink(),
      ]),
    ]);
    head.appendChild(titleRow);

    const stocks =
      group === 'all' ? data.stocks : data.stocks.filter((s) => s.group === group);
    const filtered = filterQuery
      ? stocks.filter((s) => s.t.startsWith(filterQuery) || s.name.toUpperCase().includes(filterQuery))
      : stocks;

    const kpiRow = el('div', { className: 'kpi-grid kpi-grid--4' }, [
      renderKpiCard({
        label: '红色公告（近 7 天）',
        value: data.kpi.red7d.n,
        sub: data.kpi.red7d.tickers != null ? `涉及 ${data.kpi.red7d.tickers} 只股票` : undefined,
        large: true,
      }),
      renderKpiCard({
        label: '未来 30 天财报',
        value: data.kpi.earn30d.n,
        sub: data.kpi.earn30d.next
          ? `最近 ${data.kpi.earn30d.next.t}${data.kpi.earn30d.next.d ? ` · ${data.kpi.earn30d.next.d}` : ''}`
          : undefined,
        large: true,
      }),
      renderKpiCard({
        label: 'EPS 预期上调 / 下调（30 天）',
        value:
          data.kpi.rev30d.up != null && data.kpi.rev30d.down != null
            ? `${data.kpi.rev30d.up} / ${data.kpi.rev30d.down}`
            : null,
        sub: '按 NTM 共识变化计',
        large: true,
      }),
      renderKpiCard({
        label: '待验证跟踪项',
        value: data.kpi.todo,
        sub: '来自各股「财报解读 · 本期关注」',
        large: true,
      }),
    ]);
    head.append(kpiRow);
    root.appendChild(head);

    const tableSection = el('section', { className: 'section' });
    tableSection.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '指标对比' }),
          el('div', { className: 'section__sub', text: '点击代码进入个股 · Forward PE 默认升序' }),
        ]),
      ]),
    );
    tableSection.appendChild(
      renderDataTable({
        headers: [
          { label: '代码 / 名称', align: 'left' },
          { label: '分组' },
          { label: '股价' },
          { label: '1D' },
          { label: 'YTD' },
          { label: '市值' },
          { label: 'NTM EPS' },
          { label: '修正 30D' },
          { label: 'Forward PE' },
          { label: '做空' },
          { label: '最近财报' },
          { label: '财报次日' },
          { label: '下次财报' },
          { label: '红色' },
        ],
        rows: filtered.map((s) => ({
          cells: [
            {
              text: s.has_page ? `${s.t} ${s.name}` : `${s.t} ${s.name}`,
              className: s.has_page ? 'wl-ticker wl-ticker--link' : 'wl-ticker wl-ticker--muted',
              title: s.has_page ? `进入 ${s.t}` : '个股页尚未接入',
            },
            { text: s.sub },
            { text: s.price != null ? `$${s.price.toFixed(2)}` : null },
            { text: s.d1 != null ? formatRatioChange(s.d1) : null, color: s.d1_tone },
            { text: s.ytd != null ? formatRatioChange(s.ytd) : null, color: s.ytd_tone },
            { text: s.mcap },
            { text: s.ntm_eps != null ? `$${s.ntm_eps.toFixed(2)}` : null },
            { text: s.rev30 != null ? formatRatioChange(s.rev30) : null, color: s.rev30_tone },
            { text: s.fpe != null ? s.fpe.toFixed(1) : null },
            { text: s.short != null ? `${(s.short * 100).toFixed(1)}%` : null },
            {
              text: s.last.q ? `${s.last.d ?? ''}\n${formatRatioChange(s.last.eps_surp)}` : s.last.d,
              color: s.last.eps_surp_tone,
            },
            { text: s.react != null ? formatRatioChange(s.react) : null, color: s.react_tone },
            { text: s.next.d ?? s.next.approx },
            {
              text: s.red7d != null && s.red7d > 0 ? String(s.red7d) : s.red7d === 0 ? '0' : null,
              className: s.red7d && s.red7d > 0 ? 'wl-red-badge' : '',
            },
          ],
        })),
      }),
    );
    root.appendChild(tableSection);

    const lower = el('div', { className: 'watchlist-lower' });

    const newsCard = el('div', { className: 'card watchlist-news' });
    newsCard.appendChild(
      el('div', { className: 'card__head' }, [
        el('span', { className: 'card__title', text: '公告与新闻' }),
        createSegmented(
          '公告筛选',
          [
            { value: 'red', label: '只看红色' },
            { value: 'all', label: '全部' },
          ],
          newsMode,
          (v) => {
            newsMode = v as 'red' | 'all';
            paint();
          },
        ),
      ]),
    );
    const newsList = el('div', { className: 'news-list' });
    const items = data.news.filter((n) => newsMode === 'all' || n.red).slice(0, 30);
    for (const n of items) {
      const row = el('article', { className: `news-item${n.red ? ' news-item--red' : ''}` });
      row.appendChild(el('div', { className: 'news-item__bar', 'aria-hidden': 'true' }));
      const body = el('div', { className: 'news-item__body' });
      const meta = el('div', { className: 'news-item__meta' }, [
        el('span', { className: 'mono', text: displayValue(n.d, '[日期]') }),
        el('span', { className: 'news-item__ticker', text: n.t }),
        el('span', { className: 'news-item__type', text: n.type }),
      ]);
      body.append(meta);
      const title = n.title ?? '[ ]';
      if (n.url) {
        body.appendChild(el('a', { className: 'news-item__title', href: n.url, target: '_blank', text: title }));
      } else {
        body.appendChild(el('div', { className: 'news-item__title', text: title }));
      }
      if (n.why) body.appendChild(el('div', { className: 'news-item__why', text: n.why }));
      row.appendChild(body);
      newsList.appendChild(row);
    }
    newsCard.appendChild(newsList);
    newsCard.appendChild(
      el('p', {
        className: 'footnote',
        text: '红色规则见 config/red_rules.yaml；8-K 2.02、Form 4 公开市场买入等。',
      }),
    );

    const side = el('div', { className: 'watchlist-side' });
    const calCard = el('div', { className: 'card' });
    calCard.appendChild(
      el('div', { className: 'card__head' }, [
        el('span', { className: 'card__title', text: '财报日历' }),
        el('span', { className: 'card__unit', text: '未来 60 天 · 北京' }),
      ]),
    );
    const calList = el('ul', { className: 'cal-list' });
    for (const c of data.calendar) {
      const timing = c.timing === 'after_close' ? '盘后' : '盘前';
      calList.appendChild(
        el('li', {
          text: `${displayValue(c.d, '[日期]')} ${timing} ${c.t} ${c.q} · 共识 EPS ${displayValue(c.cons_eps != null ? `$${c.cons_eps}` : null)}`,
        }),
      );
    }
    calCard.appendChild(calList);

    const recentCard = el('div', { className: 'card' });
    recentCard.appendChild(el('div', { className: 'card__head' }, [
      el('span', { className: 'card__title', text: '最近发布' }),
    ]));
    const recentList = el('ul', { className: 'recent-list' });
    for (const r of data.recent) {
      const li = el('li');
      const link = el('a', {
        href: `#/${r.t}/review/${r.q}`,
        text: `${r.d} ${r.t} ${r.q} · EPS ${formatRatioChange(r.eps_surp)} / 收入 ${formatRatioChange(r.rev_surp)} →`,
      });
      li.appendChild(link);
      recentList.appendChild(li);
    }
    recentCard.append(recentList);
    side.append(calCard, recentCard);

    lower.append(newsCard, side);
    root.append(lower);

    root.appendChild(
      renderFooterNote([
        'Forward PE = 股价 ÷ NTM 共识 EPS；最近财报列显示 EPS 超预期幅度。',
        '红色公告徽标仅统计近 7 天；数值缺失显示 [ ]。',
      ]),
    );

    root.querySelectorAll('.wl-ticker--link').forEach((cell) => {
      cell.addEventListener('click', () => {
        const t = cell.textContent?.split(' ')[0];
        if (t) location.hash = `#/${t}`;
      });
      (cell as HTMLElement).style.cursor = 'pointer';
    });
  };

  paint();
  return root;
}
