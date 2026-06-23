import json
import streamlit as st
import pandas as pd
from datetime import datetime
from dbManager import InventorySystem
import time
from streamlit_qrcode_scanner import qrcode_scanner


# ---------------------------------------------------------------------------
# BANCO DE DADOS
# ---------------------------------------------------------------------------
if 'repo' not in st.session_state:
    st.session_state.repo = InventorySystem()

repo = st.session_state.repo

FILIAIS = {
    "sao_jose": "São José",
    "jaragua": "Jaraguá do Sul",
    "chapeco": "Chapecó",
}
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


def tela_dashboard():
    filial = st.session_state.get("filial", "")
    filial_name = FILIAIS.get(filial, filial)
    st.title(F"📦 Estoque de {filial_name}")

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
    tabelas_map = {
        "Produtos": "produtos",
        "Movimentação": "movimentacao"
    }

    selecionado_label = st.selectbox(
        label="Dados a ser baixado:", options=list(tabelas_map.keys()))
    tabela_nome = tabelas_map[selecionado_label]

    if st.button("Preparar arquivo para download"):
        try:
            with db.get_connection() as conn:
                cursor = conn.execute(f"PRAGMA table_info({tabela_nome})")
                colunas = [row[1]
                           for row in cursor.fetchall() if row[1].lower() != "id"]

            colunas_str = ", ".join(colunas)

            df = db.read(f"SELECT {colunas_str} FROM {tabela_nome}")

            csv = df.to_csv(index=False, sep=";",
                            decimal=",", encoding="latin-1")

            st.download_button(
                label=f"📥 Baixar {selecionado_label}",
                data=csv.encode("latin-1"),
                file_name=f"{tabela_nome}_{st.session_state.get('filial', 'geral')}_{datetime.now().strftime('%d-%m-%Y')}.csv",
                mime="text/csv"
            )
            st.success("Dados preparados com sucesso!")

        except Exception as e:
            st.error(f"Erro ao gerar o CSV: {e}")


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
    comment_input = st.text_area("Comentario:", key="Out_comment")
    user_input = loged_User

    if st.button("Confirmar Saida"):
        if not user_input.strip():
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
            filial, cod_input, 'Saida', qtd_input, value_input, user_input, comment_input)

        st.success("✅ Estoque atualizado!")


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
    comment_input = st.text_area("Comentario:", key="in_comment")
    user_input = loged_User

    if st.button("Confirmar Entrada"):
        if not user_input.strip():
            st.error("Coloque seu nome no registro")
            st.stop()

        repo.registrar_Movimentacao(
            filial, cod_input, 'Entrada', qtd_input, value_input, user_input, comment_input)
        db.write(
            "UPDATE Produtos SET quantidade = quantidade + ?, valor = ? WHERE cod_prod = ?",
            (qtd_input, value_input, cod_input)
        )
        st.success("Estoque atualizado!")


def tela_Movimentacoes(loged_User):
    st.title("Movimentações")

    tab1, tab2, tab3 = st.tabs(
        ["📝 Histórico de Movimentações", "📦 Entradas", "📦 Saidas"])
    with tab1:
        def ShowTabela(DBtoShow):
            st.dataframe(
                DBtoShow.iloc[:, 1:],
                width="stretch",
                hide_index=True,
                column_config={
                    "valor": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f"),
                    "quantidade": st.column_config.NumberColumn("Quantidade"),
                    "cod_prod": "Código do Produto",
                    "tipo": "Movimentação",
                    "nome": "Descrição do Produto",
                    "localizacao": "Local",
                    "User": "Usuario",
                    "data": "Data da movimentação",
                    "comentario": "Comentario"
                }
            )
        db = get_db()
        df_saidas = db.read(
            "SELECT * FROM Movimentacao WHERE tipo = 'Saida'")
        df_entradas = db.read(
            "SELECT * FROM Movimentacao WHERE tipo = 'Entrada'")
        st.title("📊 Relatórios de movimentações")
        st.text("Entradas", width="stretch")
        ShowTabela(df_entradas)
        st.text("📤 Saida de produtos:")
        ShowTabela(df_saidas)
    with tab2:
        tela_saidas(loged_User)
    with tab3:
        entrada_Produtos(loged_User)


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


def edição_de_itens(isAdmin):
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

    def addcolunas():
        for filial in ["sao_jose", "jaragua", "chapeco"]:
            repo.get_db(filial).add_column(
                "Movimentacao", "comentario", "TEXT")

    st.write("botão para add coluna")
    st.button(label="Adicionar colunas",
              on_click=addcolunas, disabled=not isAdmin)


def tela_pedidos():
    db = get_db()
    st.title("📋 Pedidos")

    tab1, tab2 = st.tabs(["📝 Lista da Semana", "📦 Pedidos Enviados"])

    with tab1:
        st.subheader("📝 Lista de Itens")

        # Busca fora do form
        busca = st.text_input(
            "🔍 Digite o código ou nome do produto", placeholder="Ex: 1010411")

        if busca:
            df_produtos = db.read(
                "SELECT cod_prod, nome, valor FROM Produtos WHERE CAST(cod_prod AS TEXT) LIKE :busca OR nome LIKE :busca ORDER BY nome LIMIT 10",
                {"busca": f"%{busca}%"}
            )
            opcoes = {f"{r['cod_prod']} — {r['nome']}": r for _,
                      r in df_produtos.iterrows()}
        else:
            opcoes = {}

        # Selectbox fora do form
        if opcoes:
            produto_sel = st.selectbox("Produto", options=list(opcoes.keys()))
            produto_dados = opcoes[produto_sel]
        else:
            if busca:
                st.warning("Nenhum produto encontrado.")
            produto_dados = None

        # Form só com quantidade, valor e botão
        with st.form("adicionar_item"):
            col1, col2 = st.columns(2)
            qtd = col1.number_input("Quantidade", min_value=1, value=1)
            valor = col2.number_input(
                "Valor",
                value=float(produto_dados["valor"]
                            ) if produto_dados is not None else 0.0,
                step=0.01,
                format="%.2f"
            )

            if st.form_submit_button("➕ Adicionar à Lista"):
                if produto_dados is None:
                    st.error("Selecione um produto antes de adicionar.")
                else:
                    # Verifica se já existe na lista
                    existente = db.read(
                        "SELECT id, quantidade FROM Lista_Pedido WHERE cod_prod = :cod",
                        {"cod": int(produto_dados["cod_prod"])}
                    )

                    if not existente.empty:
                        # Atualiza a quantidade do item existente
                        nova_qtd = int(existente.iloc[0]["quantidade"]) + qtd
                        db.write(
                            "UPDATE Lista_Pedido SET quantidade = :qtd WHERE id = :id",
                            {"qtd": nova_qtd, "id": int(
                                existente.iloc[0]["id"])}
                        )

                    else:
                        # Insere novo item
                        db.write(
                            "INSERT INTO Lista_Pedido (cod_prod, nome, quantidade, valor, adicionado_por, data) VALUES (:cod, :nome, :qtd, :valor, :user, :data)",
                            {
                                "cod": int(produto_dados["cod_prod"]),
                                "nome": produto_dados["nome"],
                                "qtd": qtd,
                                "valor": valor,
                                "user": st.session_state["name"],
                                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        )

                    st.rerun()

        # Lista acumulada
        df_lista = db.read("SELECT * FROM Lista_Pedido ORDER BY data DESC")

        if df_lista.empty:
            st.info("Lista vazia. Adicione produtos acima.")
        else:
            st.dataframe(df_lista.drop(
                columns=["id"]), hide_index=True, use_container_width=True)

            total = (df_lista["quantidade"] * df_lista["valor"]).sum()
            st.metric("Total da Lista", f"R$ {total:,.2f}")

            st.divider()

            item_remover = st.selectbox(
                "Remover item:",
                options=df_lista["id"].tolist(),
                format_func=lambda x: df_lista[df_lista["id"]
                                               == x]["nome"].values[0]
            )
            if st.button("🗑️ Remover item"):
                db.write("DELETE FROM Lista_Pedido WHERE id = :id",
                         {"id": item_remover})
                st.rerun()

            st.divider()

            st.subheader("📤 Enviar Pedido")
            with st.form("enviar_pedido"):
                numero_pedido = st.text_input(
                    "Número do Pedido", placeholder="Ex: PED-2026-001")

                if st.form_submit_button("✅ Confirmar Envio"):
                    if not numero_pedido:
                        st.error("Informe o número do pedido.")
                    else:
                        itens = df_lista.drop(
                            columns=["id"]).to_dict(orient="records")
                        itens_json = json.dumps(itens, ensure_ascii=False)
                        total = (df_lista["quantidade"] *
                                 df_lista["valor"]).sum()

                        try:
                            db.write(
                                "INSERT INTO Pedidos (numero_pedido, itens, total, criado_por, data_criacao) VALUES (:num, :itens, :total, :user, :data)",
                                {
                                    "num": numero_pedido,
                                    "itens": itens_json,
                                    "total": total,
                                    "user": st.session_state["name"],
                                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                            )
                            db.write("DELETE FROM Lista_Pedido")
                            st.success(f"✅ Pedido {numero_pedido} enviado!")
                            st.rerun()
                        except Exception as e:
                            if "UNIQUE constraint failed" in str(e):
                                st.error(
                                    f"❌ Número '{numero_pedido}' já existe.")
                            else:
                                st.error(f"Erro: {e}")

    with tab2:
        st.subheader("📦 Pedidos Enviados")

        df_pedidos = db.read(
            "SELECT * FROM Pedidos ORDER BY data_criacao DESC")

        if df_pedidos.empty:
            st.info("Nenhum pedido enviado.")
            return

        for _, pedido in df_pedidos.iterrows():
            with st.expander(f"📦 {pedido['numero_pedido']} — {pedido['data_criacao']} — por {pedido['criado_por']}"):
                # Deserializa os itens do JSON
                itens = json.loads(pedido["itens"])
                df_itens = pd.DataFrame(itens)
                st.dataframe(df_itens, hide_index=True,
                             width='stretch')
                st.metric("Total", f"R$ {pedido['total']:,.2f}")


def QR_Reader():
    @st.dialog("📷 Leitor de QR Code / Código de Barras")
    def barcode_Reader():
        st.info("🎥 Aponte para um QR Code ou código de barras.")
        codigo_lido = qrcode_scanner(key="qrcode_scanner")

        if codigo_lido:
            st.session_state.resultado_qr = codigo_lido
            st.rerun()

        if st.button("❌ Fechar"):
            st.rerun()

    if st.button("📷 Abrir Câmera"):
        barcode_Reader()

    if st.session_state.get("resultado_qr"):
        st.success("✅ Código lido com sucesso!")
        st.code(st.session_state.resultado_qr)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Nova Leitura"):
                st.session_state.resultado_qr = None
                barcode_Reader()
        with col2:
            if st.button("🗑️ Limpar"):
                st.session_state.resultado_qr = None
                st.rerun()
