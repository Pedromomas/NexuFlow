import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PerformanceCenterComponent } from './performance-center.component';
import { NexusService } from './core/nexus.service';
import { Telemetry } from './core/models';

describe('Performance centers 2.1', () => {
  beforeEach(() => localStorage.clear());
  async function create() {
    await TestBed.configureTestingModule({imports: [PerformanceCenterComponent]}).compileComponents();
    const f = TestBed.createComponent(PerformanceCenterComponent);
    return {f, c: f.componentInstance, service: TestBed.inject(NexusService)};
  }
  it('shows missing readings as unknown, never optimized', async () => {
    const {f, c} = await create(); c.mode = 'pc'; f.detectChanges();
    expect(f.nativeElement.textContent).toContain('Sem leitura');
    expect(c.pcCards.every(x => !x.attention)).toBe(true); f.destroy();
  });
  it('keeps timeouts as gaps, accepts real zero RTT and hides stale readings', async () => {
    const {f, c} = await create();
    c.telemetry = {engine_online: true, connection_history: {stale: false, samples: [
      {latency_ms: 0}, {latency_ms: null}, {latency_ms: 20}, {latency_ms: 10}
    ]}} as Telemetry;
    expect(c.graphPaths.length).toBe(2); expect(c.timeouts.length).toBe(1); expect(c.live).toBe(true);
    c.telemetry.connection_history!.stale = true; expect(c.live).toBe(false); f.destroy();
  });
  it('reports scanner failure and releases busy state', async () => {
    const {f, c, service} = await create();
    vi.spyOn(service, 'scanConnection').mockRejectedValue(new Error('offline'));
    await c.run('scan'); expect(service.centerBusy).toBe(false); expect(c.notice).toContain('offline'); f.destroy();
  });
  it('does not start duplicate diagnostics or open arbitrary settings', async () => {
    const {f, c, service} = await create();
    const spy = vi.spyOn(service, 'scanConnection'); service.centerBusy = true;
    await c.run('scan'); expect(spy).not.toHaveBeenCalled();
    await expect(service.openPcSettings('powershell')).rejects.toThrow('não permitido'); f.destroy();
  });
  it('ignores malformed local history', async () => {
    localStorage.setItem('nexuflow_connection_scans_v17', '[null, {}, {"schema": 1}]');
    const {f, service} = await create(); expect(service.connectionScans).toEqual([]); f.destroy();
  });
  it('runs a bounded speed test only when boost is off', async () => {
    const {f, c, service} = await create();
    const spy = vi.spyOn(service, 'runSpeedTest').mockResolvedValue({schema: 1, kind: 'bounded_speed_test', measured_at: 1, provider: 'Cloudflare', endpoint: 'speed.cloudflare.com', download_mbps: 100, upload_mbps: 40, download_samples_mbps: [100], upload_samples_mbps: [40], transferred_bytes_max: 30 * 1024 * 1024, read_only: true, mutation_performed: false, note: 'local'});
    c.boosted = true; await c.runSpeed(); expect(spy).not.toHaveBeenCalled();
    c.boosted = false; await c.runSpeed(); expect(c.speedTest?.download_mbps).toBe(100); f.destroy();
  });
  it('blocks the speed test in a protected runtime and exposes every automation state', async () => {
    const {f, c, service} = await create();
    const spy = vi.spyOn(service, 'runSpeedTest');
    c.telemetry = {engine_online: true, anti_cheat: {active: true}} as Telemetry;
    await c.runSpeed(); expect(spy).not.toHaveBeenCalled();
    c.boostIntent = 'starting'; expect(c.automationState).toBe('preparando');
    c.boostIntent = 'stopping'; expect(c.automationState).toBe('restaurando');
    c.boostIntent = 'idle'; c.boosted = true; expect(c.automationState).toBe('ligado');
    c.boosted = false; expect(c.automationState).toBe('desligado'); f.destroy();
  });
  it('keeps Safe Core independent and emits the automation action', async () => {
    const {f, c} = await create(); c.mode = 'pc'; c.telemetry = {engine_online: true} as Telemetry;
    const spy = vi.spyOn(c.toggleSmart, 'emit'); f.detectChanges();
    expect(f.nativeElement.textContent).toContain('Safe não podem ser desligados');
    expect(f.nativeElement.textContent).toContain('Desligado significa “nenhuma otimização ativa”');
    f.nativeElement.querySelector('.pc-flow-console').click(); expect(spy).toHaveBeenCalledOnce(); f.destroy();
  });
});
