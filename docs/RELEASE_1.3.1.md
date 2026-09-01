# NexuFlow 1.3.1 — Scroll Fix

Patch de interface para janelas menores e páginas longas.

- Restaura scroll vertical com roda do mouse e touchpad no Tauri/WebView2.
- A coluna principal passa a ser o scroll container, mantendo sidebar e hotbar fixas.
- Os botões ↑ e ↓ da hotbar agora controlam a coluna principal, não apenas `window`.
- Adiciona scrollbar discreta e espaço inferior nas páginas longas.
- Respeita a preferência existente de movimento reduzido.
- Nenhuma alteração nas políticas Riot/Vanguard Safe ou Valve/VAC Safe.
