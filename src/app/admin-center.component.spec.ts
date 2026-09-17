import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { AccountService } from './core/account.service';
import { AdminCenterComponent } from './admin-center.component';

function setup(admin: boolean) {
  const account = {authenticated: true, profile: {isAdmin: admin},
    adminSearch: vi.fn().mockResolvedValue({users: []}),
    adminCreateCode: vi.fn().mockResolvedValue({id: 'hash', code: 'NEXU-TEST'})};
  TestBed.configureTestingModule({imports: [AdminCenterComponent], providers: [{provide: AccountService, useValue: account}]});
  const fixture = TestBed.createComponent(AdminCenterComponent);
  fixture.detectChanges();
  return {fixture, account};
}

describe('AdminCenterComponent', () => {
  it('does not display administration to ordinary accounts', () => {
    const {fixture, account} = setup(false);
    expect(fixture.nativeElement.querySelector('form')).toBeNull();
    expect(account.adminSearch).not.toHaveBeenCalled();
  });
  it('creates a seven-day code without duplicate requests', async () => {
    const {fixture, account} = setup(true);
    const instance = fixture.componentInstance;
    const first = instance.create();
    await instance.create();
    await first;
    fixture.detectChanges();
    expect(account.adminCreateCode).toHaveBeenCalledTimes(1);
    expect(account.adminCreateCode).toHaveBeenCalledWith({theme: null, days: 7, lifetime: false, redeemBefore: null});
    expect(fixture.nativeElement.querySelector('[aria-label="Código criado"]').value).toBe('NEXU-TEST');
  });
  it('shows permission errors instead of claiming success', async () => {
    const {fixture, account} = setup(true);
    account.adminCreateCode.mockRejectedValue(new Error('Permissão administrativa removida.'));
    await fixture.componentInstance.create();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Permissão administrativa removida.');
    expect(fixture.componentInstance.createdCode()).toBe('');
  });
});
