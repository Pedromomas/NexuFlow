# NexuFlow — documentação resumida

Versão atual de testes: **2.1.0-beta.3 — Portas Abertas**

## O que é o NexuFlow

O NexuFlow é um aplicativo para Windows criado para ajudar jogadores a entender a conexão, acompanhar o desempenho do computador e aplicar otimizações temporárias e reversíveis.

O aplicativo não promete acabar completamente com o lag e não altera o código dos jogos.

## O que existe no projeto

### BOOST

- prepara o computador e a conexão para jogar;
- possui modos Ping, PC, Completo e Hardcore Safe;
- detecta jogos automaticamente;
- mostra resposta visual imediata ao ligar ou desligar;
- cria um snapshot antes de alterar o Windows;
- restaura as configurações quando o BOOST é encerrado.

### Proteção para jogos

- possui regras específicas para Vanguard, VAC, EAC e BattlEye;
- usa um perfil mais restrito quando encontra um jogo protegido;
- não lê memória do jogo;
- não injeta DLL ou código;
- não utiliza driver próprio;
- não intercepta ou modifica pacotes da partida;
- não altera arquivos ou serviços do anticheat;
- jogos desconhecidos entram em modo conservador automaticamente.
- Roblox usa apenas ajustes comuns e reversíveis do Windows/rede conforme Ping, PC ou Completo, sem alterar o cliente do jogo.

O Safe Core é obrigatório e não depende do botão da Central do PC. Desligar a automação significa somente que não existe otimização ativa.

### Central de Conexão

- mostra ping, jitter, perda de respostas e picos;
- apresenta um gráfico com as amostras recentes;
- compara referências diferentes da internet;
- testa provedores DNS sem trocar o DNS durante a medição;
- possui comparação DNS ao vivo por até 60 segundos;
- oferece teste aproximado de download e upload;
- permite exportar um relatório local.

### Central do PC

- mostra memória disponível e uso da CPU;
- consulta a temperatura da GPU quando o sensor está disponível;
- mostra o estado do Modo de Jogo e do plano de energia;
- inicia uma automação segura pelo mesmo motor do BOOST;
- não encerra programas automaticamente;
- não controla ventoinhas;
- não apaga arquivos;
- não desativa silenciosamente a Game Bar.

### Jogos e histórico

- catálogo de jogos monitorados;
- detecção de jogos instalados e em execução;
- lista de favoritos;
- histórico local das sessões;
- comparação das medições antes e depois;
- painel Investigador para mostrar o que o NexuFlow fez.

### Drivers e saúde do Windows

- consulta atualizações oferecidas pelo Windows Update;
- não baixa drivers de sites desconhecidos;
- não instala drivers sem confirmação;
- mostra informações de rede, GPU, energia e memória;
- apresenta sinais simples de possíveis microtravadas.

### Aparência e acessibilidade

- oito temas públicos;
- ajuste do tamanho do texto;
- alto contraste;
- opção de reduzir animações;
- visualização limpa da arte em tela cheia;
- sistema de códigos cosméticos locais;
- áudio especial ao desbloquear a coleção secreta.

## O que foi acrescentado na atualização 2.1 beta

### Auditoria da versão 1.7

- pacote original conferido usando SHA-256;
- 194 arquivos verificados sem divergência;
- proteções anticheat comparadas com a versão atual;
- auditores de segurança e de rede executados novamente;
- proteção automática confirmada como independente da interface.
- 271 testes do motor/API e 1 teste do host desktop aprovados na beta 3;
- matriz completa dos quatro objetivos públicos executada para Riot, Valve, EAC, BattlEye, Roblox e jogos desconhecidos;
- políticas oficiais relidas em 04/09/2026, sem alegar certificação ou risco zero.

### Central do PC reformulada

- novo controle visual próprio, substituindo o botão circular reaproveitado;
- estado ligado, desligado e preparando mais fácil de entender;
- aviso destacado de que o Safe Core está sempre ativo;
- explicação simples das etapas Detectar, Preparar, Acompanhar e Restaurar;
- texto correto sobre a confirmação administrativa do Windows.

### Segurança durante a troca de jogos

- se um jogo protegido abrir durante um BOOST comum, o NexuFlow restaura primeiro a sessão anterior;
- somente depois da restauração o perfil protegido é iniciado;
- runtime genérico EAC ou BattlEye mantém o sistema em modo restrito quando o jogo não pode ser identificado com segurança.

### Central de Atualizações

- novo cartão de atualização nos Ajustes;
- botão Verificar agora;
- barra de notificação para quando existir uma versão nova;
- atualização adiada durante BOOST ou partida protegida;
- integração preparada para pacotes assinados;
- configuração incompleta permanece bloqueada, sem instalar pacote não assinado.

A atualização automática pública ainda depende da chave definitiva, do GitHub Releases e dos testes reais de atualização entre versões.

### Novas artes secretas

- Edição Origem reformulada em formato amplo;
- novo tema Rio Pulse;
- novo tema Kiwi Signal;
- cores, fundos, painéis, navegação e detalhes mudam de acordo com cada universo;
- imagens convertidas para WebP para reduzir o peso;
- temas continuam totalmente cosméticos e não alteram o funcionamento do BOOST.

Na beta.2, cada coleção também recebeu uma segunda arte própria, símbolo da marca e ícones exclusivos. A interface deixa de reutilizar a mesma identidade visual entre os três códigos.

### Entrada, login e cadastro

- nova tela de boas-vindas inspirada em produtos gamer, mas com visual e arte originais do NexuFlow;
- oferece Entrar, Criar conta e Continuar com o Safe Core;
- Safe Core permanece gratuito e não exige conta;
- cadastro e login só são habilitados quando backend HTTPS, Termos e Política de Privacidade estiverem configurados;
- enquanto essa infraestrutura externa não existe, nenhum cadastro falso é gravado localmente e nenhuma senha é enviada.

### Melhorias gerais

- versão atualizada para 2.1.0-beta.3;
- corrigido o carregamento do CSS no aplicativo instalado e adicionada uma barreira automatizada contra esse tipo de pacote quebrado;
- projeto do VS Code configurado para ignorar pastas pesadas de compilação;
- código-fonte empacotado sem caches e arquivos temporários;
- novo instalador e novo pacote de código-fonte gerados;
- testes da interface, motor, API e host desktop aprovados.

## Estado atual

Esta versão pode ser usada para testes locais. Antes de uma distribuição comercial ainda são necessários assinatura digital Authenticode, canal oficial de atualização, testes em instalações limpas do Windows e validação presencial com jogos protegidos atuais.

Pagamento, contas, assinatura e trial ainda não foram implementados como sistema real. Essas funções dependem de backend, Mercado Pago, domínio, política de privacidade e testes próprios de segurança.
