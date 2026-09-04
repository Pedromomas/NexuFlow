import { Injectable } from '@angular/core';
import { SubscriptionPlanId } from './subscription.service';

export type AccountState = 'disabled' | 'ready' | 'busy' | 'signed-in' | 'verification-required' | 'error';

export interface AccountProfile {
  id: string;
  email: string;
  displayName: string;
  emailVerified: boolean;
  plan: 'free' | SubscriptionPlanId;
  subscriptionStatus: 'free' | 'trial' | 'active' | 'past_due' | 'cancelled';
  subscriptionEndsAt?: string | null;
  duoInviteEmail?: string | null;
}

interface RuntimeConfig {
  accountApiBase?: string;
  privacyPolicyUrl?: string;
  termsUrl?: string;
}

interface SessionResponse {
  accessToken: string;
  expiresInSeconds: number;
  profile: AccountProfile;
}

@Injectable({ providedIn: 'root' })
export class AccountService {
  configured = false;
  initialized = false;
  state: AccountState = 'disabled';
  message = 'Contas entram no ar depois que o backend HTTPS e a política de privacidade forem publicados.';
  profile: AccountProfile | null = null;
  privacyPolicyUrl = '';
  termsUrl = '';

  private apiBase = '';
  private accessToken = '';
  private tokenExpiresAt = 0;

  async initialize(): Promise<void> {
    if (this.initialized) return;
    this.initialized = true;
    try {
      const configUrl = new URL('nexuflow-runtime-config.json', document.baseURI);
      const response = await fetch(configUrl, { cache: 'no-store', redirect: 'error' });
      if (!response.ok) throw new Error('Configuração de conta indisponível.');
      const config = await response.json() as RuntimeConfig;
      this.privacyPolicyUrl = this.safePublicUrl(config.privacyPolicyUrl);
      this.termsUrl = this.safePublicUrl(config.termsUrl);
      const endpoint = this.validateApiBase(config.accountApiBase);
      if (!endpoint || !this.privacyPolicyUrl || !this.termsUrl) return;
      this.apiBase = endpoint;
      this.configured = true;
      this.state = 'ready';
      this.message = 'Canal de conta protegido e pronto.';
    } catch {
      // Fail closed: the free local core remains available without pretending
      // that registration, login or payment succeeded.
    }
  }

  get authenticated(): boolean {
    return !!this.profile && !!this.accessToken && Date.now() < this.tokenExpiresAt;
  }

  async register(displayName: string, email: string, password: string): Promise<void> {
    this.requireConfigured();
    this.validateCredentials(displayName, email, password);
    this.state = 'busy'; this.message = 'Criando conta segura…';
    try {
      const result = await this.request<{ message?: string }>('/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ displayName: displayName.trim(), email: email.trim().toLowerCase(), password })
      });
      this.state = 'verification-required';
      this.message = result.message || 'Confira seu e-mail para confirmar a conta.';
    } catch (error) { this.fail(error); }
  }

  async login(email: string, password: string): Promise<void> {
    this.requireConfigured();
    this.validateCredentials('Conta NexuFlow', email, password);
    this.state = 'busy'; this.message = 'Entrando com conexão protegida…';
    try {
      const session = await this.request<SessionResponse>('/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase(), password })
      });
      if (!session.accessToken || session.expiresInSeconds < 60 || !session.profile?.id) {
        throw new Error('O servidor devolveu uma sessão inválida.');
      }
      this.accessToken = session.accessToken;
      this.tokenExpiresAt = Date.now() + Math.min(session.expiresInSeconds, 86_400) * 1000;
      this.profile = session.profile;
      this.state = 'signed-in';
      this.message = `Bem-vindo, ${session.profile.displayName}.`;
    } catch (error) { this.clearSession(); this.fail(error); }
  }

  async inviteDuo(email: string): Promise<void> {
    this.requireSession();
    const normalized = email.trim().toLowerCase();
    if (!this.validEmail(normalized)) throw new Error('Digite um e-mail válido para o convite.');
    this.state = 'busy'; this.message = 'Enviando convite seguro…';
    try {
      const profile = await this.request<AccountProfile>('/v1/account/duo-invite', {
        method: 'POST', body: JSON.stringify({ email: normalized })
      }, true);
      this.profile = profile; this.state = 'signed-in'; this.message = 'Convite enviado. O amigo precisa confirmar o próprio e-mail.';
    } catch (error) { this.fail(error); }
  }

  async requestCheckout(plan: SubscriptionPlanId): Promise<string> {
    this.requireSession();
    this.state = 'busy'; this.message = 'Criando checkout dentro do Mercado Pago…';
    try {
      const result = await this.request<{ checkoutUrl: string }>('/v1/billing/checkout', {
        method: 'POST', body: JSON.stringify({ plan })
      }, true);
      const url = new URL(result.checkoutUrl);
      if (url.protocol !== 'https:' || !/(^|\.)mercadopago\.com(\.br)?$/i.test(url.hostname)) {
        throw new Error('O servidor devolveu um checkout fora do Mercado Pago.');
      }
      this.state = 'signed-in'; this.message = 'Checkout oficial preparado.';
      return url.toString();
    } catch (error) { this.fail(error); throw error; }
  }

  async requestAccountDeletion(): Promise<void> {
    this.requireSession();
    this.state = 'busy'; this.message = 'Registrando solicitação de exclusão…';
    try {
      await this.request('/v1/account/delete-request', { method: 'POST', body: '{}' }, true);
      this.clearSession();
      this.state = 'ready'; this.message = 'Solicitação registrada. O servidor enviará a confirmação por e-mail.';
    } catch (error) { this.fail(error); }
  }

  logout(): void {
    this.clearSession();
    this.state = this.configured ? 'ready' : 'disabled';
    this.message = 'Sessão encerrada neste dispositivo.';
  }

  private validateApiBase(value?: string): string {
    if (!value?.trim()) return '';
    try {
      const url = new URL(value.trim());
      if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return '';
      return url.toString().replace(/\/$/, '');
    } catch { return ''; }
  }

  private safePublicUrl(value?: string): string {
    if (!value?.trim()) return '';
    try { const url = new URL(value); return url.protocol === 'https:' ? url.toString() : ''; }
    catch { return ''; }
  }

  private validateCredentials(displayName: string, email: string, password: string): void {
    if (displayName.trim().length < 2 || displayName.trim().length > 50) throw new Error('O nome precisa ter entre 2 e 50 caracteres.');
    if (!this.validEmail(email.trim())) throw new Error('Digite um e-mail válido.');
    if (password.length < 10 || password.length > 128) throw new Error('A senha precisa ter entre 10 e 128 caracteres.');
  }

  private validEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value.length <= 254;
  }

  private requireConfigured(): void {
    if (!this.configured) throw new Error('Cadastro ainda bloqueado: backend HTTPS não publicado.');
  }

  private requireSession(): void {
    this.requireConfigured();
    if (!this.authenticated) throw new Error('Entre na sua conta para continuar.');
  }

  private clearSession(): void {
    this.accessToken = ''; this.tokenExpiresAt = 0; this.profile = null;
  }

  private fail(error: unknown): void {
    this.state = 'error';
    this.message = error instanceof Error ? error.message : 'A operação não foi concluída.';
  }

  private async request<T = unknown>(path: string, init: RequestInit, authenticated = false): Promise<T> {
    const url = new URL(path, `${this.apiBase}/`);
    if (!url.pathname.startsWith('/v1/') || url.origin !== new URL(this.apiBase).origin) {
      throw new Error('Destino bloqueado pela política de rede da conta.');
    }
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    headers.set('Content-Type', 'application/json');
    if (authenticated) headers.set('Authorization', `Bearer ${this.accessToken}`);
    const response = await fetch(url, { ...init, headers, cache: 'no-store', redirect: 'error', credentials: 'omit' });
    if (!response.ok) {
      let detail = `Falha ${response.status}`;
      try { detail = (await response.json() as { detail?: string }).detail || detail; } catch { /* keep status */ }
      throw new Error(detail);
    }
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  }
}
