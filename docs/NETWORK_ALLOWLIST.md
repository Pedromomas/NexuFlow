# Allowlist de Rede — 1.6

Regra estrutural: negar por padrão.

| Uso | Destino permitido | Dados enviados |
|---|---|---|
| Interface ↔ motor local | `http://127.0.0.1:8000/api/v1/` | Comandos locais e respostas sanitizadas |
| Qualidade/rota | `1.1.1.1`, `8.8.8.8`, `9.9.9.9` | Sondas DNS/ICMP/TCP sem identificador do usuário |
| Política | Cache local assinado | Nenhum download automático na 1.6 |

Não há analytics, anúncios, login, publicidade ou comando remoto. O navegador valida origem e caminho antes de cada chamada. O motor publica o mesmo contrato no Modo Investigador e os testes falham se a regra local for violada.
