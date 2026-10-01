import { createSegmented, el } from '../../components/segmented';
import { createToggleChip } from '../../components/toggleChip';
import { renderDataTable, type Row } from '../../components/dataTable';
import { renderFooterNote } from '../../components/footerNote';
import { formatAmtMillions, MISSING } from '../../lib/fmt';

type FinRow = {
  id?: string;
  name: string;
  kind?: string;
  unit?: string;
  fmt?: string;
  values?: Array<number | null>;
  v?: Array<number | null>;
  yoy?: Array<number | null | string> | null;
  qoq?: Array<number | null | string> | null;
  yoy_tone?: Array<string | null> | null;
  qoq_tone?: Array<string | null> | null;
  formula?: string | null;
};

type FinTable = {
  title: string;
  cols: string[];
  col_labels?: string[];
  col_end?: Array<string | null>;
  rows: FinRow[];
  note?: string;
};

export interface FinancialsPage {
  tables: Record<string, Partial<Record<'q' | 'ytd' | 'y', FinTable>>>;
  mode_notes?: Record<string, string>;
  ticker?: string;
}

const STATEMENTS = [
  { id: 'is', label: '利润表' },
  { id: 'bs', label: '资产负债表' },
  { id: 'cf', label: '现金流量表' },
  { id: 'eq', label: '股东权益' },
];

function sliceCols(cols: string[], range: '5' | '12' | 'all'): { cols: string[]; start: number } {
  if (range === 'all' || cols.length <= 5) return { cols, start: 0 };
  const n = range === '5' ? 5 : 12;
  const start = Math.max(0, cols.length - n);
  return { cols: cols.slice(start), start };
}

function rowValues(r: FinRow): Array<number | null> {
  return r.values ?? r.v ?? [];
}

function formatCell(r: FinRow, v: number | null | undefined, unit: 'M' | 'B'): string {
  if (v == null) return MISSING;
  if (r.fmt === 'eps') return `$${v.toFixed(2)}`;
  if (r.fmt === 'days' || r.unit === '天') return String(Math.round(v));
  if (r.fmt === 'pct' || r.fmt === 'ratio' || r.unit === '%') {
    const pct = Math.abs(v) <= 1.5 ? v * 100 : v;
    return `${pct.toFixed(1)}%`;
  }
  return formatAmtMillions(v, unit);
}

function formatChangeCell(v: number | string | null | undefined): string {
  if (v == null) return MISSING;
  if (typeof v === 'string') return v;
  const p = v * 100;
  const sign = p >= 0 ? '+' : '−';
  const abs = Math.abs(p);
  const body = abs >= 1000 ? String(Math.round(abs)) : abs.toFixed(1);
  return `${sign}${body}%`;
}

function todayStamp(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function isRowAllEmpty(r: FinRow, start: number, n: number): boolean {
  if (r.kind === 's' || r.kind === 'group' || r.kind === 'sec' || r.kind === 'h') return false;
  const vals = rowValues(r).slice(start, start + n);
  return vals.length > 0 && vals.every((v) => v == null);
}

export function renderFinancialsPage(data: FinancialsPage): HTMLElement {
  let stmt = 'is';
  let mode: 'q' | 'ytd' | 'y' = 'q';
  let range: '5' | '12' | 'all' = '5';
  let unit: 'M' | 'B' = 'M';
  let showYoy = true;
  let showQoq = false;
  let hideEmpty = true;
  const root = el('main', { className: 'main financials-page' });
  const ticker = data.ticker ?? 'MU';

  const paint = () => {
    root.replaceChildren();
    const qoqDisabled = mode !== 'q';
    if (qoqDisabled) showQoq = false;

    const modeNote =
      (stmt === 'bs' || stmt === 'eq') && mode === 'ytd'
        ? (data.mode_notes?.bs_ytd ?? data.mode_notes?.ytd)
        : data.mode_notes?.[mode];

    const head = el('div', { className: 'section__head' }, [
      el('div', {}, [
        el('h2', { text: '财务报表' }),
        el('div', {
          className: 'section__sub',
          text: modeNote ?? '金额默认百万美元；比率类变化用 pp',
        }),
      ]),
      el('div', { className: 'toolbar' }, [
        createSegmented(
          '报表',
          STATEMENTS.map((s) => ({ value: s.id, label: s.label })),
          stmt,
          (v) => {
            stmt = v;
            paint();
          },
        ),
        createSegmented(
          '视图',
          [
            { value: 'q', label: '单季' },
            { value: 'ytd', label: '累计' },
            { value: 'y', label: '年度' },
          ],
          mode,
          (v) => {
            mode = v as typeof mode;
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
          qoqDisabled,
        ),
        createToggleChip('隐藏全空行', hideEmpty, (n) => {
          hideEmpty = n;
          paint();
        }),
        el('button', {
          className: 'toggle-chip',
          type: 'button',
          text: '导出 CSV',
        }),
      ]),
    ]);
    root.appendChild(el('section', { className: 'section' }, [head]));

    const table = data.tables[stmt]?.[mode];
    const card = el('div', { className: 'card' });
    if (!table || !table.cols?.length) {
      card.appendChild(
        el('p', {
          className: 'faint',
          text: '该视图暂无数据',
        }),
      );
      root.appendChild(card);
      root.appendChild(renderFooterNote(['来源：SEC EDGAR XBRL']));
      return;
    }

    const { cols, start } = sliceCols(table.cols, range);
    const labels = (table.col_labels ?? table.cols).slice(start, start + cols.length);
    const headers = [
      { label: '项目', align: 'left' as const },
      ...labels.map((c, i) => {
        const end = table.col_end?.[start + i];
        const endPart =
          mode === 'q' && end && stmt === 'bs'
            ? ` · ${String(end).slice(5, 10).replace('-', '-')}`
            : mode === 'q' && end
              ? ''
              : '';
        // BS: show end date MM-DD
        let label = c;
        if (stmt === 'bs' && end) {
          const md = String(end).slice(5).replace('-', '-');
          label = `${table.cols[start + i]} · ${md}`;
        } else if (table.col_labels) {
          label = c;
        }
        return { label: label + endPart };
      }),
    ];

    const rows: Row[] = [];
    const visibleRows = table.rows.filter((r) => !hideEmpty || !isRowAllEmpty(r, start, cols.length));

    for (const r of visibleRows) {
      const vals = rowValues(r).slice(start, start + cols.length);
      const isBold = r.kind === 'total' || r.kind === 'b' || r.kind === 't';
      const isGroup = r.kind === 'group' || r.kind === 'sec' || r.kind === 's' || r.kind === 'h';
      const isDerived = r.kind === 'd';
      const isIndent = r.kind === 'i' || isDerived;

      if (isGroup) {
        rows.push({
          kind: 'sec',
          cells: [{ text: r.name, bold: true }, ...cols.map(() => ({ text: '' }))],
        });
        continue;
      }

      rows.push({
        kind: 'normal',
        cells: [
          {
            text: r.name,
            bold: isBold,
            className: isIndent ? 'indent' : '',
            title: r.formula ?? undefined,
          },
          ...vals.map((v) => ({
            text: formatCell(r, v, unit),
            bold: isBold,
            className: isDerived ? 'derived' : '',
            title: r.formula ?? undefined,
          })),
        ],
      });

      if (showYoy && r.yoy) {
        const yoy = r.yoy.slice(start, start + cols.length);
        rows.push({
          kind: 'sub',
          cells: [
            { text: '↳ 同比' },
            ...yoy.map((v, i) => ({
              text: formatChangeCell(v),
              color: r.yoy_tone?.[start + i] ?? undefined,
            })),
          ],
        });
      }
      if (showQoq && !qoqDisabled && r.qoq) {
        const qoq = r.qoq.slice(start, start + cols.length);
        rows.push({
          kind: 'sub',
          cells: [
            { text: '↳ 环比' },
            ...qoq.map((v, i) => ({
              text: formatChangeCell(v),
              color: r.qoq_tone?.[start + i] ?? undefined,
            })),
          ],
        });
      }
    }

    const unitLabel = unit === 'M' ? '百万美元' : '十亿美元';
    card.appendChild(
      el('div', {
        className: 'card__title',
        text: `${table.title}　单位：$ ${unitLabel}${stmt === 'is' ? '，EPS 为 $' : ''}`,
      }),
    );
    card.appendChild(renderDataTable({ headers, rows, stickyFirst: true }));
    if (table.note) card.appendChild(el('div', { className: 'footnote', text: table.note }));

    const exportBtn = head.querySelector('button.toggle-chip:last-child') as HTMLButtonElement | null;
    if (exportBtn) {
      exportBtn.onclick = () => {
        const stmtLabel = STATEMENTS.find((s) => s.id === stmt)?.label ?? stmt;
        const modeLabel = mode === 'q' ? '单季' : mode === 'ytd' ? '累计' : '年度';
        const headerLine = `# ${ticker} ${stmtLabel} ${modeLabel}；单位：$ ${unitLabel}；含同比=${showYoy} 环比=${showQoq}`;
        const lines: string[] = [headerLine, ['项目', ...labels].join(',')];
        for (const r of visibleRows) {
          if (r.kind === 's' || r.kind === 'sec' || r.kind === 'group') {
            lines.push([JSON.stringify(r.name), ...cols.map(() => '')].join(','));
            continue;
          }
          lines.push(
            [
              JSON.stringify(r.name),
              ...rowValues(r)
                .slice(start, start + cols.length)
                .map((v) => (v == null ? '' : formatCell(r, v, unit))),
            ].join(','),
          );
          if (showYoy && r.yoy) {
            lines.push(
              [
                JSON.stringify('↳ 同比'),
                ...r.yoy.slice(start, start + cols.length).map((v) => formatChangeCell(v)),
              ].join(','),
            );
          }
          if (showQoq && !qoqDisabled && r.qoq) {
            lines.push(
              [
                JSON.stringify('↳ 环比'),
                ...r.qoq.slice(start, start + cols.length).map((v) => formatChangeCell(v)),
              ].join(','),
            );
          }
        }
        const bom = '\uFEFF';
        const blob = new Blob([bom + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${ticker}_${stmtLabel}_${modeLabel}_${todayStamp()}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      };
    }

    root.appendChild(card);
    root.appendChild(
      renderFooterNote([
        '第一列固定；窄屏下表格在卡片内横向滚动。',
        '同比 / 环比颜色：蓝=增加，橙=减少，灰=n.m. / 缺失。',
        '来源：SEC EDGAR companyfacts（GAAP）；Non-GAAP 来自新闻稿覆盖。',
      ]),
    );
  };

  paint();
  return root;
}
