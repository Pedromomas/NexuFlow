import { Injectable } from '@angular/core';
import { invoke } from '@tauri-apps/api/core';
import { check, Update } from '@tauri-apps/plugin-updater';
import { NexusService } from './nexus.service';

export type UpdateState = 'dormant' | 'checking' | 'available' | 'downloading' | 'waiting' | 'installing' | 'ready' | 'error';

@Injectable({ providedIn: 'root' })
export class UpdateService {
  configured = false;
  // Legacy flag: automatic delivery remains gated until signed upgrade validation.
  // Public source alone does not mean an updater channel is ready. Never embed a token.
  privateDistribution = true;
  readonly channel = 'beta';
  state: UpdateState = 'dormant';
  version = '';
  notes = '';
  requiresSecurityUpdate = false;
  progress = 0;
  error = '';
  detailsOpen = false;
  dismissedVersion = '';
  lastCheckedAt: Date | null = null;
  private pending: Update | null = null;
  private downloaded = false;
  private operation = false;

  constructor(private readonly nexus: NexusService) {}

  async initialize(): Promise<void> {
    if (!this.nexus.isDesktop()) return;
    try { this.configured = await invoke<boolean>('updater_configured'); }
    catch { this.configured = false; }
  }

  private async safeNow(): Promise<boolean> {
    if (this.nexus.centerBusy || this.nexus.boostStarting) return false;
    const t = await this.nexus.telemetry();
    const age = Date.now() - t.timestamp;
    // Missing protection data is unknown, never an authorization to update.
    return Number.isFinite(age) && age >= 0 && age < 5_000
      && t.engine_online === true && t.daemon_active === false && t.recovery_required === false
      && t.anti_cheat?.active === false && !t.active_game
      && !['riot_safe', 'valve_safe', 'protected_safe', 'unknown_safe'].includes(t.effective_profile ?? '')
      && !this.nexus.centerBusy && !this.nexus.boostStarting;
  }

  async checkWhenSafe(protectedActive: boolean, boostActive: boolean): Promise<void> {
    if (!this.configured || this.privateDistribution || !this.nexus.isDesktop() || protectedActive || boostActive || this.operation || this.pending) return;
    this.operation = true; this.nexus.updateInProgress = true;
    this.state = 'checking'; this.error = '';
    try {
      if (!await this.safeNow()) { this.state = 'dormant'; return; }
      const update = await check({ timeout: 15_000 });
      this.lastCheckedAt = new Date();
      if (!update) { this.state = 'dormant'; return; }
      this.pending = update; this.version = update.version; this.notes = update.body ?? '';
      this.requiresSecurityUpdate = /^\s*\[SECURITY-REQUIRED\]/i.test(this.notes);
      try { this.dismissedVersion = localStorage.getItem('nexuflow_dismissed_update') ?? ''; } catch { /* optional */ }
      // Manifest metadata is not a verified package. Installation rechecks live state.
      this.state = 'available';
    } catch {
      this.error = 'Não foi possível consultar o canal. Verifique a conexão e tente novamente.';
      this.state = 'error';
    } finally { this.operation = false; this.nexus.updateInProgress = false; }
  }

  async checkNow(protectedActive: boolean, boostActive: boolean): Promise<void> {
    if (this.operation) return;
    if (protectedActive || boostActive) {
      this.error = 'Feche a partida protegida e desative o BOOST antes de verificar atualizações.';
      return;
    }
    if (!this.configured) {
      this.error = 'Este build não inclui o canal assinado. Use uma versão oficial gerada pelo fluxo de release do NexuFlow.';
      this.state = 'error'; return;
    }
    if (this.privateDistribution) {
      this.error = 'Atualizações automáticas aguardam validação do canal assinado. Consulte as versões no GitHub; nenhum token do GitHub é incluído no app.';
      this.state = 'error'; return;
    }
    await this.checkWhenSafe(false, false);
  }

  get statusLabel(): string {
    if (this.privateDistribution) return 'Atualizações automáticas em preparação';
    if (!this.configured) return 'Aguardando canal assinado';
    if (this.state === 'checking') return 'Consultando nova versão…';
    if (this.state === 'available') return `Versão ${this.version} disponível`;
    if (this.state === 'waiting') return 'Atualização aguardando fim da sessão';
    if (this.state === 'downloading') return `Baixando ${this.progress}%`;
    if (this.state === 'installing') return 'Instalando pacote verificado…';
    if (this.state === 'ready') return 'Instalação iniciada · reiniciando';
    if (this.state === 'error') return 'Atualização não concluída · tente novamente';
    return this.lastCheckedAt ? 'Nenhuma nova versão encontrada' : 'Pronto para verificar';
  }

  dismiss(): void {
    if (!this.version || this.requiresSecurityUpdate || this.operation) return;
    this.dismissedVersion = this.version;
    try { localStorage.setItem('nexuflow_dismissed_update', this.version); } catch { /* optional */ }
  }
  get visible(): boolean {
    return !!this.pending && (this.requiresSecurityUpdate || this.version !== this.dismissedVersion);
  }
  get busy(): boolean { return this.operation; }
  get securityUpdateBlocking(): boolean { return this.requiresSecurityUpdate && this.state !== 'dormant'; }
  get displayNotes(): string { return this.notes.replace(/^\s*\[SECURITY-REQUIRED\]\s*/i, '').trim(); }

  async install(): Promise<void> {
    if (!this.configured || this.privateDistribution || !this.pending || this.operation || this.state === 'ready') return;
    this.operation = true; this.nexus.updateInProgress = true; this.error = '';
    let total = 0; let downloaded = 0;
    try {
      if (!await this.safeNow()) { this.state = 'waiting'; return; }
      if (!this.downloaded) {
        this.state = 'downloading'; this.progress = 0;
        // Tauri rejects modified packages here. No signature bypass or fallback.
        await this.pending.download(event => {
          if (event.event === 'Started') total = event.data.contentLength ?? 0;
          if (event.event === 'Progress') downloaded += event.data.chunkLength;
          this.progress = event.event === 'Finished' ? 100 : total > 0 ? Math.min(99, Math.round(downloaded / total * 100)) : 0;
        }, { timeout: 120_000 });
        this.downloaded = true;
      }
      if (!await this.safeNow()) { this.state = 'waiting'; return; }
      this.state = 'installing';
      await this.pending.install();
      this.state = 'ready';
    } catch {
      this.error = 'Pacote recusado ou transferência interrompida. Nenhuma falha autoriza instalar sem validação. Confira a conexão e tente novamente.';
      this.state = 'error';
    } finally { this.operation = false; this.nexus.updateInProgress = false; }
  }
}
