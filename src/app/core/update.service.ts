import { Injectable } from '@angular/core';
import { invoke } from '@tauri-apps/api/core';
import { check, Update } from '@tauri-apps/plugin-updater';
import { NexusService } from './nexus.service';

export type UpdateState = 'dormant' | 'checking' | 'available' | 'downloading' | 'ready' | 'error';

@Injectable({ providedIn: 'root' })
export class UpdateService {
  // Activation is intentionally fail-closed. This becomes true only in the
  // release commit that embeds the real public key and GitHub Releases URL.
  configured = false;
  state: UpdateState = 'dormant';
  version = '';
  notes = '';
  requiresSecurityUpdate = false;
  progress = 0;
  error = '';
  dismissedVersion = '';
  lastCheckedAt: Date | null = null;
  private pending: Update | null = null;

  constructor(private readonly nexus: NexusService) {}

  async initialize(): Promise<void> {
    if (!this.nexus.isDesktop()) return;
    try { this.configured = await invoke<boolean>('updater_configured'); }
    catch { this.configured = false; }
  }

  async checkWhenSafe(protectedActive: boolean, boostActive: boolean): Promise<void> {
    if (!this.configured || !this.nexus.isDesktop() || protectedActive || boostActive || this.state === 'checking' || this.state === 'downloading') return;
    this.state = 'checking'; this.error = '';
    try {
      const update = await check({ timeout: 15_000 });
      this.lastCheckedAt = new Date();
      if (!update) { this.state = 'dormant'; return; }
      await this.pending?.close();
      this.pending = update;
      this.version = update.version;
      this.notes = update.body ?? '';
      this.requiresSecurityUpdate = /^\s*\[SECURITY-REQUIRED\]/i.test(this.notes);
      this.dismissedVersion = localStorage.getItem('nexuflow_dismissed_update') ?? '';
      this.state = 'available';
      // Critical packages are applied immediately only after the normal Tauri
      // signature verification. A forged/broken artifact fails closed and
      // returns to diagnostic-only access instead of creating a permanent lock.
      if (this.requiresSecurityUpdate) await this.install();
    } catch (error) {
      this.error = String(error);
      this.state = 'error';
    }
  }

  async checkNow(protectedActive: boolean, boostActive: boolean): Promise<void> {
    if (protectedActive || boostActive) {
      this.error = 'Feche a partida protegida e desative o BOOST antes de verificar atualizações.';
      this.state = 'error';
      return;
    }
    if (!this.configured) {
      this.error = 'Este build não inclui o canal assinado. Use uma versão oficial gerada pelo fluxo de release do NexuFlow.';
      this.state = 'error';
      return;
    }
    await this.checkWhenSafe(false, false);
  }

  get statusLabel(): string {
    if (!this.configured) return 'Aguardando canal assinado';
    if (this.state === 'checking') return 'Verificando assinatura…';
    if (this.state === 'available') return this.requiresSecurityUpdate ? `Correção crítica ${this.version} obrigatória` : `Versão ${this.version} disponível`;
    if (this.state === 'downloading') return `Baixando ${this.progress}%`;
    if (this.state === 'ready') return 'Atualização pronta para reiniciar';
    if (this.state === 'error') return 'Verificação não concluída';
    return this.lastCheckedAt ? 'Você está na versão mais recente' : 'Pronto para verificar';
  }

  dismiss(): void {
    if (!this.version || this.requiresSecurityUpdate) return;
    this.dismissedVersion = this.version;
    try { localStorage.setItem('nexuflow_dismissed_update', this.version); } catch { /* optional preference */ }
  }

  get visible(): boolean {
    return ['available', 'downloading', 'ready'].includes(this.state)
      && (this.requiresSecurityUpdate || this.version !== this.dismissedVersion);
  }

  get securityUpdateBlocking(): boolean {
    return this.requiresSecurityUpdate && ['available', 'downloading', 'ready'].includes(this.state);
  }

  get displayNotes(): string {
    return this.notes.replace(/^\s*\[SECURITY-REQUIRED\]\s*/i, '').trim();
  }

  async install(): Promise<void> {
    if (!this.pending || this.state !== 'available') return;
    this.state = 'downloading'; this.progress = 0;
    let total = 0; let downloaded = 0;
    try {
      await this.pending.downloadAndInstall(event => {
        if (event.event === 'Started') total = event.data.contentLength ?? 0;
        if (event.event === 'Progress') downloaded += event.data.chunkLength;
        if (event.event === 'Finished') this.progress = 100;
        else this.progress = total > 0 ? Math.min(99, Math.round(downloaded / total * 100)) : 0;
      });
      this.state = 'ready';
    } catch (error) {
      this.error = `Atualização recusada ou indisponível: ${String(error)}`;
      this.state = 'error';
    }
  }
}
