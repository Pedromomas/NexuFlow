# NexuFlow 2.1.0-beta.4 — Universos e coleção

Data: 05/09/2026. Distribuição privada. Não é versão estável.

## Implementado

- Perfil de explorador com apelido local, passaporte, contador de descobertas e galeria de insígnias.
- Cada código continua liberando apenas o respectivo tema. Coleção antiga migra sem liberar recompensas extras.
- Origem, Rio e Kiwi têm retratos novos e separados do cenário, insígnias vetoriais originais e companheiros diferentes.
- Avatar do tema equipado aparece na navegação, no perfil e na conta. Recompensa mostra avatar e insígnia no resgate.
- Kiwi: pássaro adulto e filhote com movimentos curtos; Origem: cristal flutuante; Rio: skyline e pulsos de sinal. Movimento reduzido respeitado.
- BOOST usa a assinatura visual do universo. Cosméticos não alteram políticas, configurações do Windows ou licença.
- Atualizador reconsulta o motor antes da consulta, antes do download e antes da instalação; estado desconhecido bloqueia a operação.
- Download separado de instalação. Se uma sessão começar durante a transferência, instalação fica em espera. Retentativa disponível sem instalar após erro.
- Operações concorrentes de BOOST e medições da Central bloqueadas durante consulta/download/instalação no fluxo da interface.
- Metadados de atualização não são mais descritos como pacote já validado. Validação continua pertencendo ao plugin oficial.
- CI de interface/motor em push e PR, erros intermediários interrompem release, Rust testado no fluxo assinado.
- Geração de SBOM com versões efetivas de dependências, hashes e notas anexáveis à release.
- Corrigida a versão interna antiga do motor e removida a comparação fixa com beta.1 no script de build.

## Limitações explícitas

A coleção e o apelido ficam neste computador; não há sincronização online implementada. Os códigos cosméticos são locais e não são mecanismo de licença. Cadastro e pagamentos continuam bloqueados até existir backend HTTPS real e validado.

O repositório continua privado. O aplicativo não recebe um token GitHub e não consegue consumir releases privadas como canal público. Nesta beta, o fluxo de rede do atualizador fica suspenso com explicação na interface. A chave pública existente foi preservada; nenhuma chave privada foi lida, trocada ou publicada.

O instalador local de teste não tem Authenticode nem assinatura de pacote Tauri gerada neste build. Não deve ser usado como atualização de produção. O fluxo do GitHub permanece responsável por gerar artefatos assinados com os segredos cadastrados.

Os testes de atualização desta entrega usam um plugin simulado: verificam estados, bloqueios e reação a falhas, não demonstram um upgrade real nem a verificação criptográfica executada no Windows. Não impedem que alguém abra um jogo externamente no intervalo final entre a última leitura e o início do instalador; esse cenário exige validação de integração e uma trava nativa antes da versão estável.

Sem novas alegações de compatibilidade anticheat ou garantia contra ban. Nenhuma partida real foi executada nesta tarefa.

## Evidência

Consulte o relatório da entrega em outputs/release-evidence, após o build, e a lista em STABLE_GATES.md. Resultados de testes locais não equivalem à execução do GitHub Actions nem à matriz física.

Referência do atualizador: [documentação oficial do Tauri](https://v2.tauri.app/plugin/updater/). A assinatura obrigatória não substitui Authenticode.
