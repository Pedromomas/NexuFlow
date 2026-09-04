import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PerformanceCenterComponent } from './performance-center.component';
import { NexusService } from './core/nexus.service';
import { Telemetry } from './core/models';

describe('Performance centers 1.7', () => {
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
});
