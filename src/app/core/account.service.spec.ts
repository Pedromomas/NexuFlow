import { TestBed } from '@angular/core/testing';
import { OFFLINE_ACCOUNT_MODE } from './build-mode';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { AccountService } from './account.service';

@Component({standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<p>{{account.state}} {{account.message}} {{account.profile?.displayName}}</p>'})
class AccountStateProbe { account = inject(AccountService); }

describe('AccountService', () => {
  beforeEach(() => TestBed.configureTestingModule({providers: [{provide: OFFLINE_ACCOUNT_MODE, useValue: false}]}));
  afterEach(() => vi.unstubAllGlobals());

  it('does not restore a session when a late login completes after logout', async () => {
    let finish!: (response: Response) => void;
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({
      accountApiBase: 'https://nexuflow-api-dev.onrender.com', loginOnly: true
    }))).mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    const service = TestBed.inject(AccountService);
    await service.initialize();
    const pending = service.login('test@example.com', 'long-password');
    await service.login('test@example.com', 'long-password');
    expect(fetchMock).toHaveBeenCalledTimes(2);
    service.logout();
    finish(new Response(JSON.stringify({accessToken: 'token', refreshToken: 'refresh', expiresInSeconds: 3600,
      profile: {id: 'late', displayName: 'Late', email: 'test@example.com'}})));
    await pending;
    expect(service.authenticated).toBe(false);
    expect(service.profile).toBeNull();
  });

  it('updates an OnPush view after password-reset response without another click', async () => {
    let finish!: (value: Response) => void;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({
      accountApiBase: 'https://nexuflow-api-dev.onrender.com', loginOnly: true
    }))).mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; })));
    const fixture = TestBed.createComponent(AccountStateProbe);
    await fixture.componentInstance.account.initialize();
    fixture.autoDetectChanges();
    const pending = fixture.componentInstance.account.resetPassword('test@example.com');
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('busy');
    finish(new Response(JSON.stringify({message: 'Confira o e-mail.'})));
    await pending;
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('ready Confira o e-mail.');
  });

  it('leaves busy state when an authentication request times out', async () => {
    vi.useFakeTimers();
    try {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({
        accountApiBase: 'https://nexuflow-api-dev.onrender.com', loginOnly: true
      }))).mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
      })));
      const service = TestBed.inject(AccountService);
      await service.initialize();
      const pending = service.login('test@example.com', 'long-password');
      await vi.advanceTimersByTimeAsync(90_000);
      await pending;
      expect(service.state).toBe('error');
      expect(service.message).toContain('demorou');
      expect(service.authenticated).toBe(false);
    } finally { vi.useRealTimers(); }
  });

  it('permits explicit existing-account testing without opening registration', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      accountApiBase: 'https://nexuflow-api-dev.onrender.com', loginOnly: true
    }), {status: 200}));
    vi.stubGlobal('fetch', fetchMock);
    const service = TestBed.inject(AccountService);
    await service.initialize();
    expect(service.configured).toBe(true);
    expect(service.registrationEnabled).toBe(false);
    await expect(service.register('Test', 'test@example.com', 'long-password')).rejects.toThrow('Novos cadastros');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not silently enable login when legal configuration is absent', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      accountApiBase: 'https://nexuflow-api-dev.onrender.com'
    }), {status: 200})));
    const service = TestBed.inject(AccountService);
    await service.initialize();
    expect(service.configured).toBe(false);
  });

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
        legalVersion: 'test-1',
        privacyPolicyUrl: 'https://nexuflow.example/privacidade',
        termsUrl: 'https://nexuflow.example/termos'
      }), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        accessToken: 'opaque-session-token', refreshToken: 'opaque-refresh-token-value', expiresInSeconds: 3600,
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
