# NexuFlow 1.5.8 — Secret Art Edition

## Novidade

- Nova aba **Código secreto** abaixo de Ajustes.
- Código validado localmente, sem API, telemetria ou armazenamento do texto digitado.
- Desbloqueio persistente somente no computador atual.
- Tema **Arte Secreta** adicionado à Aparência depois do desbloqueio.
- Ícone, mascote e capa originais fornecidos pelo criador do NexuFlow.
- Novo atalho `Alt+6` para abrir a área de código.

## Limite de segurança

O código é uma surpresa cosmética, não autenticação forte. A lógica executada no cliente pode ser estudada por alguém com acesso ao binário. O desbloqueio não concede comandos, otimizações ou permissões adicionais.

## Compatibilidade

As preferências públicas da 1.5.7 são preservadas. O tema secreto só é restaurado quando o marcador local de desbloqueio já existe. Em caso de preferência inválida, o aplicativo volta ao Nebula sem impedir a inicialização.

## Segurança

Esta versão não modifica engine, mutações do Windows, rede, política anti-cheat ou IPC. A Arte Secreta é formada apenas por HTML, CSS, imagens locais e uma preferência em `localStorage`.
