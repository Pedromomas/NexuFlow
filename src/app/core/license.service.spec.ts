import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountService } from './account.service';
import { LicenseService } from './license.service';

describe('LicenseService', () => {
  beforeEach(() => localStorage.clear());

  it('makes community features free irrespective of old account or license state', () => {
    const account = { authenticated: false, profile: { id: 'owner', emailVerified: true } };
    TestBed.overrideProvider(AccountService, { useValue: account });
    const service = TestBed.inject(LicenseService);
    service.payload = { schema: 1, subject: 'owner', installation: 'test', status: 'active',
      plan: 'month', entitlements: [], issuedAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 3600000).toISOString() };
    vi.spyOn(service as any, 'trustedNow').mockReturnValue(Date.now());
    expect(service.has('latency-lab')).toBe(true);
    account.authenticated = true;
    expect(service.has('latency-lab')).toBe(true);
    account.profile.id = 'other';
    expect(service.has('latency-lab')).toBe(true);
    account.profile.id = 'owner';
    account.profile.emailVerified = false;
    expect(service.has('latency-lab')).toBe(true);
    expect(service.has('safe-core')).toBe(true);
  });

  it('keeps the core free without granting premium or admin access', () => {
    const service = TestBed.inject(LicenseService);
    for (const feature of ['safe-core', 'network-basic', 'system-basic', 'themes', 'flux', 'latency-lab', 'dns-profiles']) {
      expect(service.has(feature)).toBe(true);
    }
    for (const feature of ['admin', 'arbitrary-privilege']) {
      expect(service.has(feature)).toBe(false);
    }
  });

  async function publicKey(): Promise<string> {
    const pair = await crypto.subtle.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify']) as CryptoKeyPair;
    const raw = new Uint8Array(await crypto.subtle.exportKey('raw', pair.publicKey));
    return btoa(String.fromCharCode(...raw));
  }

  it('never contacts the license endpoint during a protected game or active boost', async () => {
    const service = TestBed.inject(LicenseService);
    await service.initialize(await publicKey());
    const requestLicense = vi.fn();
    const account = { authenticated: true, requestLicense } as unknown as AccountService;
    await service.refreshWhenSafe(account, true, false);
    await service.refreshWhenSafe(account, false, true);
    expect(requestLicense).not.toHaveBeenCalled();
  });

  it('rejects an unsigned cached license', async () => {
    localStorage.setItem('nexuflow_signed_license_v1', JSON.stringify({
      algorithm: 'Ed25519', signature: btoa('not-a-real-signature'),
      payload: { schema: 1, subject: 'x', installation: 'y', status: 'active', plan: 'month', entitlements: [], issuedAt: new Date().toISOString(), expiresAt: new Date(Date.now() + 3600000).toISOString() }
    }));
    const service = TestBed.inject(LicenseService);
    await service.initialize(await publicKey());
    expect(service.payload).toBeNull();
    expect(service.status).toBe('error');
  });

  it('can retry online after a bad cache instead of discarding the public key', async () => {
    localStorage.setItem('nexuflow_signed_license_v1', '{broken');
    const service = TestBed.inject(LicenseService);
    await service.initialize(await publicKey());
    const requestLicense = vi.fn().mockRejectedValue(new Error('offline'));
    const account = { authenticated: true, requestLicense } as unknown as AccountService;
    await service.refreshWhenSafe(account, false, false);
    await service.refreshWhenSafe(account, false, false);
    expect(requestLicense).toHaveBeenCalledTimes(1);
    expect(service.has('admin')).toBe(false);
  });

  it('refuses future cached licenses even when their signature is valid', async () => {
    const pair = await crypto.subtle.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify']) as CryptoKeyPair;
    const payload = {
      entitlements: [], expiresAt: new Date(Date.now() + 7200000).toISOString(),
      installation: 'test', issuedAt: new Date(Date.now() + 3600000).toISOString(),
      plan: 'week', schema: 1, status: 'active', subject: 'test'
    };
    const signature = new Uint8Array(await crypto.subtle.sign('Ed25519', pair.privateKey,
      new TextEncoder().encode(JSON.stringify(payload))));
    localStorage.setItem('nexuflow_signed_license_v1', JSON.stringify({
      payload, algorithm: 'Ed25519', signature: btoa(String.fromCharCode(...signature))
    }));
    const raw = new Uint8Array(await crypto.subtle.exportKey('raw', pair.publicKey));
    const service = TestBed.inject(LicenseService);
    await service.initialize(btoa(String.fromCharCode(...raw)));
    expect(service.has('admin')).toBe(false);
    expect(service.status).toBe('error');
  });
});
