import sqlite3
import os
import pandas as pd
from datetime import datetime
import streamlit as st
from typing import Literal


class DataBaseManager:

    def __init__(self, db_name):

        self.db_path = os.path.join("DB", f"{db_name}.db")
        os.makedirs("DB", exist_ok=True)

    def get_connection(self):
        """RETORNA COM OS DADOS DO BANCO"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def read(self, query, params=()):
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def write(self, query, parms=()):
        with self.get_connection() as conn:
            conn.execute(query, parms)
            conn.commit()

    def import_csv(self, tabela, arquivo_csv, encoding, if_exists: Literal["fail", "replace", "append", "delete_rows"] = "append"):
        """Importa um csv para o banco de dados """
        df = pd.read_csv(arquivo_csv, sep=";", encoding=encoding)
        with self.get_connection() as conn:
            df.to_sql(tabela, con=conn, if_exists=if_exists, index=False)
        return df


# LOGICA DO SISTEMA


class InventorySystem:
    def __init__(self):
        # Inicializa os 3 gerenciadores independentes
        self.db_estoque_SJ = DataBaseManager("Estoque_SJ")

        # Cria as tabelas se não existirem
        self._init_all_dbs()

    def _init_all_dbs(self):
        """Configuração inicial de cada banco de dados"""
        # 1. Tabela de Produtos (Estoque)
        self.db_estoque_SJ.write('''
            CREATE TABLE IF NOT EXISTS Produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_prod INTEGER UNIQUE NOT NULL,
                EAN INTEGER UNIQUE NOT NULL,
                nome TEXT UNIQUE NOT NULL,
                quantidade INTEGER DEFAULT 0,
                valor REAL NOT NULL,
                localizacao TEXT DEFAULT ''
            )
        ''')

        # 2. Tabela de movimentacoes
        self.db_estoque_SJ.write('''
            CREATE TABLE IF NOT EXISTS Movimentacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_prod INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('Entrada', 'Saida')),
                quantidade INTEGER NOT NULL,
                valor REAL DEFAULT 0.0,
                User TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')

    def registrar_Movimentacao(self, cod_prod, qtd, tipo, valor, user):
        """Exemplo de método para registrar no banco de saídas"""
        query = """
            INSERT INTO Movimentacao (cod_prod, tipo, quantidade, valor, User, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            cod_prod,
            qtd,
            tipo,
            valor,
            user,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        try:
            self.db_estoque_SJ.write(query, params)
            # Aqui você também poderia chamar self.db_estoque para subtrair a quantidade
            st.success("Movimentação registrada com sucesso!")
        except Exception as e:
            st.error(f"Erro na saída: {e}")
