import { Injectable, signal, inject } from '@angular/core';
import { OFFLINE_ACCOUNT_MODE } from './build-mode';
import { SubscriptionPlanId } from './subscription.service';

export type AccountState = 'disabled' | 'ready' | 'busy' | 'signed-in' | 'verification-required' | 'error';

export interface AccountProfile {
  id: string;
  email: string;
  displayName: string;
  emailVerified: boolean;
  isAdmin?: boolean;
  plan: 'free' | 'lifetime' | 'access-code' | SubscriptionPlanId;
  subscriptionStatus: 'free' | 'trial' | 'active' | 'past_due' | 'cancelled';
  subscriptionEndsAt?: string | null;
  duoInviteEmail?: string | null;
}

interface RuntimeConfig {
  legalVersion?: string;
  loginOnly?: boolean;
  accountApiBase?: string;
  privacyPolicyUrl?: string;
  termsUrl?: string;
  licensePublicKey?: string;
}

interface SessionResponse {
  accessToken: string;
  refreshToken: string;
  expiresInSeconds: number;
  profile: AccountProfile;
}

@Injectable({ providedIn: 'root' })
export class AccountService {
  private readonly offline = inject(OFFLINE_ACCOUNT_MODE);
  private readonly configuredValue = signal(false);
  get configured(): boolean { return this.configuredValue(); }
  set configured(value: boolean) { this.configuredValue.set(value); }
  private readonly registrationValue = signal(false);
  get registrationEnabled(): boolean { return this.registrationValue(); }
  set registrationEnabled(value: boolean) { this.registrationValue.set(value); }
  initialized = false;
  private readonly stateValue = signal<AccountState>('disabled');
  get state(): AccountState { return this.stateValue(); }
  set state(value: AccountState) { this.stateValue.set(value); }
  private readonly messageValue = signal('Contas entram no ar depois que o backend HTTPS e a política de privacidade forem publicados.');
  get message(): string { return this.messageValue(); }
  set message(value: string) { this.messageValue.set(value); }
  private readonly profileValue = signal<AccountProfile | null>(null);
  get profile(): AccountProfile | null { return this.profileValue(); }
  set profile(value: AccountProfile | null) { this.profileValue.set(value); }
  privacyPolicyUrl = '';
  termsUrl = '';
  licensePublicKey = '';
  private legalVersion = '';

  private apiBase = '';
  private accessToken = '';
  private refreshToken = '';
  private tokenExpiresAt = 0;
  private sessionGeneration = 0;
  private readonly pendingRequests = new Set<AbortController>();

  async initialize(): Promise<void> {
    if (this.initialized) return;
    this.initialized = true;
    if (this.offline) return;
    try {
      const configUrl = new URL('nexuflow-runtime-config.json', document.baseURI);
      const response = await fetch(configUrl, { cache: 'no-store', redirect: 'error' });
      if (!response.ok) throw new Error('Configuração de conta indisponível.');
      const config = await response.json() as RuntimeConfig;
      this.privacyPolicyUrl = this.safePublicUrl(config.privacyPolicyUrl);
      this.termsUrl = this.safePublicUrl(config.termsUrl);
      this.licensePublicKey = this.safeBase64Key(config.licensePublicKey);
      const endpoint = this.validateApiBase(config.accountApiBase);
      if (!endpoint) return;
      this.legalVersion = typeof config.legalVersion === 'string' && /^[A-Za-z0-9._-]{1,80}$/.test(config.legalVersion) && !/draft/i.test(config.legalVersion) ? config.legalVersion : '';
      const legalReady = !!this.privacyPolicyUrl && !!this.termsUrl && !!this.legalVersion;
      if (!legalReady && config.loginOnly !== true) return;
      this.registrationEnabled = legalReady && config.loginOnly !== true;
      this.apiBase = endpoint;
      this.configured = true;
      this.state = 'ready';
      this.message = this.registrationEnabled ? 'Canal de conta protegido e pronto.' : 'Teste de login para contas existentes. Novos cadastros e cobranças estão desativados.';
    } catch {
      // Fail closed: the free local core remains available without pretending
      // that registration, login or payment succeeded.
    }
  }

  get authenticated(): boolean {
    return !!this.profile && !!this.accessToken && (Date.now() < this.tokenExpiresAt || !!this.refreshToken);
  }

  async register(displayName: string, email: string, password: string, acceptedTerms = false): Promise<void> {
    this.requireConfigured();
    if (!this.registrationEnabled) throw new Error('Novos cadastros ainda não estão liberados. Use uma conta de teste já criada.');
    if (!acceptedTerms) throw new Error('Leia e aceite os documentos antes de criar a conta.');
    if (this.state === 'busy') return;
    this.validateCredentials(displayName, email, password);
    this.state = 'busy'; this.message = 'Criando conta segura…';
    try {
      const result = await this.request<{ message?: string }>('/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ displayName: displayName.trim(), email: email.trim().toLowerCase(), password, acceptedTerms, legalVersion: this.legalVersion })
      });
      this.state = 'verification-required';
      this.message = result.message || 'Confira seu e-mail para confirmar a conta.';
    } catch (error) { this.fail(error); }
  }

  async login(email: string, password: string): Promise<void> {
    this.requireConfigured();
    if (this.state === 'busy') return;
    this.validateCredentials('Conta NexuFlow', email, password);
    this.state = 'busy'; this.message = 'Entrando com conexão protegida…';
    try {
      const session = await this.request<SessionResponse>('/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase(), password })
      });
      this.applySession(session);
      this.state = 'signed-in';
      this.message = `Bem-vindo, ${session.profile.displayName}.`;
    } catch (error) { this.clearSession(); this.fail(error); }
  }

  async resetPassword(email: string): Promise<void> {
    this.requireConfigured();
    if (this.state === 'busy') return;
    const normalized = email.trim().toLowerCase();
    if (!this.validEmail(normalized)) throw new Error('Digite um e-mail válido.');
    this.state = 'busy'; this.message = 'Solicitando redefinição segura…';
    try {
      const result = await this.request<{ message?: string }>('/v1/auth/password-reset', {
        method: 'POST', body: JSON.stringify({ email: normalized })
      });
      this.state = 'ready';
      this.message = result.message || 'Se a conta existir, enviaremos as instruções por e-mail.';
    } catch (error) { this.fail(error); }
  }

  async resendVerification(): Promise<void> {
    this.requireSession();
    if (this.state === 'busy') return;
    this.state = 'busy';
    try {
      const result = await this.request<{ message: string }>('/v1/auth/verify-email', { method: 'POST' }, true);
      this.state = 'signed-in'; this.message = result.message;
    } catch (error) { this.fail(error); }
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

  async removeDuo(): Promise<void> {
    this.requireSession();
    this.state = 'busy'; this.message = 'Removendo o acesso compartilhado…';
    try {
      this.profile = await this.request<AccountProfile>('/v1/account/duo-invite', { method: 'DELETE' }, true);
      this.state = 'signed-in'; this.message = 'Acesso do amigo removido.';
    } catch (error) { this.fail(error); }
  }

  async redeemAccessCode(code: string): Promise<string[]> {
    this.requireSession();
    const normalized = code.trim().toUpperCase();
    if (normalized.length < 12 || normalized.length > 128) throw new Error('Código inválido.');
    const result = await this.request<{ rewards: string[] }>('/v1/codes/redeem', {
      method: 'POST', body: JSON.stringify({ code: normalized })
    }, true);
    this.profile = await this.request<AccountProfile>('/v1/account/profile', { method: 'GET' }, true);
    return Array.isArray(result.rewards) ? result.rewards : [];
  }

  async requestCheckout(plan: SubscriptionPlanId): Promise<string> {
    this.requireSession();
    throw new Error('Cobranças reais ainda não estão liberadas. O teste PagBank é separado e restrito à administração.');
  }

  async requestSandboxCheckout(plan: SubscriptionPlanId): Promise<string> {
    this.requireSession();
    if (!this.profile?.isAdmin || !this.profile.emailVerified) throw new Error('O teste exige administrador com e-mail confirmado.');
    const result = await this.request<{checkoutUrl: string; environment: string}>('/v1/admin/pagbank/checkout', {
      method: 'POST', body: JSON.stringify({plan})
    }, true);
    const url = new URL(result.checkoutUrl);
    if (result.environment !== 'sandbox' || url.protocol !== 'https:' || url.username || url.password ||
        !/(^|\.)(pagbank\.com\.br|pagseguro\.uol\.com\.br)$/i.test(url.hostname)) {
      throw new Error('Checkout de teste recusado: ambiente ou endereço inesperado.');
    }
    return url.toString();
  }

  async requestLicense(installationToken: string): Promise<unknown> {
    this.requireSession();
    if (!/^[A-Za-z0-9_-]{32,256}$/.test(installationToken)) throw new Error('Identificador de instalação inválido.');
    return await this.request('/v1/license', {
      method: 'POST', body: JSON.stringify({ installationToken })
    }, true);
  }

  async requestAccountDeletion(): Promise<void> {
    this.requireSession();
    this.state = 'busy'; this.message = 'Excluindo a conta com confirmação de sessão recente…';
    try {
      await this.request('/v1/account/delete-request', { method: 'POST', body: '{}' }, true);
      this.clearSession();
      this.state = 'ready'; this.message = 'Conta excluída e sessão local encerrada.';
    } catch (error) { this.fail(error); }
  }

  async exportAccountData(): Promise<unknown> {
    this.requireSession();
    this.state = 'busy'; this.message = 'Preparando sua cópia de dados…';
    try {
      const result = await this.request('/v1/account/export', { method: 'GET' }, true);
      this.state = 'signed-in'; this.message = 'Cópia de dados preparada neste dispositivo.';
      return result;
    } catch (error) { this.fail(error); throw error; }
  }

  logout(): void {
    this.clearSession();
    this.state = this.configured ? 'ready' : 'disabled';
    this.message = 'Sessão encerrada neste dispositivo.';
  }

  async adminSearch(email: string): Promise<{users: Array<{id: string; email: string; displayName: string; emailVerified: boolean; plan: string; codeAccessEndsAt?: string}>}> {
    this.requireSession();
    return this.request(`/v1/admin/users?email=${encodeURIComponent(email.trim())}`, { method: 'GET' }, true);
  }

  async adminCreateCode(body: {theme: string | null; days: number | null; lifetime: boolean; redeemBefore: string | null}): Promise<{id: string; code: string}> {
    this.requireSession();
    return this.request('/v1/admin/codes', { method: 'POST', body: JSON.stringify(body) }, true);
  }

  private validateApiBase(value?: string): string {
    if (!value?.trim()) return '';
    try {
      const url = new URL(value.trim());
      if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return '';
      return url.toString().replace(/\/$/, '');
    } catch { return ''; }
  }

  async adminRevokeCode(code: string): Promise<void> {
    this.requireSession();
    const normalized = code.trim().toUpperCase();
    if (normalized.length < 12 || normalized.length > 128) throw new Error('Código inválido.');
    await this.request('/v1/admin/codes/revoke', {method: 'POST', body: JSON.stringify({code: normalized})}, true);
  }

  private safePublicUrl(value?: string): string {
    if (!value?.trim()) return '';
    try { const url = new URL(value); return url.protocol === 'https:' ? url.toString() : ''; }
    catch { return ''; }
  }

  private safeBase64Key(value?: string): string {
    if (!value?.trim() || !/^[A-Za-z0-9+/]{43}=$/.test(value.trim())) return '';
    return value.trim();
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
    this.sessionGeneration += 1;
    for (const controller of this.pendingRequests) controller.abort();
    this.pendingRequests.clear();
    this.accessToken = ''; this.refreshToken = ''; this.tokenExpiresAt = 0; this.profile = null;
  }

  private applySession(session: SessionResponse): void {
    if (!session.accessToken || !session.refreshToken || session.expiresInSeconds < 60 || !session.profile?.id) {
      throw new Error('O servidor devolveu uma sessão inválida.');
    }
    this.accessToken = session.accessToken;
    this.refreshToken = session.refreshToken;
    this.tokenExpiresAt = Date.now() + Math.min(session.expiresInSeconds, 3600) * 1000;
    this.profile = session.profile;
  }

  private async refreshSession(): Promise<void> {
    if (!this.refreshToken) throw new Error('A sessão expirou. Entre novamente.');
    const session = await this.request<SessionResponse>('/v1/auth/refresh', {
      method: 'POST', body: JSON.stringify({ refreshToken: this.refreshToken })
    });
    this.applySession(session);
  }

  private fail(error: unknown): void {
    this.state = 'error';
    this.message = error instanceof Error ? error.message : 'A operação não foi concluída.';
  }

  private async request<T = unknown>(path: string, init: RequestInit, authenticated = false): Promise<T> {
    const generation = this.sessionGeneration;
    if (authenticated && Date.now() >= this.tokenExpiresAt - 60_000) await this.refreshSession();
    if (generation !== this.sessionGeneration) throw new Error('Sessão encerrada. Entre novamente para continuar.');
    const url = new URL(path, `${this.apiBase}/`);
    if (!url.pathname.startsWith('/v1/') || url.origin !== new URL(this.apiBase).origin) {
      throw new Error('Destino bloqueado pela política de rede da conta.');
    }
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    headers.set('Content-Type', 'application/json');
    if (authenticated) headers.set('Authorization', `Bearer ${this.accessToken}`);
    const controller = new AbortController();
    this.pendingRequests.add(controller);
    const timer = setTimeout(() => controller.abort(), 90_000);
    try {
    const response = await fetch(url, { ...init, headers, signal: controller.signal, cache: 'no-store', redirect: 'error', credentials: 'omit' });
    if (!response.ok) {
      let detail = `Falha ${response.status}`;
      try { detail = (await response.json() as { detail?: string }).detail || detail; } catch { /* keep status */ }
      throw new Error(detail);
    }
    const result = response.status === 204 ? undefined : await response.json();
    if (generation !== this.sessionGeneration) throw new Error('Sessão encerrada. Entre novamente para continuar.');
    return result as T;
    } catch (error) {
      if (generation !== this.sessionGeneration) throw new Error('Operação cancelada porque a sessão foi encerrada.');
      if (controller.signal.aborted) throw new Error('O servidor demorou a responder. Aguarde um pouco e tente novamente.');
      throw error;
    } finally { clearTimeout(timer); this.pendingRequests.delete(controller); }
  }
}
