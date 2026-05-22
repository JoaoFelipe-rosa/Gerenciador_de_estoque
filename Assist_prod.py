import json

import numpy as np
import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from datetime import datetime
from dbManager import InventorySystem
import cv2
from pyzbar import pyzbar
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import time
import queue

# ---------------------------------------------------------------------------
# BANCO DE DADOS
# ---------------------------------------------------------------------------
if 'repo' not in st.session_state:
    st.session_state.repo = InventorySystem()

repo = st.session_state.repo


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def get_db():
    """RETORNA A FILIAL DO USER LOGADO"""

    filial = st.session_state.get("filial")
    if not filial:
        st.error(
            "❌ Usuário sem filial cadastrada. Contate o administrador.")
        st.stop()
    return repo.get_db(filial)


def buscar_nome_produto(cod):
    db = get_db()
    if cod == 0:
        return "Insira um codigo de produto"
    resultado = db.read(
        "SELECT nome FROM Produtos WHERE cod_prod = ?", (cod,))

    if resultado is not None and not resultado.empty:
        return resultado.iloc[0, 0]
    return None


def tela_cadastro():
    st.title("📦 Cadastro de Produtos")

    db = get_db()

    with st.form("form_cadastro"):
        cod = st.number_input("Código do Produto", step=1)
        nome = st.text_input("Nome do Produto")
        valor = st.number_input("Preço Unitário", format="%.2f")
        local = st.text_input("Localização (Prateleira/Corredor)")

        if st.form_submit_button("Salvar"):
            try:
                db.write(
                    "INSERT INTO Produtos (cod_prod, nome, valor, localizacao) VALUES ( ?, ?, ?,?)",
                    (cod, nome, valor, local)
                )
                st.success("Produto cadastrado com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")


def tela_saidas(loged_User):
    st.title("📤 Saida de Estoque")
    db = get_db()
    filial = st.session_state["filial"]

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
    user_input = loged_User

    if st.button("Confirmar Saida"):
        if user_input == "":
            st.error("Coloque seu nome no registro")
            st.stop()

        with db.get_connection()as conn:
            cursor = conn.execute("UPDATE Produtos SET quantidade = quantidade - ? WHERE cod_prod = ? AND quantidade >= ?",
                                  (qtd_input, cod_input, qtd_input))
            conn.commit()

        if cursor.rowcount == 0:
            st.error(f"❌ Estoque insuficiente para o produto {cod_input}!")
            st.stop()

        repo.registrar_Movimentacao(
            filial, cod_input, 'Saida', qtd_input, value_input, user_input)

        st.success("✅ Estoque atualizado!")


def tela_dashboard():
    st.title("📦 Estoque")

    db = get_db()

    # Lendo dados de bancos diferentes
    df_estoque = db.read(
        "SELECT * FROM Produtos WHERE quantidade >= 1")

    pesquisa = st.text_input(
        "🔍 Pesquisar", placeholder="Digite para buscar...")

    if pesquisa:
        mask = df_estoque.apply(lambda col: col.astype(
            str).str.contains(pesquisa, case=False, na=False)).any(axis=1)
        df_filtrado = df_estoque[mask].iloc[:, 1:]
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


def exportar_csv():
    db = get_db()
    options = ["Produtos", "Movimentacao"]

    selecionado = st.selectbox(label="Dados a ser baixado:", options=options)

    df = db.read(f"SELECT * FROM {selecionado}")
    csv = df.to_csv(index=False, sep=";", decimal=",", encoding="latin-1")
    st.download_button(
        label="📥 Exportar dados dos produtos",
        data=csv.encode("latin-1"),
        file_name=f"estoque_{st.session_state.get('filial', 'geral')}_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv"
    )


def entrada_Produtos(loged_User):
    st.title("📥 Entrada de Estoque")
    db = get_db()
    filial = st.session_state["filial"]
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
    user_input = loged_User

    if st.button("Confirmar Entrada"):
        if user_input == "":
            st.error("Coloque seu nome no registro")
            st.stop()

        repo.registrar_Movimentacao(
            filial, cod_input, 'Entrada', qtd_input, value_input, user_input)
        db.write(
            "UPDATE Produtos SET quantidade = quantidade + ?, valor = ? WHERE cod_prod = ?",
            (qtd_input, value_input, cod_input)
        )
        st.success("Estoque atualizado!")


def tela_Movimentacoes():
    db = get_db()

    df_saidas = db.read(
        "SELECT * FROM Movimentacao WHERE tipo = 'Saida'")
    df_entradas = db.read(
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
    db = get_db()

    if arquivo:
        try:
            df = pd.read_csv(arquivo, sep=";", encoding="latin-1")
        except UnicodeDecodeError:
            arquivo.seek(0)
            df = pd.read_csv(arquivo, sep=";", encoding="cp1252")

        # Remove colunas Unnamed
        df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]

        # Separa linhas inválidas (nome vazio ou cod_prod nulo)
        mask_invalidas = df["nome"].isna() | (
            df["nome"].str.strip() == "") | df["cod_prod"].isna()
        df_invalido = df[mask_invalidas]
        df_valido = df[~mask_invalidas].copy()

        if not df_invalido.empty:
            st.warning(
                f"⚠️ {len(df_invalido)} linha(s) sem nome ou código serão ignoradas:")
            st.dataframe(df_invalido, hide_index=True)

        st.write(f"**{len(df_valido)} registros válidos encontrados:**")
        st.dataframe(df_valido, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar inserção"):
                try:
                    arquivo.seek(0)
                    db.import_csv(
                        "Produtos", arquivo, encoding="latin-1")
                    st.success(f"{len(df_valido)} registros inseridos!")
                except Exception as e:
                    import traceback
                    st.error(f"Erro ao inserir: {e}")
                    st.code(traceback.format_exc())
        with col2:
            if st.button("❌ Cancelar"):
                st.warning("Importação cancelada.")


def edição_de_itens():
    st.subheader("✏️ Editar Produto")
    db = get_db()

    if "reset_busca" not in st.session_state:
        st.session_state["reset_busca"] = 0

    cod_busca = st.text_input(
        "🔍 Digite o código do produto", key=f"cod_busca_input_{st.session_state['reset_busca']}")

    if cod_busca:
        st.session_state["cod_busca"] = cod_busca

    codigo = st.session_state.get("cod_busca", "")

    if codigo:
        df = db.read(
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
                        db.write(
                            """UPDATE Produtos SET cod_prod = ?, nome = ?, valor = ?, localizacao = ? WHERE cod_prod = ?""",
                            (int(cod_prod), str(nome), float(
                                valor), str(localizacao), int(produto["cod_prod"]))
                        )
                        st.session_state["cod_busca"] = ""
                        st.session_state["reset_busca"] += 1
                        st.success("Produto atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")


def qrCode():
    if "codigo_detectado" not in st.session_state:
        st.session_state.codigo_detectado = None

    st.title("📷 Leitor de QR Code / Barcode")

    # --- ESTADO 2: Código já encontrado ---
    if st.session_state.codigo_detectado is not None:
        resultado = st.session_state.codigo_detectado
        st.success("✅ Código detectado com sucesso!")
        st.markdown(f"**Tipo:** {resultado['tipo']}")
        st.markdown(f"**Dados:** `{resultado['dados']}`")

        if st.button("🔄 Nova leitura"):
            st.session_state.codigo_detectado = None
            st.rerun()
        return

    # --- ESTADO 1: Leitura ativa ---
    st.info("🎥 Câmera ativa — aponte para um QR Code ou código de barras.")

    if "resultado_buffer" not in st.session_state:
        st.session_state.resultado_buffer = queue.Queue(maxsize=1)

    resultado_queue = st.session_state.resultado_buffer

    def processar_frame(frame):
        img = frame.to_ndarray(format="bgr24")
        codigos = pyzbar.decode(img)

        if codigos:
            codigo = codigos[0]
            (x, y, w, h) = codigo.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            try:
                resultado_queue.put_nowait({
                    "dados": codigo.data.decode("utf-8"),
                    "tipo": codigo.type
                })
            except queue.Full:
                pass

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    ctx = webrtc_streamer(
        key="leitor",
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=processar_frame,
        media_stream_constraints={"video": True, "audio": False},
        desired_playing_state=True,
    )

    # Polling externo ao ctx — roda a cada rerun do Streamlit
    if not resultado_queue.empty():
        try:
            resultado = resultado_queue.get_nowait()
            st.session_state.codigo_detectado = resultado
            st.session_state.resultado_buffer = queue.Queue(
                maxsize=1)  # reseta a fila
            st.rerun()
        except queue.Empty:
            pass

    # Força o Streamlit a re-executar enquanto câmera ativa
    if ctx.state.playing:
        time.sleep(0.3)
        st.rerun()
