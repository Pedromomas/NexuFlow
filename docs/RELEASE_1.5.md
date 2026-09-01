# NexuFlow 1.5.0 — Latency Lab

## O que mudou

- **Nexus Latency Lab:** separa sinais de conexão/rede local, rota/provedor, pressão do PC/driver e servidor/jogo. A conclusão traz confiança e limitações; não soma números incompatíveis nem promete uma causa sem evidência.
- **NIC Health:** consulta Energy Efficient Ethernet, Receive Side Scaling e Interrupt Moderation. É diagnóstico somente leitura; nenhuma propriedade da placa é alterada automaticamente.
- **Windows Gaming Health:** informa o estado do Game Mode e resume preferências de GPU sem exportar caminhos pessoais.
- **Stutter Health:** mede pressão agregada de CPU, memória, disco, trocas de contexto e interrupções. A camada ETW fica documentada como capacidade futura; a versão estável não inicia trace profundo.
- **Session Guard Advisor:** aponta somente nomes conhecidos de programas em segundo plano. Não fecha programas nem muda prioridade. Durante jogo protegido, a própria leitura é adiada.
- **Política Ed25519 disable-only:** o cliente contém apenas a chave pública. Uma política assinada pode desativar recursos e exibir alertas; nunca habilita recursos, executa comandos ou torna uma ação invasiva permitida. Versão monotônica, expiração, tamanho máximo e JSON estrito bloqueiam rollback e payload ambíguo.
- **Sinais de serviço EAC/BattlEye:** uma instância em execução força o perfil protegido mesmo para jogo ainda ausente do catálogo. `vgk`/`vgc` instalados permanecem apenas como evidência ambiental e não travam o PC sem um jogo Riot ativo.
- **PowerShell lockdown global:** `powershell.exe` e `pwsh.exe` são bloqueados antes da criação do processo durante qualquer sessão protegida. Rollbacks essenciais usam clientes nativos (`netsh`, `sc.exe`, `powercfg`) ou são adiados com segurança.
- **IPC mínimo:** somente Ping, PC, Completo e Hardcore Safe atravessam a API pública. Perfis internos/legados não podem ser solicitados pela WebView.
- **Privacidade padrão:** telemetria e histórico ficam locais; o relatório exportado remove token, PID e caminhos pessoais.

## Modos públicos

- **Ping:** mede a conexão e usa somente ajustes de rede permitidos fora de sessões protegidas.
- **PC:** usa apenas ajustes gerais reversíveis do Windows que a política permitir.
- **Completo:** combina Ping e PC; recomendado para uso normal.
- **Hardcore Safe:** diagnóstico e relatório, sem mutação.

Riot Safe, Valve Safe, EAC/BattlEye Safe e Unknown Game Safe são proteções automáticas, não opções para contornar o anticheat.

## O que não foi prometido

ExitLag/NoPing dependem de uma rede mundial de relays e túnel/multipath. A 1.5 não intercepta tráfego e não apresenta diagnóstico local como “rota mágica”. Alterações automáticas de EEE/RSS/Interrupt Moderation, prioridade de programas e trace ETW profundo ficaram fora do release estável até existir validação ampla por hardware, consentimento granular e rollback comprovado.

## Segurança da distribuição

O release inclui instalador, SBOM CycloneDX, manifesto SHA-256 e hash do ZIP. O script de release executa testes, auditoria anti-cheat, No-Driver Contract e build antes do empacotamento. Um build local sem certificado ainda aparece como **Fornecedor desconhecido** no UAC; hashes não substituem assinatura comercial, mas permitem verificar integridade.

