import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import streamlit_antd_components as sac
import Assist_prod


# 1. Carrega o config
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)


def sessionLogout(*args, **kwargs):
    st.session_state["authentication_status"] = None
    st.session_state["username"] = None
    st.session_state["name"] = None
    st.session_state["filial"] = None
    st.rerun()


def requer_role(roles_permitidas: list):
    """Bloqueia acesso se o usuário não tiver a role necessária"""
    roles_usuario = config["credentials"]["usernames"][st.session_state["username"]].get(
        "roles", [])

    if not any(r in roles_permitidas for r in roles_usuario):
        st.error("❌ Você não tem permissão para acessar esta página.")
        st.stop()


st.set_page_config(
    page_title="ESTOQUE ASISTE SJ",
    page_icon="📦",
)

# 2. Cria o autenticador
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],

)

# 3. Renderiza o formulário de login, com maximo de tentativas
try:
    authenticator.login(max_login_attempts=3, single_session=False)
except Exception as e:
    if "Maximum number of login attempts exceeded" in str(e):
        st.error(
            "🔒 Usuário bloqueado por excesso de tentativas. Contate o administrador.")
        st.stop()
    else:
        st.error(f"Erro no login: {e}")
        st.stop()


# 4. Controla o acesso e mostra os menus
if st.session_state.get("authentication_status"):
    authenticator.logout("Sair", "sidebar", key="side_bar",
                         callback=sessionLogout)
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

    with st.sidebar:
        st.title("Navegação")

        menu = sac.menu(
            items=[
                sac.MenuItem('📦Estoque Geral'),
                sac.MenuItem('📝Cadastrar Produto'),
                sac.MenuItem(type='divider'),
                sac.MenuItem('📥Registrar Entrada'),
                sac.MenuItem('📤Registrar Saída'),
                sac.MenuItem('🚚Movimentações'),
                sac.MenuItem(type='divider'),
                sac.MenuItem('✏️Editar itens'),
                sac.MenuItem('📱leitura de codigo de barra'),
                sac.MenuItem('Importar Dados')
            ],
            key='menu_lateral_principal'
        )

    match menu:
        case "📦Estoque Geral":
            Assist_prod.tela_dashboard()
        case "🚚Movimentações":
            Assist_prod.tela_Movimentacoes()
        case "📝Cadastrar Produto":
            Assist_prod.tela_cadastro()
        case "📤Registrar Saída":
            Assist_prod.tela_saidas(loged_User)
        case "📥Registrar Entrada":
            Assist_prod.entrada_Produtos(loged_User)
        case "Importar Dados":
            Assist_prod.upload_csv()
            Assist_prod.exportar_csv()
        case "✏️Editar itens":
            requer_role(["admin"])
            Assist_prod.edição_de_itens()
        case "📱leitura de codigo de barra":
            Assist_prod.qrCode()

elif st.session_state.get("authentication_status") is False:
    st.error("❌ Usuário ou senha incorretos.")

else:
    st.warning("Por favor, faça login")

with open("config.yaml", "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False)
