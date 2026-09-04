import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { ConnectionScan, GamingHealth, Telemetry } from './core/models';
import { NexusService } from './core/nexus.service';

@Component({
  selector: 'app-performance-center', standalone: true, imports: [CommonModule],
  templateUrl: './performance-center.component.html', changeDetection: ChangeDetectionStrategy.OnPush
})
export class PerformanceCenterComponent {
  @Input() mode: 'connection' | 'pc' = 'connection';
  @Input() telemetry: Telemetry | null = null;
  @Input() health: GamingHealth = {};
  @Output() refresh = new EventEmitter<void>();
  @Output() preparePc = new EventEmitter<void>();
  notice = '';
  selectedScan = 0;
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
    if (this.nexus.centerBusy) return;
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
  compare(target?: string | null): string {
    const current = this.scan?.results.find(r => r.target === target);
    const previousScan = this.nexus.connectionScans[this.selectedScan + 1];
    const previous = previousScan?.results.find(r => r.target === target);
    if (current?.latency_ms == null || previous?.latency_ms == null || previousScan?.method !== this.scan?.method) return 'Sem comparação anterior';
    const delta = current.latency_ms - previous.latency_ms;
    return `${delta > 0 ? '+' : ''}${delta.toFixed(1)} ms vs. scan anterior (não prova ganho do BOOST)`;
  }
  exportReport(): void {
    const payload = { product: 'NexuFlow 1.7', exported_at: new Date().toISOString(), scan: this.scan, dns: this.nexus.dnsRanking,
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
  get pcCards(): Array<{title: string; status: string; description: string; action: string; section: string; attention: boolean}> {
    const online = !!this.telemetry?.engine_online;
    const memory = online ? this.health.memory?.['available_gb'] : null;
    const cpu = online ? this.telemetry?.cpu_percent : null;
    const temp = online ? this.telemetry?.gpu_temperature_c : null;
    const gameMode = online ? this.health.windows_gaming?.['game_mode']?.enabled : null;
    return [
      {title: 'Memória disponível', status: typeof memory === 'number' ? `${memory.toFixed(1)} GB livres` : 'Sem leitura', attention: typeof memory === 'number' && memory < 2,
        description: 'Pouca RAM pode causar paginação. Revise apps antes de jogar; não esvaziamos o cache nem forçamos limpeza de memória.', action: 'Revisar inicialização', section: 'startup'},
      {title: 'Carga da CPU', status: cpu == null ? 'Sem leitura' : `${cpu.toFixed(0)}% em uso`, attention: cpu != null && cpu >= 85,
        description: 'Uma amostra alta não identifica o culpado. Use o Investigador para contexto; nenhum programa será encerrado automaticamente.', action: 'Revisar apps', section: 'startup'},
      {title: 'Temperatura da GPU', status: temp == null ? 'Sensor indisponível' : `${temp.toFixed(0)} °C`, attention: temp != null && temp >= 85,
        description: 'Temperatura elevada merece atenção à ventilação e à carga. Não comprova throttling; sensores variam por fabricante.', action: 'Ajustes gráficos', section: 'graphics'},
      {title: 'Modo de Jogo', status: gameMode === true ? 'Ativado' : gameMode === false ? 'Desativado' : 'Preferência não informada', attention: gameMode === false,
        description: 'Revise a opção nativa do Windows. Ausência de valor salvo não significa desativado e ativar não garante mais FPS.', action: 'Abrir Modo de Jogo', section: 'game_mode'},
      {title: 'Gravações em segundo plano', status: 'Revisão manual', attention: false,
        description: 'Capturas podem consumir recursos. Confira se você precisa gravar; preservamos Game Bar, Xbox e seus serviços.', action: 'Revisar capturas', section: 'captures'},
      {title: 'Energia e armazenamento', status: online ? String(this.health.power?.['name'] || 'Plano não informado') : 'Sem leitura', attention: false,
        description: 'Mais potência pode aumentar calor e consumo. O BOOST usa seu fluxo reversível; ajustes manuais no Windows são independentes.', action: 'Revisar energia', section: 'power'}
    ];
  }
}
