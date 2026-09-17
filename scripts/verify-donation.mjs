import { readFileSync } from 'node:fs';
import QRCode from 'qrcode';
import { donationPayload } from '../src/app/core/donation.ts';

const expected = await QRCode.toString(donationPayload(), {type:'svg',errorCorrectionLevel:'M',margin:4,width:280});
const actual = readFileSync(new URL('../public/donation-pix.svg',import.meta.url),'utf8');
if (actual.trim() !== expected.trim()) throw Error('QR Code differs from the Pix Copia e Cola payload.');
console.log('Donation QR exactly matches the local Pix payload; no fixed amount.');
