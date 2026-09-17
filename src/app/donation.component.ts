import { Component, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { DONATION_KEY, DONATION_NAME, donationPayload } from './core/donation';

@Component({
  selector: 'app-donation', standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article class="support-card">
      <div class="support-copy">
        <span class="eyebrow">FEITO COM A COMUNIDADE</span>
        <h2>O NexuFlow te deu uma força?</h2>
        <p>Se o aplicativo te ajudou e você puder retribuir, até R$ 1 já é uma força para continuar o projeto. Se não puder, tudo bem: aproveite, compartilhe e ajude contando o que podemos melhorar.</p>
        <strong>100% gratuito, com ou sem doação.</strong>
        <p class="support-note">Apoio voluntário, de qualquer valor, sem assinatura, recompensa ou desbloqueio de funções. O pagamento só acontece se você confirmar no seu banco.</p>
        <label for="donation-key">Chave Pix aleatória</label>
        <input id="donation-key" readonly [value]="key" spellcheck="false" aria-label="Chave Pix para copiar manualmente">
        <div class="support-actions">
          <button type="button" (click)="copy(key, 'Chave Pix copiada.')">Copiar chave Pix</button>
          <button type="button" (click)="copy(payload, 'Pix Copia e Cola copiado.')">Copiar Pix Copia e Cola</button>
        </div>
        <p class="support-status" role="status" aria-live="polite">{{ message }}</p>
      </div>
      <figure>
        <img src="donation-pix.svg" width="280" height="280" alt="QR Code Pix de apoio voluntário ao NexuFlow, sem valor definido">
        <figcaption>Leia com o aplicativo do seu banco.<br><b>{{ name }}</b></figcaption>
        <p class="support-note">Confira o destinatário e o valor antes de confirmar. O NexuFlow não consulta seu banco nem confirma recebimentos.</p>
      </figure>
    </article>`,
  styles: [`
    :host{display:block}.support-card{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:36px;padding:32px;border:1px solid var(--border, #3d475c);border-radius:24px;background:var(--panel, #131925);color:var(--text, #f0f3fa)}
    h2{font-size:clamp(24px,3vw,34px);line-height:1.15;margin:14px 0 18px}p{line-height:1.7}.eyebrow{font-size:12px;letter-spacing:.14em;font-weight:800}strong{display:block;margin:22px 0 12px}.support-note{font-size:13px;opacity:.85}label{display:block;margin:24px 0 8px;font-size:13px}input{box-sizing:border-box;width:100%;min-width:0;padding:14px;border:1px solid #64748b;border-radius:10px;background:#0d1422;color:#f3f6ff;font:13px monospace}.support-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}button{min-height:44px;padding:12px 18px;background:#dce8ff;color:#101a30;border:1px solid transparent;border-radius:12px;font:inherit;font-weight:700;cursor:pointer}button:hover{background:#fff}button:focus-visible,input:focus-visible{outline:3px solid #8fb7ff;outline-offset:3px}figure{margin:0;text-align:center}img{display:block;width:100%;max-width:280px;height:auto;margin:0 auto 16px;background:#fff;border:10px solid #fff;border-radius:12px;box-sizing:border-box}figcaption{font-size:13px;line-height:1.7}.support-status{min-height:24px;font-size:13px;margin-bottom:0}@media(max-width:760px){.support-card{grid-template-columns:1fr;padding:22px;gap:20px}figure{max-width:320px;margin:auto}}
  `]
})
export class DonationComponent {
  readonly key = DONATION_KEY;
  readonly name = DONATION_NAME;
  readonly payload = donationPayload();
  message = '';
  constructor(private readonly cdr: ChangeDetectorRef) {}
  async copy(value: string, success: string): Promise<void> {
    try { await navigator.clipboard.writeText(value); this.message = success; }
    catch { this.message = 'Não foi possível copiar. Selecione a chave acima ou leia o QR Code no seu banco.'; }
    this.cdr.markForCheck();
  }
}
