import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AccountService } from './account.service';

describe('AccountService', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('fails closed when no HTTPS account backend is published', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ accountApiBase: '' }), {
      status: 200, headers: { 'Content-Type': 'application/json' }
    })));
    const service = TestBed.inject(AccountService);
    await service.initialize();
    expect(service.configured).toBe(false);
    expect(service.state).toBe('disabled');
    await expect(service.login('user@example.com', 'long-password')).rejects.toThrow('backend HTTPS não publicado');
  });

  it('accepts only an HTTPS runtime endpoint and keeps the access token out of localStorage', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        accountApiBase: 'https://api.nexuflow.example',
        privacyPolicyUrl: 'https://nexuflow.example/privacidade',
        termsUrl: 'https://nexuflow.example/termos'
      }), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        accessToken: 'opaque-session-token', expiresInSeconds: 3600,
        profile: { id: 'u1', email: 'user@example.com', displayName: 'User', emailVerified: true, plan: 'free', subscriptionStatus: 'free' }
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const service = TestBed.inject(AccountService);
    await service.initialize();
    await service.login('user@example.com', 'long-password');
    expect(service.authenticated).toBe(true);
    expect(service.profile?.id).toBe('u1');
    expect(Object.values(localStorage)).not.toContain('opaque-session-token');
    expect(fetchMock.mock.calls[1][0].toString()).toBe('https://api.nexuflow.example/v1/auth/login');
  });
});
