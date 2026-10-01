import { el } from './segmented';

export type TagKind = 'new' | 'up' | 'chg' | 'ok' | 'mid' | 'bad' | 'alert';

const KIND_CLASS: Record<TagKind, string> = {
  new: 'tag tag--new',
  up: 'tag tag--up',
  chg: 'tag tag--chg',
  ok: 'tag tag--ok',
  mid: 'tag tag--mid',
  bad: 'tag tag--bad',
  alert: 'tag tag--alert',
};

export function renderTag(label: string, kind: TagKind = 'new'): HTMLElement {
  return el('span', { className: KIND_CLASS[kind], text: label });
}
