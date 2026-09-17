import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { DonationComponent } from './donation.component';
import { crc16, donationPayload, DONATION_KEY } from './core/donation';

function fields(payload: string): Record<string, string> {
  const result: Record<string,string> = {};
  for (let i = 0; i < payload.length;) {
    const id = payload.slice(i, i + 2), length = Number(payload.slice(i + 2, i + 4));
    if (!Number.isFinite(length) || length < 1 || i + 4 + length > payload.length) throw Error('Invalid TLV');
    result[id] = payload.slice(i + 4, i + 4 + length); i += 4 + length;
  }
  return result;
}

describe('voluntary community donations', () => {
  afterEach(() => vi.restoreAllMocks());
  it('creates a Pix payload with correct fields and no fixed amount', () => {
    const payload = donationPayload(), tlv = fields(payload);
    expect(crc16('123456789')).toBe('29B1');
    expect(tlv['63']).toBe(crc16(payload.slice(0, -4)));
    expect(fields(tlv['26'])['01']).toBe(DONATION_KEY);
    expect(fields(tlv['26'])['00']).toBe('br.gov.bcb.pix');
    expect(tlv['53']).toBe('986'); expect(tlv['58']).toBe('BR');
    expect(tlv['59']).toBe('PEDRO FERNANDES BAHIA ROC');
    expect(tlv['59'].length).toBe(25);
    expect(tlv['60']).toBe('RIO DE JANEIRO');
    expect(tlv['54']).toBeUndefined();
    expect(fields(tlv['62'])['05']).toBe('***');
  });
  it('explains that all functions remain free and displays the local QR', async () => {
    await TestBed.configureTestingModule({imports:[DonationComponent]}).compileComponents();
    const fixture = TestBed.createComponent(DonationComponent); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('100% gratuito, com ou sem doação.');
    expect(fixture.nativeElement.querySelector('img').getAttribute('src')).toBe('donation-pix.svg');
    expect(fixture.nativeElement.querySelector('input').value).toBe(DONATION_KEY);
    fixture.destroy();
  });
  it('reports a clipboard failure without claiming that a payment happened', async () => {
    await TestBed.configureTestingModule({imports:[DonationComponent]}).compileComponents();
    const fixture = TestBed.createComponent(DonationComponent);
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:vi.fn().mockRejectedValue(new Error('denied'))}});
    await fixture.componentInstance.copy(DONATION_KEY,'Copiado'); fixture.detectChanges();
    expect(fixture.componentInstance.message).toContain('Não foi possível copiar');
    fixture.destroy();
  });
});
