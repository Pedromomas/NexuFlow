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
});
