# Manifesto de Confiança NexuFlow

O NexuFlow existe para melhorar a experiência de jogo usando recursos documentados do Windows. Confiança não deve depender de promessa: cada versão deve trazer código, inventário de componentes, hashes e registros locais suficientes para inspeção independente.

## O que o NexuFlow nunca faz

- Não injeta DLL, não lê nem escreve memória de jogos e não cria overlays dentro do processo.
- Não instala driver próprio, filtro de pacotes, hook de kernel ou certificado raiz.
- Não desliga Vanguard, VAC, EAC, BattlEye, Secure Boot, TPM, VBS/HVCI ou proteções do Windows.
- Não executa comandos recebidos por feed remoto. A política assinada só pode desativar recursos.
- Não envia analytics, publicidade, lista de programas, hardware ID, token, PID ou caminhos pessoais.
- Não promete reduzir um ping que depende do provedor, da rota externa ou do servidor do jogo.

## O que pode ser verificado

- `MANIFEST.sha256` confirma cada arquivo do pacote.
- `SBOM.cdx.json` lista as dependências.
- `NETWORK_ALLOWLIST.md` descreve os únicos destinos aceitos.
- O Modo Investigador mostra as operações iniciadas pelo NexuFlow.
- O relatório de sessão usa Ed25519 para detectar alteração após a exportação.
- `scripts/verify-session-report.ps1` confere a assinatura sem depender da interface.
- `release-check.ps1` executa testes, auditorias e empacotamento.

## Limite honesto da assinatura local

A assinatura do relatório prova que o conteúdo não mudou e que saiu da mesma instalação. Ela não substitui uma assinatura comercial do fornecedor. O instalador oficial deverá usar Authenticode antes de distribuição pública.

Este manifesto está preparado localmente para a versão 1.6. Ele não foi publicado automaticamente.
