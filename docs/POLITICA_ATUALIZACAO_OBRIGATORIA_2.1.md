# Política de atualização obrigatória

## Regra

Atualizações comuns mostram a barra in-app e podem ser adiadas. Uma release cuja nota começa exatamente com `[SECURITY-REQUIRED]` é tratada como correção crítica: não pode ser dispensada, é baixada automaticamente quando BOOST e jogo protegido estão inativos e bloqueia uma nova ativação do BOOST até terminar.

## Proteções contra bloqueio malicioso ou release quebrada

- o Tauri valida o instalador com a chave pública embutida; assinatura inválida nunca é instalada;
- a checagem e instalação nunca começam durante BOOST ou partida protegida;
- falha de assinatura ou download coloca o atualizador em erro e libera o modo consultivo/diagnóstico, evitando um bloqueio permanente causado por rede ou manifesto falso;
- rollback continua disponível;
- somente pessoas com acesso à chave privada de updater devem publicar a marca crítica;
- a release deve começar como draft e passar pelo upgrade N → N+1 e pelo teste de assinatura adulterada antes de ser publicada.

## Por que nem toda atualização é obrigatória

Obrigar tema, texto ou mudança estética aumenta risco de indisponibilidade sem benefício de segurança. A marca obrigatória é reservada para vulnerabilidade explorável, revogação de backend/licença, incompatibilidade anticheat perigosa ou versão mínima sem suporte.

## Nota de release crítica

Exemplo:

```text
[SECURITY-REQUIRED] Corrige validação de origem no canal de atualização. O BOOST fica indisponível até a instalação terminar.
```
