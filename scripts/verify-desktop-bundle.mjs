import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputRoot = resolve(projectRoot, 'dist', 'nexuflow', 'browser');
const indexPath = resolve(outputRoot, 'index.html');

if (!existsSync(indexPath)) {
  throw new Error(`Desktop bundle ausente: ${indexPath}`);
}

const html = readFileSync(indexPath, 'utf8');

// Angular's critical-CSS optimizer can emit a print-only stylesheet that is
// activated by an inline onload handler. Tauri's CSP correctly blocks that
// handler, leaving the installed application practically unstyled.
if (/<link\b[^>]*rel=["']stylesheet["'][^>]*media=["']print["'][^>]*onload=/i.test(html)) {
  throw new Error('Bundle recusado: a folha de estilos depende de onload inline bloqueado pela CSP do Tauri.');
}

const assetReferences = [...html.matchAll(/(?:src|href)=["']([^"']+\.(?:css|js))["']/gi)]
  .map(match => match[1]);

if (!assetReferences.length) {
  throw new Error('Bundle recusado: index.html nao referencia CSS ou JavaScript.');
}

for (const reference of assetReferences) {
  if (/^(?:[a-z]+:|\/\/|\/)/i.test(reference)) {
    throw new Error(`Bundle recusado: caminho absoluto nao permitido no desktop: ${reference}`);
  }
  const cleanReference = reference.split(/[?#]/, 1)[0];
  const assetPath = resolve(outputRoot, cleanReference);
  if (!existsSync(assetPath)) {
    throw new Error(`Bundle recusado: arquivo referenciado nao existe: ${reference}`);
  }
}

console.log(`Desktop bundle verificado: ${assetReferences.length} arquivos locais e CSS compativel com a CSP.`);
