/** Shared formatting helpers (also covered by vitest). */

export const MISSING = '[ ]';
export const NM = 'n.m.';
export const MINUS = '−'; // U+2212

export function isNullish(v: unknown): v is null | undefined {
  return v === null || v === undefined;
}

/** YoY / PoP growth per 01_common: n.m. when base<=0 or (current<0 && base>0); [ ] when missing. */
export function formatGrowth(current: number | null | undefined, base: number | null | undefined): string {
  if (isNullish(current) || isNullish(base)) return MISSING;
  if (base <= 0 || (current < 0 && base > 0)) return NM;
  const p = (current / base - 1) * 100;
  const sign = p >= 0 ? '+' : MINUS;
  return `${sign}${Math.round(Math.abs(p))}%`;
}

/** Consensus revision etc.: keep 1 decimal when |p| < 100. */
export function formatPct(current: number | null | undefined, base: number | null | undefined): string {
  if (isNullish(current) || isNullish(base) || base === 0) return '—';
  const p = (current / base - 1) * 100;
  const sign = p >= 0 ? '+' : MINUS;
  const abs = Math.abs(p);
  const body = abs >= 100 ? String(Math.round(abs)) : abs.toFixed(1);
  return `${sign}${body}%`;
}

export function formatNum(v: number | null | undefined, digits = 2): string {
  if (isNullish(v)) return MISSING;
  if (v < 0) return `${MINUS}${Math.abs(v).toFixed(digits)}`;
  return v.toFixed(digits);
}

export function formatMoney(v: number | null | undefined, digits = 2, suffix = ''): string {
  if (isNullish(v)) return MISSING;
  return `$${formatNum(v, digits).replace(MINUS, MINUS)}${suffix}`;
}

export function formatEps(v: number | null | undefined): string {
  if (isNullish(v)) return MISSING;
  return `$${v < 0 ? MINUS : ''}${Math.abs(v).toFixed(2)}`;
}

export function formatRev(v: number | null | undefined): string {
  if (isNullish(v)) return MISSING;
  return `$${v.toFixed(2)}B`;
}

export function colorForSignedText(v: string): string {
  if (!v) return 'var(--ink)';
  const ch = v.charAt(0);
  if (ch === '+') return 'var(--up)';
  if (ch === MINUS || ch === '-') return 'var(--down)';
  if (v === '—' || v === MISSING || v === NM || v === '不可得' || v.startsWith('[')) return 'var(--faint)';
  return 'var(--ink)';
}

export function peMultiple(price: number | null | undefined, eps: number | null | undefined): string {
  if (!price || price <= 0 || isNullish(eps) || eps <= 0) return '[x.x]';
  return (price / eps).toFixed(1);
}

export function ttmShare(ttm: number, eps: number | null | undefined): string {
  if (isNullish(eps) || eps === 0) return MISSING;
  return `${Math.round((ttm / eps) * 100)}%`;
}

/** Precomputed change ratio (e.g. 0.056 → +5.6%). */
export function formatRatioChange(
  r: number | null | undefined,
  opts: { asPp?: boolean; digits?: number } = {},
): string {
  if (isNullish(r)) return MISSING;
  const { asPp = false, digits = 1 } = opts;
  if (asPp) {
    const pp = r * 100;
    const sign = pp >= 0 ? '+' : MINUS;
    return `${sign}${Math.abs(pp).toFixed(digits)}pp`;
  }
  const p = r * 100;
  const sign = p >= 0 ? '+' : MINUS;
  const abs = Math.abs(p);
  const body = abs >= 1000 ? String(Math.round(abs)) : abs.toFixed(digits);
  return `${sign}${body}%`;
}

export function formatAmtMillions(v: number | null | undefined, unit: 'M' | 'B'): string {
  if (isNullish(v)) return MISSING;
  const neg = v < 0;
  const abs = Math.abs(v);
  const body = unit === 'B' ? (abs / 1000).toFixed(2) : Math.round(abs).toLocaleString('en-US');
  return neg ? `${MINUS}${body}` : body;
}

/** A percent already stored in percent units (0.64 → 0.64%, not 64%). */
export function formatStoredPct(v: number | null | undefined, digits = 1): string {
  if (isNullish(v)) return MISSING;
  const sign = v < 0 ? MINUS : '';
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}

export function formatTablePct(v: number | null | undefined): string {
  if (isNullish(v)) return MISSING;
  return formatRatioChange(v);
}
