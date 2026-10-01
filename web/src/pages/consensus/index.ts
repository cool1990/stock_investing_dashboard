import type { ConsensusPage, GrowthKind, MetricKind, PeriodKind } from '../../lib/types';
import { createSegmented, el } from '../../components/segmented';
import { renderValuesCard, renderGrowthCard } from './gridTable';
import { renderTrendChart } from './trendChart';
import { renderForwardPe } from './forwardPe';
import { renderDetail } from './detailTable';
import { renderRevision } from './revisionChart';
import { renderHistoryChart, renderHistoryTable, renderHistoryTiles } from './history';

interface State {
  fm: MetricKind;
  gg: GrowthKind;
  price: string;
  ep: 'q' | 'y';
  hm: MetricKind;
  hp: PeriodKind;
}

export function renderConsensusPage(data: ConsensusPage): HTMLElement {
  const state: State = {
    fm: 'eps',
    gg: 'yoy',
    price: data.future.pe.last_close != null ? String(data.future.pe.last_close) : '',
    ep: 'q',
    hm: 'eps',
    hp: 'q',
  };

  const root = el('main', { className: 'main' });

  const paint = () => {
    root.replaceChildren();

    // ---- Section 1 ----
    const s1 = el('section', { className: 'section' });
    const metricSeg = createSegmented(
      '指标',
      [
        { value: 'eps', label: 'EPS（调整后）' },
        { value: 'rev', label: '营收' },
      ],
      state.fm,
      (v) => {
        state.fm = v as MetricKind;
        paint();
      },
    );
    s1.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '1 未来预期' }),
          el('div', {
            className: 'section__sub',
            text: '逐季 / 逐年的已公布值与分析师共识放在一张表里，右侧看增速，下方看走势和 Forward PE',
          }),
        ]),
        el('div', { style: 'display:flex;gap:8px;align-items:center' }, [
          el('span', { style: 'font-size:12px;color:var(--muted)', text: '指标' }),
          metricSeg,
        ]),
      ]),
    );
    s1.appendChild(el('div', { className: 'banner', text: data.meta.snapshot_note }));

    const growthSeg = createSegmented(
      '增速口径',
      [
        { value: 'yoy', label: '同比' },
        { value: 'pop', label: '环比' },
      ],
      state.gg,
      (v) => {
        state.gg = v as GrowthKind;
        paint();
      },
    );

    const grid = el('div', { className: 'future-grid' }, [
      renderValuesCard(data, state.fm),
      renderGrowthCard(data, state.fm, state.gg, growthSeg),
      renderTrendChart(data, state.fm),
      renderForwardPe(data, state.price, (v) => {
        state.price = v;
      }),
    ]);
    s1.appendChild(grid);
    s1.appendChild(
      el('div', { className: 'legend-row' }, [
        el('span', { className: 'legend-swatch' }, [
          el('i'),
          document.createTextNode('底色 = 分析师共识（预估）；无底色 = 已公布'),
        ]),
        document.createTextNode('季度为该公司财季'),
        document.createTextNode('n.m. = 基数为负或为零，增速无意义'),
        document.createTextNode('[ ] = 待接入'),
      ]),
    );
    s1.appendChild(renderDetail(data, state.fm));
    root.appendChild(s1);

    // ---- Section 2 ----
    const s2 = el('section', { className: 'section' });
    const rank = (k: string) => {
      const y = /(\d{2})$/.exec(k);
      const q = /FQ(\d)/.exec(k);
      return (y ? Number(y[1]) : 0) * 10 + (q ? Number(q[1]) : 0);
    };
    const revKeys = Object.keys(data.revision ?? {}).sort((a, b) => rank(a) - rank(b));
    const qKey = revKeys.find((k) => k.startsWith('FQ')) ?? revKeys[0] ?? '';
    const yKey = revKeys.find((k) => k.startsWith('FY')) ?? qKey;
    const revKey = state.ep === 'q' ? qKey : yKey;
    const revSeg = createSegmented(
      '期间',
      [
        { value: 'q', label: qKey ? `${qKey} EPS` : '季度 EPS' },
        { value: 'y', label: yKey ? `${yKey} EPS` : '年度 EPS' },
      ],
      state.ep,
      (v) => {
        state.ep = v as 'q' | 'y';
        paint();
      },
    );
    s2.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '2 共识演变' }),
          el('div', {
            className: 'section__sub',
            text: '共识在过去 90 天被怎样修正：修正的方向和速度，往往比共识水平本身更影响股价',
          }),
        ]),
        revSeg,
      ]),
    );
    s2.appendChild(renderRevision(data, revKey));
    root.appendChild(s2);

    // ---- Section 3 ----
    const s3 = el('section', { className: 'section' });
    const hMetric = createSegmented(
      '指标',
      [
        { value: 'eps', label: 'EPS' },
        { value: 'rev', label: '营收' },
      ],
      state.hm,
      (v) => {
        state.hm = v as MetricKind;
        paint();
      },
    );
    const hPeriod = createSegmented(
      '期间',
      [
        { value: 'q', label: '季度' },
        { value: 'y', label: '年度' },
      ],
      state.hp,
      (v) => {
        state.hp = v as PeriodKind;
        paint();
      },
    );
    s3.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '3 历史：预期、指引与实际' }),
          el('div', { className: 'section__sub', text: '评估分析师和管理层各自偏离实际多少' }),
        ]),
        el('div', { style: 'display:flex;gap:8px;align-items:center' }, [hMetric, hPeriod]),
      ]),
    );
    const rows = data.history[state.hm][state.hp];
    s3.append(
      renderHistoryTiles(data, state.hm, state.hp),
      renderHistoryChart(rows, state.hm),
      renderHistoryTable(data, state.hm, state.hp),
    );
    root.appendChild(s3);

    root.appendChild(
      el('footer', {
        className: 'page-footer',
        text: '未来预期与共识修正取自 Yahoo Finance 快照；已公布值优先公司新闻稿与 XBRL；历史共识取自 MarketBeat 并与 Yahoo 交叉校验。没有数据源的字段显示「未接入」。蓝 = 上调 / 好于预期，橙 = 下调 / 差于预期。',
      }),
    );
  };

  paint();
  return root;
}
