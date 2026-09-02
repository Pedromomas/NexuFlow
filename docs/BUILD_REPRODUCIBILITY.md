# Build verificável — 1.6

## Garantido agora

O pacote-fonte reprodutível usa ordem de arquivos e timestamps normalizados. Com a mesma árvore de arquivos, o SHA-256 do ZIP-fonte deve ser idêntico. Dependências ficam registradas no lockfile e no SBOM. A proveniência grava versões das ferramentas e hashes dos artefatos.

## Ainda não prometido

O instalador NSIS/PE completo ainda não é declarado bit a bit reprodutível. Tauri, Rust, PyInstaller, NSIS e assinatura Authenticode podem inserir timestamp, caminho ou metadado do ambiente. O `release-check.ps1` verifica conteúdo, testes, No-Driver Contract, SBOM, manifesto e assinatura; ele não mascara essa limitação.

## Verificação

1. Execute `scripts/release-check.ps1` no Windows com as versões registradas em `build/toolchain.lock.json`.
2. Compare o hash do pacote-fonte determinístico.
3. Execute `scripts/verify-release.ps1` sobre o pacote final.
4. Confira o estado Authenticode do instalador antes de publicação.
