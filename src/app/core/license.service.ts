import { Injectable, inject } from '@angular/core';
import { AccountService } from './account.service';
import { LicenseClock } from './license-clock';
import { FREE_FEATURES, grantsPaidFeature } from './access-policy';

export interface LicensePayload {
  schema: number;
  subject: string;
  installation: string;
  status: 'free' | 'trial' | 'active' | 'past_due' | 'cancelled';
  plan: string;
  entitlements: string[];
  issuedAt: string;
  expiresAt: string;
}

interface SignedLicense {
  payload: LicensePayload;
  signature: string;
  algorithm: 'Ed25519';
}

@Injectable({ providedIn: 'root' })
export class LicenseService {
  private readonly account = inject(AccountService);
  payload: LicensePayload | null = null;
  status: 'disabled' | 'ready' | 'checking' | 'valid' | 'error' = 'disabled';
  private publicKey: CryptoKey | null = null;
  private nextNetworkCheckAt = 0;
  private retryAfter = 0;
  private readonly cacheKey = 'nexuflow_signed_license_v1';
  private readonly installationKey = 'nexuflow_installation_token_v1';
  private readonly observedTimeKey = 'nexuflow_license_observed_time_v1';
  private readonly clock = new LicenseClock();

  async initialize(publicKeyBase64: string): Promise<void> {
    if (!publicKeyBase64) return;
    try {
      this.publicKey = await crypto.subtle.importKey(
        'raw', this.decodeBase64(publicKeyBase64), { name: 'Ed25519' }, false, ['verify']
      );
      this.status = 'ready';
      const cached = localStorage.getItem(this.cacheKey);
      if (cached) {
        try { await this.accept(JSON.parse(cached) as SignedLicense, false); }
        catch {
          this.payload = null;
          this.status = 'error';
          localStorage.removeItem(this.cacheKey);
        }
      }
    } catch {
      this.publicKey = null;
      this.payload = null;
      this.status = 'error';
    }
  }

  async refreshWhenSafe(account: AccountService, protectedGame: boolean, boostActive: boolean): Promise<void> {
    if (!this.publicKey || !account.authenticated || protectedGame || boostActive || this.status === 'checking') return;
    if (performance.now() < this.retryAfter) return;
    const current = this.trustedNow();
    if (current !== null && current < this.nextNetworkCheckAt && this.payload && this.payload.subject === account.profile?.id && Date.parse(this.payload.expiresAt) > current) return;
    this.status = 'checking';
    try {
      const document = await account.requestLicense(this.installationToken()) as SignedLicense;
      if (!account.authenticated || !account.profile?.emailVerified || document.payload?.subject !== account.profile.id) {
        throw new Error('A licença não pertence à conta autenticada.');
      }
      await this.accept(document, true);
      this.retryAfter = 0;
    } catch {
      this.retryAfter = performance.now() + 15 * 60 * 1000;
      const current = this.trustedNow();
      this.nextNetworkCheckAt = (current ?? 0) + 15 * 60 * 1000;
      this.status = current !== null && this.payload && Date.parse(this.payload.expiresAt) > current ? 'valid' : 'error';
    }
  }

  has(entitlement: string): boolean {
    if (FREE_FEATURES.has(entitlement)) return true;
    // Cached signatures alone must never authorize a signed-out or different user.
    if (!this.account.authenticated || !this.account.profile?.emailVerified ||
        this.payload?.subject !== this.account.profile.id) return false;
    const current = this.trustedNow();
    if (!this.payload || current === null || Date.parse(this.payload.expiresAt) <= current) return false;
    return grantsPaidFeature(this.payload, entitlement);
  }

  private async accept(document: SignedLicense, persist: boolean): Promise<void> {
    if (!this.publicKey || document?.algorithm !== 'Ed25519' || !document.payload || !Array.isArray(document.payload.entitlements)) {
      throw new Error('Licença inválida.');
    }
    const issuedAt = Date.parse(document.payload.issuedAt);
    const expiresAt = Date.parse(document.payload.expiresAt);
    const wallNow = Date.now();
    const lastObserved = Number(localStorage.getItem(this.observedTimeKey) || 0);
    if (!Number.isFinite(issuedAt) || !Number.isFinite(expiresAt) || expiresAt <= issuedAt || expiresAt - issuedAt > 25 * 60 * 60 * 1000) {
      throw new Error('Licença expirada ou fora da validade permitida.');
    }
    if (!persist && (expiresAt <= wallNow || issuedAt > wallNow + 5 * 60_000 ||
        !Number.isFinite(lastObserved) || wallNow < lastObserved - 5 * 60_000)) {
      throw new Error('Conecte-se fora da partida para confirmar a validade da licença.');
    }
    const valid = await crypto.subtle.verify(
      { name: 'Ed25519' }, this.publicKey, this.decodeBase64(document.signature),
      new TextEncoder().encode(this.canonical(document.payload))
    );
    if (!valid) throw new Error('Assinatura da licença recusada.');
    this.clock.anchor(persist ? issuedAt : Math.max(wallNow, issuedAt, lastObserved));
    // A fresh server response can recover from an incorrect Windows calendar.
    localStorage.setItem(this.observedTimeKey, String(persist ? issuedAt : Math.max(wallNow, issuedAt, lastObserved)));
    this.payload = document.payload;
    this.status = 'valid';
    this.nextNetworkCheckAt = Math.min(issuedAt + 23 * 60 * 60 * 1000, expiresAt - 30 * 60 * 1000);
    if (persist) localStorage.setItem(this.cacheKey, JSON.stringify(document));
  }

  private trustedNow(): number | null {
    const current = this.clock.now();
    if (current !== null) {
      const previous = Number(localStorage.getItem(this.observedTimeKey) || 0);
      if (current > previous + 60_000) localStorage.setItem(this.observedTimeKey, String(current));
    }
    return current;
  }

  private installationToken(): string {
    const current = localStorage.getItem(this.installationKey);
    if (current && /^[A-Za-z0-9_-]{32,256}$/.test(current)) return current;
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    const token = btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
    localStorage.setItem(this.installationKey, token);
    return token;
  }

  private canonical(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(item => this.canonical(item)).join(',')}]`;
    if (value && typeof value === 'object') {
      const record = value as Record<string, unknown>;
      return `{${Object.keys(record).sort().map(key => `${JSON.stringify(key)}:${this.canonical(record[key])}`).join(',')}}`;
    }
    return JSON.stringify(value);
  }

  private decodeBase64(value: string): ArrayBuffer {
    const binary = atob(value);
    const buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return buffer;
  }
}
