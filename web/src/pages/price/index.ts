import { el } from '../../components/segmented';
import { renderKpiCard } from '../../components/kpiCard';
import { renderDataTable } from '../../components/dataTable';
import { renderBanner } from '../../components/banner';
import { renderFooterNote } from '../../components/footerNote';
import { displayValue } from '../../components/placeholder';
import { formatRatioChange } from '../../lib/fmt';

export interface PricePage {
  windows: string[];
  kpi: Record<
    string,
    { latest: number | null; latest_tone: string; avg8: number | null; up8: number | null }
  >;
  vol: { avg_abs_move: number | null; avg_iv: number | null; iv_note?: string };
  beat_but_down: { n: number | null; of: number; note?: string };
  series: { dates: string[]; close_adj: number[] };
  events: Array<{
    q: string;
    d: string;
    timing: string;
    rd: string;
    pre_close: number | null;
    ah: number | null;
    ah_tone: string;
    ah_note?: string;
    open: number | null;
    close: number | null;
    close_tone: string;
    t5: number | null;
    t5_tone: string;
    iv: number | null;
    iv_note?: string;
    eps_surp: number | null;
    eps_surp_tone: string;
    rev_surp: number | null;
    rev_surp_tone: string;
    guide_vs_cons: number | null;
    guide_vs_cons_tone: string;
    note: { text: string | null; confirmed: boolean };
  }>;
}

function sparkline(dates: string[], closes: number[], events: PricePage['events']): HTMLElement {
  const wrap = el('div', { className: 'card' });
  wrap.appendChild(el('div', { className: 'card__title', text: '日线（复权）· 财报日标记 (E)' }));
  if (!dates.length || !closes.length) {
    wrap.appendChild(el('p', { className: 'faint', text: '价格序列待 P3 接入' }));
    return wrap;
  }
  const w = 640;
  const h = 160;
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const pts = closes
    .map((c, i) => {
      const x = (i / Math.max(closes.length - 1, 1)) * (w - 20) + 10;
      const y = h - 20 - ((c - min) / Math.max(max - min, 1e-9)) * (h - 40);
      return `${x},${y}`;
    })
    .join(' ');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('class', 'price-svg');
  svg.innerHTML = `<polyline fill="none" stroke="var(--up)" stroke-width="2" points="${pts}" />`;
  for (const ev of events) {
    const idx = dates.indexOf(ev.d);
    if (idx < 0) continue;
    const x = (idx / Math.max(closes.length - 1, 1)) * (w - 20) + 10;
    svg.innerHTML += `<circle cx="${x}" cy="16" r="3" fill="var(--warn)" /><text x="${x}" y="12" font-size="10" text-anchor="middle" fill="var(--muted)">(E)</text>`;
  }
  wrap.appendChild(svg);
  return wrap;
}

function scatter(events: PricePage['events']): HTMLElement {
  const wrap = el('div', { className: 'card' });
  wrap.appendChild(el('div', { className: 'card__title', text: '超预期 vs 次日涨跌（散点）' }));
  const pts = events.filter((e) => e.eps_surp != null && e.close != null);
  if (!pts.length) {
    wrap.appendChild(el('p', { className: 'faint', text: '散点数据待 P3 接入' }));
    return wrap;
  }
  const w = 360;
  const h = 200;
  const xs = pts.map((p) => p.eps_surp as number);
  const ys = pts.map((p) => p.close as number);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('class', 'price-svg');
  let circles = '';
  pts.forEach((p) => {
    const x = 30 + (((p.eps_surp as number) - xMin) / Math.max(xMax - xMin, 1e-9)) * (w - 50);
    const y = h - 30 - (((p.close as number) - yMin) / Math.max(yMax - yMin, 1e-9)) * (h - 50);
    circles += `<circle cx="${x}" cy="${y}" r="4" fill="var(--up-mid)" opacity="0.85"><title>${p.q}</title></circle>`;
  });
  svg.innerHTML = `<line x1="30" y1="${h - 30}" x2="${w - 10}" y2="${h - 30}" stroke="var(--axis)" /><line x1="30" y1="20" x2="30" y2="${h - 30}" stroke="var(--axis)" />${circles}`;
  wrap.appendChild(svg);
  return wrap;
}

export function renderPricePage(data: PricePage): HTMLElement {
  const root = el('main', { className: 'main price-page' });
  root.appendChild(
    renderBanner('盘后用次日开盘相对前收盘近似，并标明「近似」。期权隐含波动未接入。'),
  );

  root.appendChild(
    el('div', { className: 'section__head' }, [
      el('div', {}, [
        el('h2', { text: '股价反应' }),
        el('div', { className: 'section__sub', text: `窗口：${data.windows.join(' · ')}` }),
      ]),
    ]),
  );

  const kpis = el('div', { className: 'kpi-grid' });
  const labels: Record<string, string> = {
    ah: '本次盘后',
    d1: '次日',
    d5: 'T+5',
  };
  for (const key of ['ah', 'd1', 'd5']) {
    const k = data.kpi[key];
    if (!k) continue;
    kpis.appendChild(
      renderKpiCard({
        label: labels[key] ?? key,
        value: formatRatioChange(k.latest),
        color: k.latest_tone,
        sub: `近 8 次均 ${formatRatioChange(k.avg8)} · 上涨 ${displayValue(k.up8)} 次`,
      }),
    );
  }
  kpis.appendChild(
    renderKpiCard({
      label: '实际波动 vs 隐含',
      value:
        data.vol.avg_abs_move != null && data.vol.avg_iv != null
          ? `${formatRatioChange(data.vol.avg_abs_move)} / ${formatRatioChange(data.vol.avg_iv)}`
          : data.vol.iv_note || '未接入',
      sub: '近 8 次 |Δ| 均 vs 期权隐含',
    }),
  );
  kpis.appendChild(
    renderKpiCard({
      label: '超预期却下跌',
      value: data.beat_but_down.n != null ? `${data.beat_but_down.n} / ${data.beat_but_down.of}` : null,
      sub: data.beat_but_down.note ?? 'EPS 超预期且次日收跌',
    }),
  );
  root.appendChild(kpis);

  root.appendChild(
    el('div', { className: 'split-2' }, [sparkline(data.series.dates, data.series.close_adj, data.events), scatter(data.events)]),
  );

  const tableCard = el('div', { className: 'card' });
  tableCard.appendChild(el('div', { className: 'card__title', text: '历史财报反应' }));
  tableCard.appendChild(
    renderDataTable({
      headers: [
        { label: '财季', align: 'left' },
        { label: '发布' },
        { label: '盘后' },
        { label: '次日' },
        { label: 'T+5' },
        { label: 'IV' },
        { label: 'EPS 超预期' },
        { label: '收入超预期' },
        { label: '指引 vs 共识' },
        { label: '一句话' },
      ],
      rows: data.events.map((e) => ({
        cells: [
          { text: e.q },
          { text: `${e.d} ${e.timing === 'after_close' ? '盘后' : '盘前'}` },
          {
            text:
              e.ah != null
                ? `${formatRatioChange(e.ah)}${e.ah_note ? ` ${e.ah_note}` : ''}`
                : e.ah_note || '未接入',
            color: e.ah_tone,
          },
          { text: formatRatioChange(e.close), color: e.close_tone },
          { text: formatRatioChange(e.t5), color: e.t5_tone },
          { text: e.iv != null ? formatRatioChange(e.iv) : e.iv_note || '未接入' },
          { text: formatRatioChange(e.eps_surp), color: e.eps_surp_tone },
          { text: formatRatioChange(e.rev_surp), color: e.rev_surp_tone },
          {
            text: e.guide_vs_cons != null ? formatRatioChange(e.guide_vs_cons) : '未接入',
            color: e.guide_vs_cons_tone,
          },
          {
            text: e.note.text ?? '未接入',
            className: e.note.text ? '' : 'faint',
          },
        ],
      })),
    }),
  );
  root.appendChild(tableCard);

  root.appendChild(
    renderFooterNote([
      '色类字段 *_tone 由后端给出；前端只渲染。',
      '复盘笔记由 AI 草稿 + 人工确认（P4）；未确认显示占位句。',
    ]),
  );
  return root;
}
