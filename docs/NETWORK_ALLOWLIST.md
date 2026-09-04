# Allowlist de Rede — 1.7

Regra estrutural: negar por padrão.

| Uso | Destino permitido | Dados enviados |
|---|---|---|
| Interface ↔ motor local | `http://127.0.0.1:8000/api/v1/` | Comandos locais e respostas sanitizadas |
| Qualidade/rota | `1.1.1.1`, `8.8.8.8`, `9.9.9.9` | Sondas DNS/ICMP/TCP sem identificador do usuário |
| DNS Lab (sob demanda) | `1.1.1.1`, `1.0.0.1`, `8.8.8.8`, `8.8.4.4`, `9.9.9.9`, `149.112.112.112`, UDP/53 | Consultas a `example.com`, `www.microsoft.com`, `www.cloudflare.com`; não envia histórico de navegação |
| Teste rápido de velocidade (clique explícito) | `https://speed.cloudflare.com/__down` e `/__up` | Até 30 MiB por execução. O servidor recebe o IP público necessário à conexão; o NexuFlow não envia o resultado |
| Política | Cache local assinado | Nenhum download automático na 1.6 |

Não há analytics, anúncios, login, publicidade ou comando remoto. O navegador valida origem e caminho antes de cada chamada. O motor publica o mesmo contrato no Modo Investigador e os testes falham se a regra local for violada.

O scanner da 1.7 aceita apenas as três referências fixas, sem parâmetro de destino externo. Provedores de DNS e referências de internet recebem o IP de origem necessário à conexão normal; o NexuFlow não o inclui no relatório exportado. Abrir ajustes de rede no Windows não troca DNS nem aplica rotas.
