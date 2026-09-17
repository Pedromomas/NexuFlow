import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, OnDestroy, Output } from '@angular/core';
import { ConnectionScan, DnsRanking, GamingHealth, SpeedTestResult, Telemetry } from './core/models';
import { NexusService } from './core/nexus.service';

@Component({
  selector: 'app-performance-center', standalone: true, imports: [CommonModule],
  templateUrl: './performance-center.component.html', changeDetection: ChangeDetectionStrategy.OnPush
})
export class PerformanceCenterComponent implements OnDestroy {
  @Input() mode: 'connection' | 'pc' = 'connection';
  @Input() telemetry: Telemetry | null = null;
  @Input() health: GamingHealth = {};
  @Input() boosted = false;
  @Input() boostBusy = false;
  @Input() boostIntent: 'idle' | 'starting' | 'stopping' = 'idle';
  @Output() refresh = new EventEmitter<void>();
  @Output() preparePc = new EventEmitter<void>();
  @Output() toggleSmart = new EventEmitter<void>();
  notice = '';
  selectedScan = 0;
  speedTest: SpeedTestResult | null = null;
  speedBusy = false;
  dnsLive = false;
  dnsLiveSeconds = 0;
  dnsLiveSamples: Array<{measured_at: number; results: DnsRanking['results']}> = [];
  private dnsTimer?: ReturnType<typeof setTimeout>;
  private destroyed = false;
  private readonly historyKey = 'nexuflow_connection_scans_v17';
  constructor(public readonly nexus: NexusService, private readonly cdr: ChangeDetectorRef) {
    if (!nexus.connectionScans.length) {
      try {
        const raw = localStorage.getItem(this.historyKey);
        if (raw && raw.length < 100000) {
          const parsed: unknown = JSON.parse(raw);
          if (Array.isArray(parsed)) nexus.connectionScans = parsed.filter(this.validScan).slice(0, 10);
        }
      } catch { /* Local history is optional; a damaged cache never blocks startup. */ }
    }
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.stopDnsLive();
  }

  private validScan(value: unknown): value is ConnectionScan {
    if (!value || typeof value !== 'object') return false;
    const s = value as ConnectionScan;
    return s.schema === 1 && s.kind === 'connection_scan' && Number.isFinite(s.measured_at)
      && typeof s.conclusion === 'string' && typeof s.method === 'string' && Array.isArray(s.results)
      && s.results.length === 3 && s.results.every(r => r && ['1.1.1.1', '8.8.8.8', '9.9.9.9'].includes(r.target ?? '') && typeof r.name === 'string');
  }

  get scan(): ConnectionScan | null { return this.nexus.connectionScans[this.selectedScan] ?? null; }
  get monitor() { return this.telemetry?.engine_online ? this.telemetry.connection_history : null; }
  get live(): boolean { return !!this.monitor && !this.monitor.stale; }
  get protectedGameActive(): boolean {
    return this.telemetry?.anti_cheat?.active === true
      || ['riot_safe', 'valve_safe', 'protected_safe', 'unknown_safe'].includes(this.telemetry?.effective_profile ?? '');
  }
  get automationState(): 'desligado' | 'preparando' | 'ligado' | 'restaurando' {
    if (this.boostIntent === 'starting') return 'preparando';
    if (this.boostIntent === 'stopping') return 'restaurando';
    return this.boosted ? 'ligado' : 'desligado';
  }
  get graphMax(): number { return Math.max(10, ...(this.monitor?.samples ?? []).map(s => s.latency_ms ?? 0)); }
  get graphPaths(): string[] {
    const samples = this.monitor?.samples ?? [];
    const paths: string[] = []; let current = '';
    samples.forEach((s, i) => {
      if (s.latency_ms === null) { if (current) paths.push(current); current = ''; return; }
      const x = 10 + (i / Math.max(1, samples.length - 1)) * 780;
      const y = 170 - (s.latency_ms / this.graphMax) * 145;
      current += `${current ? ' L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    });
    if (current) paths.push(current);
    return paths;
  }
  get timeouts(): number[] {
    const samples = this.monitor?.samples ?? [];
    return samples.flatMap((s, i) => s.latency_ms === null ? [10 + i / Math.max(1, samples.length - 1) * 780] : []);
  }
  async run(kind: 'scan' | 'dns'): Promise<void> {
    if (this.nexus.centerBusy || this.nexus.updateInProgress) return;
    this.nexus.centerBusy = true; this.notice = kind === 'scan' ? 'Comparando três referências; cerca de 3 a 12 segundos…' : 'Consultando dois servidores de cada provedor…';
    try {
      if (kind === 'scan') {
        const result = await this.nexus.scanConnection();
        this.nexus.connectionScans = [result, ...this.nexus.connectionScans].slice(0, 10);
        this.selectedScan = 0;
        try { localStorage.setItem(this.historyKey, JSON.stringify(this.nexus.connectionScans)); }
        catch { this.notice = 'Scan concluído; o histórico local não pôde ser salvo.'; return; }
      } else this.nexus.dnsRanking = await this.nexus.rankDns();
      this.notice = 'Medição concluída. Nenhuma configuração foi alterada.';
    } catch (error) { this.notice = `Não foi possível concluir: ${String(error)}`; }
    finally { this.nexus.centerBusy = false; this.cdr.markForCheck(); }
  }
  async toggleDnsLive(): Promise<void> {
    if (this.dnsLive) { this.stopDnsLive(); return; }
    if (this.nexus.centerBusy || this.nexus.updateInProgress || !this.telemetry?.engine_online) return;
    this.dnsLive = true;
    this.dnsLiveSeconds = 0;
    this.dnsLiveSamples = [];
    this.notice = 'Comparação DNS ao vivo iniciada por até 60 segundos. Nenhum DNS será trocado.';
    await this.captureDnsLive();
  }
  stopDnsLive(): void {
    this.dnsLive = false;
    if (this.dnsTimer) clearTimeout(this.dnsTimer);
    this.dnsTimer = undefined;
    this.cdr.markForCheck();
  }
  private async captureDnsLive(): Promise<void> {
    if (!this.dnsLive || this.destroyed || this.nexus.centerBusy || this.nexus.updateInProgress) { this.stopDnsLive(); return; }
    this.nexus.centerBusy = true;
    try {
      const result = await this.nexus.rankDns();
      this.nexus.dnsRanking = result;
      this.dnsLiveSamples = [...this.dnsLiveSamples, {measured_at: result.measured_at, results: result.results}].slice(-8);
    } catch (error) {
      this.notice = `Comparação DNS interrompida: ${String(error)}`;
      this.stopDnsLive();
      return;
    } finally {
      this.nexus.centerBusy = false;
      this.cdr.markForCheck();
    }
    this.dnsLiveSeconds += 10;
    if (this.dnsLiveSeconds >= 60) {
      this.notice = 'Comparação DNS concluída. Isso mede resolução de nomes, não o ping da partida.';
      this.stopDnsLive();
      return;
    }
    this.dnsTimer = setTimeout(() => void this.captureDnsLive(), 10000);
  }
  dnsSpark(provider: string): string {
    const values = this.dnsLiveSamples.map(sample => sample.results.find(row => row.provider === provider)?.median_ms ?? null);
    const finite = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (finite.length < 2) return '';
    const maximum = Math.max(5, ...finite);
    return values.map((value, index) => {
      const x = 5 + index / Math.max(1, values.length - 1) * 190;
      const y = value == null ? 46 : 46 - value / maximum * 38;
      return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }
  async runSpeed(): Promise<void> {
    if (this.speedBusy || this.boosted || this.protectedGameActive || this.nexus.centerBusy || this.nexus.updateInProgress) return;
    this.speedBusy = true;
    this.nexus.centerBusy = true;
    this.speedTest = null;
    this.notice = 'Transferindo no máximo 30 MiB para medir download e upload. Não feche esta tela.';
    this.cdr.markForCheck();
    try {
      this.speedTest = await this.nexus.runSpeedTest();
      this.notice = 'Teste rápido concluído. Resultado aproximado para um único edge, sem alterar sua rede.';
    } catch (error) { this.notice = `Teste indisponível: ${String(error)}`; }
    finally { this.speedBusy = false; this.nexus.centerBusy = false; this.cdr.markForCheck(); }
  }
  compare(target?: string | null): string {
    const current = this.scan?.results.find(r => r.target === target);
    const previousScan = this.nexus.connectionScans[this.selectedScan + 1];
    const previous = previousScan?.results.find(r => r.target === target);
    if (current?.latency_ms == null || previous?.latency_ms == null || previousScan?.method !== this.scan?.method) return 'Sem comparação anterior';
    const delta = current.latency_ms - previous.latency_ms;
    return `${delta > 0 ? '+' : ''}${delta.toFixed(1)} ms vs. scan anterior (não prova ganho do BOOST)`;
  }
  exportReport(): void {
    const payload = { product: 'NexuFlow 2.1 beta', exported_at: new Date().toISOString(), scan: this.scan, dns: this.nexus.dnsRanking, speed_test: this.speedTest,
      monitoring: this.monitor, scope: 'Referências neutras; não mede a partida. Sem IP pessoal, caminhos ou identificadores de hardware. Relatório local não assinado.' };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = `NexuFlow-Conexao-${Date.now()}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async openSettings(section: string): Promise<void> {
    try { await this.nexus.openPcSettings(section); this.notice = 'Ajustes abertos no Windows. Mudanças feitas ali não pertencem ao rollback do BOOST.'; }
    catch (error) { this.notice = String(error); }
    this.cdr.markForCheck();
  }
  get pcCards(): Array<{title: string; status: string; description: string; attention: boolean}> {
    const online = !!this.telemetry?.engine_online;
    const memory = online ? this.health.memory?.['available_gb'] : null;
    const cpu = online ? this.telemetry?.cpu_percent : null;
    const temp = online ? this.telemetry?.gpu_temperature_c : null;
    const gameMode = online ? this.health.windows_gaming?.['game_mode']?.enabled : null;
    return [
      {title: 'Memória disponível', status: typeof memory === 'number' ? `${memory.toFixed(1)} GB livres` : 'Sem leitura', attention: typeof memory === 'number' && memory < 2,
        description: 'Pouca RAM pode causar paginação. O fluxo automático não encerra seus programas nem força limpeza de cache.'},
      {title: 'Carga da CPU', status: cpu == null ? 'Sem leitura' : `${cpu.toFixed(0)}% em uso`, attention: cpu != null && cpu >= 85,
        description: 'Uma amostra alta não identifica o culpado. O NexuFlow acompanha o contexto sem encerrar programas.'},
      {title: 'Temperatura da GPU', status: temp == null ? 'Sensor indisponível' : `${temp.toFixed(0)} °C`, attention: temp != null && temp >= 85,
        description: 'Permanece consultiva: uma curva automática genérica poderia causar risco de hardware.'},
      {title: 'Modo de Jogo', status: gameMode === true ? 'Ativado' : gameMode === false ? 'Desativado' : 'Preferência não informada', attention: gameMode === false,
        description: 'O Fluxo Vivo usa apenas o caminho seguro do BOOST; a preferência nativa continua visível e transparente.'},
      {title: 'Energia temporária', status: this.boosted ? 'Gerenciada pelo NexuFlow' : online ? String(this.health.power?.['name'] || 'Plano não informado') : 'Sem leitura', attention: false,
        description: 'Quando necessário, o BOOST clona um plano temporário e restaura o original ao desligar.'},
      {title: 'Capturas e armazenamento', status: 'Preservados', attention: false,
        description: 'O NexuFlow não desliga Game Bar nem apaga arquivos. Essas ações continuam fora da automação.'}
    ];
  }
}
