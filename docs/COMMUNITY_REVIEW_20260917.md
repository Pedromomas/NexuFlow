# NexuFlow 2.1 — revisão da Edição Comunidade

Data: 17/09/2026. Candidato local: **2.1.0-rc.1**. Não é certificação de compatibilidade, ausência de bugs ou aprovação de anticheat.

## Decisão de produto

O aplicativo é gratuito permanentemente. Não exige cadastro, assinatura, pagamento, trial, validação de licença nem relógio de expiração para usar funções implementadas. Ping, PC, Completo, Hardcore Safe, diagnósticos, Latency Lab, DNS, temas e coleção não têm restrição comercial. Dependências técnicas e bloqueios de segurança continuam obrigatórios. Gratuito não significa remover proteções nem prometer redução de ping/FPS em todo computador.

O perfil é local. Os códigos cosméticos são locais e gratuitos, um por tema. Não concedem privilégios administrativos nem alteram o motor. Não há sincronização de conta.

## Mudanças verificadas nesta revisão

- Retirados da raiz da interface o serviço de contas, formulário de entrada, área de assinatura, cliente de licença e fluxo de resgate online. O aplicativo abre diretamente.
- Removidos preços, checkout e mensagens de validação cosmética temporária. A configuração de distribuição identifica a edição Comunidade.
- A compilação recusa configuração de conta/licença na edição Comunidade. O verificador do JavaScript distribuído recusa rotas de login, cadastro, licença e checkout administrativo.
- O estado do botão BOOST usa uma revisão da operação para descartar telemetria atrasada; cliques duplicados continuam bloqueados. A restauração também invalida respostas antigas.
- Uma restauração malsucedida agora impede iniciar outra sessão e sobrescrever o snapshot anterior, inclusive se o relatório indicar sucesso mas o estado continuar ativo.
- O daemon não anuncia inicialização bem-sucedida após recuperação incompleta.
- Ao desligar, o processo elevado aguarda o daemon; se o prazo terminar, não começa uma segunda restauração concorrente.
- O retorno do comando elevado e da API local não declara rollback completo enquanto houver estado pendente. Falhas mantêm os dados necessários para nova tentativa.
- Teste da API não inicia mais um daemon real quando executado por um administrador: a inicialização é simulada nesse teste.

## Evidências locais

- Motor e API: **283 testes aprovados**, incluindo novas regressões de recuperação e restauração concorrente.
- Interface: **77 testes aprovados** em 11 arquivos.
- Suíte adicional de compatibilidade de acesso/contas legadas: **24 testes aprovados**. Há sobreposição com a suíte da interface; os números não devem ser somados como testes únicos.
- Host Rust: teste de confirmação de encerramento/rollback aprovado.
- Compilação Angular e verificador de CSS/arquivos locais aprovados. Nenhuma rota comercial identificada nos arquivos JavaScript distribuídos pelo verificador.
- Motor recompilado com PyInstaller; consulta somente leitura de telemetria retornou JSON válido, processo terminou com código 0 e informou motor online, sem recuperação pendente neste computador.
- Busca estática nos diretórios de execução não encontrou as APIs invasivas enumeradas pelo script de auditoria (injeção, leitura/escrita de memória de processo, hooks e captura por WinDivert/Npcap). Essa busca não prova ausência de todo risco.
- Advertências não bloqueantes: depreciação da integração FastAPI/httpx, mock do atualizador não declarado no topo do arquivo de teste e scrollTo não implementado pelo simulador de DOM.

## Limites e itens anteriores à publicação estável

1. Não foram executadas nesta revisão partidas reais com Vanguard, VAC, EAC, BattlEye ou Roblox, nem a matriz Windows 10/11 limpos e adaptadores físicos. Não existe garantia de ausência de ban.
2. O instalador local não recebe assinatura Authenticode nem assinatura de distribuição do atualizador neste fluxo. Pode exibir editor desconhecido. O canal público assinado e a separação estável/beta ainda precisam ser publicados e testados, inclusive rejeição de pacote adulterado.
3. A interface compilada foi validada por testes de componentes; instalação interativa, escalas do Windows e comportamento visual completo ainda precisam de teste manual.
4. Revisar arquivos e histórico antes de abrir o repositório: a busca pontual de credenciais no fonte atual não é uma auditoria completa de histórico. Chaves privadas e senhas não devem ser incluídas.
5. Confirmar autorização/licença de redistribuição dos recursos fornecidos, especialmente o áudio de terceiros. A licença do código não licencia automaticamente esses recursos.
6. Documentos antigos sobre monetização permanecem históricos. O backend e componentes legados estão preservados no fonte, mas não são carregados pela interface atual. Separá-los e revisar a documentação antes da publicação pública.
7. Nenhum serviço remoto, conta Firebase, implantação Render, segredo ou repositório foi apagado ou alterado nesta revisão. Encerrar serviços e tratar dados de teste é uma decisão separada.

## Entrega

Instalador gerado: `outputs/community-rc1-20260917/NexuFlow_2.1.0-rc.1_x64-setup.exe` (43.561.167 bytes).

SHA-256: `085D23F3AD85ED90E484AA294DC73AD2C45AFBB5047C6D33312AFE09099AB089`.

Authenticode consultado: `NotSigned`. O hash do motor recompilado coincide com o arquivo fornecido ao empacotamento: `1A16F9E3DE0A5497F4E6C895ED4A0B2D236BF34AC61315123742E42D5A0BC7B1`. Compilação NSIS concluída com sucesso; instalador não executado nesta revisão.

O instalador candidato é para revisão local, não uma declaração de que toda a matriz de lançamento foi concluída. Nenhuma publicação no GitHub foi realizada nesta etapa. O aplicativo usa diagnósticos de rede externos quando solicitados; edição sem conta não significa que speed test e ping funcionem sem internet.
