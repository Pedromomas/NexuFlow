import { Injectable } from '@angular/core';

export type SubscriptionPlanId = 'day' | 'week' | 'month' | 'year';

export interface SubscriptionPlan {
  id: SubscriptionPlanId;
  label: string;
  priceBrl: number;
  durationLabel: string;
  highlight?: boolean;
}

@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  /**
   * Payments stay fail-closed until the HTTPS backend, Mercado Pago webhook
   * validation, privacy policy and account deletion route are deployed.
   */
  readonly configured = false;
  readonly plans: readonly SubscriptionPlan[] = [
    { id: 'day', label: 'Passe diário', priceBrl: 1, durationLabel: '1 dia' },
    { id: 'week', label: 'Passe semanal', priceBrl: 5, durationLabel: '7 dias' },
    { id: 'month', label: 'Plano mensal', priceBrl: 10, durationLabel: '30 dias', highlight: true },
    { id: 'year', label: 'Plano anual', priceBrl: 80, durationLabel: '1 ano' }
  ];
  readonly freeFeatures = ['Safe Core', 'Diagnóstico básico', 'Otimizações simples', 'Todos os temas', 'Mascote Flux'];
  readonly premiumFeatures = ['Latency Lab completo', 'Perfis automáticos de DNS por jogo', 'Recursos avançados futuros'];
  readonly duoPolicy = 'Titular + 1 amigo por convite de e-mail verificado, com conta separada, revogação e troca protegida por carência.';
}
