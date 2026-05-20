import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import streamlit_antd_components as sac
import Assist_prod


# 1. Carrega o config
with open("config.yaml", encoding="utf-8") as f:
    config = yaml.load(f, Loader=SafeLoader)

# 2. Cria o autenticador
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# 3. Renderiza o formulário de login
authenticator.login()

# 4. Controla o acesso
if st.session_state.get("authentication_status"):
    authenticator.logout("Sair", "sidebar")
    st.write(f"Bem-vindo, **{st.session_state['name']}**!")
    loged_User = st.session_state['name']
    with st.sidebar:
        st.title("Navegação")

        # Adicionamos uma key única aqui para forçar o Streamlit a isolar o componente
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
            key='menu_lateral_principal'  # <--- ADICIONE ISSO
        )

    # Corrigindo seus cases (removendo os emojis no match se necessário,
    # ou mantendo igual ao texto do MenuItem)
    match menu:
        # Nota: O retorno do sac vem exatamente como o texto do MenuItem (com emoji)
        case "📦Estoque Geral":
            Assist_prod.tela_dashboard()
        case "🚚Movimentações":
            Assist_prod.tela_Movimentacoes()
        case "📝Cadastrar Produto":
            Assist_prod.tela_cadastro()
        case "📤Registrar Saída":
            Assist_prod.tela_saidas(loged_User)
        case "📥Registrar Entrada":
            Assist_prod.entrada_Produtos()
        case "Importar Dados":
            Assist_prod.upload_csv()
        case "✏️Editar itens":
            Assist_prod.edição_de_itens()
        case "📱leitura de codigo de barra":
            Assist_prod.qrCode()

elif st.session_state.get("authentication_status") is False:
    st.error("Usuário ou senha incorretos")

else:
    st.warning("Por favor, faça login")

# 5. IMPORTANTE: salva o config atualizado (hashes gerados)
with open("config.yaml", "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False)
