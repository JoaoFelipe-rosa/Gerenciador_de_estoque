import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import streamlit_antd_components as sac
import Assist_prod

# ============================================================================================================
# 1. PUXA A CONFIGURAÇÃO DO YAML
# ============================================================================================================
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)


def requer_role(roles_permitidas: list):
    """Bloqueia acesso se o usuário não tiver a role necessária"""
    roles_usuario = config["credentials"]["usernames"][st.session_state["username"]].get(
        "roles", [])

    if not any(r in roles_permitidas for r in roles_usuario):
        st.error("❌ Você não tem permissão para acessar esta página.")
        st.stop()


def is_admin():
    return "admin" not in st.session_state.get("roles", [])


st.set_page_config(
    page_title="ASSISTENTE DE ESTOQUE",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ============================================================================================================
# 2. Cria o autenticador
# ============================================================================================================
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],

)
# ============================================================================================================
# 3. Renderiza o formulário de login, com maximo de 3 tentativas
# ============================================================================================================
try:
    authenticator.login(max_login_attempts=3, single_session=False,)
except Exception as e:
    if "Maximum number of login attempts exceeded" in str(e):
        st.error(
            "🔒 Usuário bloqueado por excesso de tentativas. Contate o administrador.")
        st.stop()
    else:
        st.error(f"Erro no login: {e}")
        st.stop()

# ============================================================================================================
# 4. Controla o acesso e mostra os menus diferenciando usuarios de admins
# ============================================================================================================
if st.session_state.get("authentication_status"):
    authenticator.logout("Sair", "sidebar", key="side_bar")
    st.title(f"**VOCE ESTA NO AMBIENTE DE DESENVOLVIMENTO**",)
    st.write(f"Bem-vindo, **{st.session_state['name']}**!")

    loged_User = st.session_state['name']
    username = st.session_state["username"]
    filial = config.get("filiais", {}).get(username)

    if not filial:
        st.error(
            "❌ Seu usuário não possui filial cadastrada. Contate o administrador.")
        st.stop()

    if "filial" not in st.session_state:
        st.session_state["filial"] = filial
# ==================================================================================================================================================================
 # MENU LATERAL
# ==================================================================================================================================================================
    with st.sidebar:
        st.title("**ENV DEV**")
        st.title("Navegação")

        itens_menu: list = [
            sac.MenuItem('Estoque Geral', icon="bi bi-box2"),
            sac.MenuItem(type='divider'),
            sac.MenuItem('Movimentações', icon="bi bi-truck"),
            sac.MenuItem('Pedidos', icon="bi bi-cart"),
        ]

        if not is_admin():
            adminrole = True
            itens_menu.append(sac.MenuItem(type='divider'))
            itens_menu.append(sac.MenuItem("Admin", icon="bi bi-tools", children=[
                sac.MenuItem('Editar itens', icon="bi bi-pencil-square"),
                sac.MenuItem('Cadastrar Produto',
                             icon="bi bi-clipboard-plus"),
                sac.MenuItem('Importar e exportar Dados',
                             icon="bi bi-floppy"),
                sac.MenuItem('Leitor', icon="bi bi-upc-scan")
            ]))

        menu = sac.menu(items=itens_menu, key='menu_lateral_principal')

    match menu:
        case "Estoque Geral":
            Assist_prod.tela_dashboard()
        case "Movimentações":
            Assist_prod.tela_Movimentacoes(loged_User)
        case "Cadastrar Produto":
            requer_role(["admin"])
            Assist_prod.tela_cadastro()
        case "Pedidos":
            Assist_prod.tela_pedidos()
        case "Importar e exportar Dados":
            requer_role(["admin"])
            Assist_prod.upload_csv()
            Assist_prod.exportar_csv()
        case "Editar itens":
            requer_role(["admin"])
            Assist_prod.edição_de_itens(is_admin)
        case "Leitor":
            Assist_prod.QR_Reader()


elif st.session_state.get("authentication_status") is False:
    st.error("❌ Usuário ou senha incorretos.")

else:
    st.warning("Por favor, faça login")

with open("config.yaml", "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False)
