import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
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
    expect(document.documentElement.dataset['theme']).toBe('secret');
    expect(fixture.nativeElement.querySelectorAll('.theme-tile').length).toBe(9);
    expect(fixture.nativeElement.querySelector('.theme-mascot')?.getAttribute('src')).toContain('nexuflow-secret-mascot.png');
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
