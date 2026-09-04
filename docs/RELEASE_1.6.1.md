# NexuFlow 1.6.1 — Polish Edition

## O que mudou

- Acessibilidade: “Ver papel de parede” exibe a arte inteira, esconde menus e cartões e abre tela cheia quando disponível. Esc ou Voltar restaura a interface. A sessão de BOOST continua no estado em que estava.
- A Arte Secreta agora usa somente a capa original enviada no modo papel de parede, sem sobreposição do mascote, texturas ou cartões.
- Bandeja do Windows: Abrir NexuFlow, Ocultar na bandeja e Sair — restaurar e encerrar. O X da janela também pede encerramento com restauração. Para continuar em segundo plano, use Ocultar na bandeja.
- O encerramento espera as operações de BOOST em andamento e exige confirmação de que o motor parou e não há restauração pendente. Se não conseguir, mantém a janela disponível para tentar novamente.
- Código secreto: depois do resgate, “Resgatar outro código” abre o campo novamente. Não há novos códigos cosméticos nesta versão.
- O primeiro resgate válido ganhou uma celebração em tela cheia inspirada em conquistas de videogame. Ela é finita, fecha pelo botão ou Esc e respeita Movimento reduzido.
- “Ver em Aparência”, “Resgatar outro código” e “Fechar códigos” agora compartilham altura, margem e alinhamento.
- Para testar os resgates do zero, digite `RESET-CODIGOS` no mesmo campo e clique em Resgatar. Remove somente o desbloqueio cosmético; preserva histórico, token, escala de texto e modo de BOOST. Se o tema secreto estiver ativo, volta ao Nebula.
- Card do mascote com texto centralizado verticalmente e imagem contida. A Arte Secreta usa “Conheça o João” e o PNG transparente existente; os demais temas apresentam o Flux.

## Limites

O desbloqueio continua sendo um easter egg local, não um mecanismo de sigilo ou controle de acesso. Nenhuma promessa de compatibilidade ou risco zero de ban é adicionada nesta atualização. Os executáveis locais continuam sem assinatura Authenticode comercial.

## Validação desta edição

- 116 testes Python do motor/API aprovados; um aviso de depreciação do cliente de testes, sem falha.
- 11 testes da interface aprovados, incluindo reset, novo resgate e retorno de tela cheia quando o navegador recusa a solicitação.
- Teste Rust aprovado: encerramento recusado quando a resposta é incompleta, contém falha, motor ativo ou restauração pendente.
- Interface conferida no navegador: João alinhado, arte sem menus, retorno com Esc e reset dos resgates.
- Auditorias estáticas anti-cheat, No-Driver Contract e allowlist de rede aprovadas.

O clique no ícone da bandeja do aplicativo instalado e um ciclo de saída com BOOST ativo precisam de smoke test no Windows. Os testes acima não substituem um reteste com jogos/anticheats nem certificam ausência de vulnerabilidades.

## Uso

Instale o novo instalador com a versão anterior fechada. Para desenvolvimento, extraia o pacote Source em uma pasta própria, execute `scripts/setup.ps1 -Desktop` e `scripts/dev.ps1`. O ícone da bandeja existe no aplicativo Windows; o preview de navegador usa os recursos visuais.

A bandeja usa a [API nativa do Tauri](https://v2.tauri.app/learn/system-tray/), sem serviço residente instalado nem permissões de shell adicionadas à interface.
