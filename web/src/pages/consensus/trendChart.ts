import type { ConsensusPage, MetricKind } from '../../lib/types';
import { formatNum } from '../../lib/fmt';
import { el } from '../../components/segmented';

export function renderTrendChart(data: ConsensusPage, metric: MetricKind): HTMLElement {
  const years = data.future.years;
  const estYears = new Set(data.future.est_years);
  const grid = metric === 'eps' ? data.future.eps : data.future.rev;

  const allQ: number[] = [];
  const allY: number[] = [];
  for (const y of years) {
    for (const v of grid[y].slice(0, 4)) if (v !== null) allQ.push(v);
    if (grid[y][4] !== null) allY.push(grid[y][4] as number);
  }
  const qmax = Math.max(...allQ, 0.01);
  const qmin = Math.min(0, ...allQ);
  const ymax = Math.max(...allY, 0.01);
  const ymin = Math.min(0, ...allY);
  const QH = 132;
  const YT = (v: number) => 18 + (1 - (v - ymin) / (ymax - ymin || 1)) * 70;
  const qz = ((0 - qmin) / (qmax - qmin || 1)) * QH + 6;
  const cx = (i: number) => ((i + 0.5) / years.length) * 100;

  const act: string[] = [];
  const est: string[] = [];
  years.forEach((y, i) => {
    const v = grid[y][4];
    if (v === null) return;
    const pt = `${cx(i).toFixed(2)},${YT(v).toFixed(2)}`;
    if (estYears.has(y)) est.push(pt);
    else act.push(pt);
  });
  if (est.length && act.length) est.unshift(act[act.length - 1]);

  const card = el('div', { className: 'card' });
  const head = el('div', { className: 'card__head' }, [
    el('div', { className: 'card__title', text: '走势' }),
    el('div', { className: 'legend-row', style: 'gap:14px;margin:0' }, [
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:12px;height:12px;background:#8A93A0;border-radius:2px;display:inline-block',
        }),
        document.createTextNode('已公布'),
      ]),
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style:
            'width:12px;height:12px;background:#DCE5FB;border:1.5px dashed #1D4ED8;border-radius:2px;display:inline-block;box-sizing:border-box',
        }),
        document.createTextNode('共识'),
      ]),
    ]),
  ]);
  card.appendChild(head);

  const body = el('div', { style: 'display:flex;gap:8px' });
  const labels = el('div', {
    style: 'width:22px;display:flex;flex-direction:column;font-size:11px;color:var(--faint)',
  });
  labels.innerHTML =
    '<div style="height:130px;display:flex;align-items:center;justify-content:center"><span style="writing-mode:vertical-rl">全年</span></div>' +
    '<div style="height:150px;display:flex;align-items:center;justify-content:center"><span style="writing-mode:vertical-rl">逐季</span></div>';
  body.appendChild(labels);

  const charts = el('div', { style: 'flex-grow:1;display:flex;flex-direction:column' });
  const yearPane = el('div', {
    style: 'position:relative;height:130px;border-bottom:1px solid var(--line-2)',
  });
  if (ymin < 0) {
    yearPane.appendChild(
      el('div', {
        style: `position:absolute;left:0;right:0;top:${YT(0)}%;border-top:1px dashed var(--axis)`,
      }),
    );
  }
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 100 100');
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  Object.assign(svg.style, {
    position: 'absolute',
    left: '0',
    top: '0',
    width: '100%',
    height: '100%',
    overflow: 'visible',
  });
  const mkPoly = (pts: string, stroke: string, dash?: string) => {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    p.setAttribute('points', pts);
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', stroke);
    p.setAttribute('stroke-width', '2.5');
    p.setAttribute('stroke-linejoin', 'round');
    p.setAttribute('vector-effect', 'non-scaling-stroke');
    if (dash) p.setAttribute('stroke-dasharray', dash);
    svg.appendChild(p);
  };
  if (act.length) mkPoly(act.join(' '), '#5B6370');
  if (est.length) mkPoly(est.join(' '), '#1D4ED8', '5 4');
  yearPane.appendChild(svg);

  years.forEach((y, i) => {
    const v = grid[y][4];
    if (v === null) return;
    const e = estYears.has(y);
    const dot = el('div', {
      style: `position:absolute;left:${cx(i)}%;top:${YT(v)}%;width:9px;height:9px;transform:translate(-50%,-50%);border-radius:50%;box-sizing:border-box;border:2px solid ${e ? '#1D4ED8' : '#5B6370'};background:${e ? '#FFFFFF' : '#5B6370'}`,
    });
    const lab = el('span', {
      className: 'mono',
      style: `position:absolute;left:${cx(i)}%;top:calc(${YT(v)}% - 22px);transform:translateX(-50%);font-size:11px;font-weight:600;white-space:nowrap;color:${e ? '#1E3A8A' : '#3A414C'}`,
      text: formatNum(v),
    });
    yearPane.append(dot, lab);
  });
  charts.appendChild(yearPane);

  const qPane = el('div', {
    style: 'position:relative;height:150px;border-bottom:1px solid var(--axis)',
  });
  qPane.appendChild(
    el('div', {
      style: `position:absolute;left:0;right:0;bottom:${qz}px;border-top:1px solid #B8BEC8`,
    }),
  );
  years.forEach((y, i) => {
    grid[y].slice(0, 4).forEach((v, k) => {
      const left = ((i + 0.12 + k * 0.2) / years.length) * 100;
      const w = (0.16 / years.length) * 100;
      const e = estYears.has(y);
      if (v === null) {
        qPane.appendChild(
          el('div', {
            style: `position:absolute;left:${left}%;width:${w}%;bottom:${qz}px;height:6px;border:1px dashed #B8BEC8;border-bottom:none;box-sizing:border-box`,
          }),
        );
        return;
      }
      const h = Math.max(2, (Math.abs(v) / (qmax - qmin || 1)) * QH);
      const bottom = v >= 0 ? qz : qz - h;
      const radius = v >= 0 ? '3px 3px 0 0' : '0 0 3px 3px';
      const bg = e
        ? 'background:#DCE5FB;border:1.5px dashed #1D4ED8'
        : `background:${v < 0 ? '#C2410C' : '#8A93A0'}`;
      qPane.appendChild(
        el('div', {
          style: `position:absolute;left:${left}%;width:${w}%;bottom:${bottom}px;height:${h}px;box-sizing:border-box;border-radius:${radius};${bg}`,
        }),
      );
    });
  });
  charts.appendChild(qPane);

  const xlabels = el('div', { style: 'display:flex;padding-top:6px' });
  for (const y of years) {
    xlabels.appendChild(
      el('span', {
        className: 'mono',
        style: 'flex:1;text-align:center;font-size:12px;color:var(--muted)',
        text: estYears.has(y) ? `${y}E` : y,
      }),
    );
  }
  charts.appendChild(xlabels);
  body.appendChild(charts);
  card.appendChild(body);
  card.appendChild(
    el('div', {
      className: 'footnote',
      text: '每组 4 根柱依次为 Q1–Q4；FY23–FY24 为下行周期亏损，柱体在零线以下',
    }),
  );
  return card;
}
