# NexuFlow 1.7.0 — Insight Edition

Data: 02/09/2026. Build local para Windows x64.

## O que mudou

### Som da Arte Secreta

- O MP3 enviado pelo usuário toca uma vez junto da animação após cada novo resgate bem-sucedido de `NEXU-SECRETO-157`, inclusive ao testar novamente depois de `RESET-CODIGOS`.
- Áudio local, sem download, sem loop e a 70% do volume do player. Não toca ao abrir o aplicativo, ao trocar tema, com código inválido ou em tentativa de resgatar um código já desbloqueado.
- Botão para silenciar durante a animação. Continuar/Esc, resetar os resgates ou encerrar a interface interrompe a reprodução.
- Se o ambiente bloquear a reprodução automática, a recompensa permanece salva e aparece o botão “Tocar som do desbloqueio”.

### Central de Conexão

- Novo acesso na navegação e atalho Alt+8.
- Histórico ao vivo de até dois minutos, reutilizando as medições locais do engine. Nenhum segundo monitor foi criado para a tela.
- Mediana, jitter, consultas sem resposta, percentil 95 e contagem de picos. Respostas de 0 ms são válidas; timeouts não viram 0 ms.
- Gráfico com lacunas e marcas de perda. Mudança de referência inicia um novo segmento. Amostras antigas deixam de aparecer como leitura atual após cinco segundos.
- Scanner sob demanda: Cloudflare, Google e Quad9 em paralelo; 12 consultas por destino, timeout de 600 ms, intervalo de 250 ms. Máximo de 36 consultas. No Windows usa ICMP; fora dele o fallback é TCP/443 e a metodologia informa essa diferença.
- Conclusão em linguagem direta: referências estáveis, divergência entre destinos, oscilação compartilhada ou nenhuma resposta. Não atribui culpa automaticamente ao provedor.
- Últimos dez scans guardados no armazenamento local da interface. Seleção por horário e diferença da mediana em relação ao scan anterior. Comparação temporal não é prova de ganho causado pelo BOOST.
- Exportação JSON do scan selecionado, última classificação DNS e janela de monitoramento. Sem IP pessoal, MAC, caminhos ou dados do jogo; este relatório de diagnóstico não é assinado. O relatório de sessão assinado existente continua separado.
- Scanner e ranking compartilham um bloqueio entre processos; duas instâncias não executam esses diagnósticos simultaneamente. O bloqueio é liberado mesmo após encerramento inesperado do processo.

### DNS Lab

- Ranking medido de Cloudflare, Google e Quad9, com dois servidores de cada provedor.
- Seis consultas UDP/53 por provedor a três domínios públicos fixos. Mostra mediana e respostas recebidas, não números de exemplo.
- Menos de 75% de sucesso torna o resultado inelegível. Dentro da categoria elegível, pontuação = mediana + 150 ms × proporção de falhas.
- Falha total produz resultado inconclusivo, nunca recomendação inventada.
- Validação da origem IP/porta da resposta DNS além dos controles existentes de transação e status.
- Não troca DNS. Não compara o DNS atual; não é recomendação universal sobre privacidade, filtros ou disponibilidade. Troca automática protegida já existente permanece no fluxo de BOOST autorizado.

### Central do PC

- Novo acesso e atalho Alt+9.
- Leituras de memória disponível, CPU, temperatura da GPU e preferência explícita do Modo de Jogo. Sensores ausentes aparecem como indisponíveis.
- Avisos para memória abaixo de 2 GB, CPU a partir de 85% e GPU a partir de 85 °C. São sinais de atenção, não provas de gargalo ou throttling.
- Revisão de capturas e plano de energia; atalhos fixos para Modo de Jogo, capturas, gráficos, apps de inicialização, armazenamento, energia e rede do Windows.
- Preparar perfil PC seleciona o modo e abre o Dashboard. Não ativa BOOST sem clique.
- Atalhos não alteram configurações. Mudanças feitas pelo usuário no Windows não entram no rollback do NexuFlow.
- Sem limpeza compulsória de RAM, exclusão de apps, desativação de Windows Update/antivírus ou alterações de boot.

### Catálogo e proteção

O catálogo passa de quatro para dez jogos. Adicionados: Fortnite, Fall Guys, PUBG: BATTLEGROUNDS, Rainbow Six Siege, DayZ e Arma 3.

- Nomes de executáveis individuais mapeiam cada título para Protected Safe, em todos os perfis públicos e internos. Inclui nomes alternativos conhecidos; novos patches podem mudar esses nomes.
- Bibliotecas adicionais da Steam são consultadas pelos caminhos conhecidos. Instalações personalizadas fora desses locais podem não aparecer antes de o jogo abrir.
- Detecção de jogos protegidos enumera nome/PID sem consultar o caminho do processo em execução, memória, módulos ou sockets.
- Fortnite usa classificação conservadora EAC/BattlEye; Fall Guys, EAC; demais novos títulos, BattlEye. Isso não afirma que cada fabricante usa apenas aquele componente.
- Busca, filtros de encontrados/favoritos e favoritos locais.
- Lista mantém a identidade dos botões durante atualizações automáticas; textos de jogos não encontrados ficam legíveis. Navegação possui nomes acessíveis e dicas também na janela compacta.
- Interface separa política testada por automação de teste em partida. Não há certificação dos fabricantes nem garantia de ausência de banimento.
- Correção no observador: um jogo protegido tem precedência sobre Roblox quando ambos estão abertos.

## Escopo da validação

Testes automatizados verificam perfis, detecção simulada, bloqueio de mutações, ausência de abertura de processos protegidos, bibliotecas Steam temporárias, scanner limitado, falha total, ranking DNS, expiração de histórico, concorrência e estados da interface.

A revisão visual e os testes de scanner/DNS usam a máquina de desenvolvimento. Não substituem instalação limpa em outros computadores, medições de FPS em partida ou certificação EAC/BattlEye. Nenhuma partida dos seis novos títulos foi executada neste trabalho. A revisão das fontes confirma associação dos títulos ao anticheat; não é aprovação do NexuFlow por essas empresas.

O build local continua sem certificado comercial Authenticode. Hashes verificam integridade, não identidade de um fornecedor certificado. Não contorne alertas do Windows sem conferir procedência.

## Como testar

1. Abra Conexão: espere o monitor reunir amostras. Execute scanner e Classificar DNS, separadamente.
2. Repita o scanner em outro momento, selecione o histórico e exporte o relatório. Resultados diferentes podem refletir a rede, não o NexuFlow.
3. Em Central do PC, confira leituras. Preparar perfil PC deve levar ao Dashboard sem ativar BOOST.
4. Em Jogos, busque um título, favorite e filtre. Feche/reabra o app para verificar persistência dos favoritos.
5. Para validar um jogo EAC/BattlEye em partida: use máquina de teste, anote versões do Windows/jogo/anticheat, confirme Protected Safe e ausência de mutações bloqueadas no Investigador, teste início/fim/rollback em cada objetivo e registre o resultado. Não force o processo nem desative o anticheat para passar no teste.

## Limites de produto

Não adiciona rede de relays, VPN, seleção geográfica de servidor, bonding de múltiplas internets, multiplicação de banda, garantia de redução de ping ou aumento de FPS. Veja [análise dos prints](COMPETITOR_REVIEW_1.7.md) para as decisões.
