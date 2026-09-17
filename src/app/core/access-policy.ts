/** Product access policy, not a substitute for native/server authorization. */
export const FREE_FEATURES = new Set([
  'safe-core', 'network-basic', 'system-basic', 'themes', 'flux', 'latency-lab', 'dns-profiles'
]);
export const PAID_FEATURES = new Set(['latency-lab', 'dns-profiles']);

export function grantsPaidFeature(
  payload: {status: string; entitlements: string[]}, feature: string
): boolean {
  // A paid subscription must never imply admin, arbitrary future capabilities,
  // or cosmetic rewards that have not been redeemed.
  if (!PAID_FEATURES.has(feature)) return false;
  if (payload.status === 'cancelled' || payload.status === 'past_due') return false;
  return payload.status === 'active' || payload.status === 'trial' ||
    (payload.status === 'free' && payload.entitlements.includes('premium:lifetime'));
}
