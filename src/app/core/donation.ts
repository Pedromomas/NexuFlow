export const DONATION_KEY = 'eba4282e-5305-4de8-ae77-220a07d831e7';
export const DONATION_NAME = 'Pedro Fernandes Bahia Rocha';
export const DONATION_CITY = 'Rio de Janeiro';

export function crc16(value: string): string {
  let crc = 0xffff;
  for (const byte of new TextEncoder().encode(value)) {
    crc ^= byte << 8;
    for (let bit = 0; bit < 8; bit++) crc = ((crc << 1) ^ ((crc & 0x8000) ? 0x1021 : 0)) & 0xffff;
  }
  return crc.toString(16).toUpperCase().padStart(4, '0');
}

function field(id: string, value: string): string {
  return id + new TextEncoder().encode(value).length.toString().padStart(2, '0') + value;
}

function emvText(value: string, limit: number): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().slice(0, limit);
}

// Static BR Code. No amount (54): the donor chooses in their banking app.
// Merchant Name is limited to 25 characters; the bank resolves the actual holder.
export function donationPayload(): string {
  const body = field('00', '01') + field('26', field('00', 'br.gov.bcb.pix') + field('01', DONATION_KEY))
    + field('52', '0000') + field('53', '986') + field('58', 'BR')
    + field('59', emvText(DONATION_NAME, 25)) + field('60', emvText(DONATION_CITY, 15))
    + field('62', field('05', '***')) + '6304';
  return body + crc16(body);
}
