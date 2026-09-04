import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppComponent } from './app.component';
import { NexusService } from './core/nexus.service';
import { EngineResponse } from './core/models';

describe('AppComponent', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue();
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it('plays the local secret clip once per new reward, including after reset', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    const play = vi.mocked(HTMLMediaElement.prototype.play);
    app.secretCodeDraft = 'invalid'; await app.redeemSecretCode();
    expect(play).not.toHaveBeenCalled();
    app.secretCodeDraft = 'NEXU-SECRETO-157'; await app.redeemSecretCode();
    expect(play).toHaveBeenCalledTimes(1);
    const clip = play.mock.contexts[0] as HTMLMediaElement;
    expect(clip.src).toContain('theme-art/secret/secret-unlock.mp3');
    expect(clip.volume).toBe(0.7); expect(clip.loop).toBe(false);
    app.dismissUnlockCelebration(); expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    app.secretCodeDraft = 'NEXU-SECRETO-157'; await app.redeemSecretCode();
    expect(play).toHaveBeenCalledTimes(1);
    app.secretCodeDraft = 'RESET-CODIGOS'; await app.redeemSecretCode();
    app.secretCodeDraft = 'NEXU-SECRETO-157'; await app.redeemSecretCode();
    expect(play).toHaveBeenCalledTimes(2); fixture.destroy();
  });

  it('requires one independent code for each secret theme', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;

    app.secretCodeDraft = 'NEXU-SECRETO-157'; await app.redeemSecretCode();
    expect(app.unlockedSecretRewards).toEqual(['origin']);
    expect(app.secretOriginUnlocked).toBe(true);
    expect(app.secretRioUnlocked).toBe(false);
    expect(app.secretKiwiUnlocked).toBe(false);
    app.dismissUnlockCelebration();

    app.secretCodeDraft = 'NEXU-RIO-021'; await app.redeemSecretCode();
    expect(app.unlockedSecretRewards).toEqual(['origin', 'rio']);
    expect(app.uiTheme).toBe('secret-rio');
    expect(app.unlockReward.animationClass).toBe('unlock-rio');
    app.dismissUnlockCelebration();

    app.secretCodeDraft = 'NEXU-KIWI-021'; await app.redeemSecretCode();
    expect(app.unlockedSecretRewards).toEqual(['origin', 'rio', 'kiwi']);
    expect(app.uiTheme).toBe('secret-kiwi');
    expect(app.unlockReward.animationClass).toBe('unlock-kiwi');
    expect(JSON.parse(localStorage.getItem('nexuflow_secret_rewards_v2') || '[]')).toEqual(['origin', 'rio', 'kiwi']);
    fixture.destroy();
  });

  it('keeps the reward unlocked when automatic audio is blocked', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    vi.mocked(HTMLMediaElement.prototype.play).mockRejectedValue(new Error('NotAllowedError'));
    app.secretCodeDraft = 'NEXU-SECRETO-157'; await app.redeemSecretCode();
    expect(app.secretUnlocked).toBe(true); expect(app.unlockCelebration).toBe(true);
    expect(app.secretAudioState).toBe('blocked');
    fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Tocar som do desbloqueio'); fixture.destroy();
  });

  it('filters games and persists favorites without losing stable row identity', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.games = [{id: 'fortnite', display_name: 'Fortnite', installed: false, running: false}, {id: 'roblox', display_name: 'Roblox', installed: true, running: true}];
    app.toggleFavorite('fortnite'); app.gameFilter = 'favorites';
    expect(app.filteredGames.map(g => g.id)).toEqual(['fortnite']);
    expect(JSON.parse(localStorage.getItem('nexuflow_favorite_games_v17')!)).toEqual(['fortnite']);
    expect(app.trackGameId(0, {...app.games[0]})).toBe('fortnite');
    app.gameFilter = 'all'; app.gameQuery = 'ROB';
    expect(app.filteredGames.map(g => g.id)).toEqual(['roblox']);
    fixture.destroy();
  });

  it('prepares the PC objective without starting boost', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.preparePc(); expect(app.tab).toBe('dashboard'); expect(app.profile).toBe('pc'); expect(app.boosted).toBe(false);
    fixture.destroy();
  });

  it('resets only code rewards, restores the mystery and allows another redemption', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.secretCodeDraft = 'NEXU-SECRETO-157';
    await app.redeemSecretCode();
    app.setFontScale(120);
    app.profile = 'ping';
    localStorage.setItem('nexuflow_api_token', 'keep-test-token');
    app.setTab('redeem');
    app.openCodeForm();
    app.secretCodeDraft = 'invalid-code';
    await app.redeemSecretCode();
    expect(app.secretUnlocked).toBe(true);
    expect(app.tab).toBe('redeem');
    app.secretCodeDraft = 'RESET-CODIGOS';
    await app.redeemSecretCode();
    fixture.detectChanges();
    expect(app.uiTheme).toBe('nebula');
    expect(app.fontScale).toBe(120);
    expect(app.profile).toBe('ping');
    expect(localStorage.getItem('nexuflow_api_token')).toBe('keep-test-token');
    expect(localStorage.getItem('nexuflow_secret_art_unlocked_v1')).toBeNull();
    expect(localStorage.getItem('nexuflow_secret_rewards_v2')).toBeNull();
    expect(fixture.nativeElement.querySelector('.vault-cover')).toBeNull();
    expect(fixture.nativeElement.querySelector('.vault-mystery')).toBeTruthy();
    app.secretCodeDraft = 'NEXU-SECRETO-157';
    await app.redeemSecretCode();
    fixture.detectChanges();
    expect(app.secretUnlocked).toBe(true);
    expect(fixture.nativeElement.querySelector('.flux-story')?.textContent).toContain('CONHEÇA O JOÃO');
    fixture.destroy();
  });

  it('keeps artwork view usable when browser fullscreen is denied and exits with Escape', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    const previousRequest = Object.getOwnPropertyDescriptor(document.documentElement, 'requestFullscreen');
    Object.defineProperty(document.documentElement, 'requestFullscreen', { configurable: true, value: vi.fn().mockRejectedValue(new Error('not allowed')) });
    try {
      app.tab = 'appearance';
      app.boosted = true;
      await app.enterWallpaperMode();
      fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.shell.wallpaper-mode')).toBeTruthy();
      expect(fixture.nativeElement.querySelector('.wallpaper-art')).toBeTruthy();
      expect(fixture.nativeElement.querySelector('#wallpaper-exit')).toBeTruthy();
      app.handleKeyboard(new KeyboardEvent('keydown', { key: 'Escape' }));
      await Promise.resolve();
      fixture.detectChanges();
      expect(app.wallpaperMode).toBe(false);
      expect(app.boosted).toBe(true);
      expect(app.tab).toBe('appearance');
    } finally {
      if (previousRequest) Object.defineProperty(document.documentElement, 'requestFullscreen', previousRequest);
      else delete (document.documentElement as Partial<HTMLElement>).requestFullscreen;
      fixture.destroy();
    }
  });
  it('creates the NexuFlow shell', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance).toBeTruthy();
    fixture.destroy();
  });

  it('identifies browser preview instead of reporting a broken desktop engine', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.telemetry = {
      timestamp: Date.now(), engine_online: false, cpu_percent: 0, memory_percent: 0,
      memory_used_gb: 0, memory_total_gb: 0, ping_ms: null, jitter_ms: null,
      packet_loss_percent: null, nexus_score: 0, quality_grade: 'Offline',
      network_status: 'Previa sem motor', active_game: null, gpu_name: null,
      gpu_utilization: null, daemon_active: false
    };
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('MODO WEB');
    expect(fixture.nativeElement.textContent).toContain('Previa no navegador');
    fixture.destroy();
  });

  it('shows BOOST feedback before the engine finishes preparing', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    const nexus = TestBed.inject(NexusService);
    let release!: (value: EngineResponse) => void;
    const pending = new Promise<EngineResponse>(resolve => { release = resolve; });
    vi.spyOn(nexus, 'startBoost').mockReturnValue(pending);
    let releaseRefresh!: () => void;
    const backgroundRefresh = new Promise<void>(resolve => { releaseRefresh = resolve; });
    const privateApp = app as unknown as {refreshTelemetry: () => Promise<void>};
    vi.spyOn(privateApp, 'refreshTelemetry').mockReturnValue(backgroundRefresh);
    vi.spyOn(app, 'refreshGames').mockResolvedValue(undefined);
    vi.spyOn(app, 'refreshHealth').mockResolvedValue(undefined);

    const operation = app.toggleBoost();
    expect(app.boostIntent).toBe('starting');
    expect(app.busy).toBe(true);
    expect(app.message).toContain('Analisando');

    release({ok: true, action: 'start', message: 'Fluxo Vivo ativado.'});
    await operation;
    expect(app.boosted).toBe(true);
    expect(app.boostIntent).toBe('idle');
    expect(app.busy).toBe(false);
    releaseRefresh();
    await backgroundRefresh;
    fixture.destroy();
  });

  it('blocks a new BOOST session while a signed critical update is pending', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    const nexus = TestBed.inject(NexusService);
    const start = vi.spyOn(nexus, 'startBoost');
    app.updates.requiresSecurityUpdate = true;
    app.updates.state = 'available';
    await app.toggleBoost();
    expect(start).not.toHaveBeenCalled();
    expect(app.boosted).toBe(false);
    expect(app.message).toContain('correção crítica');
    fixture.destroy();
  });

  it('does not overlap periodic reads when the engine is slow', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    let releaseRefresh!: () => void;
    const slowRefresh = new Promise<void>(resolve => { releaseRefresh = resolve; });
    const privateApp = app as unknown as {
      periodicRefresh: () => Promise<void>;
      refreshTelemetry: () => Promise<void>;
    };
    const refresh = vi.spyOn(privateApp, 'refreshTelemetry')
      .mockReturnValueOnce(slowRefresh)
      .mockResolvedValue(undefined);

    const firstCycle = privateApp.periodicRefresh();
    await privateApp.periodicRefresh();
    expect(refresh).toHaveBeenCalledTimes(1);

    releaseRefresh();
    await firstCycle;
    await privateApp.periodicRefresh();
    expect(refresh).toHaveBeenCalledTimes(2);
    fixture.destroy();
  });

  it('defaults legacy or invalid choices to the clear Complete objective', async () => {
    localStorage.removeItem('nexuflow_boost_mode_v142');
    localStorage.setItem('nexuflow_boost_mode_v141', 'roblox');
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance.profile).toBe('complete');
    fixture.destroy();
    localStorage.clear();
  });

  it('applies the selected text scale to the complete UI token', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.setFontScale(125);
    expect(document.documentElement.style.getPropertyValue('--font-scale')).toBe('1.25');
    expect(fixture.componentInstance.fontScale).toBe(125);
    fixture.destroy();
  });

  it('ships the on-demand Windows Update Driver Center', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.tab = 'settings';
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Central de drivers');
    expect(fixture.nativeElement.textContent).toContain('Verificar drivers');
    fixture.destroy();
  });

  it('keeps update status visible and fails closed without release credentials', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    app.tab = 'settings'; fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('CENTRAL DE ATUALIZAÇÕES');
    expect(fixture.nativeElement.textContent).toContain('Aguardando canal assinado');
    await app.checkForUpdates(); fixture.detectChanges();
    expect(app.updates.state).toBe('error');
    expect(app.updates.error).toContain('build não inclui o canal assinado');
    fixture.destroy();
  });

  it('keeps the signed update channel visible from every page', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    for (const tab of ['dashboard', 'games', 'connection', 'pc', 'history', 'investigator', 'appearance', 'settings', 'account', 'redeem'] as const) {
      fixture.componentInstance.tab = tab;
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.global-update-status')).toBeTruthy();
    }
    fixture.destroy();
  });

  it('shows account, profile and subscription entry points without fake registration', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.tab = 'account'; fixture.detectChanges();
    await Promise.resolve(); fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Conta e assinatura');
    expect(text).toContain('Criar conta');
    expect(text).toContain('Cadastro ainda não foi aberto');
    expect(fixture.nativeElement.querySelector('.account-submit').disabled).toBe(true);
    fixture.destroy();
  });

  it('shows every planned price without enabling a fake checkout', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.tab = 'settings'; fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('R$1');
    expect(text).toContain('R$5');
    expect(text).toContain('R$10');
    expect(text).toContain('R$80');
    expect(text).toContain('Titular + 1 amigo');
    expect(fixture.nativeElement.querySelector('.subscription-preview button')).toBeNull();
    fixture.destroy();
  });

  it('keeps Appearance separate from system settings and exposes eight original themes', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.setTab('appearance');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Um NexuFlow com a sua energia.');
    expect(fixture.nativeElement.textContent).toContain('Arte original, não afiliado');
    expect(fixture.nativeElement.querySelectorAll('.theme-tile').length).toBe(8);
    fixture.destroy();
  });

  it('applies an inspired theme as a cosmetic root preference', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.setTheme('relic');
    expect(document.documentElement.dataset['theme']).toBe('relic');
    expect(fixture.componentInstance.gamesNavigationIcon).toBe('icon-relic');
    expect(fixture.componentInstance.themeSignatureIcon).toBe('icon-relic');
    expect(JSON.parse(localStorage.getItem('nexuflow_ui_preferences_v1') || '{}').theme).toBe('relic');
    fixture.destroy();
    localStorage.clear();
  });

  it('unlocks the secret art locally and reveals its theme only after redemption', async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    fixture.componentInstance.tab = 'redeem';
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.vault-mystery')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.vault-cover')).toBeNull();

    fixture.componentInstance.setTab('appearance');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.theme-tile').length).toBe(8);

    fixture.componentInstance.secretCodeDraft = 'nexu-secreto-157';
    await fixture.componentInstance.redeemSecretCode();
    fixture.detectChanges();

    expect(fixture.componentInstance.secretUnlocked).toBe(true);
    expect(fixture.componentInstance.uiTheme).toBe('secret');
    expect(fixture.componentInstance.unlockCelebration).toBe(true);
    expect(document.documentElement.dataset['theme']).toBe('secret');
    expect(fixture.nativeElement.querySelectorAll('.theme-tile').length).toBe(9);
    expect(fixture.nativeElement.querySelector('.secret-cover')?.getAttribute('src')).toContain('nexuflow-secret-origin-2.1.webp');
    expect(fixture.nativeElement.querySelector('.unlock-celebration')?.textContent).toContain('Edição Origem');
    fixture.componentInstance.dismissUnlockCelebration();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.unlock-celebration')).toBeNull();
    await fixture.componentInstance.enterWallpaperMode();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.wallpaper-art')?.getAttribute('src')).toContain('nexuflow-secret-origin-2.1.webp');
    await fixture.componentInstance.exitWallpaperMode();
    expect(JSON.parse(localStorage.getItem('nexuflow_secret_rewards_v2') || '[]')).toEqual(['origin']);
    fixture.componentInstance.setTheme('nebula');
    fixture.destroy();
    localStorage.clear();
  });

  it('maps latency evidence to distinct visual status tones', async () => {
    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance.latencyStatusTone('no_issue_observed')).toBe('good');
    expect(fixture.componentInstance.latencyStatusTone('insufficient_data')).toBe('warning');
    expect(fixture.componentInstance.latencyStatusTone('degradation_observed')).toBe('danger');
    expect(fixture.componentInstance.latencyStatusTone('indeterminate')).toBe('neutral');
    fixture.destroy();
  });
});
