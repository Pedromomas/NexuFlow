# Registro de validações pendentes — lançamento 2.1.0 em 18/09/2026

O responsável autorizou o lançamento oficial 2.1.0 após relatar funcionamento no seu computador. Isso não conclui a matriz física abaixo nem certifica compatibilidade com anticheats. A lista histórica permanece para transparência: repositório e artefatos já estão públicos, e a RC.2 passou nos testes automatizados e na verificação criptográfica independente, inclusive rejeição de alterações em memória. Upgrade real e partidas não foram comprovados. As pendências não devem ser apresentadas como testes aprovados.

Estado desta lista: pendências, não certificação. Edição Comunidade totalmente gratuita. Publicação do repositório será uma etapa posterior, após revisão dos arquivos e do histórico.

## 1. Atualização real

- [ ] Disponibilizar manifesto e pacotes em HTTPS acessível ao aplicativo. GitHub Releases privado não oferece download anônimo; não embutir token.
- [ ] Definir hospedagem de artefatos sem tornar o código público antes do lançamento.
- [ ] Separar rotas de beta e estável e impedir que o canal estável receba pre-release.
- [ ] Instalar beta.2 e receber beta.3 no próprio aplicativo; registrar instalador, hash, versão, data e resultado.
- [ ] Testar rejeição criptográfica de pacote adulterado com chave de laboratório, nunca modificar artefato oficial publicado.
- [ ] Validar queda de conexão, download incompleto, falha de instalação e retentativa.
- [ ] Validar jogo aberto durante consulta/download, BOOST ativo, rollback pendente e motor offline.
- [ ] Implementar/testar exclusão mútua nativa na instalação e no início de otimizações; rechecagem JS não elimina toda corrida com processos externos.

## 2. Windows e hardware

- [ ] Windows 10 limpo e Windows 11 limpo: instalar, abrir, desinstalar e reinstalar.
- [ ] Conta padrão e administrativa; aprovação e recusa do UAC.
- [ ] Encerramento forçado e reinício durante BOOST, com restauração na abertura seguinte.
- [ ] Intel, Realtek, Wi-Fi e Ethernet; computador limitado e intermediário.
- [ ] Comparar DNS, MTU e energia antes/durante/depois. Registrar apenas resultados necessários, sem dados pessoais.

## 3. Partidas reais

- [ ] VALORANT e LoL / Vanguard Safe.
- [ ] CS2 / Valve Safe e Trusted Mode normal.
- [ ] Fortnite ou Fall Guys / EAC.
- [ ] Um título BattlEye (PUBG, Rainbow Six, DayZ ou Arma 3).
- [ ] Roblox / Ping, PC e Completo.
- [ ] Releitura das políticas oficiais após patches. Registrar versão do jogo, Windows, NexuFlow, política aplicada, horário e rollback.

Use VALIDATION_RECORD_TEMPLATE.json. Ausência de ban em teste não é aprovação do fornecedor nem garantia futura.

## 4. Assinatura do Windows

- [ ] Certificado Authenticode ou aprovação SignPath.
- [ ] Assinatura válida do app, instalador e motor.
- [ ] Verificar propriedades e Get-AuthenticodeSignature; testar Defender e SmartScreen.
- [ ] Confirmar ordem de assinatura: assinatura Authenticode do instalador ANTES da assinatura do atualizador e do hash final. Não modificar depois.

## 5. Edição Comunidade e dados

- [x] Remover entrada por conta, checkout e consultas de licença do aplicativo principal. Funções avançadas são gratuitas.
- [x] Manter coleção e resgate cosmético locais, sem depender de Firebase, Render ou gateway de pagamento.
- [x] Recusar compilação Comunidade que configure servidor de contas/licença ou inclua as rotas comerciais no JavaScript distribuído.
- [ ] Revisar política de privacidade para refletir diagnósticos, armazenamento local e distribuição de atualizações.
- [ ] Definir contato real para privacidade e incidentes, retenção e procedimento de atendimento.
- [ ] Decidir separadamente o encerramento dos antigos serviços e tratamento das contas de teste. Nenhuma conta ou serviço remoto foi apagado nesta revisão.

Cadastro, cobrança, trial, compartilhamento de assinatura e licenças pagas foram cancelados pelo responsável; não são pendências para esta edição gratuita. O código legado permanece fora da interface distribuída e deve ser separado antes de publicar o fonte.

## 6. Documentação e publicação

- SECURITY.md, TRUST_MANIFEST.md, UAC_E_ASSINATURAS_2.1.md e documentação de rollback já existem; precisam de revisão final e publicação.
- [ ] Canal real e privado para vulnerabilidades; publicar o contato autorizado.
- [ ] Página de download com hashes, limitações e distinção beta/estável.
- [ ] Página de compatibilidade com evidência e data de teste, nunca selos de reteste automáticos sem partidas.
- [ ] Política/termos correspondentes à edição local, sem promessas de sincronização ou serviços comerciais inexistentes.
- [ ] Confirmar licença de todo recurso redistribuído, inclusive áudio enviado pelo responsável.

## 7. Processo de release

- [ ] Executar o novo workflow Quality gates no GitHub; adicionar seu check como obrigatório na branch main.
- [ ] Configurar proteção da branch na conta/plano GitHub disponível (não configurada por editar YAML).
- [ ] Testar o fluxo de release com SBOM, hashes e notas anexados.
- [ ] Registrar versões das ferramentas e hashes; instalador bit a bit determinístico não está demonstrado.
- [ ] Guardar chave privada e senha com recuperação segura, fora do código e dos artefatos.
- [ ] Aprovação humana da matriz física antes de retirar beta. Publicar draft só depois dos testes.

## O que os testes locais cobrem

Regressão de lógica do motor/API, renderização e estado da interface, resgate individual e bloqueios do atualizador usando mocks. Não substituem os itens acima.
