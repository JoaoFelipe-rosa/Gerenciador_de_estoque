import json

import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
from dbManager import InventorySystem

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
        nome = st.text_input("Nome do Produto")
        valor = st.number_input("Preço Unitário", format="%.2f")
        local = st.text_input("Localização (Prateleira/Corredor)")

        if st.form_submit_button("Salvar"):
            try:
                repo.db_estoque_SJ.write(
                    "INSERT INTO Produtos (cod_prod, nome, valor, localizacao) VALUES (?, ?, ?, ?)",
                    (cod, nome, valor, local)
                )
                st.success("Produto cadastrado com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")


def tela_saidas():
    st.title("📥 Saida de Estoque")
    cod_input = st.number_input("Código do Produto", step=1)
    nome_produto = buscar_nome_produto(cod_input)
    st.write("Produto selecionado:")
    st.write(f"{nome_produto}")

    qtd_input = st.number_input("Quantidade a Adicionar", min_value=1)

    if st.button("Confirmar Saida"):
        repo.db_estoque_SJ.write(
            "INSERT INTO Saidas (cod_prod, produto_id, tipo, quantidade, data) VALUES (?,?,?,?,?)",
            (cod_input, 0, 'SAIDA', qtd_input,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        repo.db_estoque_SJ.write(
            "UPDATE Produtos SET quantidade = quantidade - ? WHERE cod_prod = ? AND quantidade >= ?",
            (qtd_input, cod_input, qtd_input)
        )
        st.success("Estoque atualizado!")


def tela_dashboard():
    st.title("📦 Estoque")

    # Lendo dados de bancos diferentes
    df_estoque = repo.db_estoque_SJ.read("SELECT * FROM Produtos")
    estoque_json = json.loads(df_estoque.to_json(orient="records"))

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

    qtd_input = st.number_input("Quantidade a Adicionar", min_value=1)

    if st.button("Confirmar Entrada"):
        # Lógica: Registra no db_entrada e atualiza db_estoque
        repo.db_estoque_SJ.write(
            "INSERT INTO Entradas (cod_prod, produto_id, tipo, quantidade, data) VALUES (?,?,?,?,?)",
            (cod_input, 0, 'ENTRADA', qtd_input,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        repo.db_estoque_SJ.write(
            "UPDATE Produtos SET quantidade = quantidade + ? WHERE cod_prod = ?",
            (qtd_input, cod_input)
        )
        st.success("Estoque atualizado!")


def tela_Movimentacoes():

    df_saidas = repo.db_estoque_SJ.read("SELECT * FROM Saidas")
    df_entradas = repo.db_estoque_SJ.read("SELECT * FROM Entradas")
    st.title("📊 Relatórios de movimentações")
    st.text("Saida de produtos:")
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

# ---------------------------------------------------------------------------
# INTERFACE
# ---------------------------------------------------------------------------


def main():
    st.sidebar.title("Navegação")
    menu = st.sidebar.radio(
        "Selecione uma opção:",
        ["Estoque Geral", "Cadastrar Produto",
            "Registrar Entrada", "Registrar Saída", "Movimentações", "Importar Dados", "Editar itens cadastrados"]
    )
    match menu:
        case "Estoque Geral":
            tela_dashboard()
        case "Movimentações":
            tela_Movimentacoes()
        case "Cadastrar Produto":
            tela_cadastro()
        case "Registrar Saída":
            tela_saidas()
        case "Registrar Entrada":
            entrada_Produtos()
        case "Importar Dados":
            upload_csv()
        case "Editar itens cadastrados":
            edição_de_itens()


if __name__ == "__main__":
    main()
