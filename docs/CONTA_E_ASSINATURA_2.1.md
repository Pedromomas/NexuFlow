# NexuFlow 2.1 — conta, perfil e assinatura

## Estado atual

A interface e o cliente seguro estão implementados, mas permanecem **fail-closed**. `public/nexuflow-runtime-config.json` só libera cadastro quando os três endereços HTTPS forem publicados: API de conta, termos de uso e política de privacidade. Sem isso, os campos e botões ficam bloqueados e nenhum dado é coletado.

O Safe Core, diagnóstico básico, otimizações simples, temas e o mascote continuam disponíveis sem conta e sem pagamento.

## Contrato HTTPS esperado

- `POST /v1/auth/register`: recebe `displayName`, `email`, `password`; cria conta pendente e envia confirmação.
- `POST /v1/auth/login`: devolve token de acesso opaco e curto, validade em segundos e perfil mínimo.
- `POST /v1/account/duo-invite`: exige sessão; convida um e-mail verificado sem compartilhar senha.
- `POST /v1/billing/checkout`: exige sessão; recebe somente o identificador do plano e devolve URL HTTPS oficial do Mercado Pago.
- `POST /v1/account/delete-request`: exige sessão; inicia exclusão confirmada pelo e-mail do titular.

O aplicativo aceita resposta de checkout somente em domínio `mercadopago.com` ou `mercadopago.com.br`. Redirecionamentos HTTP são recusados. A origem da API fica presa ao endereço HTTPS assinado dentro da configuração do release.

## Segurança obrigatória do servidor

- Hash de senha com Argon2id e parâmetros atualizáveis; jamais senha reversível ou texto puro.
- Confirmação de e-mail, rate limiting por conta e endereço, bloqueio progressivo e logs sem senha/token.
- Token curto; nenhum token de acesso é salvo no `localStorage`. A implementação atual mantém a sessão apenas na memória e exige novo login ao reiniciar.
- Mercado Pago cria o checkout e valida webhook assinado. NexuFlow nunca recebe número de cartão, CVV ou credencial PIX.
- Autorização aplicada a cada rota; o plano nunca é decidido pelo frontend.
- Identificador de dispositivo pseudonimizado e rotacionável. Nenhum número de série bruto deve sair do PC.
- Consulta de licença antes do BOOST ou após a sessão, nunca durante jogo protegido.
- Rotas de exportação e exclusão de dados, retenção definida e plano de incidente compatível com LGPD.

## Planos apresentados

- R$ 1 por um dia.
- R$ 5 por sete dias.
- R$ 10 por trinta dias.
- R$ 80 por um ano.
- Duo: titular e um convidado com conta própria, convite verificado, revogação e carência de troca.

## O que ainda bloqueia produção

1. domínio oficial e backend hospedado;
2. banco de dados e serviço de e-mail transacional;
3. credenciais e webhooks do Mercado Pago;
4. termos, política de privacidade e fluxo LGPD publicados;
5. testes de abuso, rate limiting, recuperação de conta e exclusão;
6. revisão jurídica e teste do upgrade assinado N para N+1.

No release que ativar a conta, o domínio exato da API também precisa entrar em `app.security.csp.connect-src`. A configuração atual permite apenas IPC local; por isso um endpoint externo colocado somente no JSON continua bloqueado pela WebView.

Nenhum desses itens deve ser simulado dentro do executável público.
