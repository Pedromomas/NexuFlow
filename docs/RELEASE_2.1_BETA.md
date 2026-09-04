# NexuFlow 2.1.0-beta.1 — Portas Abertas

Este é um marco de validação, não uma release comercial.

## Entregue neste marco

- regressão completa da fonte 1.7 com manifesto e auditores aprovados;
- Safe Core explicado como camada obrigatória e independente do botão da Central do PC;
- Central do PC redesenhada com controle próprio, estado claro, etapas e expectativa correta sobre UAC;
- resposta visual imediata, rollback pelo daemon elevado e nenhuma tentativa de contornar o Windows;
- Central de Atualizações visível nos Ajustes, inclusive quando o canal assinado ainda não foi publicado;
- Edição Origem reformulada em 16:9 e novos universos Rio Pulse e Kiwi Signal;
- fundos WebP leves e mudanças completas de cores, painéis, navegação e animações por universo;
- DNS comparativo ao vivo, speed test voluntário e monitor de conexão herdados do Fluxo Vivo.

## Decisões que não foram falsificadas

O atualizador não é marcado como ativo sem chave e GitHub Release reais. Pagamento, conta, licença, webhook e trial não são simulados como produção: exigem backend, domínio, credenciais, política de privacidade e testes de segurança.

Para o futuro controle de trial, a preferência é uma chave de instalação aleatória e um token de dispositivo pseudonimizado. Coleta silenciosa de serial de hardware foi rejeitada por privacidade e LGPD. Qualquer sinal adicional precisa ser mínimo, explicado, consentido e possuir caminho de suporte/reset.

## Para sair do beta

1. criar e proteger a chave definitiva do updater;
2. publicar repositório e release HTTPS oficiais;
3. assinar e testar upgrade entre duas versões;
4. concluir a matriz física/anticheat descrita em `SECURITY_AUDIT_2.1.md`;
5. somente depois integrar backend de conta e Mercado Pago em ambiente de testes.

