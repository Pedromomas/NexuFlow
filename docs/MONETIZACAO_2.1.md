# NexuFlow 2.1 — Portas Abertas

Implementação de interface e contrato: consulte `CONTA_E_ASSINATURA_2.1.md`.

## Estado atual

A interface de preços e os contratos locais foram adicionados, mas o checkout fica deliberadamente desativado. Cobrar antes de existir backend HTTPS, webhook validado, exclusão de conta e política de privacidade seria um risco financeiro e de LGPD.

## Produtos

| Plano | Preço | Duração |
|---|---:|---:|
| Passe diário | R$ 1 | 1 dia |
| Passe semanal | R$ 5 | 7 dias |
| Plano mensal | R$ 10 | 30 dias |
| Plano anual | R$ 80 | 1 ano |

O Safe Core, diagnóstico básico, otimizações simples, temas e mascote Flux permanecem gratuitos. Latency Lab completo, perfis automáticos de DNS por jogo e funções avançadas futuras podem exigir assinatura.

## Plano Duo

Uma assinatura pode ter o titular e um convidado. O amigo recebe convite em qualquer e-mail verificado — não precisa ser Gmail — e usa conta própria. O titular pode revogar o assento; trocar de convidado deve ter carência de sete dias para reduzir revenda e abuso. Senha e token nunca são compartilhados.

## Arquitetura mínima antes de ligar pagamentos

1. Conta com e-mail confirmado, senha em Argon2id e sessão curta com renovação segura.
2. API HTTPS que retorna apenas direitos ativos e nunca executa otimizações.
3. Checkout hospedado pelo Mercado Pago; cartão e PIX nunca passam pelo app ou banco NexuFlow.
4. Webhook do Mercado Pago validado por assinatura, idempotência e consulta do pagamento no provedor.
5. Cache local de licença assinado, de curta validade, checado fora de BOOST e partidas protegidas.
6. Trial de sete dias ligado a uma chave aleatória de instalação e token de dispositivo pseudonimizado. Evitar impressão digital invasiva de hardware.
7. Rate limit por conta e origem, auditoria sem códigos ou tokens em texto puro e códigos vitalícios aleatórios, de uso único e revogáveis.
8. Política de privacidade, retenção, exportação/exclusão da conta e plano de incidente antes do primeiro cadastro público.

## Segredos e ambientes

Credenciais do Mercado Pago, chave de sessão, sal/pepper e acesso ao banco pertencem apenas ao cofre do backend. Nunca entram no Angular, no executável, no repositório ou no manifesto do atualizador. Desenvolvimento, homologação e produção usam credenciais e bancos separados.

## Critério para sair do modo “Em preparação”

Checkout em ambiente de teste aprovado; webhook testado contra repetição e falsificação; cancelamento e expiração funcionando; convite Duo, revogação e carência validados; exclusão de conta exercitada; revisão LGPD concluída; e testes de licença confirmando que nenhuma consulta ocorre durante sessão protegida.
