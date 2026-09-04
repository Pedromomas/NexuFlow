import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IonApp } from '@ionic/angular';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import {
  BoostProfile,
  DriverScanReport,
  GameInfo,
  GamingHealth,
  InvestigatorSnapshot,
  QualitySnapshot,
  RouteDiagnostics,
  SessionRecord,
  Telemetry
} from './core/models';
import { NexusService } from './core/nexus.service';
import { PerformanceCenterComponent } from './performance-center.component';

type Tab = 'dashboard' | 'games' | 'history' | 'investigator' | 'appearance' | 'settings' | 'redeem' | 'connection' | 'pc';
type UiTheme = 'nebula' | 'midnight' | 'emerald' | 'high-contrast' | 'blocks' | 'relic' | 'tactical' | 'operation' | 'secret';
type AppearanceSection = 'themes' | 'accessibility';
type LearnTopic = 'ping' | 'pc' | 'complete' | 'hardcore_safe' | 'uac';

interface LearnMoreContent {
  title: string;
  intro: string;
  does: string[];
  doesNot: string[];
  glossary?: Array<{ term: string; meaning: string }>;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, IonApp, PerformanceCenterComponent],
  templateUrl: './app.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent implements OnInit, OnDestroy {
  tab: Tab = 'dashboard';
  profile: BoostProfile = 'complete';
  boosted = false;
  busy = false;
  message = 'Pronto para otimizar';
  telemetry: Telemetry | null = null;
  games: GameInfo[] = [];
  gameQuery = '';
  gameFilter: 'all' | 'installed' | 'favorites' = 'all';
  favoriteGames: string[] = [];
  history: SessionRecord[] = [];
  investigator: InvestigatorSnapshot | null = null;
  gamingHealth: GamingHealth = {};
  routeReport: RouteDiagnostics | null = null;
  routeBusy = false;
  driverReport: DriverScanReport | null = null;
  driverBusy = false;
  driverMessage = 'O scan só começa quando você clicar. Nenhum driver é instalado automaticamente.';
  pingSeries = Array.from({ length: 28 }, () => 0);
  cpuSeries = Array.from({ length: 28 }, () => 0);
  networkSeries = Array.from({ length: 28 }, () => 0);
  gpuSeries = Array.from({ length: 28 }, () => 0);
  apiTokenDraft = '';
  transport = 'Inicializando';
  readonly desktopMode: boolean;
  uiTheme: UiTheme = 'nebula';
  fontScale = 100;
  reducedMotion = false;
  accessibilityOpen = false;
  wallpaperMode = false;
  wallpaperBusy = false;
  unlockCelebration = false;
  secretAudioState: 'idle' | 'playing' | 'blocked' = 'idle';
  private secretAudio: HTMLAudioElement | null = null;
  private wallpaperReturnFocus: HTMLElement | null = null;
  private previousFullscreen = false;
  appearanceSection: AppearanceSection = 'themes';
  secretUnlocked = false;
  secretCodeDraft = '';
  secretCodeFormOpen = false;
  secretCodeBusy = false;
  secretCodeMessage = 'Digite um código para revelar conteúdos cosméticos guardados neste computador.';
  learnTopic: LearnTopic | null = null;
  private timer?: ReturnType<typeof setInterval>;
  private desktopUnlisten?: UnlistenFn;
  private destroyed = false;
  private tick = 0;
  private readonly uiPrefsKey = 'nexuflow_ui_preferences_v1';
  private readonly secretUnlockKey = 'nexuflow_secret_art_unlocked_v1';
  private readonly secretCodeDigest = 'cc4a2c7e4588853f351cdb6b3fb919a7118280aa2d76aa4921b84fa7acfeb529';
  private readonly boostModeKey = 'nexuflow_boost_mode_v155';
  private readonly legacyBoostModeKey = 'nexuflow_boost_mode_v150';
  private readonly olderBoostModeKey = 'nexuflow_boost_mode_v142';

  constructor(private readonly nexus: NexusService, private readonly cdr: ChangeDetectorRef) {
    this.apiTokenDraft = this.nexus.getStoredApiToken();
    this.transport = this.nexus.transportLabel();
    this.desktopMode = this.nexus.isDesktop();
    this.loadSecretUnlock();
    this.loadUiPreferences();
    this.loadBoostMode();
    try {
      const stored: unknown = JSON.parse(localStorage.getItem('nexuflow_favorite_games_v17') || '[]');
      if (Array.isArray(stored)) this.favoriteGames = stored.filter(x => typeof x === 'string').slice(0, 50);
    } catch { /* Favorites are optional. */ }
  }

  async ngOnInit(): Promise<void> {
    if (this.desktopMode) {
      const unlisten = await listen<string>('desktop-status', event => {
        this.message = event.payload;
        if (this.wallpaperMode) void this.exitWallpaperMode();
        this.cdr.markForCheck();
      });
      if (this.destroyed) { unlisten(); return; }
      this.desktopUnlisten = unlisten;
    }
    await this.checkCrashRecovery();
    await Promise.all([this.refreshTelemetry(), this.refreshGames(), this.refreshHealth(), this.refreshHistory()]);
    if (!this.destroyed) this.timer = setInterval(() => void this.periodicRefresh(), 1000);
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.stopSecretAudio();
    this.desktopUnlisten?.();
    if (this.timer) clearInterval(this.timer);
  }

  private async periodicRefresh(): Promise<void> {
    this.tick += 1;
    await this.refreshTelemetry();
    if (this.tick % 3 === 0) await this.refreshGames();
    if (this.tick % 15 === 0) await this.refreshHealth();
    if (this.tab === 'investigator' && this.tick % 3 === 0) await this.refreshInvestigator();
  }

  private async checkCrashRecovery(): Promise<void> {
    const recovery = await this.nexus.recoveryStatus();
    if (!recovery.required) return;

    this.message = 'Sessão anterior interrompida detectada. Preparando rollback seguro…';
    this.cdr.markForCheck();

    // Desktop can request its own UAC helper. In browser development mode the
    // token/admin API must be available, so leave an explicit warning instead.
    if (!this.desktopMode && !this.nexus.getStoredApiToken()) {
      this.message = 'Recovery pendente. Abra a API elevada e use Restaurar tudo.';
      return;
    }

    const result = await this.nexus.restoreAll(this.profile);
    this.message = result.ok ? 'Estado interrompido restaurado automaticamente.' : `Recovery falhou: ${result.message}`;
  }

  setTab(tab: Tab): void {
    this.tab = tab;
    if (tab === 'history') void this.refreshHistory();
    if (tab === 'investigator') void this.refreshInvestigator();
    if (tab === 'settings' || tab === 'pc') void this.refreshHealth();
    this.cdr.markForCheck();
    queueMicrotask(() => this.scrollToTop());
  }

  setAppearanceSection(section: AppearanceSection): void {
    this.appearanceSection = section;
    this.cdr.markForCheck();
  }

  async redeemSecretCode(): Promise<void> {
    if (this.secretCodeBusy) return;
    const normalized = this.secretCodeDraft.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (normalized === 'RESETCODIGOS') {
      try {
        this.stopSecretAudio();
        localStorage.removeItem(this.secretUnlockKey);
        this.secretUnlocked = false;
        this.unlockCelebration = false;
        this.secretCodeDraft = '';
        this.secretCodeFormOpen = false;
        if (this.uiTheme === 'secret') this.setTheme('nebula');
        this.secretCodeMessage = 'Resgates removidos. Você pode testar o código novamente.';
      } catch {
        this.secretCodeMessage = 'Não foi possível remover o resgate salvo. Tente novamente.';
      }
      this.cdr.markForCheck();
      return;
    }
    if (!normalized) {
      this.secretCodeMessage = 'Digite o código antes de confirmar.';
      this.cdr.markForCheck();
      return;
    }

    this.secretCodeBusy = true;
    try {
      const bytes = new TextEncoder().encode(normalized);
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const hex = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
      if (hex !== this.secretCodeDigest) {
        this.secretCodeMessage = 'Código não reconhecido. Confira os caracteres e tente novamente.';
        this.secretCodeDraft = '';
        this.cdr.markForCheck();
        return;
      }

      if (this.secretUnlocked) {
        this.secretCodeDraft = '';
        this.secretCodeMessage = 'Você já resgatou este código. Pode testar outro quando houver novidades.';
        return;
      }
      localStorage.setItem(this.secretUnlockKey, '1');
      this.secretUnlocked = true;
      this.secretCodeFormOpen = false;
      this.secretCodeDraft = '';
      this.secretCodeMessage = 'Arte Secreta desbloqueada! Ela já está ativa e disponível em Aparência.';
      this.uiTheme = 'secret';
      this.appearanceSection = 'themes';
      this.tab = 'appearance';
      this.unlockCelebration = true;
      this.applyUiPreferences();
      this.persistUiPreferences();
      void this.playSecretUnlockAudio();
      setTimeout(() => document.getElementById('unlock-continue')?.focus());
    } catch {
      this.secretCodeMessage = 'Não foi possível validar o código neste ambiente.';
    } finally {
      this.secretCodeBusy = false;
      this.cdr.markForCheck();
    }
  }

  openCodeForm(): void {
    this.secretCodeFormOpen = !this.secretCodeFormOpen;
    this.cdr.markForCheck();
    if (this.secretCodeFormOpen) setTimeout(() => document.getElementById('secret-code')?.focus());
  }

  get wallpaperArtwork(): string {
    return this.uiTheme === 'secret' && this.secretUnlocked
      ? 'theme-art/secret/nexuflow-secret-cover.jpg'
      : 'theme-art/flux-mascot.png';
  }

  dismissUnlockCelebration(): void {
    this.stopSecretAudio();
    this.unlockCelebration = false;
    this.cdr.markForCheck();
    setTimeout(() => document.getElementById('secret-theme-tile')?.focus());
  }

  async playSecretUnlockAudio(): Promise<void> {
    if (!this.unlockCelebration || !this.secretUnlocked) return;
    this.stopSecretAudio();
    const clip = new Audio('theme-art/secret/secret-unlock.mp3');
    this.secretAudio = clip;
    clip.volume = 0.7;
    clip.loop = false;
    clip.onended = () => {
      if (this.secretAudio !== clip) return;
      this.secretAudioState = 'idle';
      this.cdr.markForCheck();
    };
    try {
      await clip.play();
      if (this.secretAudio === clip) this.secretAudioState = 'playing';
    } catch {
      // Autoplay or device failure must never undo a successful reward.
      if (this.secretAudio === clip) this.secretAudioState = 'blocked';
    }
    if (!this.destroyed) this.cdr.markForCheck();
  }

  stopSecretAudio(): void {
    if (this.secretAudio) {
      this.secretAudio.onended = null;
      this.secretAudio.pause();
      this.secretAudio.currentTime = 0;
      this.secretAudio = null;
    }
    this.secretAudioState = 'idle';
  }

  async enterWallpaperMode(): Promise<void> {
    if (this.wallpaperBusy || this.wallpaperMode) return;
    this.wallpaperBusy = true;
    this.wallpaperReturnFocus = document.activeElement as HTMLElement | null;
    this.wallpaperMode = true;
    this.cdr.markForCheck();
    try {
      if (this.desktopMode) {
        this.previousFullscreen = await this.nexus.setArtworkFullscreen(true);
      } else if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
        this.previousFullscreen = false;
      } else {
        this.previousFullscreen = !!document.fullscreenElement;
      }
    } catch {
      // The clean artwork view still works if fullscreen is unavailable.
      this.previousFullscreen = false;
    } finally {
      this.wallpaperBusy = false;
      this.cdr.markForCheck();
      setTimeout(() => document.getElementById('wallpaper-exit')?.focus());
    }
  }

  async exitWallpaperMode(): Promise<void> {
    if (this.wallpaperBusy || !this.wallpaperMode) return;
    this.wallpaperBusy = true;
    try {
      if (this.desktopMode) await this.nexus.setArtworkFullscreen(this.previousFullscreen);
      else if (document.fullscreenElement && !this.previousFullscreen) await document.exitFullscreen();
    } catch {
      this.message = 'Interface restaurada. Use os controles da janela para ajustar a tela.';
    } finally {
      this.wallpaperMode = false;
      this.wallpaperBusy = false;
      this.cdr.markForCheck();
      const previous = this.wallpaperReturnFocus;
      setTimeout(() => { if (previous?.isConnected) previous.focus(); });
    }
  }

  @HostListener('document:fullscreenchange')
  onFullscreenChange(): void {
    if (!this.desktopMode && this.wallpaperMode && !document.fullscreenElement && !this.wallpaperBusy) {
      void this.exitWallpaperMode();
    }
  }

  private loadSecretUnlock(): void {
    try {
      this.secretUnlocked = localStorage.getItem(this.secretUnlockKey) === '1';
      if (this.secretUnlocked) this.secretCodeMessage = 'Arte Secreta já desbloqueada neste computador.';
    } catch {
      this.secretUnlocked = false;
    }
  }

  setProfile(profile: BoostProfile): void {
    if (this.boosted) {
      this.message = 'Desative o BOOST antes de trocar o objetivo da sessão.';
      this.cdr.markForCheck();
      return;
    }
    this.profile = profile;
    try { localStorage.setItem(this.boostModeKey, profile); } catch { /* local preference only */ }
    this.message = `${this.effectiveProfileLabel} selecionado. Veja abaixo exatamente o que será aplicado.`;
    this.cdr.markForCheck();
  }

  private loadBoostMode(): void {
    try {
      const saved = (localStorage.getItem(this.boostModeKey) ?? localStorage.getItem(this.legacyBoostModeKey) ?? localStorage.getItem(this.olderBoostModeKey)) as BoostProfile | null;
      this.profile = saved && ['ping', 'pc', 'complete', 'hardcore_safe'].includes(saved) ? saved : 'complete';
      localStorage.setItem(this.boostModeKey, this.profile);
    } catch {
      this.profile = 'complete';
    }
  }

  boostObjective(profile: BoostProfile = this.profile): 'ping' | 'pc' | 'complete' | 'hardcore_safe' {
    if (profile === 'ping') return 'ping';
    if (profile === 'pc') return 'pc';
    if (profile === 'hardcore_safe') return 'hardcore_safe';
    return 'complete';
  }

  objectiveLabel(mode = this.telemetry?.objective_mode ?? this.boostObjective()): string {
    return ({ ping: 'Ping', pc: 'PC Booster', complete: 'Completo', hardcore_safe: 'Hardcore Safe' } as Record<string, string>)[mode] ?? 'Completo';
  }

  get riotGameActive(): boolean {
    return ['valorant', 'lol'].includes((this.telemetry?.active_game_id ?? '').toLowerCase());
  }

  get valveGameActive(): boolean {
    return (this.telemetry?.active_game_id ?? '').toLowerCase() === 'cs2';
  }

  get robloxGameActive(): boolean {
    return (this.telemetry?.active_game_id ?? '').toLowerCase() === 'roblox';
  }

  get effectiveProfileLabel(): string {
    const objective = this.objectiveLabel();
    if (this.riotGameActive) return `Vanguard Safe + ${objective}`;
    if (this.valveGameActive) return `Valve Safe + ${objective}`;
    const effective = this.telemetry?.effective_profile;
    if (effective === 'unknown_safe') return `Unknown Safe + ${objective}`;
    if (effective === 'protected_safe') return `EAC / BattlEye Safe + ${objective}`;
    if (this.robloxGameActive) return `${objective} para Roblox`;
    if (effective) return this.profileLabel(effective as BoostProfile);
    return this.profileLabel(this.profile);
  }

  get selectedBoostDescription(): string {
    const objective = this.telemetry?.objective_mode ?? this.boostObjective();
    if (objective === 'ping') return 'Observa a qualidade da conexão e usa somente ajustes de rede permitidos. Em jogos protegidos, não altera o tráfego durante a partida.';
    if (objective === 'pc') return 'Usa um plano de energia temporário para favorecer o desempenho geral. Em jogos protegidos, não mexe no processo do jogo.';
    if (objective === 'hardcore_safe') return 'Apenas analisa e mostra possíveis problemas. Não muda configurações do Windows, da rede ou do jogo.';
    return 'Combina os recursos seguros de conexão e desempenho. A proteção do jogo decide automaticamente o que pode ou não ser aplicado.';
  }

  get installedGamesCount(): number {
    return this.games.filter(game => game.installed).length;
  }

  get runningGamesCount(): number {
    return this.games.filter(game => game.running).length;
  }

  get validatedGamesCount(): number {
    return this.games.length;
  }

  get filteredGames(): GameInfo[] {
    const query = this.gameQuery.trim().toLocaleLowerCase('pt-BR');
    return this.games.filter(g => (!query || g.display_name.toLocaleLowerCase('pt-BR').includes(query))
      && (this.gameFilter !== 'installed' || g.installed)
      && (this.gameFilter !== 'favorites' || this.favoriteGames.includes(g.id)))
      .sort((a, b) => Number(b.running) - Number(a.running) || Number(this.favoriteGames.includes(b.id)) - Number(this.favoriteGames.includes(a.id)) || a.display_name.localeCompare(b.display_name));
  }

  toggleFavorite(id: string): void {
    this.favoriteGames = this.favoriteGames.includes(id) ? this.favoriteGames.filter(x => x !== id) : [...this.favoriteGames, id];
    try { localStorage.setItem('nexuflow_favorite_games_v17', JSON.stringify(this.favoriteGames)); }
    catch { this.message = 'Favorito aplicado nesta sessão; não foi possível salvá-lo.'; }
  }

  trackGameId(_index: number, game: GameInfo): string { return game.id; }

  preparePc(): void { this.setProfile('pc'); this.setTab('dashboard'); }

  openLearnMore(topic: LearnTopic): void {
    this.learnTopic = topic;
    this.cdr.markForCheck();
  }

  closeLearnMore(): void {
    this.learnTopic = null;
    this.cdr.markForCheck();
  }

  get learnMoreContent(): LearnMoreContent | null {
    if (!this.learnTopic) return null;
    const content: Record<LearnTopic, LearnMoreContent> = {
      ping: {
        title: 'Modo Ping — em palavras simples',
        intro: 'Serve para entender se a conexão está estável e aplicar apenas ajustes de rede que a política do jogo permitir.',
        does: ['Mede atraso, variação e perda de conexão.', 'Compara a conexão antes e depois.', 'Verifica DNS, tamanho seguro dos pacotes e caminho até o destino quando permitido.'],
        doesNot: ['Não cria internet mais rápida que o seu plano.', 'Não troca magicamente a rota do provedor.', 'Não intercepta nem modifica pacotes do jogo.'],
        glossary: [
          { term: 'Ping', meaning: 'tempo que a informação leva para ir e voltar.' },
          { term: 'Jitter', meaning: 'quanto esse tempo fica variando.' },
          { term: 'Perda', meaning: 'dados que não chegam ao destino.' },
          { term: 'DNS', meaning: 'serviço que encontra o endereço de um site ou serviço.' },
          { term: 'PMTU', meaning: 'maior tamanho de pacote que passa sem precisar ser dividido.' }
        ]
      },
      pc: {
        title: 'Modo PC — em palavras simples',
        intro: 'Tenta deixar o Windows mais preparado para jogar sem desligar proteções de segurança.',
        does: ['Ativa temporariamente um plano de energia voltado a desempenho.', 'Acompanha CPU, memória, GPU e energia.', 'Restaura o estado anterior ao desativar.'],
        doesNot: ['Não faz overclock.', 'Não encerra programas por conta própria.', 'Com Vanguard, VAC, EAC ou BattlEye, não muda prioridade nem afinidade do jogo.'],
        glossary: [
          { term: 'Plano de energia', meaning: 'regras do Windows sobre desempenho e economia de energia.' },
          { term: 'Telemetria local', meaning: 'medidas exibidas somente no seu computador.' }
        ]
      },
      complete: {
        title: 'Modo Completo — em palavras simples',
        intro: 'É a opção recomendada: junta os recursos seguros do modo Ping e do modo PC.',
        does: ['Analisa a conexão.', 'Usa o plano de energia temporário.', 'Adapta automaticamente os limites ao jogo e ao anticheat detectados.'],
        doesNot: ['Não promete eliminar todo lag.', 'Não desativa o anticheat.', 'Não usa driver próprio, injeção ou alteração de memória.']
      },
      hardcore_safe: {
        title: 'Hardcore Safe — em palavras simples',
        intro: 'É o modo mais conservador. Ele observa e cria um relatório, mas não altera o sistema.',
        does: ['Mede a qualidade da conexão.', 'Mostra o estado do PC e das proteções do Windows.', 'Salva histórico e permite exportar relatório.'],
        doesNot: ['Não altera DNS ou tamanho de pacotes.', 'Não muda energia, processos ou serviços.', 'Não toca no jogo nem no anticheat.'],
        glossary: [{ term: 'Somente leitura', meaning: 'o NexuFlow consulta informações, mas não modifica nada.' }]
      },
      uac: {
        title: 'Por que o Windows pede “Sim ou Não”?',
        intro: 'É a proteção UAC do Windows confirmando que o NexuFlow pode fazer ajustes administrativos reversíveis.',
        does: ['Desde a 1.5.5, a autorização é solicitada uma vez ao abrir o aplicativo.', 'Enquanto o aplicativo permanecer aberto, ativar e desativar não deve repetir a pergunta.', 'O rollback continua funcionando com a mesma autorização.'],
        doesNot: ['O NexuFlow não desliga nem contorna o UAC.', '“Fornecedor desconhecido” só desaparece quando o executável recebe uma assinatura digital comercial válida.', 'Cancelar a autorização impede os ajustes administrativos.']
      }
    };
    return content[this.learnTopic];
  }

  get selectedAllowedFeatures(): string[] {
    const objective = this.telemetry?.objective_mode ?? this.boostObjective();
    if (objective === 'ping') return ['Ping / jitter / loss', 'Nexus Score e baseline', 'DNS benchmark', 'PMTU e rota read-only', 'Adaptive monitor'];
    if (objective === 'pc') return ['Plano de energia temporário', 'CPU / RAM / GPU telemetry', 'Gaming Health', 'Rollback automático'];
    if (objective === 'hardcore_safe') return ['Diagnóstico read-only', 'Histórico local', 'Relatório da sessão'];
    return ['Tudo do modo Ping', 'Plano de energia temporário', 'Gaming Health', 'Baseline antes × depois', 'Rollback automático'];
  }

  get selectedBlockedFeatures(): string[] {
    if (!this.riotGameActive && !this.valveGameActive) return [];
    return ['Memória / injection / hooks', 'Processo, prioridade e CPU Sets', 'Packet interception / modification', 'DNS ou MTU ao vivo', 'Firewall steering', 'Anticheat e arquivos do jogo'];
  }

  gameIcon(gameId?: string | null): string {
    const id = String(gameId || 'generic').toLowerCase();
    return `game-icons/${['roblox', 'lol', 'valorant', 'cs2'].includes(id) ? id : 'generic'}.svg`;
  }

  get qualityBefore(): QualitySnapshot | null {
    return this.telemetry?.session_quality?.before ?? null;
  }

  get qualityAfter(): QualitySnapshot | null {
    return this.telemetry?.session_quality?.after ?? null;
  }

  get healthWarnings(): Array<{ severity?: string; code?: string; message?: string }> {
    return this.gamingHealth.warnings ?? [];
  }

  latencyAreaLabel(value?: string): string {
    const labels: Record<string, string> = {
      connection_or_local_network: 'Conexão / rede local',
      route_or_isp: 'Rota / provedor',
      pc_or_driver_pressure: 'PC / drivers',
      server_or_game_specific: 'Servidor / jogo',
      no_issue_observed: 'Nenhum gargalo evidente',
      multiple_signals: 'Mais de um sinal',
      inconclusive: 'Ainda inconclusivo'
    };
    return labels[String(value || '')] ?? 'Coletando evidências';
  }

  latencyStatusLabel(value?: string): string {
    const labels: Record<string, string> = {
      degradation_observed: 'degradação observada',
      pressure_observed: 'pressão observada',
      no_issue_observed: 'sem problema evidente',
      insufficient_data: 'dados insuficientes',
      indeterminate: 'indeterminado',
      enabled: 'ativo',
      disabled: 'desativado',
      unknown: 'estado desconhecido',
      not_exposed_by_driver: 'não informado pelo driver',
      deferred: 'adiado durante o jogo'
    };
    return labels[String(value || '')] ?? 'coletando';
  }

  latencyStatusTone(value?: string): 'good' | 'warning' | 'danger' | 'neutral' {
    const status = String(value || '');
    if (status === 'no_issue_observed' || status === 'enabled') return 'good';
    if (status === 'degradation_observed' || status === 'pressure_observed') return 'danger';
    if (status === 'insufficient_data' || status === 'deferred' || status === 'not_exposed_by_driver') return 'warning';
    return 'neutral';
  }

  confidenceLabel(value?: string): string {
    return ({ high: 'alta', medium: 'média', low: 'baixa', none: 'sem conclusão' } as Record<string, string>)[String(value || '')] ?? 'sem conclusão';
  }

  get driverStatusLabel(): string {
    if (this.driverBusy) return 'Consultando o Windows Update…';
    if (!this.driverReport) return 'Ainda não verificado';
    if (this.driverReport.deferred) return 'Adiado pelo modo protegido';
    if (!this.driverReport.available) return 'Scan indisponível';
    if (this.driverReport.updates_offered > 0) {
      return `${this.driverReport.updates_offered} atualização(ões) oferecida(s)`;
    }
    return 'Nenhuma atualização oferecida';
  }

  async scanDrivers(): Promise<void> {
    if (this.driverBusy) return;
    this.driverBusy = true;
    this.driverMessage = 'Consultando somente a fila oficial de drivers do Windows Update…';
    this.cdr.markForCheck();
    try {
      this.driverReport = await this.nexus.scanDriverUpdates();
      if (this.driverReport.deferred) {
        this.driverMessage = this.driverReport.reason || 'Feche o jogo protegido e tente novamente.';
      } else if (!this.driverReport.available) {
        this.driverMessage = this.driverReport.reason || 'O Windows Update não respondeu ao scan.';
      } else if (this.driverReport.updates_offered > 0) {
        this.driverMessage = 'Revise cada item no Windows Update antes de instalar. Pode ser necessário reiniciar.';
      } else {
        this.driverMessage = 'O Windows Update não ofereceu driver novo agora. Isso não garante que o site do fabricante não tenha uma versão diferente.';
      }
    } catch (error) {
      this.driverReport = null;
      this.driverMessage = `Falha no scan: ${String(error)}`;
    } finally {
      this.driverBusy = false;
      this.cdr.markForCheck();
    }
  }

  async openDriverUpdates(): Promise<void> {
    if (this.driverBusy) return;
    try {
      const result = await this.nexus.openDriverUpdates();
      this.driverMessage = result.message || 'Atualizações opcionais abertas no Windows.';
    } catch (error) {
      this.driverMessage = `Não foi possível abrir o Windows Update: ${String(error)}`;
    }
    this.cdr.markForCheck();
  }

  profileLabel(profile: BoostProfile): string {
    const labels: Record<BoostProfile, string> = {
      auto: 'Automático',
      safe: 'Safe',
      roblox: 'Roblox Profile',
      riot_safe: 'Riot / Vanguard Safe',
      valve_safe: 'Valve / VAC Safe',
      aggressive: 'Aggressive',
      ping: 'Ping', pc: 'PC', complete: 'Completo', hardcore_safe: 'Hardcore Safe',
      unknown_safe: 'Unknown Game Safe', protected_safe: 'EAC / BattlEye Safe'
    };
    return labels[profile];
  }

  async exportSessionReport(): Promise<void> {
    const safe = {
      schema: 4, product: 'NexuFlow 1.6 Trust Edition', exported_at: new Date().toISOString(),
      requested_profile: this.profile, effective_profile: this.telemetry?.effective_profile ?? null,
      objective_mode: this.telemetry?.objective_mode ?? this.boostObjective(),
      game_id: this.telemetry?.active_game_id ?? null, quality: this.telemetry?.session_quality ?? null,
      anti_cheat: this.telemetry?.anti_cheat ?? null,
      latency_budget: this.telemetry?.latency_budget ?? null,
      health_summary: {
        game_mode: this.gamingHealth.windows_gaming?.['game_mode'] ?? null,
        nic: this.gamingHealth.nic_health?.['features'] ?? null,
        stutter: this.gamingHealth.stutter_health?.['classification'] ?? null,
        policy: this.gamingHealth.policy ?? null
      },
      privacy: { local_only: true, analytics: false, device_fingerprint: false },
      note: 'Relatório sanitizado: sem token, PID ou caminhos pessoais.'
    };
    try {
      const signed = await this.nexus.signSessionReport(safe);
      const blob = new Blob([JSON.stringify(signed, null, 2)], { type: 'application/json' });
      const link = document.createElement('a'); link.href = URL.createObjectURL(blob);
      link.download = `NexuFlow-session-signed-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
      link.click(); URL.revokeObjectURL(link.href);
      this.message = 'Relatório exportado com assinatura Ed25519 desta instalação.';
    } catch (error) {
      this.message = `Não foi possível assinar o relatório: ${String(error)}`;
    }
    this.cdr.markForCheck();
  }

  stutterClassificationLabel(value: unknown): string {
    const labels: Record<string, string> = {
      no_obvious_system_pressure_in_sample: 'Nenhuma pressão evidente no sistema',
      possible_system_pressure_in_sample: 'Possível pressão no sistema',
      insufficient_sample: 'Amostra ainda insuficiente',
      deferred_for_protected_game: 'Adiado durante jogo protegido'
    };
    const key = String(value ?? '');
    return labels[key] ?? (key ? key.replaceAll('_', ' ') : 'Coletando');
  }

  get themeLabel(): string {
    const labels: Record<UiTheme, string> = {
      nebula: 'Nebula',
      midnight: 'Midnight',
      emerald: 'Emerald',
      'high-contrast': 'Alto contraste',
      blocks: 'Blocos',
      relic: 'Relíquia',
      tactical: 'Tático',
      operation: 'Operação',
      secret: 'Arte Secreta'
    };
    return labels[this.uiTheme];
  }

  get gamesNavigationIcon(): string {
    const themedIcons: Partial<Record<UiTheme, string>> = {
      blocks: 'icon-cubes',
      relic: 'icon-relic',
      tactical: 'icon-tactical',
      operation: 'icon-operation',
      secret: 'icon-secret'
    };
    return themedIcons[this.uiTheme] ?? 'icon-gamepad';
  }

  get themeSignatureIcon(): string {
    const icons: Record<UiTheme, string> = {
      nebula: 'icon-orbit',
      midnight: 'icon-moon',
      emerald: 'icon-leaf',
      'high-contrast': 'icon-contrast',
      blocks: 'icon-cubes',
      relic: 'icon-relic',
      tactical: 'icon-tactical',
      operation: 'icon-operation',
      secret: 'icon-secret'
    };
    return icons[this.uiTheme];
  }

  setTheme(theme: UiTheme): void {
    if (theme === 'secret' && !this.secretUnlocked) {
      this.message = 'A Arte Secreta precisa ser desbloqueada com um código.';
      this.tab = 'redeem';
      this.cdr.markForCheck();
      return;
    }
    this.uiTheme = theme;
    this.applyUiPreferences();
    this.persistUiPreferences();
    this.cdr.markForCheck();
  }

  setFontScale(value: number): void {
    this.fontScale = Math.min(125, Math.max(90, Math.round(Number(value) || 100)));
    this.applyUiPreferences();
    this.persistUiPreferences();
    this.cdr.markForCheck();
  }

  bumpFont(delta: number): void {
    this.setFontScale(this.fontScale + delta);
  }

  toggleReducedMotion(): void {
    this.reducedMotion = !this.reducedMotion;
    this.applyUiPreferences();
    this.persistUiPreferences();
    this.cdr.markForCheck();
  }

  resetUiPreferences(): void {
    this.uiTheme = 'nebula';
    this.fontScale = 100;
    this.reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    this.applyUiPreferences();
    this.persistUiPreferences();
    this.message = 'Aparência restaurada para o padrão.';
    this.cdr.markForCheck();
  }

  toggleAccessibility(): void {
    this.accessibilityOpen = !this.accessibilityOpen;
    this.cdr.markForCheck();
  }

  private getScrollContainer(): HTMLElement | null {
    return document.querySelector<HTMLElement>('.content');
  }

  scrollToTop(): void {
    const container = this.getScrollContainer();
    if (container && typeof container.scrollTo === 'function') {
      container.scrollTo({ top: 0, behavior: this.reducedMotion ? 'auto' : 'smooth' });
      return;
    }
    window.scrollTo({ top: 0, behavior: this.reducedMotion ? 'auto' : 'smooth' });
  }

  scrollToBottom(): void {
    const container = this.getScrollContainer();
    if (container && typeof container.scrollTo === 'function') {
      container.scrollTo({ top: container.scrollHeight, behavior: this.reducedMotion ? 'auto' : 'smooth' });
      return;
    }
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: this.reducedMotion ? 'auto' : 'smooth' });
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboard(event: KeyboardEvent): void {
    if (this.wallpaperMode) {
      if (event.key === 'Escape') {
        event.preventDefault();
        void this.exitWallpaperMode();
      }
      return;
    }
    if (this.unlockCelebration) {
      if (event.key === 'Escape') {
        event.preventDefault();
        this.dismissUnlockCelebration();
      }
      return;
    }
    if (event.key === 'Escape') {
      if (this.learnTopic) {
        this.closeLearnMore();
        return;
      }
      if (this.accessibilityOpen) {
        this.accessibilityOpen = false;
        this.cdr.markForCheck();
        return;
      }
    }
    if (!event.altKey) return;
    const tabs: Record<string, Tab> = { '1': 'dashboard', '2': 'games', '3': 'history', '4': 'investigator', '5': 'appearance', '6': 'settings', '7': 'redeem', '8': 'connection', '9': 'pc' };
    const tab = tabs[event.key];
    if (tab) {
      event.preventDefault();
      this.setTab(tab);
    }
  }

  private loadUiPreferences(): void {
    const systemReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    this.reducedMotion = systemReduced;
    try {
      const raw = localStorage.getItem(this.uiPrefsKey);
      if (raw) {
        const prefs = JSON.parse(raw) as { theme?: UiTheme; fontScale?: number; reducedMotion?: boolean };
        if (['nebula', 'midnight', 'emerald', 'high-contrast', 'blocks', 'relic', 'tactical', 'operation'].includes(String(prefs.theme)) || (prefs.theme === 'secret' && this.secretUnlocked)) {
          this.uiTheme = prefs.theme as UiTheme;
        }
        this.fontScale = Math.min(125, Math.max(90, Number(prefs.fontScale) || 100));
        if (typeof prefs.reducedMotion === 'boolean') this.reducedMotion = prefs.reducedMotion;
      }
    } catch {
      // Cosmetic preference corruption must never block the app.
    }
    this.applyUiPreferences();
  }

  private persistUiPreferences(): void {
    try {
      localStorage.setItem(this.uiPrefsKey, JSON.stringify({
        theme: this.uiTheme,
        fontScale: this.fontScale,
        reducedMotion: this.reducedMotion
      }));
    } catch {
      // Cosmetic only.
    }
  }

  private applyUiPreferences(): void {
    const root = document.documentElement;
    root.dataset['theme'] = this.uiTheme;
    root.style.setProperty('--font-scale', String(this.fontScale / 100));
    root.classList.toggle('reduce-motion', this.reducedMotion);
  }

  saveApiToken(): void {
    this.nexus.setApiToken(this.apiTokenDraft);
    this.message = this.apiTokenDraft.trim() ? 'Token FastAPI salvo localmente.' : 'Token FastAPI removido.';
    this.cdr.markForCheck();
  }

  async toggleBoost(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.playEngageSound();
    this.message = this.boosted ? 'Restaurando sistema…' : 'Analisando perfil, rede e proteção anticheat…';
    this.cdr.markForCheck();

    try {
      const result = this.boosted
        ? await this.nexus.stopBoost(this.profile)
        : await this.nexus.startBoost(this.profile);
      this.boosted = this.boosted ? !result.ok : result.ok;
      this.message = result.message;
      await Promise.all([this.refreshTelemetry(), this.refreshGames(), this.refreshHealth()]);
      if (!this.boosted) await this.refreshHistory();
    } catch (error) {
      this.message = `Falha de comunicação: ${String(error)}`;
    } finally {
      this.busy = false;
      this.cdr.markForCheck();
    }
  }

  async restoreAll(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.message = 'Executando rollback completo…';
    this.cdr.markForCheck();
    try {
      const result = await this.nexus.restoreAll(this.profile);
      this.boosted = false;
      this.message = result.message;
      await Promise.all([this.refreshTelemetry(), this.refreshHistory(), this.refreshHealth()]);
    } catch (error) {
      this.message = `Falha no rollback: ${String(error)}`;
    } finally {
      this.busy = false;
      this.cdr.markForCheck();
    }
  }

  async runRouteDiagnostics(): Promise<void> {
    if (this.routeBusy) return;
    this.routeBusy = true;
    this.routeReport = null;
    this.message = 'Executando diagnóstico de rota somente leitura…';
    this.cdr.markForCheck();
    try {
      this.routeReport = await this.nexus.routeDiagnostics(this.telemetry?.quality_target ?? '1.1.1.1');
      this.message = 'Diagnóstico concluído. Nenhuma rota foi alterada.';
    } catch (error) {
      this.message = `Diagnóstico falhou: ${String(error)}`;
    } finally {
      this.routeBusy = false;
      this.cdr.markForCheck();
    }
  }

  async refreshGames(): Promise<void> {
    this.games = await this.nexus.discoverGames();
    this.cdr.markForCheck();
  }

  async refreshHistory(): Promise<void> {
    this.history = await this.nexus.history();
    this.cdr.markForCheck();
  }

  async refreshInvestigator(): Promise<void> {
    try {
      this.investigator = await this.nexus.investigator();
    } catch (error) {
      this.message = `Investigador indisponível: ${String(error)}`;
    }
    this.cdr.markForCheck();
  }

  async refreshHealth(): Promise<void> {
    this.gamingHealth = await this.nexus.gamingHealth();
    this.cdr.markForCheck();
  }

  private async refreshTelemetry(): Promise<void> {
    const next = await this.nexus.telemetry();
    this.telemetry = next;
    this.boosted = next.daemon_active;
    if (!next.engine_online && !this.busy) {
      this.message = 'Engine offline. Inicie o app desktop ou a FastAPI de desenvolvimento.';
    }
    this.push(this.pingSeries, next.ping_ms ?? 0);
    this.push(this.cpuSeries, next.cpu_percent);
    this.push(this.networkSeries, next.nexus_score ?? 0);
    this.push(this.gpuSeries, next.gpu_utilization ?? 0);
    this.cdr.markForCheck();
  }

  private push(series: number[], value: number): void {
    series.push(Number.isFinite(value) ? value : 0);
    if (series.length > 28) series.shift();
  }

  private playEngageSound(): void {
    try {
      const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(this.boosted ? 380 : 160, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(this.boosted ? 150 : 620, ctx.currentTime + 0.16);
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.065, ctx.currentTime + 0.025);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.2);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.21);
      setTimeout(() => void ctx.close(), 280);
    } catch {
      // Cosmetic only.
    }
  }
}
