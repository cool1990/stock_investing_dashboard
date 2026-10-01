import { describe, expect, it } from 'vitest';
import { formatGrowth, formatPct, peMultiple, ttmShare, MINUS, NM, MISSING } from './fmt';

describe('formatGrowth', () => {
  it('FY24 Q1 vs FY23 Q1 → n.m.', () => {
    expect(formatGrowth(-0.95, 0.04)).toBe(NM);
  });
  it('FY25 full year vs FY24 → +538%', () => {
    expect(formatGrowth(8.29, 1.3)).toBe('+538%');
  });
  it('FY26 Q4 YoY → +1003%', () => {
    expect(formatGrowth(33.42, 3.03)).toBe('+1003%');
  });
  it('FY24 Q3 PoP → +48%', () => {
    expect(formatGrowth(0.62, 0.42)).toBe('+48%');
  });
  it('missing → [ ]', () => {
    expect(formatGrowth(null, 1)).toBe(MISSING);
  });
});

describe('formatPct / PE', () => {
  it('uses unicode minus', () => {
    expect(formatPct(0.5, 1)).toBe(`${MINUS}50.0%`);
  });
  it('price 400 → TTM PE 5.3, FY27 2.6', () => {
    expect(peMultiple(400, 75.52)).toBe('5.3');
    expect(peMultiple(400, 156.53)).toBe('2.6');
  });
  it('TTM share for FY27 ≈ 48%', () => {
    expect(ttmShare(75.52, 156.53)).toBe('48%');
  });
});
