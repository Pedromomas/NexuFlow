import { beforeEach, describe, expect, it } from 'vitest';
import { ProfileCollectionComponent } from './profile-collection.component';
describe('Local cosmetic passport', () => {
  beforeEach(() => localStorage.clear());
  it('normalizes and persists a bounded nickname without account data', () => {
    const profile = new ProfileCollectionComponent();
    profile.name = '   Kiwi   '; profile.saveName();
    expect(new ProfileCollectionComponent().name).toBe('Kiwi');
    profile.name = 'x'.repeat(100); profile.saveName(); expect(profile.name.length).toBe(32);
  });
  it('cannot equip a locked reward', () => {
    const profile = new ProfileCollectionComponent();
    const reward = { id: 'kiwi', title: 'Kiwi', theme: 'secret-kiwi', artwork: '', avatar: '', badge: '', unlocked: false };
    profile.rewards = [reward]; let emitted = '';
    profile.equip.subscribe(value => emitted = value);
    profile.equipReward(reward); expect(emitted).toBe(''); expect(profile.collected).toBe(0);
    reward.unlocked = true; profile.equipReward(reward);
    expect(emitted).toBe('secret-kiwi'); expect(profile.collected).toBe(1);
  });
});
