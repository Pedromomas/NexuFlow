# Instalação — NexuFlow 1.5.5 Driver Edition

## Para usar o aplicativo

1. Extraia `NexuFlow-1.5.5-DriverEdition.zip` em uma pasta nova.
2. Abra `NexuFlow-1.5.5-Setup.exe`.
3. Conclua a instalação e abra o NexuFlow pelo Menu Iniciar.

Não extraia por cima da pasta 1.4.2/1.5.0 e não copie arquivos manualmente. O instalador atualiza o aplicativo corretamente. Preferências compatíveis são migradas; a pasta antiga pode ser mantida temporariamente como backup.

Este build local ainda não possui certificado comercial, portanto o Windows pode mostrar **Fornecedor desconhecido**. Confira o SHA-256 publicado junto do ZIP. O UAC não é desativado nem contornado.

## Para abrir o código no VS Code

1. Extraia `NexuFlow-1.5.5-DriverEdition-Source.zip` em uma pasta nova.
2. Abra `NexuFlow.code-workspace`.
3. No terminal do VS Code execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1 -Desktop
.\scripts\dev.ps1
```

Para gerar um instalador novo:

```powershell
.\scripts\build.ps1
```

## Central de drivers

Em **Ajustes → Central de drivers**, clique em **Verificar drivers**. O resultado vem do Windows Update. Para atualizar, use **Abrir atualizações oficiais**, revise os itens e confirme no próprio Windows. O NexuFlow não instala driver sozinho.

Os arquivos de manifesto, hash e SBOM são para verificação/auditoria. O usuário comum precisa somente do ZIP do aplicativo e do instalador.
