import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminCenterComponent } from './admin-center.component';
import { AccountService } from './core/account.service';
import { SubscriptionPlanId, SubscriptionService } from './core/subscription.service';

type AccountMode = 'login' | 'register';

@Component({
  selector: 'app-account-center',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminCenterComponent],
  templateUrl: './account-center.component.html',
  styleUrl: './account-center.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccountCenterComponent implements OnInit {
  @Input() avatar = 'theme-art/flux-mascot.png';
  mode: AccountMode = 'login';
  displayName = '';
  email = '';
  password = '';
  inviteEmail = '';
  acceptedTerms = false;
  selectedPlan: SubscriptionPlanId = 'month';
  deleteArmed = false;

  constructor(public readonly account: AccountService, public readonly subscription: SubscriptionService) {}

  ngOnInit(): void { void this.account.initialize(); }

  setMode(mode: AccountMode): void {
    this.mode = mode;
    this.password = '';
  }

  async submit(): Promise<void> {
    if (!this.account.configured || this.account.state === 'busy') return;
    try {
      if (this.mode === 'register') {
        if (!this.acceptedTerms) throw new Error('Aceite os termos e a política de privacidade para criar a conta.');
        await this.account.register(this.displayName, this.email, this.password, this.acceptedTerms);
      } else {
        await this.account.login(this.email, this.password);
      }
      this.password = '';
    } catch (error) {
      this.account.state = 'error';
      this.account.message = error instanceof Error ? error.message : 'Não foi possível continuar.';
    }
  }

  async resetPassword(): Promise<void> {
    try { await this.account.resetPassword(this.email); }
    catch (error) { this.account.state = 'error'; this.account.message = error instanceof Error ? error.message : 'Não foi possível redefinir a senha.'; }
  }

  async invite(): Promise<void> {
    try { await this.account.inviteDuo(this.inviteEmail); this.inviteEmail = ''; }
    catch (error) { this.account.state = 'error'; this.account.message = error instanceof Error ? error.message : 'Convite não enviado.'; }
  }

  async removeDuo(): Promise<void> { await this.account.removeDuo(); }

  choosePlan(plan: SubscriptionPlanId): void { this.selectedPlan = plan; }

  async checkout(): Promise<void> {
    try {
      const url = await this.account.requestCheckout(this.selectedPlan);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      this.account.state = 'error';
      this.account.message = error instanceof Error ? error.message : 'Checkout não iniciado.';
    }
  }

  async deleteAccount(): Promise<void> {
    if (!this.deleteArmed) { this.deleteArmed = true; return; }
    await this.account.requestAccountDeletion();
    this.deleteArmed = false;
  }

  async exportAccount(): Promise<void> {
    try {
      const data = await this.account.exportAccountData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
      const link = document.createElement('a');
      link.href = url; link.download = `NexuFlow-Meus-Dados-${Date.now()}.json`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      this.account.state = 'error';
      this.account.message = error instanceof Error ? error.message : 'Não foi possível exportar os dados.';
    }
  }
}
