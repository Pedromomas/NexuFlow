# Render Free: ambiente de desenvolvimento

Root Directory: `cloud-backend`
Build Command: `pip install .`
Start Command: `uvicorn nexuflow_cloud.main:app --host 0.0.0.0 --port $PORT`
Instance Type: **Free**. Python: 3.12 ou superior.
Health Check Path: `/health`.

Mantenha `NEXUFLOW_API_ENABLED=false` e `MERCADO_PAGO_LIVE_MODE=false`.
O processo inicia sem credenciais e `/health` responde 200. Todas as rotas
`/v1/` respondem 503 enquanto a API estiver desativada. Isso nao comprova
login nem pagamento funcionando. Nao conectar usuarios reais nesta etapa.

Antes de habilitar: configurar Firebase Admin com identidade de servico no
Render, variaveis de `.env.example`, chave Ed25519 propria da licenca,
Mercado Pago de TESTE e validar os fluxos completos. Nunca enviar senhas,
chaves privadas ou JSON de conta de servico ao repositorio.

O Render nao fornece automaticamente a identidade Firebase do Cloud Run.
Firestore continua como persistencia; nao usar disco local para contas.
O plano gratuito pode suspender o processo por inatividade.

Teste local: `pip install .[test]` e `python -m pytest`.
26 testes e 23 subtestes passaram localmente em 2026-09-05, com mocks nas
integracoes HTTP. Testes reais de Firebase e Mercado Pago ainda pendentes.
