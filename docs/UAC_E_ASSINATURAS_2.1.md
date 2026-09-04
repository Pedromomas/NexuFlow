# UAC, motor elevado e assinaturas

O aviso “Deseja permitir?” da captura é o Controle de Conta de Usuário do Windows. Ele aparece quando `nexus-engine.exe` começa uma sessão que precisa alterar configurações administrativas. Não é uma caixa criada pelo site e não deve ser contornada.

## Comportamento atual

- a janela principal abre sem privilégios administrativos;
- diagnóstico e navegação não pedem elevação;
- BOOST/Central do PC usam o mesmo fluxo e pedem uma autorização ao iniciar uma sessão real de mudanças;
- o helper elevado permanece responsável pelo snapshot e rollback daquela sessão;
- desligar/restaurar dentro da sessão não deve pedir uma segunda autorização;
- desligar, encerrar todo o motor e ativar novamente inicia outra sessão e pode pedir novo consentimento.

## “Fornecedor desconhecido”

Essa linha só desaparece com um certificado Authenticode confiável emitido para o publicador e aplicado a todos os executáveis/instaladores distribuídos. A chave do atualizador Tauri não substitui Authenticode.

## Por que não instalar um atalho silencioso agora

Um serviço permanente ou tarefa elevada poderia reduzir prompts depois de uma autorização na instalação, mas aumentaria a superfície de ataque e o risco de classificação como PUP. Essa arquitetura só deve ser considerada depois de Authenticode, auditoria independente, ACLs estritas, protocolo autenticado e lista fechada de comandos. Até lá, uma autorização explícita por sessão é a política correta.
