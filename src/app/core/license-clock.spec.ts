import { describe, expect, it } from 'vitest';
import { LicenseClock } from './license-clock';

describe('LicenseClock', () => {
  it('uses server time even when Windows has the wrong date', () => {
    let wall = 900000000;
    let monotonic = 100;
    const clock = new LicenseClock(() => wall, () => monotonic);
    clock.anchor(1000000);
    wall += 60000; monotonic += 60000;
    expect(clock.now()).toBe(1060000);
  });

  it('small repeated clock changes cannot extend a session', () => {
    let wall = 1000000;
    let monotonic = 0;
    const clock = new LicenseClock(() => wall, () => monotonic);
    clock.anchor(wall);
    monotonic += 120000;
    expect(clock.now()).toBe(1120000);
    monotonic += 240000;
    expect(clock.now()).toBeNull();
  });

  it.each([-86400000, 86400000])('requires revalidation after a date change of %s ms', shift => {
    let wall = 1000000;
    const clock = new LicenseClock(() => wall, () => 0);
    clock.anchor(wall);
    wall += shift;
    expect(clock.now()).toBeNull();
    wall = 1000000;
    expect(clock.now()).toBeNull();
    clock.anchor(2000000);
    expect(clock.now()).toBe(2000000);
  });
});
