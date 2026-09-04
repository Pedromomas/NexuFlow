import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppComponent } from './app.component';

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
    expect(fixture.nativeElement.querySelector('.theme-mascot')?.getAttribute('src')).toContain('nexuflow-secret-mascot.png');
    expect(fixture.nativeElement.querySelector('.unlock-celebration')?.textContent).toContain('Arte Secreta');
    fixture.componentInstance.dismissUnlockCelebration();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.unlock-celebration')).toBeNull();
    await fixture.componentInstance.enterWallpaperMode();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.wallpaper-art')?.getAttribute('src')).toContain('nexuflow-secret-cover.jpg');
    await fixture.componentInstance.exitWallpaperMode();
    expect(localStorage.getItem('nexuflow_secret_art_unlocked_v1')).toBe('1');
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
