import { el } from '../../components/segmented';
import { renderDataTable } from '../../components/dataTable';
import { renderFooterNote } from '../../components/footerNote';
import { renderTag, type TagKind } from '../../components/tag';
import { displayValue } from '../../components/placeholder';

export interface SourcesPage {
  intro: string;
  legend: Array<{ k: string; desc: string }>;
  rows: Array<{
    id: string;
    name: string;
    used: string;
    reliability: string;
    source: string;
    freq: string;
    missing: string;
    status: { state: string; last_ok: string | null; last_err: string | null; err_msg: string | null };
  }>;
  conventions: string[];
}

function stateTag(state: string): { label: string; kind: TagKind } {
  if (state === 'ok') return { label: '正常', kind: 'ok' };
  if (state === 'degraded') return { label: '降级', kind: 'mid' };
  if (state === 'error') return { label: '失败', kind: 'bad' };
  return { label: state || '未知', kind: 'mid' };
}

export function renderSourcesPage(data: SourcesPage): HTMLElement {
  const root = el('main', { className: 'main sources-page' });
  root.appendChild(
    el('div', { className: 'section__head' }, [
      el('div', {}, [
        el('h1', { className: 'watchlist-title', text: '数据说明' }),
        el('div', { className: 'section__sub', text: data.intro }),
      ]),
    ]),
  );

  const legend = el('div', { className: 'legend-row' });
  for (const L of data.legend) {
    legend.appendChild(el('span', { text: `${L.k}：${L.desc}` }));
  }
  root.appendChild(legend);

  const card = el('div', { className: 'card' });
  card.appendChild(
    renderDataTable({
      headers: [
        { label: '数据源', align: 'left' },
        { label: '用于' },
        { label: '可靠性' },
        { label: '来源' },
        { label: '频率' },
        { label: '缺失时' },
        { label: '状态' },
      ],
      rows: data.rows.map((r) => {
        const st = stateTag(r.status.state);
        return {
          cells: [
            { text: r.name },
            { text: r.used },
            { text: r.reliability },
            { text: r.source },
            { text: r.freq },
            { text: r.missing },
            {
              text: `${st.label} · ${displayValue(r.status.last_ok, '—')}`,
              title: r.status.err_msg ?? undefined,
              color: st.kind === 'ok' ? 'up' : st.kind === 'bad' ? 'down' : 'na',
            },
          ],
        };
      }),
    }),
  );
  root.appendChild(card);

  // Highlight remarks missing policy visually
  const remarks = data.rows.find((r) => r.id === 'remarks');
  if (remarks) {
    root.appendChild(
      el('div', { className: 'card' }, [
        el('div', { className: 'card__title', text: '准备稿缺失策略（已决）' }),
        el('p', { text: remarks.missing }),
        renderTag('不得静默顶替', 'chg'),
      ]),
    );
  }

  if (data.conventions?.length) {
    const box = el('div', { className: 'card' });
    box.appendChild(el('div', { className: 'card__title', text: '口径约定' }));
    const ul = el('ul');
    for (const c of data.conventions) ul.appendChild(el('li', { text: c }));
    box.appendChild(ul);
    root.appendChild(box);
  }

  root.appendChild(
    renderFooterNote([
      '状态来自 data/_status.json；抓取失败时保留旧数据。',
      '浏览器不请求第三方 API。',
    ]),
  );
  return root;
}
