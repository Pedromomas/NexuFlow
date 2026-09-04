# Atualizador assinado - ativacao da 1.8

O plugin oficial `tauri-plugin-updater` esta integrado, com permissao explicita, barra in-app e Central de Atualizacoes nos Ajustes. O frontend consulta o binario para saber se a feature `signed-updater` foi compilada; sem ela, permanece fail-closed e explica a pendencia sem derrubar o aplicativo.

Para ativar na release publica:

1. gerar um par exclusivo com `npm run tauri signer generate -- --write-keys "C:\Users\SEU_USUARIO\Documents\NexuFlow-Secrets\nexuflow-updater.key"`; nunca reutilizar Authenticode;
2. digitar a senha somente no terminal local e guardar a chave privada cifrada em dois cofres independentes, nunca no repositorio ou em `.env`;
3. manter somente a chave publica definitiva em `tauri.conf.json` e `src-tauri/tauri.updater.release.conf.json`; a chave privada nunca entra no projeto;
4. usar o endpoint oficial `https://github.com/Pedromomas/NexuFlow/releases/latest/download/latest.json`;
5. executar `scripts/build-signed-updater.ps1 -ConfigPath src-tauri/tauri.updater.release.conf.json`; o script recusa placeholders, endpoint que nao seja GitHub HTTPS, ausencia de artefatos e segredos ausentes;
6. configurar `TAURI_SIGNING_PRIVATE_KEY` e `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` apenas no cofre do GitHub Actions;
7. publicar `latest.json`, instalador e `.sig` no GitHub Release e testar upgrade de uma versao anterior.

O NexuFlow nunca deve aceitar atualizacao sem assinatura. Se a chave privada for perdida, clientes existentes nao poderao confiar em uma nova chave automaticamente.

## O que cada assinatura resolve

- A chave Ed25519 do Tauri prova que um pacote de atualização foi publicado pelo NexuFlow. A chave pública pode ficar no aplicativo; a privada e sua senha nunca podem ser enviadas por chat ou commitadas.
- O certificado Authenticode comercial identifica o fornecedor no aviso do Windows e melhora a reputação do executável. Ele é separado da chave do updater.
- Nenhuma das duas assinaturas deve ser usada para desligar ou contornar o UAC. Alterações administrativas continuam exigindo consentimento do Windows.

## Teste obrigatório entre duas versões

1. instalar a versão N;
2. publicar N+1, manifesto e assinatura válidos e confirmar atualização pela barra in-app;
3. adulterar uma cópia do instalador ou da assinatura e confirmar que ela é recusada;
4. repetir com BOOST desligado e com uma sessão protegida simulada/real, confirmando que a checagem fica adiada;
5. guardar logs e hashes do teste como evidência da release.

O workflow `.github/workflows/release-signed.yml` já prepara testes, sidecar, draft da release, artefatos, assinaturas e `latest.json`. Ele recusa executar a publicação se os dois segredos de assinatura não estiverem no ambiente protegido `signed-release` do GitHub.

No Windows, também é possível dar dois cliques em `CRIAR_CHAVE_ATUALIZADOR.cmd`. A janela fica aberta para mostrar erros ou sucesso e o script não sobrescreve uma chave existente.

Sem essa feature, o plugin nao e inicializado. Isso evita que uma configuracao ausente derrube o aplicativo antes de a janela abrir e mantem a atualizacao bloqueada por padrao. O botao continua visivel para o usuario entender o estado, mas nao finge que existe um canal publicado.
