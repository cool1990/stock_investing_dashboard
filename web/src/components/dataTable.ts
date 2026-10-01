import { el } from './segmented';
import { colorClass, displayValue, isPlaceholder } from './placeholder';

export type Cell = {
  text: string | number | null | undefined;
  className?: string;
  color?: string | null;
  title?: string;
  est?: boolean;
  bold?: boolean;
};

export type Row = {
  cells: Cell[];
  kind?: 'normal' | 'sub' | 'sec' | 'group';
};

export function renderDataTable(opts: {
  headers: Array<{ label: string; align?: 'left' | 'right'; className?: string }>;
  rows: Row[];
  stickyFirst?: boolean;
}): HTMLElement {
  const wrap = el('div', { className: `table-wrap${opts.stickyFirst ? ' table-wrap--sticky' : ''}` });
  const table = el('table', { className: 'data' });
  const thead = el('thead');
  const hr = el('tr');
  opts.headers.forEach((h, i) => {
    const th = el('th', {
      className: `${h.align === 'left' || i === 0 ? 'left' : ''} ${h.className ?? ''}`.trim(),
      text: h.label,
    });
    hr.appendChild(th);
  });
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = el('tbody');
  for (const row of opts.rows) {
    const tr = el('tr', {
      className:
        row.kind === 'sub'
          ? 'row-sub'
          : row.kind === 'sec'
            ? 'row-sec'
            : row.kind === 'group'
              ? 'row-group'
              : '',
    });
    row.cells.forEach((c, i) => {
      const text = displayValue(c.text);
      const cls = [
        i === 0 ? 'left' : '',
        c.est ? 'est' : '',
        c.bold ? 'bold' : '',
        isPlaceholder(c.text) ? 'faint' : colorClass(c.color),
        c.className ?? '',
      ]
        .filter(Boolean)
        .join(' ');
      const td = el('td', { className: cls, text, ...(c.title ? { title: c.title } : {}) });
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}
