# NexuFlow 2.1 beta — auditoria de regressão da 1.7

Data: 04/09/2026  
Base recebida: `NexuFlow-1.7.0-InsightEdition-Source.zip`

## Resultado

A base 1.7 foi usada somente como evidência. O manifesto SHA-256 do pacote conferiu **194 de 194 arquivos**, sem arquivo ausente ou divergente. Os auditores `anti-cheat-audit.ps1`, `audit-anticheat.ps1` e `audit-network-allowlist.ps1` passaram na fonte 1.7 e na árvore atual.

Isto demonstra aderência aos contratos do projeto, não certificação das fabricantes e não garantia de ban zero. Somente Riot, Valve e os operadores de EAC/BattlEye decidem a aplicação de suas regras.

## Proteções preservadas

- `anti_cheat.py` e `policy_runtime.py` continuam byte a byte iguais à base 1.7 auditada.
- perfis Riot/Vanguard, Valve/VAC, EAC/BattlEye e jogo desconhecido são reduções unidirecionais; a interface não consegue promover um jogo protegido para um perfil agressivo;
- jogo desconhecido falha fechado em `unknown_safe`;
- runtime genérico EAC/BattlEye falha fechado em `protected_safe` sem tentar adivinhar o jogo;
- acesso à memória, injeção, hooks, automação de entrada, inspeção de socket do jogo, interceptação de pacotes, alteração de arquivos, manipulação do anticheat, prioridade/afinidade, firewall steering, troca de DNS/MTU ao vivo, tweaks TCP, purge de standby, pausa de serviço, reset de rede e PowerShell durante sessão protegida são bloqueados;
- detecção de processos é somente nome e PID; não abre memória, módulos, threads ou sockets;
- sem driver próprio, WinDivert, Npcap, Frida, Detours ou dependências equivalentes;
- rede externa segue default-deny e API local vinculada ao loopback.

## Proteção automática versus botão da Central do PC

São duas coisas diferentes:

1. **Safe Core obrigatório:** decide o que qualquer ação do NexuFlow pode fazer. Não existe botão para desligá-lo.
2. **Automação/BOOST:** inicia ou encerra otimizações reversíveis. Em espera, o NexuFlow não aplica otimizações. Isso não aumenta o risco de ban; significa apenas que o aplicativo não está alterando o sistema.

Se um jogo protegido inicia durante uma sessão comum, o daemon atual restaura a sessão anterior antes de iniciar o perfil restrito. Essa transição é uma defesa adicional em relação à base recebida.

## UAC (“Sim ou Não”)

A janela principal usa `asInvoker` e abre sem privilégios administrativos. Quando o usuário inicia uma mudança real no Windows, o helper limitado solicita UAC. O NexuFlow não desativa, oculta ou contorna essa proteção. Enquanto o daemon elevado da sessão está ativo, o desligamento pede a ele para restaurar e sair, sem uma segunda janela. Um snapshot órfão ainda pode exigir nova autorização para restaurar com segurança.

Remover totalmente o UAC exigiria retirar as otimizações administrativas ou instalar um serviço privilegiado permanente. A segunda opção aumenta a superfície de ataque e a chance de classificação como PUP; fica rejeitada até assinatura Authenticode, revisão independente e testes limpos em Windows 10/11.

## Atualizador

A interface, o adiamento durante BOOST/jogo protegido e a validação do plugin oficial existem. O canal permanece fail-closed enquanto faltarem:

- chave pública definitiva embutida;
- chave privada com backup offline controlado;
- endpoint HTTPS oficial do GitHub Releases;
- teste real de upgrade assinado e rollback de falha;
- assinatura Authenticode do instalador público.

Nenhum placeholder deve ser aceito e a verificação de assinatura nunca deve ser desativável.

## Pendências externas antes do lançamento

- partidas reais atuais com VALORANT, LoL, CS2 e jogos EAC/BattlEye;
- smoke test em instalações limpas de Windows 10 e 11;
- teste físico em Intel, Realtek e Wi-Fi;
- revisão das políticas oficiais após patches dos anticheats;
- assinatura Authenticode comercial ou aprovação em programa equivalente.

