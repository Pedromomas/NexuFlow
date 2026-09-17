import { beforeEach, describe, expect, it, vi } from 'vitest';
import { check, Update } from '@tauri-apps/plugin-updater';
import { UpdateService } from './update.service';
import { NexusService } from './nexus.service';
vi.mock('@tauri-apps/plugin-updater', () => ({ check: vi.fn() }));

describe('Update session boundaries (plugin mocked; not a real upgrade)', () => {
  let service: UpdateService;
  let nexus: NexusService;
  let update: Update;
  let snapshot: Record<string, unknown>;
  beforeEach(() => {
    vi.clearAllMocks(); localStorage.clear();
    snapshot = { timestamp: Date.now(), engine_online: true, daemon_active: false, recovery_required: false, anti_cheat: { active: false }, active_game: null };
    nexus = { isDesktop: () => true, telemetry: vi.fn(async () => snapshot), centerBusy: false, boostStarting: false, updateInProgress: false } as unknown as NexusService;
    service = new UpdateService(nexus); service.configured = true; service.privateDistribution = false;
    update = { version: '2.1.0-beta.5', body: 'Visual update', download: vi.fn().mockResolvedValue(undefined), install: vi.fn().mockResolvedValue(undefined), close: vi.fn() } as unknown as Update;
    vi.mocked(check).mockResolvedValue(update);
  });
  it('does not request a private release or pretend it is current', async () => {
    service.privateDistribution = true;
    await service.checkWhenSafe(false, false); await service.checkNow(false, false);
    expect(check).not.toHaveBeenCalled(); expect(service.error).toContain('aguardam validação');
  });
  it.each([{ timestamp: 0 }, { timestamp: undefined }, { recovery_required: undefined }, { daemon_active: true }, { anti_cheat: { active: true } }, { anti_cheat: null }, { engine_online: false }, { recovery_required: true }, { active_game: 'Roblox' }])('fails closed on unsafe or missing status: %j', async data => {
    Object.assign(snapshot, data); await service.checkWhenSafe(false, false);
    expect(check).not.toHaveBeenCalled();
  });
  it('does not auto-install a critical manifest while a game starts during check', async () => {
    update.body = '[SECURITY-REQUIRED] correction';
    vi.mocked(check).mockImplementation(async () => { snapshot['active_game'] = 'VALORANT'; return update; });
    await service.checkWhenSafe(false, false); await service.install();
    expect(update.download).not.toHaveBeenCalled(); expect(service.state).toBe('waiting');
    expect(service.securityUpdateBlocking).toBe(true);
  });
  it('rechecks after download and resumes without downloading twice', async () => {
    await service.checkWhenSafe(false, false);
    vi.mocked(update.download).mockImplementation(async () => { snapshot['daemon_active'] = true; });
    await service.install(); expect(service.state).toBe('waiting'); expect(update.install).not.toHaveBeenCalled();
    snapshot['daemon_active'] = false;
    await service.install(); expect(update.install).toHaveBeenCalledTimes(1); expect(update.download).toHaveBeenCalledTimes(1);
  });
  it.each(['invalid signature', 'connection interrupted'])('never installs on plugin rejection: %s', async message => {
    update.body = '[SECURITY-REQUIRED] correction'; await service.checkWhenSafe(false, false);
    vi.mocked(update.download).mockRejectedValueOnce(new Error(message));
    await service.install(); expect(service.state).toBe('error'); expect(update.install).not.toHaveBeenCalled();
    expect(service.securityUpdateBlocking).toBe(true); expect(service.visible).toBe(true);
    await service.install(); expect(update.install).toHaveBeenCalledTimes(1);
  });
  it('serializes duplicate requests and prevents BOOST during transfer', async () => {
    await service.checkWhenSafe(false, false);
    let finish!: () => void;
    vi.mocked(update.download).mockImplementation(() => new Promise<void>(resolve => { finish = resolve; }));
    const first = service.install(); await vi.waitFor(() => expect(finish).toBeDefined());
    expect(nexus.updateInProgress).toBe(true);
    await service.install(); await service.checkNow(false, false);
    expect(update.download).toHaveBeenCalledTimes(1);
    finish(); await first; expect(nexus.updateInProgress).toBe(false);
  });
  it('optional dismissal never dismisses a future critical correction', async () => {
    update.body = '[SECURITY-REQUIRED] correction'; await service.checkWhenSafe(false, false);
    service.dismiss(); expect(service.visible).toBe(true);
  });
});
