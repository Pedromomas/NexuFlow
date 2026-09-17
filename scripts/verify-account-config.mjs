import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const runtime = JSON.parse(readFileSync(resolve(root, 'public/nexuflow-runtime-config.json'), 'utf8'));
const buildMode = readFileSync(resolve(root, 'src/app/core/build-mode.ts'), 'utf8');
if (/export const COMMUNITY_EDITION = true;/.test(buildMode)) {
  if (runtime.edition !== 'community' || runtime.accountApiBase || runtime.licensePublicKey) {
    throw new Error('Community builds must not configure account servers or paid licenses.');
  }
  if (process.argv.includes('--require-accounts')) {
    throw new Error('NexuFlow Community has no account or payment requirement.');
  }
}
if (process.argv.includes('--require-accounts') && runtime.loginOnly === true) {
  throw new Error('Final account release refused: loginOnly test mode is still enabled.');
}
if (runtime.accountApiBase && runtime.loginOnly !== true &&
    (!/^[A-Za-z0-9._-]{1,80}$/.test(runtime.legalVersion || '') || /draft/i.test(runtime.legalVersion))) {
  throw new Error('Registration requires an explicitly published legal document version.');
}
const tauri = JSON.parse(readFileSync(resolve(root, 'src-tauri/tauri.conf.json'), 'utf8'));
const allowed = new Set(tauri.app.security.csp['connect-src'].split(/\s+/));
if (allowed.has('*') || allowed.has('https:') || allowed.has('http:')) {
  throw new Error('Account configuration rejected: network CSP must use explicit origins.');
}
if (runtime.accountApiBase) {
  const endpoint = new URL(runtime.accountApiBase);
  if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || endpoint.search || endpoint.hash || endpoint.pathname !== '/') {
    throw new Error('Account API must be an HTTPS origin without credentials, path or query.');
  }
  if (!allowed.has(endpoint.origin)) throw new Error('Account API is blocked by desktop CSP.');
  for (const key of runtime.loginOnly === true ? [] : ['privacyPolicyUrl', 'termsUrl']) {
    const url = new URL(runtime[key]);
    if (url.protocol !== 'https:' || url.username || url.password) throw new Error(`${key} must be a public HTTPS URL.`);
  }
  if (!/^[A-Za-z0-9+/]{43}=$/.test(runtime.licensePublicKey || '')) {
    throw new Error('A 32-byte license public key is required for account-enabled builds.');
  }
  console.log(runtime.loginOnly === true ? 'Existing-account login test build. Registration and live payments remain disabled.' : 'Account configuration and desktop CSP are consistent; live integration still requires testing.');
} else {
  if (process.argv.includes('--require-accounts')) throw new Error('Account-enabled release refused: accountApiBase is empty.');
  console.log('Community build: all implemented features are free; no account, payment or license server.');
}
