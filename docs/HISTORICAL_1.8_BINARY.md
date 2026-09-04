# NexuFlow 1.8.0 - arquivo binario historico

Este marco preserva o instalador real que foi gerado localmente em 04/09/2026.
Ele nao representa um snapshot exato do codigo-fonte da 1.8: esse pacote-fonte
separado nao foi preservado. Por isso o identificador Git e
`v1.8.0-binary-archive`, e nao um tag de fonte `v1.8.0`.

## Artefato preservado

- arquivo: `NexuFlow-1.8.0-Setup-x64.exe`
- tamanho: 28.376.105 bytes
- SHA-256: `AF4A2428A5672C2D7FF05E2CA4385F707CEFDF0EA597DBF482369F2697911947`

As copias em `Downloads` e `outputs` possuem o mesmo hash.

## Limites importantes

- o instalador antecede a chave definitiva do atualizador criada para a 2.1;
- ele nao deve ser servido como atualizacao automatica para usuarios;
- ele pode exibir `Fornecedor desconhecido`, pois nao possui a futura assinatura
  Authenticode comercial;
- seu objetivo no GitHub e preservar a linha do tempo e permitir verificacao do
  binario historico, sem atribuir a ele uma fonte que nao pode ser comprovada.

As notas funcionais contemporaneas permanecem no ramo principal em
`docs/RELEASE_1.8.md`.
