import { Injectable } from '@angular/core';
import { invoke } from '@tauri-apps/api/core';
import {
  AntiCheatStatus,
  BoostProfile,
  DriverScanReport,
  EngineResponse,
  GameInfo,
  GamingHealth,
  InvestigatorSnapshot,
  RecoveryStatus,
  RouteDiagnostics,
  SessionRecord,
  Telemetry,
  SignedReportEnvelope
} from './models';

type JsonObject = Record<string, unknown>;

@Injectable({ providedIn: 'root' })
export class NexusService {
  private readonly apiBase = 'http://127.0.0.1:8000/api/v1';
  private readonly allowedApiOrigin = 'http://127.0.0.1:8000';
  private readonly tokenKey = 'nexuflow_api_token';

  isDesktop(): boolean {
    return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in (window as unknown as Record<string, unknown>);
  }

  transportLabel(): string {
    return this.isDesktop() ? 'Tauri IPC' : 'FastAPI localhost';
  }

  getStoredApiToken(): string {
    if (typeof localStorage === 'undefined') return '';
    return localStorage.getItem(this.tokenKey) ?? '';
  }

  setApiToken(value: string): void {
    if (typeof localStorage === 'undefined') return;
    const token = value.trim();
    if (token) localStorage.setItem(this.tokenKey, token);
    else localStorage.removeItem(this.tokenKey);
  }

  private async api<T>(path: string, init: RequestInit = {}, mutation = false): Promise<T> {
    const headers = new Headers(init.headers ?? {});
    headers.set('Accept', 'application/json');
    if (init.body) headers.set('Content-Type', 'application/json');

    if (mutation) {
      const token = this.getStoredApiToken();
      if (!token) {
        throw new Error('Token da API ausente. Inicie scripts/run-api.ps1 e salve o token em Ajustes.');
      }
      headers.set('X-NexuFlow-Token', token);
    }

    const url = new URL(`${this.apiBase}${path}`);
    if (url.origin !== this.allowedApiOrigin || !url.pathname.startsWith('/api/v1/')) {
      throw new Error('A allowlist de rede bloqueou um destino não local.');
    }
    const response = await fetch(url.toString(), { ...init, headers });
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const body = await response.json() as { detail?: string };
        detail = body.detail ?? detail;
      } catch {
        // Keep HTTP status.
      }
      throw new Error(detail);
    }
    return await response.json() as T;
  }

  async startBoost(profile: BoostProfile): Promise<EngineResponse> {
    try {
      if (this.isDesktop()) return await invoke<EngineResponse>('start', { profile });
      return await this.api<EngineResponse>('/boost/start', {
        method: 'POST',
        body: JSON.stringify({ profile })
      }, true);
    } catch (error) {
      return { ok: false, action: 'start', message: String(error) };
    }
  }

  async stopBoost(profile: BoostProfile = 'auto'): Promise<EngineResponse> {
    try {
      if (this.isDesktop()) return await invoke<EngineResponse>('stop', { profile });
      return await this.api<EngineResponse>('/boost/stop', { method: 'POST', body: '{}' }, true);
    } catch (error) {
      return { ok: false, action: 'stop', message: String(error) };
    }
  }

  async restoreAll(profile: BoostProfile = 'auto'): Promise<EngineResponse> {
    try {
      if (this.isDesktop()) return await invoke<EngineResponse>('restore', { profile });
      return await this.api<EngineResponse>('/restore', { method: 'POST', body: '{}' }, true);
    } catch (error) {
      return { ok: false, action: 'restore', message: String(error) };
    }
  }

  async telemetry(): Promise<Telemetry> {
    try {
      if (this.isDesktop()) return await invoke<Telemetry>('get_telemetry');
      return await this.api<Telemetry>('/telemetry');
    } catch {
      // Never fabricate healthy telemetry. An offline engine should look
      // offline, not like a real PC with 0% CPU / fake RAM.
      return {
        timestamp: Date.now(),
        engine_online: false,
        cpu_percent: 0,
        memory_percent: 0,
        memory_used_gb: 0,
        memory_total_gb: 0,
        ping_ms: null,
        jitter_ms: null,
        packet_loss_percent: null,
        nexus_score: 0,
        quality_grade: 'Offline',
        network_status: 'Engine Offline',
        active_game: null,
        gpu_name: null,
        gpu_utilization: null,
        daemon_active: false
      };
    }
  }

  async discoverGames(): Promise<GameInfo[]> {
    try {
      if (this.isDesktop()) return await invoke<GameInfo[]>('discover_games');
      return await this.api<GameInfo[]>('/games');
    } catch {
      return [];
    }
  }

  async diagnostics(): Promise<JsonObject> {
    if (this.isDesktop()) return await invoke<JsonObject>('get_diagnostics');
    return await this.api<JsonObject>('/diagnostics');
  }

  async gamingHealth(): Promise<GamingHealth> {
    try {
      if (this.isDesktop()) return await invoke<GamingHealth>('get_gaming_health');
      return await this.api<GamingHealth>('/gaming-health');
    } catch {
      return {};
    }
  }

  async scanDriverUpdates(): Promise<DriverScanReport> {
    if (this.isDesktop()) return await invoke<DriverScanReport>('scan_driver_updates');
    return await this.api<DriverScanReport>('/drivers/scan');
  }

  async openDriverUpdates(): Promise<{ ok: boolean; message?: string }> {
    if (this.isDesktop()) return await invoke<{ ok: boolean; message?: string }>('open_driver_updates');
    return await this.api<{ ok: boolean; message?: string }>('/drivers/open-updates', {
      method: 'POST',
      body: '{}'
    }, true);
  }

  async history(): Promise<SessionRecord[]> {
    try {
      if (this.isDesktop()) return await invoke<SessionRecord[]>('get_history');
      return await this.api<SessionRecord[]>('/history?limit=50');
    } catch {
      return [];
    }
  }

  async investigator(): Promise<InvestigatorSnapshot> {
    if (this.isDesktop()) return await invoke<InvestigatorSnapshot>('get_investigator');
    return await this.api<InvestigatorSnapshot>('/investigator?limit=100');
  }

  async signSessionReport(report: Record<string, unknown>): Promise<SignedReportEnvelope> {
    if (this.isDesktop()) return await invoke<SignedReportEnvelope>('sign_session_report', { report });
    return await this.api<SignedReportEnvelope>('/reports/sign', {
      method: 'POST',
      body: JSON.stringify(report)
    }, true);
  }

  async recoveryStatus(): Promise<RecoveryStatus> {
    try {
      if (this.isDesktop()) return await invoke<RecoveryStatus>('get_recovery_status');
      return await this.api<RecoveryStatus>('/recovery');
    } catch {
      return { required: false, snapshot_active: false, daemon_active: false };
    }
  }

  async antiCheatStatus(gameId?: string | null): Promise<AntiCheatStatus> {
    try {
      if (this.isDesktop()) return await invoke<AntiCheatStatus>('get_anti_cheat_status', { gameId: gameId ?? null });
      const query = gameId ? `?game_id=${encodeURIComponent(gameId)}` : '';
      return await this.api<AntiCheatStatus>(`/anti-cheat${query}`);
    } catch {
      return {};
    }
  }

  async routeDiagnostics(target = '1.1.1.1'): Promise<RouteDiagnostics> {
    if (this.isDesktop()) return await invoke<RouteDiagnostics>('get_route_diagnostics', { target });
    return await this.api<RouteDiagnostics>(`/route-diagnostics?target=${encodeURIComponent(target)}`);
  }
}
