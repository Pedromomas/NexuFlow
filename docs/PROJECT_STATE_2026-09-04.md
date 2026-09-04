# Estado consolidado do projeto NexuFlow

Data de corte: 04/09/2026  
Versao em desenvolvimento: 1.8.0 - Fluxo Vivo  
Ultima versao fechada e documentada: 1.7.0 - Insight Edition  
Plataforma: Windows 10/11 x64

## 1. Resumo executivo

O NexuFlow e um aplicativo desktop local para diagnosticar qualidade de internet e saude do PC e aplicar somente ajustes conservadores e reversiveis durante jogos. O produto nao e um relay global como ExitLag/NoPing e nao promete diminuir ping ou aumentar FPS em todos os computadores.

A versao 1.7 esta funcionalmente documentada e possui instalador/pacote local previamente gerado. A versao 1.8 ja tem uma primeira etapa implementada no codigo: resposta imediata do BOOST, nova Central do PC automatica, comparacao DNS ao vivo, speed test limitado, animacoes leves e fundacao do atualizador assinado. A 1.8 ainda nao esta pronta para distribuicao final.

O ponto mais importante do repositorio e que o `HEAD` do Git continua no commit `a2baa36` (`v1.6.0`). O fechamento da 1.7 e o inicio da 1.8 estao presentes como alteracoes locais ainda nao consolidadas em commit. Antes de publicar, deve existir um checkpoint versionado e revisado.

## 2. Fontes usadas para esta consolidacao

- historico disponivel desta tarefa/conversa;
- PDF `NexuFlow-1.7.0-Documentacao-Completa.pdf`, com seis paginas;
- codigo e documentos atuais do repositorio;
- `docs/RELEASE_1.7.md`, `docs/RELEASE_1.8.md` e `docs/UPDATER_1.8.md`;
- politicas de arquitetura, seguranca, anti-cheat, desempenho e allowlist de rede.

## 3. Principios do produto ja definidos

1. **Local-first:** configuracoes, historico, relatorios e desbloqueio cosmetico ficam no computador.
2. **Seguranca primeiro:** jogos protegidos forcam um perfil mais restrito no backend.
3. **Medir antes de concluir:** ausencia de leitura nao vira `0 ms`, `0%` ou um diagnostico inventado.
4. **Rollback:** toda mutacao persistente permitida precisa de snapshot e restauracao.
5. **Transparencia:** a interface deve diferenciar medicao, recomendacao, simulacao e validacao real.
6. **Sem promessa magica:** o aplicativo nao garante reducao de ping, aumento de FPS ou risco zero de banimento.
7. **Automacao somente quando segura:** se uma acao generica nao puder ser automatizada com seguranca, ela permanece consultiva ou fica fora do fluxo automatico.

## 4. Arquitetura atual

```text
Angular 22 + Ionic 9 (WebView sem administrador)
                 |
                 | comandos Tauri explicitamente permitidos
                 v
Tauri 2 / Rust (IPC, allowlist, cache e host desktop)
          |                         |
          | sidecar                 +--> observer Python sem privilegio
          v
Helper Python (validacao sem privilegio)
          |
          | UAC somente quando uma mutacao estreita exige
          v
Daemon Python administrador
          |
          +--> plano de energia temporario
          +--> ajustes permitidos de rede/sistema
          +--> snapshot, checkpoints e rollback
```

### Responsabilidades por camada

| Camada | Responsabilidade |
|---|---|
| Angular/Ionic | Dashboard, navegacao, conexao, Central do PC, temas, acessibilidade e feedback visual. |
| Tauri/Rust | Host desktop, comandos permitidos, sidecar, bandeja, shutdown seguro e plugin de atualizacao. |
| Observer Python | Telemetria de CPU/RAM/GPU/rede e janela de qualidade sem privilegio e sem mutacao. |
| Engine Python | Catalogo de jogos, politica anti-cheat, diagnosticos, score e orquestracao. |
| Helper/daemon | Elevacao estreita, snapshot, aplicacao e rollback das alteracoes autorizadas. |
| FastAPI | Transporte apenas para desenvolvimento em `127.0.0.1:8000`; nao e necessario no aplicativo instalado. |

### Estado local

- snapshots/recuperacao: `%PROGRAMDATA%\NexuFlow\state`;
- historico de sessoes: `%LOCALAPPDATA%\NexuFlow\history`;
- preferencias visuais e resgate secreto: armazenamento local do computador;
- interface e engine nao dependem de login ou nuvem para o fluxo normal.

## 5. Recursos consolidados ate a 1.7

### Dashboard e BOOST

- Nexus Score de 0 a 100, com maior penalidade para perda de pacotes;
- latencia mediana, jitter, perda, p95, picos e disponibilidade;
- telemetria de CPU, RAM e GPU quando o hardware fornece os dados;
- perfis publicos `ping`, `pc`, `complete` e `hardcore_safe`;
- perfis internos automaticos `riot_safe`, `valve_safe`, `protected_safe` e `unknown_safe`;
- baseline antes/depois e historico local;
- daemon permanece responsavel pelo rollback se a interface fechar;
- `Restore All` e recuperacao de sessao interrompida.

### Central de Conexao

- monitor local aproximado de 1 Hz, com janela de ate dois minutos;
- scanner neutro de Cloudflare (`1.1.1.1`), Google (`8.8.8.8`) e Quad9 (`9.9.9.9`);
- no maximo 36 sondas por scan, com destino fixo e sem alvo arbitrario;
- historico local dos ultimos dez scans;
- comparacao temporal sem atribuir causalidade ao BOOST;
- exportacao JSON;
- diagnostico de rota tipo traceroute/WinMTR, somente leitura;
- DNS Lab com Cloudflare, Google e Quad9, sem trocar automaticamente o DNS.

### Central do PC 1.7

- leituras reais de memoria, CPU, GPU e temperatura quando disponiveis;
- sinais de atencao, nao diagnosticos absolutos;
- Modo de Jogo consultivo e atalhos oficiais `ms-settings`;
- nenhuma limpeza compulsoria de RAM, exclusao de arquivo, remocao de aplicativo ou alteracao de boot;
- Driver Center manual, usando apenas o que o Windows Update oferece e sem instalar sozinho.

### Jogos e protecao

- catalogo de 10 jogos: Roblox, VALORANT, League of Legends, Counter-Strike 2, Fortnite, Fall Guys, PUBG, Rainbow Six Siege, DayZ e Arma 3;
- Riot Safe para VALORANT/LoL;
- Valve Safe e Trusted Mode preservado para CS2;
- EAC/BattlEye catalogados para os seis jogos adicionados na 1.7;
- busca, filtros, favoritos, descoberta por executavel e bibliotecas Steam conhecidas;
- validacao automatizada do catalogo e das politicas, mas sem certificacao dos fornecedores.

### Aparencia e Arte Secreta

- oito temas publicos: Nebula, Midnight, Emerald, Alto Contraste, Blocos, Reliquia, Tatico e Operacao;
- escala de texto, movimento reduzido, alto contraste e navegacao acessivel;
- codigo local `NEXU-SECRETO-157` libera somente a Arte Secreta;
- `RESET-CODIGOS` existe apenas para reset/teste local;
- capa, icone, mascote e papel de parede secretos;
- animacao de recompensa e audio local tocado uma vez em novo resgate;
- nenhum efeito no motor, rede, desempenho ou politica anti-cheat.

## 6. Modelo de seguranca e anti-cheat

A politica e **fail-closed**. A interface nunca e a autoridade final para liberar uma mutacao.

### Proibido em jogos protegidos

- ler/escrever memoria do jogo;
- abrir processo protegido para prioridade ou CPU Sets;
- DLL, injecao, hook grafico ou overlay injetado;
- automacao competitiva de entrada;
- enumeracao invasiva de modulos/threads;
- inspecao de sockets do jogo;
- interceptacao, modificacao, emulacao ou redirecionamento de pacotes;
- alteracao de arquivos, executaveis, drivers ou servicos anti-cheat;
- desativacao de Trusted Mode;
- firewall steering para jogo protegido;
- mudanca de DNS/MTU ou TCP experimental durante a partida;
- standby purge, pausa de servicos e reset automatico de Winsock/IP;
- PowerShell/pwsh enquanto Riot/Valve/EAC/BattlEye estiver ativo.

### Permitido no perfil protegido

- deteccao comum por nome de processo;
- telemetria geral de CPU/RAM/GPU/rede;
- `nvidia-smi` quando disponivel;
- sondas para referencias neutras da internet;
- diagnostico de rota somente leitura;
- benchmark DNS sem trocar o resolvedor;
- recomendacao PMTU sem aplicar durante a partida;
- plano de energia geral temporario com rollback exato;
- historico, baseline, relatorio e restauracao de estado geral.

As camadas de defesa incluem resolucao de perfil, gates do orquestrador, guards da API, managers de baixo nivel e auditoria estatica no build.

## 7. Rede, privacidade e limites

### Allowlist atual

| Uso | Destino |
|---|---|
| Interface para API local de desenvolvimento | `127.0.0.1:8000/api/v1/` |
| Qualidade/rota | `1.1.1.1`, `8.8.8.8`, `9.9.9.9` |
| DNS Lab | pares Cloudflare, Google e Quad9 por UDP/53 |
| Speed test 1.8 | `https://speed.cloudflare.com/__down` e `/__up` |

O speed test e iniciado pelo usuario, transfere no maximo 30 MiB, nao altera DNS/rota/adaptador e nao envia o resultado ao NexuFlow. Como em qualquer conexao externa, o edge da Cloudflare ve o IP publico de origem.

Nao existem analytics, anuncios, login obrigatorio, telemetria externa obrigatoria ou comando remoto. O produto tambem nao substitui relays/tuneis: mudar BGP/peering ate o mesmo servidor exigiria infraestrutura propria futura.

## 8. Decisoes tomadas para a 1.8 - Fluxo Vivo

| Item | Decisao | Estado no codigo |
|---|---|---|
| Resposta do BOOST | Mostrar `LIGANDO`, `ATIVO`, `RESTAURANDO` e `DESLIGADO` imediatamente. | Implementado. |
| Cor do BOOST | Estado ligado usa uma cor propria para cada tema. | Implementado, inclusive no tema secreto. |
| Espera do BOOST | Daemon confirma que foi armado antes da baseline longa, sem remover verificacoes. | Implementado. |
| Atualizacao da tela | Leituras secundarias continuam em segundo plano sem prender o botao; o ciclo de telemetria nao se sobrepoe quando o engine demora. | Implementado. |
| Cancelamento | Se o usuario desligar durante a preparacao, o engine cancela antes de qualquer mutacao. | Implementado. |
| Central do PC | Um botao `Fluxo Vivo` seleciona o perfil Completo e usa o BOOST normal. | Implementado na interface. |
| Energia | Continua no plano temporario clonado, com snapshot e rollback. | Ja existente e reutilizado. |
| Modo de Jogo | Nao usar Registry oculto como falsa API universal; permanece transparente/consultivo. | Sem mutacao independente. |
| Temperatura/fan | Temperatura e leitura; nenhuma curva de ventoinha generica. | Mantido consultivo. |
| Game Bar/Xbox | Nao desligar silenciosamente gravacoes ou servicos. | Preservado. |
| Armazenamento | Nenhuma limpeza automatica ou exclusao. | Preservado. |
| DNS ao vivo | Comparacao por 60 s, graficos por provedor, sem trocar DNS. | Implementado. |
| Speed test | Download/upload aproximados, sob demanda, limitado e bloqueado em sessao protegida/BOOST. | Backend, Tauri, API e UI implementados. |
| Animacoes | Opacidade/transformacao curta, sem animacao pesada continua e respeitando movimento reduzido. | Implementado. |
| Atualizador | Plugin oficial Tauri, barra propria e checagem segura. | Fundacao implementada, ativacao bloqueada. |

## 9. Atualizador assinado

O `tauri-plugin-updater` oficial esta integrado no Rust, JavaScript e capabilities. A interface esta preparada para checar na abertura e a cada 30 minutos, mas adia durante BOOST ou jogo protegido.

O recurso permanece deliberadamente com `configured = false`. Nao existe chave de teste ou placeholder. Para ativar a release publica ainda e obrigatorio:

1. gerar um par de chaves exclusivo do updater, separado do Authenticode;
2. guardar a chave privada cifrada em dois locais independentes;
3. embutir somente a chave publica;
4. configurar o endpoint HTTPS do `latest.json` no GitHub Releases;
5. habilitar a geracao dos artefatos de update;
6. guardar chave e senha apenas no cofre do GitHub Actions;
7. publicar instalador, manifesto e `.sig` e testar upgrade de uma versao anterior.

Perder a chave privada impediria atualizar toda a base instalada que confia nela. Por isso a 1.8 nao deve sair com uma chave improvisada.

## 10. Codigo/etapa exata em que o trabalho parou

### Implementacao presente

- `src/app/app.component.ts`: estado imediato `boostIntent`, verificacao periodica do updater e `toggleSmartFlow()`;
- `src/app/app.component.html`: textos/estados do BOOST, banner do updater e integracao da Central do PC;
- `src/app/performance-center.component.*`: Central de Conexao e Central do PC automatica;
- `src/app/core/update.service.ts`: maquina de estados do updater, atualmente desativada de forma fail-closed;
- `src/app/core/nexus.service.ts`: transporte desktop/API para speed test;
- `src/styles.css`: cores por tema, transicoes, DNS ao vivo, dials de velocidade e botao Fluxo Vivo;
- `engine/src/nexus_engine/network/speed_test.py`: teste fixo e limitado a 30 MiB;
- `engine/src/nexus_engine/daemon.py`: resposta de pronto antecipada;
- `engine/src/nexus_engine/orchestrator.py`: cancelamento seguro antes de mutacao;
- `src-tauri/src/commands.rs` e `src-tauri/src/lib.rs`: comando de speed test e plugin updater;
- `app/api_server.py`: rota local do speed test;
- `docs/RELEASE_1.8.md` e `docs/UPDATER_1.8.md`: estado e processo de ativacao.

### Revisao visual ja feita

Foram conferidas em navegador local, no layout desktop:

- Dashboard;
- nova Central do PC;
- Central de Conexao, incluindo DNS e speed test;
- Aparencia e Arte Secreta.

O layout principal esta legivel e alinhado. A previa estava com o engine offline, portanto os estados ativos reais nao foram acionados nessa revisao visual.

### Pendencias imediatas encontradas

1. Reexecutar toda a matriz de testes e auditorias depois dos ajustes finais.
2. Validar com o engine online os estados ativos do BOOST/Fluxo Vivo e o rollback.
3. Criar um commit/checkpoint que consolide 1.7 e o marco inicial da 1.8; hoje o Git ainda aponta para `v1.6.0`.
4. Nao gerar/publicar o instalador final 1.8 antes da chave definitiva e do teste de upgrade assinado.

## 11. Validacao conhecida

Ultimo fechamento registrado durante esta etapa:

- 219 testes Python/API/engine aprovados;
- 25 testes Angular aprovados;
- 1 teste Rust do host aprovado;
- build web concluido.

As auditorias anti-cheat, contrato sem driver e allowlist de rede passaram. A SBOM CycloneDX foi regenerada com 1.045 componentes e `git diff --check` nao encontrou erro de whitespace. Ainda falta o smoke test desktop com engine online e o ciclo de release assinado.

## 12. Pendencias de produto e distribuicao

### Antes de fechar a 1.8

- resolver as sete pendencias imediatas da secao anterior;
- configurar o updater somente com chave definitiva;
- testar instalacao e upgrade assinado 1.7 -> 1.8;
- testar UAC, encerramento inesperado, daemon e rollback;
- testar em Windows 10 e 11 limpos;
- revisar o resultado real do speed test em conexoes lenta, rapida e instavel;
- validar botoes e responsividade com engine online;
- conferir consumo de memoria/CPU e tamanho dos assets.

### Antes de distribuicao comercial

- assinatura Authenticode do instalador/helper;
- smoke test com Intel, Realtek e Wi-Fi;
- teste com versoes atuais de VALORANT, LoL, CS2 e pelo menos um titulo EAC/BattlEye;
- nova revisao das politicas oficiais dos fornecedores;
- validacao em partidas reais dos seis jogos adicionados na 1.7;
- publicacao de hashes e artefatos verificaveis.

### Ideias futuras que nao pertencem a 1.8 local

- relays/tuneis proprios para verdadeira mudanca de rota;
- infraestrutura em Sao Paulo/Rio/Curitiba e selecao de rota por relay;
- qualquer controle termico por fabricante exigiria integracoes separadas e revisao de risco.

## 13. Ordem recomendada para retomar

1. Criar uma copia/checkpoint seguro do estado atual antes de novos recursos.
2. Fechar os pequenos ajustes tecnicos e de asset encontrados na revisao visual.
3. Executar testes web, Python e Rust e todas as auditorias do projeto.
4. Fazer smoke test desktop com o engine online e conferir ligar/desligar/rollback.
5. Consolidar o marco em commit versionado.
6. Definir os dois locais de backup da chave privada e a estrategia da senha.
7. Ativar o updater no commit de release, publicar artefatos assinados e testar upgrade.
8. Somente depois gerar o instalador final da 1.8 e atualizar a documentacao completa/PDF.

## 14. Definicao de pronto da 1.8

A 1.8 pode ser considerada pronta quando o usuario consegue instalar, abrir, ligar o Fluxo Vivo, entender imediatamente o estado, comparar a rede, executar o teste de velocidade voluntariamente e desligar/restaurar tudo sem deixar alteracao pendente; jogos protegidos continuam fail-closed; o updater aceita somente artefato assinado; e toda a matriz de testes, auditorias, upgrade e smoke test Windows passa.
