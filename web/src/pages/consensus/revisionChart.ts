import type { ConsensusPage } from '../../lib/types';
import { colorForSignedText, formatEps, formatPct } from '../../lib/fmt';
import { el } from '../../components/segmented';

export function renderRevision(data: ConsensusPage, key: string): HTMLElement {
  const e = data.revision[key];
  const card = el('div', { className: 'card', style: 'padding:20px' });
  card.appendChild(
    el('div', {
      className: 'legend-row',
      style: 'margin-bottom:14px',
    }, [
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:16px;height:0;border-top:3px solid #1D4ED8;display:inline-block',
        }),
        document.createTextNode('共识均值'),
      ]),
      el('span', { className: 'legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:16px;height:0;border-top:3px dashed #C2410C;display:inline-block',
        }),
        document.createTextNode('公司指引中值'),
      ]),
      el('span', { className: 'legend to-swatch legend-swatch' }, [
        Object.assign(document.createElement('span'), {
          style: 'width:16px;height:0;border-top:2px solid #B8BEC8;display:inline-block',
        }),
        document.createTextNode('股价（右轴，待接入）'),
      ]),
    ]),
  );

  const vals = e.points.map((p) => p[1]);
  if (e.guide !== null) vals.push(e.guide);
  const elo = Math.min(...vals) * 0.94;
  const ehi = Math.max(...vals) * 1.03;
  const ey = (v: number) => (1 - (v - elo) / (ehi - elo || 1)) * 100;
  const ex = (d: number) => ((90 - d) / 90) * 100;

  const pane = el('div', {
    style: 'position:relative;height:240px;margin:12px 48px 0 64px;border-bottom:1px solid var(--axis)',
  });

  for (let k = 0; k < 5; k++) {
    const v = elo + ((ehi - elo) * k) / 4;
    pane.appendChild(
      el('div', {
        style: `position:absolute;left:0;right:0;top:${ey(v)}%;border-top:1px solid #F0F1F4`,
      }),
    );
    pane.appendChild(
      el('span', {
        className: 'mono',
        style: `position:absolute;left:-64px;width:56px;text-align:right;top:calc(${ey(v)}% - 8px);font-size:11px;color:var(--faint)`,
        text: `$${v.toFixed(v < 100 ? 1 : 0)}`,
      }),
    );
  }

  if (e.guide !== null) {
    pane.appendChild(
      el('div', {
        style: `position:absolute;left:0;right:0;top:${ey(e.guide)}%;border-top:2px dashed #C2410C`,
      }),
    );
    pane.appendChild(
      el('span', {
        className: 'mono',
        style: `position:absolute;right:0;top:calc(${ey(e.guide)}% - 20px);font-size:12px;font-weight:600;color:#C2410C`,
        text: `指引 ${formatEps(e.guide)}`,
      }),
    );
  }

  const pts = e.points.map((p) => `${ex(p[0]).toFixed(2)},${ey(p[1]).toFixed(2)}`).join(' ');
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
  const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  poly.setAttribute('points', pts);
  poly.setAttribute('fill', 'none');
  poly.setAttribute('stroke', '#1D4ED8');
  poly.setAttribute('stroke-width', '2.5');
  poly.setAttribute('stroke-linejoin', 'round');
  poly.setAttribute('vector-effect', 'non-scaling-stroke');
  svg.appendChild(poly);
  pane.appendChild(svg);

  e.points.forEach((p, i) => {
    const last = i === e.points.length - 1;
    const size = last ? 12 : 9;
    pane.appendChild(
      el('div', {
        style: `position:absolute;left:${ex(p[0])}%;top:${ey(p[1])}%;width:${size}px;height:${size}px;transform:translate(-50%,-50%);border-radius:50%;background:${last ? '#1D4ED8' : '#FFFFFF'};border:2px solid #1D4ED8;box-sizing:border-box;z-index:2`,
      }),
    );
    pane.appendChild(
      el('span', {
        className: 'mono',
        style: `position:absolute;left:${ex(p[0])}%;top:calc(${ey(p[1])}% - 26px);transform:translateX(${last ? '-90%' : '-50%'});font-size:12px;white-space:nowrap;font-weight:${last ? 700 : 500};color:${last ? '#1E3A8A' : '#3A414C'}`,
        text: formatEps(p[1]),
      }),
    );
    pane.appendChild(
      el('span', {
        style: `position:absolute;left:${ex(p[0])}%;bottom:-24px;transform:translateX(${last ? '-80%' : '-50%'});font-size:12px;color:var(--muted);white-space:nowrap`,
        text: p[0] === 0 ? '今天' : `${p[0]} 天前`,
      }),
    );
  });

  card.append(pane, el('div', { style: 'height:28px' }), el('div', { className: 'footnote', text: e.note }));

  const cur = e.points[e.points.length - 1][1];
  const hasG = e.guide !== null;
  const stats = [
    { k: '90 天修正', v: formatPct(cur, e.points[0][1]), sub: `自 ${formatEps(e.points[0][1])}` },
    { k: '30 天修正', v: formatPct(cur, e.points[2][1]), sub: '近一个月基本走平' },
    {
      k: '上调 / 下调（30 天）',
      v: `${e.up30} / ${e.down30}`,
      sub: `覆盖 ${e.n} 家，方向未形成合力`,
    },
    {
      k: '共识 vs 指引',
      v: hasG ? formatPct(cur, e.guide) : '无指引',
      sub: hasG ? '共识低于指引，发布后大概率上修' : '美光只给下一季指引',
    },
  ];

  const stack = el('div', { className: 'stat-stack' });
  for (const s of stats) {
    const v = el('div', { className: 'stat-card__v', text: s.v });
    v.style.color = colorForSignedText(s.v);
    stack.appendChild(
      el('div', { className: 'stat-card' }, [
        el('div', { className: 'stat-card__k', text: s.k }),
        v,
        el('div', { className: 'stat-card__k', text: s.sub }),
      ]),
    );
  }

  const layout = el('div', { className: 'revision-layout' }, [card, stack]);
  return layout;
}
