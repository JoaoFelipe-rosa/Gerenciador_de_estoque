import json

import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from datetime import datetime
from dbManager import InventorySystem
import cv2
from pyzbar import pyzbar

# ---------------------------------------------------------------------------
# BANCO DE DADOS
# ---------------------------------------------------------------------------
if 'repo' not in st.session_state:
    st.session_state.repo = InventorySystem()

repo = st.session_state.repo

st.set_page_config(
    page_title="ESTOQUE ASISTE SJ",
    page_icon="📦",
)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def buscar_nome_produto(cod):
    if cod == 0:
        return "Insira um codigo de produto"
    resultado = repo.db_estoque_SJ.read(
        "SELECT nome FROM Produtos WHERE cod_prod = ?", (cod,))

    if resultado is not None and not resultado.empty:
        return resultado.iloc[0, 0]
    return None


def tela_cadastro():
    st.title("📦 Cadastro de Produtos")

    with st.form("form_cadastro"):
        cod = st.number_input("Código do Produto", step=1)
        EAN = st.number_input("EAN", step=1)
        nome = st.text_input("Nome do Produto")
        valor = st.number_input("Preço Unitário", format="%.2f")
        local = st.text_input("Localização (Prateleira/Corredor)")

        if st.form_submit_button("Salvar"):
            try:
                repo.db_estoque_SJ.write(
                    "INSERT INTO Produtos (cod_prod, EAN, nome, valor, localizacao) VALUES (?, ?, ?, ?,?)",
                    (cod, EAN, nome, valor, local)
                )
                st.success("Produto cadastrado com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")


def tela_saidas():
    st.title("📤 Saida de Estoque")
    cod_input = st.number_input(
        "Código do Produto", step=1, min_value=0, key="cod_saida")
    cod_input = int(cod_input)
    nome_produto = buscar_nome_produto(cod_input)
    st.write("Produto selecionado:")
    st.write(f"{nome_produto}")

    qtd_input = st.number_input(
        "Quantidade a tirar", min_value=1, key="qtd_saida")
    value_input = st.number_input(
        "Valor Unitário (R$)", min_value=0.0, step=0.01, key="val_saida")
    user_input = st.text_input(
        "Usuario que retirou:", key="User_saida")

    if st.button("Confirmar Saida"):
        repo.registrar_Movimentacao(
            cod_input, qtd_input, 'Saida', value_input, user_input)
        repo.db_estoque_SJ.write(
            "UPDATE Produtos SET quantidade = quantidade - ? WHERE cod_prod = ? AND quantidade >= ?",
            (qtd_input, cod_input, qtd_input)
        )
        st.success("Estoque atualizado!")


def tela_dashboard():
    st.title("📦 Estoque")

    # Lendo dados de bancos diferentes
    df_estoque = repo.db_estoque_SJ.read(
        "SELECT * FROM Produtos WHERE quantidade >= 1")

    pesquisa = st.text_input(
        "🔍 Pesquisar", placeholder="Digite para buscar...")

    if pesquisa:
        mask = df_estoque.apply(lambda col: col.astype(
            str).str.contains(pesquisa, case=False, na=False)).any(axis=1)
        df_filtrado = df_estoque[mask]
    else:
        df_filtrado = df_estoque.iloc[:, 1:]

    st.dataframe(
        df_filtrado,
        width="stretch",
        hide_index=True,
        column_config={
            "valor": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f"),
            "quantidade": st.column_config.NumberColumn("Qtd. em Estoque"),
            "cod_prod": "Código do Produto",
            "nome": "Descrição do Produto",
            "localizacao": "Local"
        })


def entrada_Produtos():
    st.title("📥 Entrada de Estoque")
    # Exemplo rápido de campos para entrada
    cod_input = st.number_input(
        "Código do Produto", step=1, min_value=0, key="cod_entrada")
    cod_input = int(cod_input)
    nome_produto = buscar_nome_produto(cod_input)
    st.write("Produto selecionado:")
    st.write(f"{nome_produto}")

    qtd_input = st.number_input(
        "Quantidade a Adicionar", min_value=1, key="qtd_entrada")
    value_input = st.number_input(
        "Valor Unitário (R$)", min_value=0.0, step=0.01, key="val_entrada")
    user_input = st.text_input(
        "Usuario:", key="User_entrada")

    if st.button("Confirmar Entrada"):
        # Lógica: Registra no db_entrada e atualiza db_estoque
        # cod_prod,
        # ean,
        # tipo,
        # qtd,
        # valor,
        # user,
        repo.registrar_Movimentacao(
            cod_input, 'Entrada', qtd_input, value_input, user_input)
        repo.db_estoque_SJ.write(
            "UPDATE Produtos SET quantidade = quantidade + ?, valor = ? WHERE cod_prod = ?",
            (qtd_input, value_input, cod_input)
        )
        st.success("Estoque atualizado!")


def tela_Movimentacoes():

    df_saidas = repo.db_estoque_SJ.read(
        "SELECT * FROM Movimentacao WHERE tipo = 'Saida'")
    df_entradas = repo.db_estoque_SJ.read(
        "SELECT * FROM Movimentacao WHERE tipo = 'Entrada'")
    st.title("📊 Relatórios de movimentações")
    st.text("📤 Saida de produtos:")
    st.dataframe(
        df_saidas,
        width="stretch",
        column_config={"cod_prod": "Código", }
    )
    st.text("Entradas", width="stretch")
    st.dataframe(
        df_entradas,
        width="stretch",
        column_config={"cod_prod": "Código", }
    )


def upload_csv():
    arquivo = st.file_uploader("📂 Importar CSV", type="csv")
    if arquivo:
        df = pd.read_csv(arquivo, sep=";", encoding="utf-8")
        st.write(f"**{len(df)} registros encontrados:**")
        st.dataframe(df, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar inserção"):
                try:
                    repo.db_estoque_SJ.import_csv("Produtos", arquivo)
                    st.success(f"{len(df)} registros inseridos!")
                except Exception as e:
                    st.error(f"Erro ao inserir:{e}")
        with col2:
            if st.button("❌ Cancelar"):
                st.warning("Importação cancelada.")


def edição_de_itens():
    st.subheader("✏️ Editar Produto")
    cod_busca = st.text_input(
        "🔍 Digite o código do produto", key="cod_busca_input")

    if cod_busca:
        st.session_state["cod_busca"] = cod_busca

    codigo = st.session_state.get("cod_busca", "")

    if codigo:
        df = repo.db_estoque_SJ.read(
            "SELECT * FROM Produtos WHERE cod_prod = ?", params=(cod_busca,))

        if df.empty:
            st.warning("Produto não Encontrado!")
        else:
            produto = df.iloc[0]
            with st.form("form_edicao"):
                cod_prod = st.text_input(
                    "Código",               value=str(produto["cod_prod"]))
                nome = st.text_input(
                    "Descrição do Produto", value=produto["nome"])
                valor = st.number_input("Preço (R$)",         value=float(
                    produto["valor"]),      step=0.01, format="%.2f")
                localizacao = st.text_input(
                    "Local",            value=produto["localizacao"])
                salvar = st.form_submit_button("💾 Salvar alterações")

                if salvar:
                    try:
                        repo.db_estoque_SJ.write(
                            """UPDATE Produtos SET cod_prod = ?, nome = ?, valor = ?, localizacao = ? WHERE cod_prod = ?""",
                            (int(cod_prod), nome, float(
                                valor), localizacao, int(produto["cod_prod"]))
                        )
                        st.success("Produto atualizado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")


def qrCode():
    st.title("Leitor de QR Code / Código de Barras")
    if st.button("▶ Iniciar leitura"):

        cap = cv2.VideoCapture(0)

        frame_placeholder = st.image([])
        resultado = st.empty()
        stop = st.button("⏹ Parar")

        while cap.isOpened() and not stop:
            ret, frame = cap.read()
            if not ret:
                st.error("Câmera não encontrada.")
                break

            codigos = pyzbar.decode(frame)

            if codigos:
                codigo = codigos[0]  # pega o primeiro código encontrado
                (x, y, w, h) = codigo.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                largura = int(frame_rgb.shape[1] * 0.1)
                altura = int(frame_rgb.shape[0] * 0.1)
                frame_menor = cv2.resize(
                    frame_rgb, (largura, altura), interpolation=cv2.INTER_AREA)
                frame_placeholder.image(
                    frame_menor, channels="RGB", width="stretch")

                dados = codigo.data.decode("utf-8")
                tipo = codigo.type
                st.success("Código Detectado com Sucesso!")
                st.markdown(f"**Tipo:** {tipo}")
                st.markdown(f"**Conteúdo (Dados):** `{dados}`")
                break  # para o loop ao capturar

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(
                frame_rgb, channels="RGB", width="stretch")

        cap.release()

# ---------------------------------------------------------
# INTERFACE
# ---------------------------------------------------------------------------


def main():

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
            tela_dashboard()
        case "🚚Movimentações":
            tela_Movimentacoes()
        case "📝Cadastrar Produto":
            tela_cadastro()
        case "📤Registrar Saída":
            tela_saidas()
        case "📥Registrar Entrada":
            entrada_Produtos()
        case "Importar Dados":
            upload_csv()
        case "✏️Editar itens":
            edição_de_itens()
        case "📱leitura de codigo de barra":
            qrCode()


#  def main():
    # st.sidebar.title("Navegação")
    # menu = st.sidebar.radio(
        # "Selecione uma opção:",
        # ["📦Estoque Geral", "📝Cadastrar Produto",
            # "📥Registrar Entrada", "📤Registrar Saída", "🚚Movimentações", "✏️Editar itens", "📱leitura de codigo de barra", "Importar Dados"]
    # )
    # match menu:
        # case "Estoque Geral":
            # tela_dashboard()
        # case "Movimentações":
            # tela_Movimentacoes()
        # case "Cadastrar Produto":
            # tela_cadastro()
        # case "Registrar Saída":
            # tela_saidas()
        # case "Registrar Entrada":
            # entrada_Produtos()
        # case "Importar Dados":
            # upload_csv()
        # case "Editar itens cadastrados":
            # edição_de_itens()
        # case "leitura de codigo de barra":
            # qrCode()
if __name__ == "__main__":
    main()
