# GitHub — cadastro da assinatura do atualizador

## Caminho recomendado: ambiente protegido

1. Abra o repositório `Pedromomas/NexuFlow` no GitHub com a conta proprietária.
2. Entre em **Settings > Environments**.
3. Crie um ambiente chamado exatamente `signed-release`.
4. Em **Environment secrets**, adicione `TAURI_SIGNING_PRIVATE_KEY` com o conteúdo completo de `C:\Users\pf093\Documents\NexuFlow-Secrets\nexuflow-updater.key`.
5. Adicione `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` com a senha da chave.
6. Quando disponível no plano do GitHub, configure aprovação obrigatória antes de o ambiente liberar os segredos.

O `GITHUB_TOKEN` não precisa ser criado manualmente; o GitHub Actions fornece um token temporário ao workflow.

## Alternativa válida

Os mesmos nomes podem ficar em **Settings > Secrets and variables > Actions > Repository secrets**. O workflow atual também os encontra. O ambiente protegido é preferível porque limita o uso ao job de release e pode exigir aprovação.

## Conferência sem revelar valores

A página do GitHub deve mostrar somente os nomes dos segredos e a data da última alteração. O valor não pode ser exibido novamente. Nunca colocar a chave privada em variável comum, arquivo versionado, issue, log ou mensagem.

## Se o repositório não abrir

Se `https://github.com/Pedromomas/NexuFlow` mostrar 404 mesmo com a conta correta conectada, o repositório ainda não foi criado ou o nome/proprietário está diferente. Criar primeiro um repositório vazio chamado `NexuFlow`; não marcar README, licença ou `.gitignore`, porque o projeto local já contém seus próprios arquivos.

## Depois dos segredos

1. enviar o código e o workflow ao GitHub;
2. abrir **Actions > Release assinada do NexuFlow > Run workflow**;
3. gerar uma versão N e outra N+1 como draft;
4. instalar N em uma máquina de teste;
5. publicar N+1 e confirmar aviso, download, assinatura e instalação;
6. publicar intencionalmente um artefato de laboratório com assinatura inválida em um canal isolado e confirmar recusa;
7. somente depois usar o canal com usuários reais.

## Incidente antes da primeira release

Se a senha for criada por engano como `Environment variable`, ela fica visível e deve ser considerada exposta. Apague a variável, gere um novo par antes da primeira release e cadastre chave e senha novas somente em `Environment secrets`. Como nenhuma base instalada ainda confia nessa chave, a rotação pré-lançamento não quebra atualizações existentes.
