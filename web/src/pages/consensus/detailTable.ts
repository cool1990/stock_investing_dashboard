import type { ConsensusPage, MetricKind } from '../../lib/types';
import { formatEps, formatPct, formatRev } from '../../lib/fmt';
import { el } from '../../components/segmented';

export function renderDetail(data: ConsensusPage, metric: MetricKind): HTMLElement {
  const rows = metric === 'eps' ? data.future.detail.eps : data.future.detail.rev;
  const note = metric === 'eps' ? data.future.detail.eps_note : data.future.detail.rev_note;
  const fmt = metric === 'eps' ? formatEps : formatRev;
  const isEps = metric === 'eps';

  const details = el('details', { className: 'details-card' });
  details.appendChild(el('summary', { text: '共识明细：区间、机构数、修正与指引 ▾' }));
  const wrap = el('div', { className: 'table-wrap', style: 'margin-top:8px' });
  const table = el('table', { className: 'data', style: 'min-width:1100px' });
  const headers = [
    '期间',
    '截止',
    '共识',
    '同比',
    '最低',
    '最高',
    '机构数',
    '较 7 天前',
    '较 30 天前',
    '较 60 天前',
    '较 90 天前',
    '上调 / 下调（30 天）',
    '指引中值',
    '共识 vs 指引',
  ];
  const hr = el('tr');
  headers.forEach((h, i) => hr.appendChild(el('th', { className: i === 0 ? 'left' : undefined, text: h })));
  table.appendChild(el('thead', {}, [hr]));
  const tbody = el('tbody');
  for (const r of rows) {
    const trTrend = (old: number | null) => (!isEps ? '不可得' : formatPct(r.avg, old));
    const cells = [
      el('td', { className: 'left bold', text: r.period }),
      el('td', { className: 'faint', style: 'color:var(--muted)', text: r.end }),
      el('td', { className: 'bold', text: fmt(r.avg) }),
      el('td', { text: formatPct(r.avg, r.year_ago) }),
      el('td', { text: fmt(r.low) }),
      el('td', { text: fmt(r.high) }),
      el('td', { text: String(r.n) }),
      el('td', { text: trTrend(r.trend.d7) }),
      el('td', { text: trTrend(r.trend.d30) }),
      el('td', { text: trTrend(r.trend.d60) }),
      el('td', { text: trTrend(r.trend.d90) }),
      el('td', {
        text: !isEps
          ? '不可得'
          : `${r.revisions.up30 ?? '[ ]'} / ${r.revisions.down30 ?? '[ ]'}`,
      }),
      el('td', {
        className: r.guide === null ? 'faint' : undefined,
        text: r.guide === null ? '无' : fmt(r.guide),
      }),
      el('td', {
        className: 'bold',
        text: r.guide === null ? '—' : formatPct(r.avg, r.guide),
      }),
    ];
    // color signed pct cells
    for (const td of cells) {
      const t = td.textContent || '';
      if (t.startsWith('+')) td.classList.add('up');
      if (t.startsWith('−')) td.classList.add('down');
      if (t === '不可得' || t === '[ ]' || t === '—') td.classList.add('faint');
    }
    tbody.appendChild(el('tr', {}, cells));
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  details.append(wrap, el('div', { className: 'footnote', text: note }));
  return details;
}
