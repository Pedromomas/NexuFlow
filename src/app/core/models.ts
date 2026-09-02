export type BoostProfile = 'auto' | 'safe' | 'roblox' | 'riot_safe' | 'valve_safe' | 'aggressive' | 'ping' | 'pc' | 'complete' | 'hardcore_safe' | 'unknown_safe' | 'protected_safe';

export interface GameInfo {
  id: string;
  display_name: string;
  installed: boolean;
  running: boolean;
  executable?: string | null;
  pid?: number | null;
}

export interface QualitySnapshot {
  target?: string | null;
  sample_count?: number;
  span_seconds?: number;
  latency_ms?: number | null;
  jitter_ms?: number | null;
  packet_loss_percent?: number | null;
  nexus_score?: number;
  grade?: string;
  complete_window?: boolean;
}

export interface SessionQuality {
  before?: QualitySnapshot | null;
  after?: QualitySnapshot | null;
  delta?: {
    latency_ms?: number | null;
    jitter_ms?: number | null;
    packet_loss_percent?: number | null;
    nexus_score?: number | null;
  } | null;
  adaptive_events?: number;
}

export interface AntiCheatStatus {
  active?: boolean;
  provider?: string | null;
  mode?: string | null;
  game_id?: string | null;
  requested_profile?: string;
  effective_profile?: string;
  guarantee?: string | null;
  policy_version?: string;
  policy_reviewed_at?: string;
  lockdown?: string;
  capabilities?: Record<string, boolean> | null;
  blocked_features?: string[];
  allowed_features?: string[];
}

export interface LatencyBudgetDomain {
  status?: string;
  severity?: string;
  confidence?: string;
  evidence?: string[];
  limitations?: string[];
}

export interface LatencyBudget {
  methodology?: string;
  verdict?: {
    primary_area?: string;
    confidence?: string;
    summary?: string;
    causality?: string;
  };
  domains?: Record<string, LatencyBudgetDomain>;
  limitations?: string[];
}

export interface Telemetry {
  timestamp: number;
  engine_online: boolean;
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  ping_ms: number | null;
  jitter_ms: number | null;
  packet_loss_percent: number | null;
  nexus_score: number;
  quality_grade: string;
  quality_target?: string | null;
  quality_window_seconds?: number | null;
  network_status: string;
  active_game: string | null;
  active_game_id?: string | null;
  gpu_name: string | null;
  gpu_utilization: number | null;
  gpu_temperature_c?: number | null;
  daemon_active: boolean;
  effective_profile?: string | null;
  objective_mode?: 'ping' | 'pc' | 'complete' | 'hardcore_safe' | null;
  anti_cheat?: AntiCheatStatus | null;
  session_quality?: SessionQuality | null;
  latency_budget?: LatencyBudget | null;
  recovery_required?: boolean;
}

export interface EngineResponse {
  ok: boolean;
  action: string;
  message: string;
  data?: Record<string, unknown>;
  warnings?: string[];
}

export interface RecoveryStatus {
  required: boolean;
  snapshot_active: boolean;
  daemon_active: boolean;
  session_id?: string | null;
  game?: Record<string, unknown> | null;
  started_at?: number | null;
  restore_errors?: string[];
}

export interface SessionRecord {
  session_id: string;
  game?: { id?: string; display_name?: string } | null;
  requested_profile?: string;
  effective_profile?: string;
  objective_mode?: string;
  started_at?: number;
  ended_at?: number;
  duration_seconds?: number;
  quality_before?: QualitySnapshot | null;
  quality_after?: QualitySnapshot | null;
  quality_delta?: Record<string, number | null> | null;
  adaptive_events?: unknown[];
  fps_average?: number | null;
  fps_source?: string;
  warnings?: string[];
}

export interface GamingHealth {
  cpu?: Record<string, unknown>;
  memory?: Record<string, unknown>;
  gpu?: Record<string, unknown>;
  network?: Record<string, unknown>;
  power?: Record<string, unknown>;
  nic_health?: Record<string, any>;
  windows_gaming?: Record<string, any>;
  stutter_health?: Record<string, any>;
  session_guard?: Record<string, any>;
  policy?: Record<string, any>;
  latency_budget?: LatencyBudget;
  warnings?: Array<{ severity?: string; code?: string; message?: string }>;
}

export interface InvestigatorEvent {
  timestamp: number;
  category: string;
  action: string;
  target: string;
  result: string;
  details?: string;
  session_id?: string | null;
}

export interface InvestigatorSnapshot {
  schema: number;
  read_only: boolean;
  scope: string;
  privacy: string;
  network_contract: {
    default?: string;
    local_api_origins?: string[];
    diagnostic_targets?: string[];
    analytics?: boolean;
    advertising?: boolean;
    remote_commands?: boolean;
    policy_feed?: string;
  };
  events: InvestigatorEvent[];
}

export interface SignedReportEnvelope {
  schema: number;
  algorithm: string;
  trust_scope: string;
  trust_note: string;
  public_key_base64: string;
  key_fingerprint_sha256: string;
  payload_sha256: string;
  payload: Record<string, unknown>;
  signature_base64: string;
}

export interface DriverUpdateOffer {
  title: string;
  manufacturer?: string | null;
  model?: string | null;
  driver_class?: string | null;
  provider?: string | null;
  driver_date?: string | null;
  downloaded?: boolean;
  mandatory?: boolean;
}

export interface DriverScanReport {
  schema?: number;
  available: boolean;
  deferred: boolean;
  read_only: boolean;
  scan_source?: string;
  status: 'updates_available' | 'no_updates_offered' | 'deferred' | 'unavailable';
  updates_offered: number;
  updates: DriverUpdateOffer[];
  download_performed: boolean;
  installation_performed: boolean;
  protected_games?: string[];
  scanned_at?: string | null;
  reason?: string | null;
  caution?: string | null;
  privacy?: string | null;
}

export interface RouteDiagnostics {
  target?: string;
  read_only?: boolean;
  anti_cheat_safe?: boolean;
  hops?: Array<{
    hop?: number;
    address?: string | null;
    loss_percent?: number;
    median_ms?: number | null;
    jitter_ms?: number | null;
  }>;
  analysis?: {
    candidate_degradation_hop?: number | null;
    observations?: string[];
    caution?: string;
  };
}

export interface Diagnostics {
  platform: string;
  admin: boolean;
  interface?: Record<string, unknown>;
  dns?: Record<string, unknown>;
  gpu?: Record<string, unknown>;
  games: GameInfo[];
  daemon_active: boolean;
}
