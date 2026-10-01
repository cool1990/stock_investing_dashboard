import { createSegmented, el } from '../../components/segmented';
import { createToggleChip } from '../../components/toggleChip';
import { renderDataTable, type Row } from '../../components/dataTable';
import { renderFooterNote } from '../../components/footerNote';
import { renderBanner } from '../../components/banner';
import { formatAmtMillions, formatTablePct, MISSING } from '../../lib/fmt';

type FinRow = {
  id?: string;
  name: string;
  kind?: string;
  unit?: string;
  fmt?: string;
  values?: Array<number | null>;
  v?: Array<number | null>;
  yoy?: Array<number | null>;
  qoq?: Array<number | null>;
  yoy_tone?: string[];
  qoq_tone?: string[];
  formula?: string | null;
};

type FinTable = {
  title: string;
  cols: string[];
  col_end?: string[];
  rows: FinRow[];
  note?: string;
};

export interface FinancialsPage {
  tables: Record<string, Partial<Record<'q' | 'ytd' | 'y', FinTable>>>;
  mode_notes?: Record<string, string>;
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

export function renderFinancialsPage(data: FinancialsPage): HTMLElement {
  let stmt = 'is';
  let mode: 'q' | 'ytd' | 'y' = 'q';
  let range: '5' | '12' | 'all' = '5';
  let unit: 'M' | 'B' = 'M';
  let showYoy = true;
  let showQoq = false;
  const root = el('main', { className: 'main financials-page' });

  const paint = () => {
    root.replaceChildren();
    root.appendChild(
      renderBanner('财务报表 P0 样例：单位与同比/环比切换可用；完整 XBRL 回填在 P1。'),
    );

    const head = el('div', { className: 'section__head' }, [
      el('div', {}, [
        el('h2', { text: '财务报表' }),
        el('div', {
          className: 'section__sub',
          text: data.mode_notes?.[mode] ?? '金额默认百万美元；比率类变化用 pp',
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
            if (mode === 'y') showQoq = false;
            paint();
          },
        ),
        createSegmented(
          '范围',
          [
            { value: '5', label: '近 5 期' },
            { value: '12', label: '近 12 期' },
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
          mode === 'y',
        ),
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
          text:
            mode === 'ytd' && (stmt === 'bs' || stmt === 'eq')
              ? data.mode_notes?.bs_ytd ?? '资产负债表 / 权益表无累计视图'
              : '该视图暂无样例数据',
        }),
      );
      root.appendChild(card);
      root.appendChild(renderFooterNote(['来源：SEC EDGAR XBRL（P1 接入）']));
      return;
    }

    const { cols, start } = sliceCols(table.cols, range);
    const headers = [
      { label: '项目', align: 'left' as const },
      ...cols.map((c, i) => {
        const end = table.col_end?.[start + i];
        return { label: end ? `${c} · ${String(end).slice(5)}` : c };
      }),
    ];

    const rows: Row[] = [];
    for (const r of table.rows) {
      const vals = rowValues(r).slice(start, start + cols.length);
      const isRatio = r.unit === '%' || r.fmt === 'pct' || r.fmt === 'ratio' || r.kind === 'ratio';
      const isBold = r.kind === 'total' || r.kind === 'b' || r.kind === 't';
      const isGroup = r.kind === 'group' || r.kind === 'sec' || r.kind === 'h';
      rows.push({
        kind: isGroup ? 'group' : 'normal',
        cells: [
          { text: r.name, bold: isBold },
          ...vals.map((v) => ({
            text: isRatio
              ? v == null
                ? MISSING
                : `${(v * (Math.abs(v) <= 1.5 ? 100 : 1)).toFixed(1)}%`
              : formatAmtMillions(v, unit),
            bold: isBold,
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
              text: formatTablePct(v),
              color: r.yoy_tone?.[start + i],
            })),
          ],
        });
      }
      if (showQoq && r.qoq && mode !== 'y') {
        const qoq = r.qoq.slice(start, start + cols.length);
        rows.push({
          kind: 'sub',
          cells: [
            { text: '↳ 环比' },
            ...qoq.map((v, i) => ({
              text: formatTablePct(v),
              color: r.qoq_tone?.[start + i],
            })),
          ],
        });
      }
    }

    card.appendChild(el('div', { className: 'card__title', text: table.title }));
    card.appendChild(renderDataTable({ headers, rows, stickyFirst: true }));
    if (table.note) card.appendChild(el('div', { className: 'footnote', text: table.note }));

    const exportBtn = head.querySelector('button.toggle-chip:last-child') as HTMLButtonElement | null;
    if (exportBtn) {
      exportBtn.onclick = () => {
        const lines = [
          ['项目', ...cols].join(','),
          ...table.rows.map((r) =>
            [
              JSON.stringify(r.name),
              ...rowValues(r)
                .slice(start, start + cols.length)
                .map((v) => (v == null ? '' : v)),
            ].join(','),
          ),
        ];
        const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${stmt}-${mode}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      };
    }

    root.appendChild(card);
    root.appendChild(
      renderFooterNote([
        '第一列固定；窄屏下表格在卡片内横向滚动。',
        'Non-GAAP 与派生指标在后续阶段并入；P0 仅还原结构与主要交互。',
      ]),
    );
  };

  paint();
  return root;
}
