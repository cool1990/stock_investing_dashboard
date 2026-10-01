import { createSegmented, el } from '../../components/segmented';
import { renderKpiCard } from '../../components/kpiCard';
import { renderBanner } from '../../components/banner';
import { renderFooterNote } from '../../components/footerNote';
import { renderTag, type TagKind } from '../../components/tag';
import { renderDataTable } from '../../components/dataTable';
import { colorClass, displayValue } from '../../components/placeholder';
import { formatRatioChange, MINUS } from '../../lib/fmt';

type Tone = string;

export interface ReviewPage {
  period: string;
  release: { date: string; timing: string; press_url: string | null; remarks_url: string | null };
  verdict: {
    label: string;
    line: {
      rev_surp: number | null;
      rev_surp_tone: Tone;
      eps_surp: number | null;
      eps_surp_tone: Tone;
      guide_vs_cons: Array<number | null>;
      guide_vs_cons_tone: Tone[];
    };
    summary: { text: string | null; refs: Array<{ src: string; quote: string }>; prompt_version?: string };
    watch: Array<{ title: string; text: string | null; confirmed: boolean; resolved: boolean }>;
  };
  cards: Array<{
    key: string;
    label: string;
    basis: string;
    value: number | null;
    unit: string;
    yoy: number | null;
    yoy_tone: Tone;
    qoq: number | null;
    qoq_tone: Tone;
    vs_cons: number | null;
    vs_cons_tone: Tone;
    why?: { text: string | null; refs: unknown[] };
  }>;
  metrics: Record<
    string,
    {
      label: string;
      basis: string;
      q: { labels: string[]; v: Array<number | null>; yoy: Array<number | null>; qoq: Array<number | null> };
      y: { labels: string[]; v: Array<number | null>; yoy: Array<number | null>; qoq: Array<number | null> };
      hist_note?: string;
      struct: Array<{
        title: string;
        src?: string;
        note?: string | null | { text?: string | null; refs?: unknown[] };
        rows: Array<{
          label: string;
          value?: number | null;
          val?: string | null;
          unit?: string;
          share?: number | null;
          sub?: string | null;
          pct?: number | null;
          tone?: number | string | null;
          yoy?: number | null;
          yoy_tone?: Tone;
          qoq?: number | null;
          qoq_tone?: Tone;
          bar?: number | null;
        }>;
      }>;
    }
  >;
  guidance: {
    groups: Array<{
      title: string;
      rows: Array<{
        name?: string;
        metric?: string;
        v?: string | null;
        value?: string | null;
        qoq: number | string | null;
        yoy: number | string | null;
        vs_cons: number | string | null;
        qoq_tone?: Tone;
        yoy_tone?: Tone;
        vs_cons_tone?: Tone;
        derived?: boolean;
      }>;
    }>;
    reasons: { text: string | null; refs: unknown[] };
  };
  talk: {
    mgmt: Array<{ topic: string; tag?: string; who?: string; now: string; prev?: string; ref?: string }>;
    qa: Array<{ topic: string; who: string; firm?: string; q: string; by?: string; a: string; ref?: string }>;
  };
}

function fmtCardValue(v: number | null, unit: string): string {
  if (v == null) return '[ ]';
  if (unit === '%') return `${v.toFixed(1)}%`;
  if (unit === '$') return `$${v.toFixed(2)}`;
  if (unit === 'B') return `$${v.toFixed(2)}B`;
  if (unit === 'M') return `$${Math.round(v).toLocaleString('en-US')}M`;
  return String(v);
}

function tagKind(tag?: string): TagKind {
  if (!tag) return 'new';
  if (/新|新增/.test(tag)) return 'new';
  if (/上|强化/.test(tag)) return 'up';
  if (/弱|变|下调/.test(tag)) return 'chg';
  return 'mid';
}

export function renderReviewPage(data: ReviewPage, ticker: string): HTMLElement {
  const metrics = data.metrics ?? {};
  let metricKey = Object.keys(metrics)[0] ?? 'rev';
  let histMode: 'q' | 'y' = 'q';
  let talkMode: 'mgmt' | 'qa' = 'mgmt';
  const root = el('main', { className: 'main review-page' });

  const paint = () => {
    root.replaceChildren();
    const timing = data.release?.timing === 'after_close' ? '盘后' : '盘前';
    root.appendChild(
      renderBanner(
        `${data.period} · ${data.release?.date ?? '[ ]'} ${timing}发布。数字来自 XBRL/共识；AI 摘要未确认时显示「AI 解读待生成」。`,
      ),
    );

    // Verdict
    const v = data.verdict;
    const verdict = el('section', { className: 'section' });
    verdict.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '1 回顾' }),
          el('div', { className: 'section__sub', text: '结论卡 · 六个 KPI · 本期关注' }),
        ]),
      ]),
    );
    const card = el('div', { className: 'card verdict-card' });
    card.append(
      el('div', { className: 'verdict-card__label' }, [renderTag(v.label, 'ok')]),
      el('div', { className: 'verdict-card__line mono' }, [
        el('span', {
          className: colorClass(v.line.rev_surp_tone),
          text: `收入 ${formatRatioChange(v.line.rev_surp)}`,
        }),
        el('span', { text: ' · ' }),
        el('span', {
          className: colorClass(v.line.eps_surp_tone),
          text: `EPS ${formatRatioChange(v.line.eps_surp)}`,
        }),
        el('span', { text: ' · 指引 vs 共识 ' }),
        ...(v.line.guide_vs_cons ?? []).map((g, i) =>
          el('span', {
            className: colorClass(v.line.guide_vs_cons_tone?.[i]),
            text: `${i ? ' / ' : ''}${formatRatioChange(g)}`,
          }),
        ),
      ]),
      el('p', {
        className: 'verdict-card__summary',
        text: v.summary.text ?? 'AI 解读待生成',
      }),
    );
    if (v.watch?.length) {
      const ul = el('ul', { className: 'watch-list' });
      for (const w of v.watch) {
        ul.appendChild(
          el('li', {}, [
            el('b', { text: w.title }),
            el('span', {
              className: w.text ? '' : 'faint',
              text: ` — ${w.text ?? 'AI 解读待生成'}`,
            }),
            w.confirmed ? renderTag('已确认', 'ok') : renderTag('待确认', 'mid'),
          ]),
        );
      }
      card.appendChild(ul);
    }
    verdict.appendChild(card);

    const kpi = el('div', { className: 'kpi-grid' });
    for (const c of data.cards) {
      kpi.appendChild(
        renderKpiCard({
          label: `${c.label} · ${c.basis}`,
          value: fmtCardValue(c.value, c.unit),
          sub: `同比 ${formatRatioChange(c.yoy, { asPp: c.unit === '%' })} · 环比 ${formatRatioChange(c.qoq, { asPp: c.unit === '%' })} · vs共识 ${formatRatioChange(c.vs_cons)}`,
          color: c.yoy_tone,
        }),
      );
    }
    verdict.appendChild(kpi);
    root.appendChild(verdict);

    // Metrics breakdown
    const keys = Object.keys(metrics);
    const m = metrics[metricKey];
    const metricSec = el('section', { className: 'section' });
    metricSec.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '指标拆解' }),
          el('div', { className: 'section__sub', text: m ? `${m.label} · ${m.basis}` : '拆解待新闻稿解析' }),
        ]),
        el('div', { className: 'toolbar' }, [
          keys.length
            ? createSegmented(
                '指标',
                keys.map((k) => ({ value: k, label: metrics[k].label })),
                metricKey,
                (v2) => {
                  metricKey = v2;
                  paint();
                },
              )
            : el('span', { className: 'faint', text: '暂无拆解指标' }),
          createSegmented(
            '历史视图',
            [
              { value: 'q', label: '季度' },
              { value: 'y', label: '年度' },
            ],
            histMode,
            (v2) => {
              histMode = v2 as 'q' | 'y';
              paint();
            },
          ),
        ]),
      ]),
    );
    if (m) {
      const series = histMode === 'q' ? m.q : m.y;
      const histCard = el('div', { className: 'card' });
      const bars = el('div', { className: 'hist-bars' });
      const nums = series.v.filter((x): x is number => x != null);
      const max = Math.max(...nums.map(Math.abs), 1);
      series.labels.forEach((lab, i) => {
        const val = series.v[i];
        const h = val == null ? 0 : (Math.abs(val) / max) * 100;
        const col = el('div', { className: 'hist-bars__col' });
        col.append(
          el('div', {
            className: 'hist-bars__bar',
            style: `height:${Math.max(h, val == null ? 0 : 4)}%`,
          }),
          el('div', { className: 'hist-bars__val mono', text: displayValue(val) }),
          el('div', { className: 'hist-bars__lab', text: lab }),
        );
        bars.appendChild(col);
      });
      histCard.appendChild(bars);
      if (m.hist_note) histCard.appendChild(el('div', { className: 'footnote', text: m.hist_note }));
      metricSec.appendChild(histCard);

      if (m.struct?.length) {
        const grid = el('div', { className: 'split-2' });
        for (const panel of m.struct) {
          const p = el('div', { className: 'card' });
          p.append(
            el('div', { className: 'card__head' }, [
              el('div', { className: 'card__title', text: panel.title }),
              el('div', { className: 'card__unit', text: panel.src ?? '' }),
            ]),
          );
          for (const row of panel.rows) {
            const line = el('div', { className: 'struct-row' });
            const mainVal =
              row.val ??
              (row.value == null
                ? '[ ]'
                : `${row.unit === '%' ? '' : '$'}${row.value}${row.unit === 'B' ? 'B' : row.unit === '%' ? '%' : ''}`);
            line.append(
              el('div', { className: 'struct-row__top' }, [
                el('span', { text: row.label }),
                el('span', { className: 'mono', text: mainVal }),
              ]),
              el('div', {
                className: 'struct-row__sub',
                text:
                  row.sub ??
                  [
                    row.share != null ? `占 ${(row.share * 100).toFixed(1)}%` : null,
                    row.yoy != null ? `同比 ${formatRatioChange(row.yoy)}` : null,
                    row.qoq != null ? `环比 ${formatRatioChange(row.qoq)}` : null,
                  ]
                    .filter(Boolean)
                    .join(' · '),
              }),
            );
            const barW =
              row.pct != null
                ? Math.max(0, Math.min(100, row.pct))
                : row.bar != null
                  ? Math.max(0, Math.min(100, row.bar * 100))
                  : row.share != null
                    ? row.share * 100
                    : 0;
            line.appendChild(el('div', { className: 'struct-row__bar' }, [el('i', { style: `width:${barW}%` })]));
            p.appendChild(line);
          }
          const noteText = typeof panel.note === 'string' ? panel.note : panel.note?.text;
          if (noteText) p.appendChild(el('div', { className: 'footnote', text: noteText }));
          grid.appendChild(p);
        }
        metricSec.appendChild(grid);
      }
    }
    root.appendChild(metricSec);

    // Guidance
    const gSec = el('section', { className: 'section' });
    gSec.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [el('h2', { text: '2 指引' }), el('div', { className: 'section__sub', text: '下季与明年目标' })]),
      ]),
    );
    for (const g of data.guidance?.groups ?? []) {
      const cardG = el('div', { className: 'card' });
      cardG.appendChild(el('div', { className: 'card__title', text: g.title }));
      cardG.appendChild(
        renderDataTable({
          headers: [
            { label: '指标', align: 'left' },
            { label: '数值' },
            { label: '隐含环比' },
            { label: '隐含同比' },
            { label: '较共识' },
          ],
          rows: g.rows.map((r) => ({
            cells: [
              { text: r.name ?? r.metric ?? '[ ]' },
              { text: r.v ?? r.value ?? '[ ]' },
              {
                text: typeof r.qoq === 'number' ? formatRatioChange(r.qoq) : r.qoq,
                color: r.qoq_tone,
              },
              {
                text: typeof r.yoy === 'number' ? formatRatioChange(r.yoy) : r.yoy,
                color: r.yoy_tone,
              },
              {
                text: typeof r.vs_cons === 'number' ? formatRatioChange(r.vs_cons) : r.vs_cons,
                color: r.vs_cons_tone,
              },
            ],
          })),
        }),
      );
      gSec.appendChild(cardG);
    }
    gSec.appendChild(
      el('div', {
        className: 'footnote',
        text: data.guidance?.reasons?.text ?? '管理层原因：AI 解读待生成',
      }),
    );
    root.appendChild(gSec);

    // Talk
    const talk = data.talk ?? { mgmt: [], qa: [] };
    const tSec = el('section', { className: 'section' });
    tSec.appendChild(
      el('div', { className: 'section__head' }, [
        el('div', {}, [
          el('h2', { text: '3 互动' }),
          el('div', { className: 'section__sub', text: '管理层表述 / 分析师提问' }),
        ]),
        el('div', { className: 'toolbar' }, [
          createSegmented(
            '互动',
            [
              { value: 'mgmt', label: '管理层表述' },
              { value: 'qa', label: '分析师提问' },
            ],
            talkMode,
            (v2) => {
              talkMode = v2 as 'mgmt' | 'qa';
              paint();
            },
          ),
          el('a', { href: `#/${ticker}/call/${data.period}`, text: '完整电话会 →' }),
        ]),
      ]),
    );
    const talkCard = el('div', { className: 'card' });
    if (talkMode === 'mgmt') {
      if (!talk.mgmt?.length) {
        talkCard.appendChild(el('p', { className: 'faint', text: '未接入' }));
      }
      for (const item of talk.mgmt ?? []) {
        const row = el('div', { className: 'talk-item' });
        row.append(
          el('div', { className: 'talk-item__head' }, [
            el('b', { text: item.topic }),
            item.tag ? renderTag(item.tag, tagKind(item.tag)) : '',
            item.who ? el('span', { className: 'faint', text: item.who }) : '',
          ]),
          el('p', { text: item.now }),
          item.prev ? el('p', { className: 'faint', text: `上期：${item.prev}` }) : '',
        );
        talkCard.appendChild(row);
      }
    } else {
      if (!talk.qa?.length) {
        talkCard.appendChild(el('p', { className: 'faint', text: '未接入' }));
      }
      for (const item of talk.qa ?? []) {
        const row = el('div', { className: 'talk-item' });
        row.append(
          el('div', { className: 'talk-item__head' }, [
            el('b', { text: item.topic }),
            el('span', { className: 'faint', text: `${item.who}${item.firm ? ` · ${item.firm}` : ''}` }),
          ]),
          el('p', { text: `Q：${item.q}` }),
          el('p', { text: `A${item.by ? `（${item.by}）` : ''}：${item.a}` }),
        );
        talkCard.appendChild(row);
      }
    }
    tSec.appendChild(talkCard);
    root.appendChild(tSec);

    root.appendChild(
      renderFooterNote([
        `${data.period}。超预期色类由后端给出；负号使用 ${MINUS}。AI 文案未接入时显示「未接入」。`,
        '新闻稿 / 准备稿链接仅作展示；缺失时不静默用第三方顶替。',
      ]),
    );
  };

  paint();
  return root;
}
