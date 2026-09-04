# NexuFlow 2.1.0-beta.2 — Portas Abertas

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
- nova tela de entrada original com Entrar, Criar conta e Continuar com o Safe Core;
- conta continua opcional e falha fechada até backend HTTPS, termos e política de privacidade existirem;
- cada universo secreto ganhou painel de arte complementar, símbolo próprio e ícones próprios na navegação;
- Edição Origem usa portais e prismas, Rio Pulse usa sinais e ondas, e Kiwi Signal usa guardião, sementes e folhas;
- chave definitiva do atualizador criada fora do repositório e canal beta assinado validado no GitHub Releases.

## Decisões que não foram falsificadas

O atualizador não é marcado como ativo sem chave e GitHub Release reais. Pagamento, conta, licença, webhook e trial não são simulados como produção: exigem backend, domínio, credenciais, política de privacidade e testes de segurança.

Para o futuro controle de trial, a preferência é uma chave de instalação aleatória e um token de dispositivo pseudonimizado. Coleta silenciosa de serial de hardware foi rejeitada por privacidade e LGPD. Qualquer sinal adicional precisa ser mínimo, explicado, consentido e possuir caminho de suporte/reset.

## Para sair do beta

1. manter o backup da chave definitiva do updater e nunca colocá-la no repositório — concluído;
2. tornar público o canal oficial quando manifesto, SECURITY.md e política de privacidade estiverem prontos — pendente;
3. testar o upgrade assinado entre beta.1 e beta.2 e confirmar rejeição de assinatura inválida — pendente;
4. concluir a matriz física/anticheat descrita em `SECURITY_AUDIT_2.1.md` — pendente;
5. obter assinatura Authenticode ou aprovação SignPath para remover o aviso de editor desconhecido — pendente;
6. somente depois integrar backend de conta e Mercado Pago em ambiente de testes — pendente.
