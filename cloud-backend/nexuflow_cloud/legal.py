"""Versioned beta notices; publication requires explicit operational review."""
from html import escape
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()
VERSION = "2026-09-11-draft-1"
CONTACT = "guilhermefudido5@gmail.com"
OWNER = "Pedro Fernandes Bahia Rocha"

TERMS = (
    ("Sobre esta versão", "O NexuFlow está em fase beta. Recursos de conta e integração estão em testes. O Safe Core local pode ser utilizado sem conta. As funções disponíveis dependem da versão instalada e das condições do computador."),
    ("Uso responsável", "Utilize o aplicativo apenas em computadores que você possui ou está autorizado a administrar. Leia os ajustes antes de ativá-los e mantenha cópias dos seus dados importantes. Autorizações administrativas são solicitadas pelo Windows quando necessárias."),
    ("Desempenho e jogos", "Não há promessa de aumento específico de FPS, redução de ping ou ausência de banimento. Os perfis de compatibilidade não representam certificação ou aprovação dos fabricantes dos jogos ou dos sistemas anticheat. Interrompa o uso e procure suporte se houver comportamento inesperado."),
    ("Conta e códigos", "Proteja sua senha e confirme seu e-mail. Não compartilhe a senha com amigos: quando disponível, o compartilhamento usa contas separadas. Códigos podem ter prazo de resgate, duração de acesso e restrições informados antes do uso. A concessão de acesso depende da validação no servidor."),
    ("Pagamentos", "A cobrança real está desativada nesta etapa. Preços exibidos e testes de integração não significam que uma assinatura foi adquirida. Antes de disponibilizar vendas, serão informados preço total, duração, renovação, cancelamento e regras de reembolso. Não envie dinheiro ou dados de cartão por e-mail para ativar recursos."),
    ("Atualizações", "Use somente os canais oficiais indicados pelo projeto. Atualizações podem corrigir falhas e alterar funcionalidades. A assinatura de um pacote não substitui os testes de compatibilidade; não desative as verificações de segurança para instalar uma atualização."),
    ("Direitos e atendimento", "Estes termos não afastam direitos previstos na legislação aplicável. Dúvidas, problemas, solicitações de conta e questões de privacidade podem ser encaminhados ao contato abaixo. Não envie senhas, chaves privadas ou números completos de cartão."),
)

PRIVACY = (
    ("Responsável e escopo", "Este aviso descreve a integração de contas da versão beta do NexuFlow. O responsável e o canal de atendimento estão identificados abaixo. O uso local sem conta não exige cadastro no serviço de contas."),
    ("Dados da conta", "O cadastro utiliza nome de exibição, e-mail e senha. A senha transita por HTTPS pelo backend para autenticação no Firebase; não é gravada no banco de perfis pelo código do NexuFlow. Não devemos afirmar que a senha nunca passa pelo servidor próprio. O Firebase administra as credenciais de autenticação."),
    ("Perfil e acesso", "O banco pode registrar identificador de usuário, confirmação de e-mail, datas de cadastro e acesso concedido, período de teste, resgates de códigos e vínculos de compartilhamento. Esses dados permitem manter a conta e verificar os recursos disponíveis. A verificação de licença pode receber um token de instalação; isso não equivale a um identificador impossível de falsificar."),
    ("Registros de segurança", "Requisições podem gerar registros de horário, endereço de rede, rota e resultado no provedor de hospedagem. O controle de tentativas usa identificadores derivados de dados de rede e conta, além de contadores. Identificadores pseudonimizados não são necessariamente anônimos."),
    ("Serviços utilizados", "Firebase Authentication e Firestore, do Google, sustentam autenticação e dados de conta. O backend está hospedado no Render. O ambiente atual do Render está nos Estados Unidos e o Firestore configurado em São Paulo; outros componentes e suboperadores podem tratar dados em outros países. Os mecanismos aplicáveis às transferências internacionais precisam ser revisados antes do lançamento público."),
    ("Pagamentos em teste", "Pagamentos reais estão desativados. A integração PagBank está em preparação para testes separados das licenças reais. O checkout planejado é hospedado pelo provedor; não envie dados reais de cartão durante testes nem por e-mail. As condições e informações de privacidade de pagamentos serão atualizadas antes da abertura de vendas."),
    ("Retenção e exclusão", "A conta e o perfil são mantidos para disponibilizar o serviço. A rotina de exclusão remove a identidade de autenticação e o perfil, mas determinados registros de pedidos, códigos e segurança podem permanecer com identificadores derivados. Isso não garante anonimização nem remoção imediata de backups. Os prazos por categoria e a rotina de limpeza ainda precisam de validação operacional antes da publicação deste aviso."),
    ("Seus direitos", "Você pode solicitar informações sobre o tratamento, acesso, correção e, quando aplicável, exclusão, portabilidade e revisão de decisões automatizadas. Use o contato abaixo; pode ser necessária uma confirmação proporcional de identidade para proteger sua conta. Os direitos e suas condições são explicados pela ANPD no link ao final."),
    ("Segurança e mudanças", "A integração utiliza HTTPS, autenticação e restrições de acesso. Nenhuma medida garante risco zero. Este aviso deve ser atualizado quando houver mudança relevante no tratamento de dados. Não envie senhas ou chaves privadas ao suporte."),
)


def document(kind: str) -> str:
    title, sections = ("Termos de Uso — Beta", TERMS) if kind == "terms" else ("Política de Privacidade — Beta", PRIVACY)
    content = "".join(f"<section><h2>{escape(heading)}</h2><p>{escape(body)}</p></section>" for heading, body in sections)
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} | NexuFlow</title>
<style>body{{font:1rem/1.65 system-ui,sans-serif;margin:0;background:#10151d;color:#edf2fa}}main{{max-width:800px;margin:auto;padding:28px 22px;overflow-wrap:anywhere}}a{{color:#a8e8ff}}a:focus-visible{{outline:3px solid #a8e8ff;outline-offset:4px}}h1,h2{{line-height:1.3}}h2{{font-size:1.2rem;margin-top:2rem}}aside{{border:1px solid #e9ba68;padding:16px;border-radius:12px}}footer{{border-top:1px solid #687787;margin-top:32px;padding-top:20px}}</style></head>
<body><main><nav aria-label="Documentos"><a href="/legal/terms">Termos</a> · <a href="/legal/privacy">Privacidade</a></nav>
<h1>{title}</h1><aside>Rascunho para revisão — não aprovado para abertura pública de cadastros ou vendas. Versão {VERSION}.</aside>
{content}<footer><p>Responsável: {escape(OWNER)}<br>Suporte e privacidade: <a href="mailto:{CONTACT}">{CONTACT}</a></p>
<p><a href="https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares">Orientações da ANPD sobre direitos dos titulares</a></p></footer></main></body></html>'''


def response(kind: str) -> HTMLResponse:
    # Fail closed until retention, cross-border processing and text are reviewed.
    if os.getenv("NEXUFLOW_LEGAL_REVIEW_PREVIEW", "false") != "true":
        raise HTTPException(status_code=503, detail="Documentos em revisão. Cadastro público ainda não liberado.")
    return HTMLResponse(document(kind), headers={
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
    })


@router.get("/legal/terms", response_class=HTMLResponse)
def terms() -> HTMLResponse:
    return response("terms")


@router.get("/legal/privacy", response_class=HTMLResponse)
def privacy() -> HTMLResponse:
    return response("privacy")
