import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NexusService } from './nexus.service';

describe('NexusService browser fallback', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('reports the engine as offline instead of fabricating PC telemetry', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline for this test')));
    TestBed.configureTestingModule({});
    const service = TestBed.inject(NexusService);
    const sample = await service.telemetry();
    expect(sample.engine_online).toBe(false);
    expect(sample.network_status).toContain('npm run dev');
    expect(sample.memory_total_gb).toBe(0);
  });
});
