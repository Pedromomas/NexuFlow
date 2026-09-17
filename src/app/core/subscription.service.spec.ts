import { describe, expect, it } from 'vitest';
import { SubscriptionService } from './subscription.service';
describe('Subscription display pricing', () => {
  it('uses the requested prices with Brazilian decimal separators', () => {
    const service = new SubscriptionService();
    expect(service.plans.map(p => p.priceBrl)).toEqual([0.99, 4.99, 9.99, 79.99]);
    expect(service.plans.map(p => service.formatPrice(p.priceBrl))).toEqual(['0,99', '4,99', '9,99', '79,99']);
    expect(service.configured).toBe(false);
  });
});
