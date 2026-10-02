import type { ConsensusPage } from '../../lib/types';
import { formatNum, peMultiple, ttmShare } from '../../lib/fmt';
import { el } from '../../components/segmented';

export function renderForwardPe(
  data: ConsensusPage,
  price: string,
  onPrice: (v: string) => void,
): HTMLElement {
  const pe = data.future.pe;
  const fyCols = Object.entries(pe.fy ?? {}).sort((a, b) => a[0].localeCompare(b[0]));
  const cols: Array<[string, number | null, boolean]> = [
    ['近 4 季（TTM）', pe.ttm_eps, false],
    ['未来 12 个月（NTM）', pe.ntm_eps, true],
    ...fyCols.map(([name, v]): [string, number | null, boolean] => [`${name}E`, v, true]),
  ];

  const card = el('div', { className: 'card', style: 'display:flex;flex-direction:column' });
  const input = el('input', {
    type: 'number',
    step: '0.01',
    min: '0',
    placeholder: '输入股价',
    value: price,
    style:
      'width:120px;height:32px;box-sizing:border-box;border:1px solid var(--axis);border-radius:6px;padding:0 10px;font-family:var(--font-mono);font-size:13px;color:var(--ink)',
  }) as HTMLInputElement;

  const label = el('label', {
    style: 'display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)',
  });
  label.append(document.createTextNode('股价'), input);

  const method = pe.ntm_method?.startsWith('fy_time_weight')
    ? '本财年与下财年按剩余月份加权'
    : pe.ntm_method === 'sum_next_4_quarters'
      ? '未来四个季度加总'
      : pe.ntm_method || '—';
  card.appendChild(
    el('div', { className: 'card__head' }, [
      el('div', {}, [
        el('div', { className: 'card__title', text: 'Forward PE' }),
        el('div', {
          className: 'card__unit',
          text: `NTM 方法：${method}`,
        }),
      ]),
      label,
    ]),
  );

  const table = el('table', { className: 'data' });
  const hr = el('tr');
  hr.appendChild(el('th', { className: 'left', text: '' }));
  for (const [name] of cols) hr.appendChild(el('th', { text: name }));
  table.appendChild(el('thead', {}, [hr]));

  const tbody = el('tbody');
  const row1 = el('tr', {}, [
    el('td', { className: 'left', text: 'EPS 基数' }),
    ...cols.map(([, v, est]) =>
      el('td', {
        className: `${est ? 'est ' : ''}${v === null ? 'faint' : ''}`,
        text: formatNum(v),
      }),
    ),
  ]);

  const peRow = el('tr');
  const paintPeRow = (priceStr: string) => {
    const px = parseFloat(priceStr);
    const hasP = px > 0;
    peRow.replaceChildren(
      el('td', { className: 'left bold', text: 'P/E' }),
      ...cols.map(([, v, est]) => {
        const ok = hasP && v !== null && v > 0;
        return el('td', {
          className: `${est ? 'est ' : ''}${ok ? 'bold' : 'faint'}`,
          text: peMultiple(hasP ? px : null, v),
        });
      }),
    );
  };
  paintPeRow(price);

  const row3 = el('tr', {}, [
    el('td', { className: 'left', text: '相当于 TTM PE 的' }),
    ...cols.map(([, v, est]) =>
      el('td', {
        className: `${est ? 'est ' : ''}${v === null ? 'faint' : ''}`,
        text: ttmShare(pe.ttm_eps, v),
      }),
    ),
  ]);
  tbody.append(row1, peRow, row3);
  table.appendChild(tbody);
  card.appendChild(table);
  card.appendChild(el('div', { className: 'footnote', text: pe.note }));

  // Update PE cells in place — do not remount the page (keeps focus while typing).
  input.addEventListener('input', () => {
    onPrice(input.value);
    paintPeRow(input.value);
  });

  return card;
}
