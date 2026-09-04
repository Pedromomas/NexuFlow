# Análise dos prints — decisão para a 1.7

Referências fornecidas pelo usuário: 25 capturas do ExitLag e NoPing, incluindo telas repetidas. A análise trata rótulos e descrições como ofertas dessas interfaces, não como comprovação de eficácia. Não foi copiado código, identidade visual ou material gráfico de concorrentes.

## Decisão

Escolhemos 1.7.0 porque a entrega adiciona dois espaços completos ao aplicativo e amplia a proteção individual do catálogo, com funções verificáveis de diagnóstico, histórico e organização. O foco é dar informação útil antes de fazer ajustes, sem custos recorrentes de infraestrutura própria.

## O que os prints oferecem e o destino no NexuFlow

| Grupo observado | Decisão |
| --- | --- |
| Monitor de latência, jitter, perda, picos e disponibilidade | Implementado histórico com estatísticas e lacunas de resposta, sem número falso quando offline. |
| Scanner e histórico/exportação de diagnóstico | Implementado scanner de três referências, últimos dez resultados locais e exportação JSON. |
| Gateway e AWS separados | Não implementados neste corte. As três referências públicas não localizam isoladamente falha no roteador. Um diagnóstico de gateway exigiria seleção confiável do adaptador e tratamento de VPN/IPv6. |
| Ping para jogos | Catálogo ampliado, mas sem rotular IP genérico como servidor da partida. O ping do jogo depende de um destino realmente verificado. |
| MTR / Ping / TCPing | Scanner ICMP adicionado; diagnóstico de rota já existe em Ajustes e continua somente leitura. Não foi criado um terminal de rede arbitrário nem um novo TCPing independente. |
| Classificação de servidores DNS | DNS Lab mede três provedores existentes e publica respostas/mediana/ranking. Sem cópia dos tempos vistos nos prints e sem aplicar DNS por esse painel. |
| Restaurar DNS / perfil padrão | Rollback existente preservado. Restaurar estado anterior não equivale a impor um padrão genérico do Windows. |
| Limpeza de RAM e exceções | Não adicionada limpeza automática. Central do PC mostra pressão de memória; cache não é necessariamente desperdício. Apps não são fechados compulsoriamente. |
| Perfis padrão, alto desempenho, personalizado e “ativar tudo” | Mantidos Ping, PC, Completo e Hardcore Safe. Central do PC conduz ao perfil existente; não há ativação indiscriminada de dezenas de tweaks. |
| Minimizar para bandeja e encerrar | Já entregue na 1.6.1, com restauração antes de encerrar. Preferência de iniciar com o Windows não foi adicionada nesta versão. |
| Hardware/estatísticas em tempo real | Telemetria existente reaproveitada. Não há novo driver para sensores nem gráfico de FPS inventado. |
| Modo de Jogo, capturas, energia, apps de inicialização | Nova Central do PC reúne leituras, explicações e páginas oficiais do Windows para revisão. |
| Efeitos visuais/transparência, Explorer compacto, wallpaper JPEG, contatos/notificações | Preferências de uso, não ganho universal para jogos. Não alteradas automaticamente; temas e acessibilidade próprios do NexuFlow permanecem. |
| Cortana, HomeGroup, Fax, impressão, Xbox, OneDrive, toque | Não desligados. Dependem do uso da máquina, versão do Windows e necessidades do usuário; vários são legados ou podem prejudicar recursos úteis. |
| Telemetria de navegadores/Office/Visual Studio/Windows | Não incluída alteração de políticas de terceiros. Não há base para apresentar isso como melhoria medida de FPS nesta entrega. |
| Contadores de desempenho, relatório de erros, SysMain, indexação, serviços/tarefas | Sem desativação em massa. Remover observabilidade pode dificultar diagnóstico; serviços podem ser necessários. |
| “Otimizar registro”, “desativar NTFS”, apps pré-instalados | Não implementados como ações genéricas. Não há limpeza destrutiva do registro ou sistema de arquivos. |
| Processador, todos os núcleos, prioridades de fundo | Mantidas as fronteiras existentes. Sem forçar núcleos ou modificar processos protegidos; o Observador prioriza a identificação do jogo protegido. |
| MSI, interrupções, I/O, offload, NIC, TCP, DSCP e banda | Nenhuma mudança global nova. Exigem contexto de driver/rede, medição e rollback. DSCP local não obriga o provedor a dar prioridade. |
| BCDEdit, ticks dinâmicos, mitigações e Windows Update | Não entram como “boost”. Boot e proteções de segurança não serão enfraquecidos para prometer desempenho. |
| Mouse, teclas de filtragem, tecla Windows, teclado turbo e Snap Tap | Nenhuma automação de entrada adicionada. Recursos de acessibilidade não devem ser desligados em lote e regras competitivas variam por jogo. |
| Rotas duplas, multi-internet, roteamento WFP, otimização inteligente | Não simulados por botões. Uma rede com relays, transporte e operação confiável tem engenharia, infraestrutura, segurança e custo recorrente. |
| Aim Trainer, AudioPads, Replay, Pro Settings vistos no menu | Menu não comprova funcionamento nem detalhes. Não implementados nesta entrega; gravação/overlays exigiriam análise própria de custo e compatibilidade. |
| Idioma, tamanho, login, notificações, promoções e conta | Não copiados só para preencher tela. O app permanece local, PT-BR, sem assinatura comercial de uso e sem marketing compulsório. |

## O que fica melhor que uma lista de switches

- Ausência de dados aparece como ausência, não como 0% de uso ou conexão perfeita na Central.
- Cada teste mostra destino, método e limitações.
- O histórico ajuda a comparar horários e condições; a interface não atribui automaticamente uma variação ao BOOST.
- Os controles protegidos continuam no mecanismo, não só desabilitados na interface.
- Os atalhos manuais são distinguidos das mudanças temporárias do BOOST.
- Associação a EAC/BattlEye, detecção automatizada e teste real são evidências diferentes.

## Próximas etapas possíveis, não entregues

Validação real dos seis jogos em computadores de teste; catálogo versionado de destinos oficiais de jogo quando disponíveis; diagnóstico de gateway com contexto de múltiplos adaptadores; comparação controlada antes/durante/depois em condições equivalentes; alertas locais de degradação com opt-in. Relays/multipath só após orçamento e projeto de transporte, sem promessa antecipada.

## Fontes consultadas em 02/09/2026

- [BattlEye — títulos e parceiros](https://www.battleye.com/): PUBG, Rainbow Six Siege, Fortnite, DayZ e Arma 3 aparecem na página oficial.
- [Epic Games — problemas do Easy Anti-Cheat](https://www.epicgames.com/help/c-37599050/a24092251): associação a jogos Epic, incluindo Fall Guys.
- [Epic — Easy Anti-Cheat no Fortnite](https://www.epicgames.com/help/c-202300000001636/c-202300000001719/easy-anti-cheatfortnite-a202300000010358).
- [Microsoft — abrir páginas de Configurações](https://learn.microsoft.com/en-us/windows/apps/develop/launch/launch-settings): destinos fixos `ms-settings:` e variação por versão/SKU.
- [ExitLag](https://www.exitlag.com/) e [NoPing](https://noping.com/): contexto comercial; as alegações de marketing não foram adotadas como medições independentes.

As classificações de risco acima são decisões de engenharia do NexuFlow com base no seu contrato de segurança, não acusações sobre a implementação interna dos concorrentes, que não foi inspecionada.
