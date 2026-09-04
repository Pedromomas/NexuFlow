import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AccountService } from './core/account.service';
import { SubscriptionPlanId, SubscriptionService } from './core/subscription.service';

type AccountMode = 'login' | 'register';

@Component({
  selector: 'app-account-center',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './account-center.component.html',
  styleUrl: './account-center.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccountCenterComponent implements OnInit {
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
        await this.account.register(this.displayName, this.email, this.password);
      } else {
        await this.account.login(this.email, this.password);
      }
      this.password = '';
    } catch (error) {
      this.account.state = 'error';
      this.account.message = error instanceof Error ? error.message : 'Não foi possível continuar.';
    }
  }

  async invite(): Promise<void> {
    try { await this.account.inviteDuo(this.inviteEmail); this.inviteEmail = ''; }
    catch (error) { this.account.state = 'error'; this.account.message = error instanceof Error ? error.message : 'Convite não enviado.'; }
  }

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
}
