import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface CollectibleReward {
  id: string; title: string; theme: string; artwork: string;
  avatar: string; badge: string; unlocked: boolean;
}

@Component({
  selector: 'app-profile-collection', standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile-collection.component.html',
  styleUrl: './profile-collection.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ProfileCollectionComponent {
  @Input() rewards: readonly CollectibleReward[] = [];
  @Input() activeTheme = '';
  @Input() avatar = 'theme-art/flux-mascot.png';
  @Output() equip = new EventEmitter<string>();
  @Output() redeem = new EventEmitter<void>();
  name = this.loadName();
  editing = false;
  saved = '';
  get collected(): number { return this.rewards.filter(reward => reward.unlocked).length; }
  get active(): CollectibleReward | undefined { return this.rewards.find(r => r.theme === this.activeTheme && r.unlocked); }
  private loadName(): string {
    try { return (localStorage.getItem('nexuflow_collector_name_v1') || 'Explorador do fluxo').slice(0, 32); }
    catch { return 'Explorador do fluxo'; }
  }
  saveName(): void {
    this.name = this.name.trim().slice(0, 32) || 'Explorador do fluxo';
    try { localStorage.setItem('nexuflow_collector_name_v1', this.name); this.saved = 'Apelido salvo neste computador.'; }
    catch { this.saved = 'Armazenamento indisponível. Apelido vale só nesta sessão.'; }
    this.editing = false;
  }
  equipReward(reward: CollectibleReward): void { if (reward.unlocked) this.equip.emit(reward.theme); }
}
