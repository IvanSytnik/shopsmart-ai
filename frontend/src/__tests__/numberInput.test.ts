import { describe, expect, it } from 'vitest';
import { normalizeDecimalInput, parseDecimal } from '../numberInput';

describe('normalizeDecimalInput', () => {
  it.each([
    ['', ''],
    ['040', '40'],
    ['0', '0'],
    ['00', '0'],
    ['0,5', '0,5'],
    ['12,5', '12,5'],
    ['12.5', '12.5'],
    ['1,2,3', '1,23'],
    ['€ 50', '50'],
    ['-20', '20'],
  ])('%j → %j', (raw, expected) => {
    expect(normalizeDecimalInput(raw)).toBe(expected);
  });
});

describe('parseDecimal', () => {
  it('reads comma and dot decimals, empty is NaN', () => {
    expect(parseDecimal('12,5')).toBe(12.5);
    expect(parseDecimal('12.5')).toBe(12.5);
    expect(parseDecimal('40')).toBe(40);
    expect(parseDecimal('')).toBeNaN();
  });
});
