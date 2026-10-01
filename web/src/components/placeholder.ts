import { el } from './segmented';

const PLACEHOLDER_TEXTS = new Set(['[ ]', '[x.x]', '[±x%]', '[日期]', '不可得', '未披露', 'n.m.', '—', 'NM']);

export function isPlaceholder(v: unknown): boolean {
  if (v === null || v === undefined || v === '') return true;
  return typeof v === 'string' && (PLACEHOLDER_TEXTS.has(v) || v.startsWith('['));
}

export function displayValue(v: unknown, fallback = '[ ]'): string {
  if (isPlaceholder(v) && (v === null || v === undefined || v === '')) return fallback;
  if (v === null || v === undefined) return fallback;
  return String(v);
}

export function renderPlaceholder(text: string, title?: string): HTMLElement {
  return el('span', {
    className: 'ph',
    text,
    title: title ?? '数据尚未接入或不可得',
  });
}

export function colorClass(cls: string | null | undefined): string {
  if (!cls || cls === 'na') return 'faint';
  if (cls === 'up' || cls === 'down' || cls === 'flat' || cls === 'warn') return cls;
  return 'faint';
}
