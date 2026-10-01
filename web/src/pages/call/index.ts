import { createSegmented, el } from '../../components/segmented';
import { renderBanner } from '../../components/banner';
import { renderFooterNote } from '../../components/footerNote';
import { renderTag } from '../../components/tag';
export interface CallPage {
  period: string;
  date_et: string;
  duration_min: number | null;
  status: string;
  links: { remarks_pdf: string | null; webcast: string | null; third_party: string | null };
  executives: Array<{ ini: string; name: string; role_zh: string }>;
  guidance: Array<{ label: string; v: string }>;
  prev_period: string;
  speakers: Array<{
    ini: string;
    name: string;
    role: string;
    rel?: string;
    cols: Array<{
      title: string;
      items: Array<{ topic?: string; tag?: string; text: string; ref?: string; prev?: string }>;
    }>;
  }>;
  qa_topics: Array<{ topic: string; n: number }>;
  qa: Array<{
    analyst: string;
    firm?: string;
    ts?: string;
    topic: string;
    turns: Array<{ kind?: string; q?: string; who?: string; a?: string; src?: string }>;
  }>;
  transcript: {
    sources: Array<{ id: string; label: string; note?: string } | string>;
    paras: Array<{
      id: string;
      src: string;
      ts?: string;
      who: string;
      role?: string;
      en: string;
      zh: string | null;
    }>;
  };
  corrections?: string[];
  ai?: { model: string; prompts?: Record<string, string> };
}

export function renderCallPage(data: CallPage, ticker: string): HTMLElement {
  let tab: 'points' | 'qa' | 'transcript' = 'points';
  const sources = data.transcript?.sources ?? [];
  let srcId = sources.length
    ? typeof sources[0] === 'string'
      ? sources[0]
      : sources[0]?.id ?? 'remarks'
    : '';
  let query = '';
  const root = el('main', { className: 'main call-page' });

  const sourceMeta = () => {
    const s = data.transcript.sources.find((x) =>
      typeof x === 'string' ? x === srcId : x.id === srcId,
    );
    if (!s) return { label: srcId, note: '' };
    if (typeof s === 'string') return { label: s, note: '' };
    return { label: s.label, note: s.note ?? '' };
  };

  const paint = () => {
    root.replaceChildren();
    const remarksMissing = !data.links.remarks_pdf;
    root.appendChild(
      renderBanner(
        remarksMissing
          ? '准备稿未获取。原文 tab 可切换第三方来源，但必须明确标注，不得静默顶替官方准备稿。'
          : `${data.period} 电话会 · ${data.date_et} ET · 状态 ${data.status}`,
      ),
    );

    const head = el('div', { className: 'section__head' }, [
      el('div', {}, [
        el('h2', { text: '电话会' }),
        el('div', {
          className: 'section__sub',
          text: `时长 ${data.duration_min != null ? data.duration_min : '未接入'} 分钟 · 上期 ${data.prev_period || '未接入'}`,
        }),
      ]),
      el('div', { className: 'toolbar' }, [
        createSegmented(
          '电话会区块',
          [
            { value: 'points', label: '要点' },
            { value: 'qa', label: '问答' },
            { value: 'transcript', label: '原文' },
          ],
          tab,
          (v) => {
            tab = v as typeof tab;
            paint();
          },
        ),
        data.links.remarks_pdf
          ? el('a', { href: data.links.remarks_pdf, target: '_blank', rel: 'noopener', text: '准备稿 PDF' })
          : el('span', { className: 'faint', text: '准备稿未获取' }),
        data.links.webcast
          ? el('a', { href: data.links.webcast, target: '_blank', rel: 'noopener', text: 'Webcast' })
          : '',
        el('a', { href: `#/${ticker}/review/${data.period}`, text: '← 财报解读' }),
      ]),
    ]);
    root.appendChild(el('section', { className: 'section' }, [head]));

    if (tab === 'points') {
      const exec = el('div', { className: 'split-2' });
      for (const e of data.executives) {
        exec.appendChild(
          el('div', { className: 'card' }, [
            el('div', { className: 'card__title', text: `${e.ini} · ${e.name}` }),
            el('div', { className: 'section__sub', text: e.role_zh }),
          ]),
        );
      }
      root.appendChild(exec);

      if (data.guidance.length) {
        const g = el('div', { className: 'card' });
        g.appendChild(el('div', { className: 'card__title', text: '本期指引要点' }));
        const ul = el('ul');
        for (const item of data.guidance) ul.appendChild(el('li', { text: `${item.label}：${item.v}` }));
        g.appendChild(ul);
        root.appendChild(g);
      }

      if (!data.speakers.length) {
        root.appendChild(el('div', { className: 'card faint', text: '要点待生成' }));
      }
      for (const sp of data.speakers) {
        const card = el('div', { className: 'card' });
        card.append(
          el('div', { className: 'card__head' }, [
            el('div', { className: 'card__title', text: `${sp.name}（${sp.ini}）` }),
            el('div', { className: 'card__unit', text: sp.role }),
          ]),
        );
        const cols = el('div', { className: 'split-2' });
        for (const col of sp.cols) {
          const c = el('div', {});
          c.appendChild(el('div', { className: 'card__title', text: col.title }));
          for (const it of col.items) {
            const line = it.topic ? `${it.topic}：${it.text}` : it.text;
            c.appendChild(
              el('div', { className: 'talk-item' }, [
                it.tag ? renderTag(it.tag, /新/.test(it.tag) ? 'new' : /变|弱/.test(it.tag) ? 'chg' : 'up') : '',
                el('p', { text: line || '待生成' }),
                it.prev ? el('div', { className: 'talk-prev', text: `上一场：${it.prev}` }) : '',
              ]),
            );
          }
          cols.appendChild(c);
        }
        card.appendChild(cols);
        root.appendChild(card);
      }
    } else if (tab === 'qa') {
      const topics = el('div', { className: 'toolbar' });
      for (const t of data.qa_topics) {
        topics.appendChild(renderTag(`${t.topic} ${t.n}`, 'up'));
      }
      root.appendChild(topics);
      if (!data.qa.length) {
        root.appendChild(el('div', { className: 'card faint', text: '问答待生成' }));
      }
      for (const q of data.qa) {
        const card = el('div', { className: 'card talk-item' });
        card.append(
          el('div', { className: 'talk-item__head' }, [
            el('b', { text: q.topic }),
            el('span', {
              className: 'faint',
              text: `${q.analyst}${q.firm ? ` · ${q.firm}` : ''}${q.ts ? ` · ${q.ts}` : ''}`,
            }),
          ]),
        );
        for (const turn of q.turns) {
          if (turn.q) card.appendChild(el('p', { text: `Q：${turn.q}` }));
          if (turn.a) card.appendChild(el('p', { text: `A${turn.who ? `（${turn.who}）` : ''}：${turn.a}` }));
        }
        root.appendChild(card);
      }
    } else {
      if (!sources.length) {
        root.appendChild(el('div', { className: 'card faint', text: '未接入：没有电话会原文来源。' }));
        return;
      }
      const srcOpts = sources.map((s) =>
        typeof s === 'string'
          ? { value: s, label: s === 'remarks' ? '官方准备稿' : s }
          : { value: s.id, label: s.label },
      );
      const meta = sourceMeta();
      const bar = el('div', { className: 'toolbar' }, [
        createSegmented('原文来源', srcOpts, srcId, (v) => {
          srcId = v;
          paint();
        }),
        el('span', {
          className: meta.note || srcId !== 'remarks' ? 'tag tag--chg' : 'faint',
          text: meta.note || (srcId === 'remarks' ? '来源：官方准备稿' : `来源：${meta.label}`),
        }),
      ]);
      const search = el('input', {
        className: 'call-search',
        type: 'search',
        placeholder: '搜索原文',
        value: query,
        'aria-label': '搜索电话会原文',
      }) as HTMLInputElement;
      search.value = query;
      search.addEventListener('input', () => {
        query = search.value.trim();
        paintBody();
      });
      root.append(bar, search);

      const body = el('div', { className: 'card transcript-body' });
      const paintBody = () => {
        body.replaceChildren();
        const matched = data.transcript.paras.filter((p) => !p.src || p.src === srcId);
        const list = (matched.length ? matched : data.transcript.paras).filter((p) => {
          if (!query) return true;
          return `${p.en} ${p.zh ?? ''}`.toLowerCase().includes(query.toLowerCase());
        });
        if (!list.length) {
          body.appendChild(
            el('p', {
              className: 'faint',
              text:
                srcId === 'remarks' && remarksMissing
                  ? '准备稿未获取'
                  : '文字稿未获取或无匹配段落',
            }),
          );
          return;
        }
        for (const p of list) {
          body.appendChild(
            el('div', { className: 'transcript-para', id: p.id }, [
              el('div', {
                className: 'transcript-para__meta faint',
                text: `${p.ts ?? ''} ${p.who}${p.role ? ` · ${p.role}` : ''} · 来源 ${p.src}`,
              }),
              el('p', { text: p.en }),
              el('p', {
                className: 'transcript-para__zh',
                text: p.zh ?? '中文翻译待生成',
              }),
            ]),
          );
        }
      };
      paintBody();
      root.appendChild(body);
    }

    root.appendChild(
      renderFooterNote([
        '准备稿缺失时显示「准备稿未获取」；第三方文字稿必须标注来源。',
        `AI model: ${data.ai?.model ?? 'cursor-manual'}（手动模式）`,
      ]),
    );
  };

  paint();
  return root;
}
