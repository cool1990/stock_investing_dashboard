import type { ConsensusPage, HistoryRow, MetricKind, PeriodKind } from '../../lib/types';
import { colorForSignedText, formatEps, formatPct, formatRev } from '../../lib/fmt';
import { el } from '../../components/segmented';

function fmt(metric: MetricKind, v: number | null): string {
  return metric === 'eps' ? formatEps(v) : formatRev(v);
}

export function renderHistoryTiles(
  data: ConsensusPage,
  metric: MetricKind,
  period: PeriodKind,
): HTMLElement {
  const block = data.history[metric];
  const tiles =
    period === 'q'
      ? [
          { k: '超预期次数', v: block.stats_q.beat_count, sub: block.stats_q.beat_sub },
          { k: '平均超预期（8 季）', v: block.stats_q.avg_surprise, sub: block.stats_q.avg_surprise_sub },
          { k: '实际 vs 指引中值', v: block.stats_q.vs_guide, sub: block.stats_q.vs_guide_sub },
          { k: '共识 vs 指引', v: block.stats_q.cons_vs_guide, sub: block.stats_q.cons_vs_guide_sub },
        ]
      : [
          { k: 'FY26 实际 vs 共识', v: block.stats_y.fy26_vs_cons, sub: block.stats_y.fy26_sub },
          { k: 'FY25 实际 vs 共识', v: block.stats_y.fy25_vs_cons, sub: block.stats_y.fy25_sub },
          { k: '年度指引', v: '无', sub: '美光只给下季指引' },
          { k: '次日股价（年报季）', v: '[±x%]', sub: '见「股价反应」' },
        ];

  const wrap = el('div', { className: 'history-tiles' });
  for (const t of tiles) {
    const v = el('div', { className: 'stat-card__v lg', text: t.v });
    v.style.color = colorForSignedText(t.v);
    wrap.appendChild(
      el('div', { className: 'stat-card', style: 'padding:14px 16px' }, [
        el('div', { className: 'stat-card__k', text: t.k }),
        v,
        el('div', { className: 'stat-card__k', text: t.sub }),
      ]),
    );
  }
  return wrap;
}

export function renderHistoryChart(
  rows: HistoryRow[],
  metric: MetricKind,
): HTMLElement {
  let hmax = 0;
  for (const r of rows) {
    for (const x of [r.consensus, r.actual, r.guide]) {
      if (x !== null) hmax = Math.max(hmax, x);
    }
  }
  hmax = hmax || 1;

  const card = el('div', { className: 'card', style: 'padding:20px' });
  card.appendChild(
    el('div', { className: 'legend-row', style: 'margin-bottom:10px' }, [
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:12px;height:12px;background:#9DB5F2;border-radius:2px;display:inline-block',
        }),
        document.createTextNode('实际'),
      ]),
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:16px;height:0;border-top:3px solid #1E3A8A;display:inline-block',
        }),
        document.createTextNode('发布前共识'),
      ]),
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:16px;height:0;border-top:3px dashed #C2410C;display:inline-block',
        }),
        document.createTextNode('上季给的指引中值'),
      ]),
      document.createTextNode('柱顶数字 = 较共识'),
    ]),
  );

  const bars = el('div', {
    style: 'display:flex;gap:12px;align-items:flex-end;height:240px;border-bottom:1px solid var(--axis);padding:0 1%',
  });
  rows.forEach((r, i) => {
    const hh = (r.actual / hmax) * 200;
    const col = el('div', {
      style: 'flex:1;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center',
    });
    col.appendChild(
      el('span', {
        className: 'mono',
        style: 'font-size:12px;font-weight:600;color:var(--up);margin-bottom:4px',
        text: r.consensus === null ? '—' : formatPct(r.actual, r.consensus),
      }),
    );
    const bar = el('div', {
      style: `position:relative;width:56%;max-width:64px;height:${hh}px;background:${i === rows.length - 1 ? '#1D4ED8' : '#9DB5F2'};border-radius:4px 4px 0 0`,
    });
    if (r.consensus !== null) {
      bar.appendChild(
        el('div', {
          style: `position:absolute;left:-8px;right:-8px;bottom:${(r.consensus / hmax) * 200}px;border-top:3px solid #1E3A8A`,
        }),
      );
    }
    if (r.guide !== null) {
      bar.appendChild(
        el('div', {
          style: `position:absolute;left:-12px;right:-12px;bottom:${(r.guide / hmax) * 200}px;border-top:3px dashed #C2410C`,
        }),
      );
    }
    col.appendChild(bar);
    bars.appendChild(col);
  });
  card.appendChild(bars);

  const labels = el('div', { style: 'display:flex;gap:12px;padding:8px 1% 0' });
  for (const r of rows) {
    labels.appendChild(
      el('span', {
        className: 'mono',
        style: 'flex:1;text-align:center;font-size:12px;color:var(--muted)',
        text: r.period,
      }),
    );
  }
  card.appendChild(labels);
  void metric;
  return card;
}

export function renderHistoryTable(
  data: ConsensusPage,
  metric: MetricKind,
  period: PeriodKind,
): HTMLElement {
  const rows = [...data.history[metric][period]].reverse();
  const isY = period === 'y';
  const note = isY ? data.history[metric].note_y : data.history[metric].note_q;

  const card = el('div', { className: 'card', style: 'padding:8px 20px 16px;overflow-x:auto' });
  const table = el('table', { className: 'data', style: 'min-width:1000px' });
  const headers = [
    '期间',
    '发布日',
    metric === 'eps' ? 'EPS 共识' : '营收共识',
    '实际',
    '超预期',
    '指引（中值）',
    '相对指引',
    '次日股价',
  ];
  const hr = el('tr');
  headers.forEach((h, i) =>
    hr.appendChild(el('th', { className: i < 2 ? 'left' : undefined, text: h })),
  );
  table.appendChild(el('thead', {}, [hr]));
  const tbody = el('tbody');
  for (const r of rows) {
    const diff =
      r.secondary !== null && r.consensus !== null
        ? Math.abs(r.consensus / r.secondary - 1) * 100
        : 0;
    const warn = diff > 3;
    const consTxt =
      r.consensus === null ? '[ ]' : `${fmt(metric, r.consensus)}${warn ? ' ⚠' : ''}`;
    const consTd = el('td', {
      className: warn ? 'warn' : undefined,
      text: consTxt,
      title: warn
        ? `主源 ${fmt(metric, r.consensus)} · 次源 ${fmt(metric, r.secondary)}`
        : undefined,
    });
    const surprise = r.consensus === null ? '—' : formatPct(r.actual, r.consensus);
    const guideTxt =
      r.guide === null ? (isY ? '无年度指引' : '[ ]') : fmt(metric, r.guide);
    const vsGuide = r.guide === null ? '—' : formatPct(r.actual, r.guide);
    const next =
      r.next_day === null ? '[±x%]' : formatPct(1 + r.next_day, 1);

    const tr = el('tr', {}, [
      el('td', { className: 'left bold', text: r.period }),
      el('td', { className: 'left', style: 'color:var(--muted)', text: r.release_date }),
      consTd,
      el('td', { className: 'bold', text: fmt(metric, r.actual) }),
      el('td', { className: 'bold', text: surprise }),
      el('td', { className: r.guide === null ? 'faint' : undefined, text: guideTxt }),
      el('td', { className: 'bold', text: vsGuide }),
      el('td', { className: 'faint', text: next }),
    ]);
    for (const td of tr.querySelectorAll('td')) {
      const t = td.textContent || '';
      if (t.startsWith('+')) td.classList.add('up');
      if (t.startsWith('−')) td.classList.add('down');
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  card.append(table, el('div', { className: 'footnote', text: note }));
  return card;
}
