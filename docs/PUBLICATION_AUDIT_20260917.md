# Revisão de publicação — 17/09/2026

- Histórico Git buscado do repositório oficial antes da revisão.
- Verificação pontual de 453 blobs de texto: nenhum padrão de chave privada, token GitHub/AWS ou token de pagamento encontrado.
- Gitleaks 8.30.1, obtido da release oficial e conferido contra seu checksum: 25 commits analisados. Os 15 alertas são referências a códigos cosméticos e ao digest cosmético do aplicativo, não credenciais de infraestrutura.
- Árvore de publicação analisada com Gitleaks: 9 alertas. Oito são códigos cosméticos em testes; um é a chave Pix publicada por solicitação explícita do titular. Nenhum segredo de autenticação identificado nesses alertas.
- Não são enviados ambientes virtuais, dependências instaladas, logs locais, relatórios de telemetria, arquivos de conta de serviço, chaves privadas nem diretórios de saída. Os documentos locais de configuração pessoal não fazem parte da seleção nova.
- O backend já versionado permanece preservado como histórico; não é carregado pela edição Comunidade nem foi reimplantado nesta publicação.
- A autorização de redistribuição do áudio Origem foi confirmada pelo responsável nesta data.

Limites: a análise não equivale a certificação de ausência de segredos, vulnerabilidades ou direitos de terceiros. Artefatos binários históricos não foram decompilados. Não foi reescrito o histórico nem removida nenhuma release anterior. Relatos de segurança devem seguir SECURITY.md.
