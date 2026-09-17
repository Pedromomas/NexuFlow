import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AccountService } from './core/account.service';
import { SubscriptionPlanId } from './core/subscription.service';

@Component({
  selector: 'app-admin-center', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <section class="admin" *ngIf="account.authenticated && account.profile?.isAdmin">
      <header><span class="eyebrow">NEXUFLOW · ACESSO RESTRITO</span><h2>Central do administrador</h2></header>
      <p>Gerencie acessos individuais. Para alterações, entre na conta novamente se o servidor solicitar.</p>
      <nav aria-label="Áreas da administração">
        <button type="button" [attr.aria-pressed]="area() === 'codes'" (click)="area.set('codes')">Códigos de acesso</button>
        <button type="button" [attr.aria-pressed]="area() === 'users'" (click)="area.set('users')">Usuários</button>
        <button type="button" [attr.aria-pressed]="area() === 'payments'" (click)="area.set('payments')">Pagamentos · teste</button>
      </nav>
      <section [hidden]="area() !== 'users'" class="panel">
      <h3>Encontre uma conta</h3>
      <form (ngSubmit)="search()">
        <label>E-mail completo do usuário<input name="searchEmail" [(ngModel)]="email" type="email" required maxlength="254"></label>
        <button [disabled]="busy()" type="submit">Pesquisar usuário</button>
      </form>
      <div *ngFor="let user of users()" class="result">
        <strong>{{user.displayName || 'Sem nome'}} · {{user.email}}</strong>
        <p>{{user.emailVerified ? 'E-mail confirmado' : 'E-mail pendente'}} · Plano: {{user.plan}}</p>
        <p *ngIf="user.codeAccessEndsAt">Acesso por código até {{user.codeAccessEndsAt | date:'short'}}</p>
      </div>
      </section>
      <section [hidden]="area() !== 'payments'" class="panel">
      <span class="eyebrow">AMBIENTE DE TESTES</span><h3>PagBank — simulação</h3>
      <p>Somente dados de teste do provedor. Nenhum pagamento simulado libera assinatura real.</p>
      <label>Passe de teste<select [(ngModel)]="testPlan"><option value="day">1 dia</option><option value="week">7 dias</option><option value="month">30 dias</option><option value="year">365 dias</option></select></label>
      <button type="button" [disabled]="busy()" (click)="prepareCheckout()">Preparar checkout de teste</button>
      <p *ngIf="testCheckout()"><a [href]="testCheckout()" target="_blank" rel="noopener noreferrer">Abrir simulação no PagBank</a></p>
      </section>
      <section [hidden]="area() !== 'codes'" class="panel">
      <span class="eyebrow">UM CÓDIGO · UMA ATIVAÇÃO</span><h3>Crie um acesso especial</h3>
      <form (ngSubmit)="create()">
        <label>Tema<select name="theme" [(ngModel)]="theme"><option value="">Nenhum</option><option value="origin">Origem</option><option value="rio">Rio Pulse</option><option value="kiwi">Kiwi</option></select></label>
        <label>Acesso avançado<select name="kind" [(ngModel)]="kind"><option value="none">Só o tema</option><option value="timed">Por tempo limitado</option><option value="lifetime">Vitalício</option></select></label>
        <label *ngIf="kind === 'timed'">Dias a partir do resgate<input name="days" [(ngModel)]="days" type="number" min="1" max="365" required></label>
        <label>Prazo para resgatar (opcional)<input name="deadline" [(ngModel)]="deadline" type="datetime-local"></label>
        <p>Uso único. Um código libera no máximo um tema. O prazo do benefício começa quando a pessoa resgata.</p>
        <button type="submit" [disabled]="busy() || (kind === 'none' && !theme)">{{busy() ? 'Aguarde…' : 'Criar código'}}</button>
      </form>
      <div *ngIf="createdCode()" class="result"><label>Código criado — guarde antes de sair<input readonly [value]="createdCode()" aria-label="Código criado"></label><button type="button" (click)="createdCode.set('')">Ocultar código</button></div>
      <details><summary>Cancelar um código não resgatado</summary>
      <p>O histórico é preservado. Códigos já usados não podem ser cancelados por esta ação.</p>
      <form (ngSubmit)="revoke()">
        <label>Código<input name="revokeCode" [(ngModel)]="revokeCode" (ngModelChange)="revokeArmed = false" autocomplete="off" maxlength="128" required></label>
        <button type="submit" [disabled]="busy() || !revokeCode.trim()">{{revokeArmed ? 'Confirmar cancelamento' : 'Cancelar este código'}}</button>
      </form>
      </details></section>
      <p class="feedback" role="status" aria-live="polite" [hidden]="!message()">{{message()}}</p>
    </section>`,
  styles: [`
    .admin { margin: 24px 0; padding: 24px; border: 1px solid var(--border, #626779); border-radius: 18px; background: var(--card-bg, #181c27); color: var(--text-primary, #f5f5fa); }
    form { display: flex; flex-wrap: wrap; align-items: end; gap: 16px; margin: 20px 0; }
    label { display: grid; gap: 8px; flex: 1 1 220px; } input, select, button { font: inherit; border-radius: 8px; padding: 12px; border: 1px solid #72788a; background: #222838; color: #fff; min-width: 0; }
    button { cursor: pointer; } button:disabled { opacity: .5; cursor: wait; } :focus-visible { outline: 3px solid #a6caff; outline-offset: 3px; }
    form p { flex-basis: 100%; } .result { padding: 16px; border: 1px solid #72788a; border-radius: 10px; margin: 12px 0; overflow-wrap: anywhere; }
    :host { display:block; } [hidden] { display:none !important; }
    .admin { background:var(--bg,#0b0d14); border-color:var(--line,#343949); color:var(--text,#f5f7ff); padding:clamp(18px,3vw,32px); }
    .eyebrow { color:var(--accent,#aa94ff); font-size:11px; font-weight:800; letter-spacing:.16em; }
    h2 { font-size:clamp(22px,3vw,30px); margin:10px 0; letter-spacing:-.035em; } h3 { margin:10px 0 16px; font-size:20px; }
    p { line-height:1.65; font-size:14px; } nav { display:flex; gap:8px; flex-wrap:wrap; margin:24px 0; }
    nav button { background:transparent; } nav button[aria-pressed=true] { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 14%,transparent); }
    .panel { padding:clamp(16px,2vw,24px); border:1px solid var(--line,#343949); border-radius:16px; background:rgba(255,255,255,.025); }
    input,select { width:100%; background:var(--bg,#10131d); border-color:var(--line,#454c60); color:var(--text,#fff); min-height:46px; }
    button { min-height:44px; background:color-mix(in srgb,var(--accent,#7857ff) 18%,var(--bg,#10131d)); border-color:var(--line,#454c60); transition:background .15s ease,border-color .15s ease; }
    button:hover:not(:disabled) { border-color:var(--accent); } :focus-visible { outline-color:var(--accent,#aa94ff); }
    details { border-top:1px solid var(--line,#343949); margin-top:24px; padding-top:20px; } summary { cursor:pointer; padding:8px 0; font-weight:600; }
    .feedback { border-left:3px solid var(--accent); padding:12px 16px; background:rgba(255,255,255,.04); border-radius:8px; overflow-wrap:anywhere; }
    @media(max-width:600px) { form { flex-direction:column; align-items:stretch; } label { flex:auto; } nav button { flex:1 1 140px; } }
    @media(prefers-reduced-motion:reduce) { button { transition:none; } }
  `]
})
export class AdminCenterComponent {
  area = signal<'codes' | 'users' | 'payments'>('codes');
  email = ''; theme = ''; kind = 'timed'; days = 7; deadline = '';
  busy = signal(false); message = signal(''); createdCode = signal('');
  users = signal<Array<{id: string; email: string; displayName: string; emailVerified: boolean; plan: string; codeAccessEndsAt?: string}>>([]);
  readonly account = inject(AccountService);
  revokeCode = ''; revokeArmed = false;

  async revoke(): Promise<void> {
    if (this.busy()) return;
    if (!this.revokeArmed) { this.revokeArmed = true; this.message.set('Confirme para impedir o resgate deste código.'); return; }
    this.busy.set(true);
    try { await this.account.adminRevokeCode(this.revokeCode); this.revokeCode = ''; this.message.set('Código cancelado. Histórico preservado.'); }
    catch (error) { this.fail(error); }
    finally { this.revokeArmed = false; this.busy.set(false); }
  }
  testPlan: SubscriptionPlanId = 'week';
  testCheckout = signal('');

  async prepareCheckout(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true); this.testCheckout.set('');
    try { this.testCheckout.set(await this.account.requestSandboxCheckout(this.testPlan)); this.message.set('Simulação preparada. Use apenas dados de teste.'); }
    catch (error) { this.fail(error); }
    finally { this.busy.set(false); }
  }

  async search(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true); this.users.set([]); this.message.set('Pesquisando…');
    try {
      const result = await this.account.adminSearch(this.email);
      this.users.set(result.users); this.message.set(result.users.length ? 'Usuário encontrado.' : 'Nenhum usuário encontrado.');
    } catch (error) { this.fail(error); } finally { this.busy.set(false); }
  }

  async create(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true); this.createdCode.set(''); this.message.set('Criando…');
    try {
      const result = await this.account.adminCreateCode({ theme: this.theme || null,
        days: this.kind === 'timed' ? this.days : null, lifetime: this.kind === 'lifetime',
        redeemBefore: this.deadline ? new Date(this.deadline).toISOString() : null });
      this.createdCode.set(result.code); this.message.set('Código criado. Ele não será exibido novamente após sair desta tela.');
    } catch (error) { this.fail(error); } finally { this.busy.set(false); }
  }

  private fail(error: unknown): void { this.message.set(error instanceof Error ? error.message : 'Não foi possível concluir.'); }
}
