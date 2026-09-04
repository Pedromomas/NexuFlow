# NexuFlow 1.8.0 - Fluxo Vivo

Data de desenvolvimento: 04/09/2026. Estado: build local validado, release assinada pendente.

## Experiencia e BOOST

- o aplicativo abre sem privilegio administrativo; o UAC aparece somente quando uma acao estreita do BOOST realmente precisa alterar o sistema;
- a tarefa do VS Code reutiliza o motor quando ele ja esta atualizado e ignora caches/builds pesados na indexacao;
- resposta visual imediata ao clique: Ligando, Ativo, Restaurando e Desligado;
- o botao deixa de esperar pelas leituras secundarias depois que o daemon confirma a acao;
- a telemetria periodica impede sobreposicao quando uma leitura demora mais de um segundo;
- cores de estado ativo especificas para cada tema, inclusive Arte Secreta;
- timing curto, easing consistente, foco visivel e suporte a movimento reduzido;
- mascote secreto otimizado para a interface em WebP responsivo, preservando o PNG mestre;
- a preparacao de baseline e as verificacoes anti-cheat continuam reais; a interface explica a espera em vez de parecer travada.

## Central do PC automatica

- uma chave Fluxo Vivo escolhe o perfil Completo e chama o mesmo BOOST com snapshot e rollback;
- deteccao do jogo e do modo protegido permanece automatica;
- energia continua usando o plano temporario reversivel existente;
- temperatura de GPU continua somente consultiva;
- Game Bar, Xbox, arquivos, armazenamento, programas e ventoinhas nao sao alterados silenciosamente.

## Conexao

- comparacao DNS ao vivo por 60 segundos, iniciada pelo usuario, com ate oito rodadas visuais;
- o DNS nao e trocado: o grafico mede apenas tempo de resolucao;
- speed test rapido sob demanda contra `speed.cloudflare.com`, com limite de 30 MiB;
- speed test bloqueado durante BOOST ou jogo protegido e nunca executado automaticamente;
- o servidor externo recebe o IP publico necessario a conexao; o NexuFlow nao envia o resultado.

## Atualizador

- plugin oficial Tauri Updater integrado no Rust, JavaScript e capabilities;
- barra in-app preparada, verificacao na abertura e a cada 30 minutos, sempre adiada durante BOOST/jogo protegido;
- plugin permanece fora do runtime enquanto endpoint e chave publica reais nao existem, evitando falha de inicializacao com configuracao incompleta;
- instalacao depende da assinatura obrigatoria do plugin;
- estado fail-closed: permanece desativado ate existir chave publica real, dois backups seguros da chave privada e um `latest.json` publicado no GitHub Releases;
- nenhuma chave de teste ou placeholder foi embutida no aplicativo.

## Validacao atual

- 219 testes Python/API/engine;
- 25 testes Angular;
- 1 teste Rust do host;
- build web concluido.
- auditorias anti-cheat, contrato sem driver e allowlist de rede aprovadas;
- SBOM CycloneDX regenerada com 1.045 componentes, incluindo o updater oficial.

O instalador final da 1.8 ainda nao deve ser publicado ate o atualizador receber a chave definitiva, o endpoint assinado e os testes de upgrade entre versoes.
