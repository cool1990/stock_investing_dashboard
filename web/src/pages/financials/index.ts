import { createSegmented, el } from '../../components/segmented';
import { createToggleChip } from '../../components/toggleChip';
import { renderDataTable, type Row } from '../../components/dataTable';
import { renderFooterNote } from '../../components/footerNote';
import { renderBanner } from '../../components/banner';
import { formatAmtMillions, formatRatioChange, MISSING } from '../../lib/fmt';

type Stmt = 'is' | 'bs' | 'cf' | 'eq';
type Period = 'q' | 'ytd' | 'y';

interface FinRow {
  kind: string;
  name: string;
  fmt: string;
  v: (number | null)[];
  yoy: (number | null)[];
  qoq: (number | null)[];
  formula: string | null;
}

interface FinTable {
  title: string;
  cols: string[];
  col_end?: string[];
  rows: FinRow[];
  note: string;
}

export interface FinancialsPage {
  tables: Record<Stmt, Partial<Record<Period, FinTable | Record<string, never>>>>;
  mode_notes: Record<string, string>;
}

const STMT_LABELS: Record<Stmt, string> = {
  is: '利润表',
  bs: '资产负债表',
  cf: '现金流量表',
  eq: '股东权益表',
};

function fmtCell(v: number | null, fmt: string, unit: 'M' | 'B'): string {
  if (v == null) return MISSING;
  if (fmt === 'amt') return formatAmtMillions(v, unit);
  if (fmt === 'pct') return `${(v <= 1.5 ? v * 100 : v).toFixed(1)}%`;
  if (fmt === 'eps') return `$${v.toFixed(2)}`;
  if (fmt === 'days') return String(Math.round(v));
  return String(v);
}

function fmtDelta(v: number | null, fmt: string): string {
  if (v == null) return '—';
  if (fmt === 'pct') return formatRatioChange(v, { asPp: true });
  if (fmt === 'days') {
    const sign = v >= 0 ? '+' : '−';
    return `${sign}${Math.abs(Math.round(v))} 天`;
  }
  return formatRatioChange(v);
}

function sliceTable(table: FinTable, range: '5' | '12' | 'all'): FinTable {
  if (range === 'all' || table.cols.length <= 5) return table;
  const n = range === '5' ? 5 : 12;
  const start = Math.max(0, table.cols.length - n);
  return {
    ...table,
    cols: table.cols.slice(start),
    col_end: table.col_end?.slice(start),
    rows: table.rows.map((r) => ({
      ...r,
      v: r.v.slice(start),
      yoy: r.yoy.slice(start),
      qoq: r.qoq.slice(start),
    })),
  };
}

export function renderFinancialsPage(data: FinancialsPage): HTMLElement {
  let stmt: Stmt = 'is';
  let period: Period = 'q';
  let unit: 'M' | 'B' = 'M';
  let range: '5' | '12' | 'all' = '5';
  let showYoy = true;
  let showQoq = true;
  let hideEmpty = true;

  const root = el('main', { className: 'main financials-page' });

  const paint = () => {
    root.replaceChildren();
    root.appendChild(renderBanner('单季流量科目由 10-Q 累计相减；资产负债表取季末余额。'));

    const modeKey =
      (stmt === 'bs' || stmt === 'eq') && period === 'ytd' ? 'bs_ytd' : period;
    const modeNote = data.mode_notes[modeKey] ?? data.mode_notes.q ?? '';

    const toolbar = el('div', { className: 'fin-controls' });
    toolbar.append(
      createSegmented(
        '报表',
        (['is', 'bs', 'cf', 'eq'] as Stmt[]).map((k) => ({ value: k, label: STMT_LABELS[k] })),
        stmt,
        (v) => {
          stmt = v as Stmt;
          paint();
        },
      ),
      createSegmented(
        '期间',
        [
          { value: 'q', label: '单季' },
          { value: 'ytd', label: '累计' },
          { value: 'y', label: '年度' },
        ],
        period,
        (v) => {
          period = v as Period;
          paint();
        },
      ),
      createSegmented(
        '范围',
        [
          { value: '5', label: '最近 5 期' },
          { value: '12', label: '最近 12 期' },
          { value: 'all', label: '全部' },
        ],
        range,
        (v) => {
          range = v as typeof range;
          paint();
        },
      ),
      createSegmented(
        '单位',
        [
          { value: 'M', label: '$M' },
          { value: 'B', label: '$B' },
        ],
        unit,
        (v) => {
          unit = v as 'M' | 'B';
          paint();
        },
      ),
      createToggleChip('同比', showYoy, (n) => {
        showYoy = n;
        paint();
      }),
      createToggleChip(
        '环比',
        showQoq,
        (n) => {
          showQoq = n;
          paint();
        },
        period !== 'q',
      ),
      createToggleChip('隐藏全空行', hideEmpty, (n) => {
        hideEmpty = n;
        paint();
      }),
      el('button', { type: 'button', className: 'toggle-chip fin-export', text: '导出 CSV' }),
    );
    root.appendChild(toolbar);
    root.appendChild(el('p', { className: 'fin-mode-note', text: modeNote }));

    const raw = data.tables[stmt]?.[period] as FinTable | undefined;
    const card = el('div', { className: 'card' });
    if (!raw?.cols?.length) {
      card.appendChild(el('p', { className: 'faint', text: '该视图暂无样例数据。' }));
      root.appendChild(card);
      return;
    }

    const block = sliceTable(raw, range);
    card.appendChild(
      el('div', { className: 'card__head' }, [
        el('span', { className: 'card__title', text: block.title }),
        el('span', { className: 'card__unit', text: unit === 'M' ? '单位：$ 百万' : '单位：$ 十亿' }),
      ]),
    );

    const headers: Array<{ label: string; align?: 'left' | 'right' }> = [
      { label: '项目', align: 'left' },
    ];
    block.cols.forEach((c, i) => {
      const end = block.col_end?.[i];
      headers.push({ label: end && stmt === 'bs' ? `${c} · ${end.slice(5)}` : c });
    });

    const rows: Row[] = [];
    for (const r of block.rows) {
      if (hideEmpty && r.v.every((x) => x == null)) continue;
      const derive = r.kind === 'd' || r.kind === 'i';
      rows.push({
        kind: r.kind === 's' ? 'sec' : 'normal',
        cells: [
          {
            text: r.name,
            bold: r.kind === 'b',
            className: derive ? 'fin-row-derive' : r.kind === 's' ? 'fin-row-sec' : '',
            title: r.formula ?? undefined,
          },
          ...r.v.map((v) => ({ text: fmtCell(v, r.fmt, unit), bold: r.kind === 'b' })),
        ],
      });
      if (showYoy && r.yoy.some((x) => x != null)) {
        rows.push({
          kind: 'sub',
          cells: [
            { text: '↳ 同比' },
            ...r.yoy.map((v) => ({ text: fmtDelta(v, r.fmt) })),
          ],
        });
      }
      if (showQoq && period === 'q' && r.qoq.some((x) => x != null)) {
        rows.push({
          kind: 'sub',
          cells: [
            { text: '↳ 环比' },
            ...r.qoq.map((v) => ({ text: fmtDelta(v, r.fmt) })),
          ],
        });
      }
    }

    card.appendChild(renderDataTable({ headers, rows, stickyFirst: true }));
    if (block.note) card.appendChild(el('p', { className: 'footnote', text: block.note }));
    root.appendChild(card);

    const exportBtn = root.querySelector('.fin-export');
    exportBtn?.addEventListener('click', () => {
      const lines = [
        headers.map((h) => h.label).join(','),
        ...rows.map((row) => row.cells.map((c) => `"${String(c.text ?? '').replace(/"/g, '""')}"`).join(',')),
      ];
      const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `MU_${STMT_LABELS[stmt]}_${period}.csv`;
      a.click();
    });

    root.appendChild(
      renderFooterNote(['GAAP 来自 SEC XBRL；null 显示 [ ]。表格在卡片内横向滚动。']),
    );
  };

  paint();
  return root;
}
