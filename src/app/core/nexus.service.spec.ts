import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { NexusService } from './nexus.service';

describe('NexusService browser fallback', () => {
  it('reports the engine as offline instead of fabricating PC telemetry', async () => {
    TestBed.configureTestingModule({});
    const service = TestBed.inject(NexusService);
    const sample = await service.telemetry();
    expect(sample.engine_online).toBe(false);
    expect(sample.network_status).toBe('Engine Offline');
    expect(sample.memory_total_gb).toBe(0);
  });
});
