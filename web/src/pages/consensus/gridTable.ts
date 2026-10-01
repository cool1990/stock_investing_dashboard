import type { ConsensusPage, GrowthKind, MetricKind } from '../../lib/types';
import { formatGrowth, formatNum } from '../../lib/fmt';
import { el } from '../../components/segmented';

function buildTable(
  years: string[],
  estYears: Set<string>,
  labels: string[],
  grid: Record<string, Array<number | null>>,
  mode: 'value' | 'growth',
  growth: GrowthKind,
): HTMLTableElement {
  const table = el('table', { className: 'data' }) as HTMLTableElement;
  const thead = el('thead');
  const hr = el('tr');
  hr.appendChild(el('th', { className: 'left', text: '' }));
  for (const y of years) {
    hr.appendChild(el('th', { text: estYears.has(y) ? `${y}E` : y }));
  }
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = el('tbody');
  labels.forEach((lab, k) => {
    const tr = el('tr');
    const isTot = k === 4;
    tr.appendChild(el('td', { className: `left${isTot ? ' bold' : ''}`, text: lab }));
    years.forEach((y, i) => {
      const v = grid[y]?.[k] ?? null;
      let text: string;
      let colorClass = '';
      if (mode === 'value') {
        text = formatNum(v);
        if (v === null) colorClass = 'faint';
      } else {
        let base: number | null | undefined;
        if (growth === 'yoy' || isTot) {
          base = i ? grid[years[i - 1]]?.[k] : undefined;
        } else {
          base = k ? grid[y]?.[k - 1] : i ? grid[years[i - 1]]?.[3] : undefined;
        }
        text = formatGrowth(v, base);
        if (text.startsWith('+')) colorClass = 'up';
        else if (text.startsWith('−')) colorClass = 'down';
        else if (text === 'n.m.' || text === '[ ]') colorClass = 'faint';
      }
      const classes = [
        estYears.has(y) ? 'est' : '',
        isTot ? 'bold' : '',
        colorClass,
      ]
        .filter(Boolean)
        .join(' ');
      tr.appendChild(el('td', { className: classes || undefined, text }));
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

export function renderValueGrowthTables(
  data: ConsensusPage,
  metric: MetricKind,
  growth: GrowthKind,
): { values: HTMLElement; growthEl: HTMLElement; unit: string } {
  const years = data.future.years;
  const est = new Set(data.future.est_years);
  const labels = data.meta.quarter_labels;
  const grid = metric === 'eps' ? data.future.eps : data.future.rev;

  const values = el('div', { className: 'card' }, [
    el('div', { className: 'card__head' }, [
      el('div', { className: 'card__title', text: '数值' }),
      el('div', {
        className: 'card__unit',
        text: metric === 'eps' ? '美元 / 股 · 调整后（Non-GAAP）' : '十亿美元',
      }),
    ]),
  ]);
  const vw = el('div', { className: 'table-wrap' });
  vw.appendChild(buildTable(years, est, labels, grid, 'value', growth));
  values.appendChild(vw);

  const growthEl = el('div', { className: 'card' });
  return { values, growthEl, unit: metric === 'eps' ? 'eps' : 'rev' };
}

export function renderGrowthCard(
  data: ConsensusPage,
  metric: MetricKind,
  growth: GrowthKind,
  control: HTMLElement,
): HTMLElement {
  const years = data.future.years;
  const est = new Set(data.future.est_years);
  const labels = data.meta.quarter_labels;
  const grid = metric === 'eps' ? data.future.eps : data.future.rev;
  const card = el('div', { className: 'card' }, [
    el('div', { className: 'card__head' }, [
      el('div', { className: 'card__title', text: '增速' }),
      control,
    ]),
  ]);
  const wrap = el('div', { className: 'table-wrap' });
  wrap.appendChild(buildTable(years, est, labels, grid, 'growth', growth));
  card.appendChild(wrap);
  return card;
}

export function renderValuesCard(data: ConsensusPage, metric: MetricKind): HTMLElement {
  const years = data.future.years;
  const est = new Set(data.future.est_years);
  const labels = data.meta.quarter_labels;
  const grid = metric === 'eps' ? data.future.eps : data.future.rev;
  const card = el('div', { className: 'card' }, [
    el('div', { className: 'card__head' }, [
      el('div', { className: 'card__title', text: '数值' }),
      el('div', {
        className: 'card__unit',
        text: metric === 'eps' ? '美元 / 股 · 调整后（Non-GAAP）' : '十亿美元',
      }),
    ]),
  ]);
  const wrap = el('div', { className: 'table-wrap' });
  wrap.appendChild(buildTable(years, est, labels, grid, 'value', 'yoy'));
  card.appendChild(wrap);
  return card;
}
