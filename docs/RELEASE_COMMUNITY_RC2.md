# NexuFlow 2.1.0-rc.2 — Comunidade

Todas as funções implementadas são gratuitas. Não há conta obrigatória, assinatura, trial, checkout ou licença comercial. O Safe Core e as regras de segurança continuam obrigatórios.

## Novidades

- Página “Apoiar o projeto”: Pix voluntário, sem valor fixo, com sugestão de R$ 1.
- QR Code local, copiar chave e Pix Copia e Cola. Sem rastreamento de doadores, gateway ou confirmação de recebimento no aplicativo.
- Titular e cidade informados pelo responsável. O campo de nome do BR Code usa o limite de 25 caracteres; o nome completo é mostrado na tela e o banco resolve o recebedor pela chave.
- Perfil e temas locais. Nenhuma doação libera funções ou vantagens.
- Correções de recuperação, restauração concorrente e estado atrasado do botão BOOST herdadas da RC1.

## Validação

Testes de estrutura TLV, CRC16, chave Pix, moeda, nome/cidade, ausência de valor e igualdade entre QR Code e Copia e Cola. Referências: [Manual BR Code do Banco Central](https://cdn-www.bcb.gov.br/content/estabilidadefinanceira/spb_docs/ManualBRCode.pdf) e [Manual de Padrões para Iniciação do Pix](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Regulamento_Pix/II_ManualdePadroesparaIniciacaodoPix.pdf).

Nenhuma transferência foi realizada pelo desenvolvimento. O responsável deve conferir no banco se a chave continua correta; a pessoa que doa deve verificar o destinatário antes de confirmar.

Fonte atual e histórico são revisados para publicação. Credenciais não são incluídas. O código de backend antigo permanece histórico e não é utilizado pelo aplicativo Comunidade.

## Limitações de pré-lançamento

Não há garantia de redução de ping/FPS nem de compatibilidade futura com anticheats. Ainda faltam matriz física de Windows/hardware, partidas reais e teste de atualização assinada entre versões. O atualizador continua bloqueado até validação do canal. Assinatura Tauri de pacote não é Authenticode: o Windows pode exibir editor desconhecido.

O responsável confirmou em 17/09/2026 que possui autorização para redistribuir o áudio de resgate Origem. Essa declaração não transforma o áudio em software MIT; direitos de terceiros continuam aplicáveis.
