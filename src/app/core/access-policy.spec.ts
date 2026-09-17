import { describe, expect, it } from 'vitest';
import { FREE_FEATURES, grantsPaidFeature } from './access-policy';

describe('community feature policy', () => {
  it('includes every formerly advanced feature without payment or login', () => {
    for (const feature of ['safe-core', 'network-basic', 'system-basic', 'themes', 'flux', 'latency-lab', 'dns-profiles']) {
      expect(FREE_FEATURES.has(feature)).toBe(true);
    }
    expect(FREE_FEATURES.has('admin')).toBe(false);
  });
});

describe('paid feature policy', () => {
  it('allows only the defined advanced features for paid or trial access', () => {
    for (const status of ['active', 'trial']) {
      expect(grantsPaidFeature({status, entitlements: []}, 'latency-lab')).toBe(true);
      expect(grantsPaidFeature({status, entitlements: []}, 'dns-profiles')).toBe(true);
      for (const feature of ['admin', 'theme:kiwi', 'unknown-future-feature']) {
        expect(grantsPaidFeature({status, entitlements: []}, feature)).toBe(false);
      }
    }
  });
  it('does not convert a cosmetic code into a subscription', () => {
    expect(grantsPaidFeature({status: 'free', entitlements: ['theme:kiwi']}, 'latency-lab')).toBe(false);
  });
  it('honors an explicit lifetime entitlement but not a revoked status', () => {
    expect(grantsPaidFeature({status: 'free', entitlements: ['premium:lifetime']}, 'dns-profiles')).toBe(true);
    for (const status of ['cancelled', 'past_due', 'unknown']) {
      expect(grantsPaidFeature({status, entitlements: ['premium:lifetime']}, 'dns-profiles')).toBe(false);
    }
  });
});
