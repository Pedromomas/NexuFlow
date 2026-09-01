# NexuFlow 1.5.7 — Visual Edition

Esta versão reorganiza a experiência visual sem alterar o motor de otimização, as políticas fail-closed ou a superfície anti-cheat.

## O que mudou

- **Aparência ganhou página própria**, com abas Temas e Acessibilidade e atalho `Alt+4`.
- **Oito temas originais:** Nebula, Midnight, Emerald, Alto Contraste, Blocos, Relíquia, Tático e Operação.
- Os quatro temas de atmosfera são marcados como **arte original, não afiliado** e não usam personagens, logos, mapas, runas, armas, agentes ou splash arts de terceiros.
- **Flux**, mascote abstrato original do NexuFlow, aparece discretamente no fundo e muda de atmosfera com o tema. Ele é removido automaticamente no Alto Contraste.
- **Dashboard redesenhado:** o jogo aparece uma única vez; Nexus Score, latência, CPU/RAM e GPU recebem hierarquia clara; o botão BOOST ganhou aparência tátil sem funcionar como spinner permanente.
- Os sinais Conexão, Rota/ISP, PC/Driver e Servidor agora usam estados visuais diferentes para resultado bom, alerta, problema e estado inconclusivo.
- “Confiança sem conclusão” foi preservado: o NexuFlow continua sem afirmar uma causa quando faltam evidências.
- A escala de texto permanece entre 90% e 125% e agora tem uma prévia dedicada.
- Animações são curtas, limitadas a opacidade/transformação e respeitam Movimento reduzido e `prefers-reduced-motion`.

## Segurança preservada

- Nenhuma mudança no engine, nas mutações de rede, no processo do jogo ou na política de anticheat.
- Temas são preferências cosméticas locais em `localStorage` e não são enviados para servidor.
- Nenhum script, endpoint, permissão Tauri ou comando IPC novo foi adicionado para o visual.
- No-Driver Contract, Protected Session Shield, Unknown Game Safe, Riot/Valve/EAC/BattlEye Safe e policy feed Ed25519 continuam ativos.

## Compatibilidade

As preferências das versões anteriores são mantidas. O tema padrão continua Nebula. Instale a 1.5.7 normalmente; não copie arquivos por cima de uma pasta antiga de código-fonte.
