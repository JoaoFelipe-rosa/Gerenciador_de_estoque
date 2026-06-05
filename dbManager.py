import sqlite3
import os
import pandas as pd
from datetime import datetime
import streamlit as st


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

    def add_column(self, tabela, coluna, tipo, default=""):
        """Adiciona coluna se não existir"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo} DEFAULT '{default}'")
                conn.commit()
            print(f"Coluna '{coluna}' adicionada em '{tabela}'")
        except Exception as e:
            if "duplicate column name" in str(e):
                print(f"Coluna '{coluna}' já existe, ignorando.")
            else:
                raise e

    def import_csv(self, tabela, arquivo_csv, encoding, if_exists="append"):
        df = pd.read_csv(arquivo_csv, sep=";", encoding=encoding)
        df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]

        if "valor" in df.columns:
            df["valor"] = (
                df["valor"]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

        # Remove linhas com campos obrigatórios vazios
        df = df.dropna(subset=["cod_prod", "nome"])
        df = df[df["nome"].str.strip() != ""]

        with self.get_connection() as conn:
            colunas = ", ".join(df.columns)
            placeholders = ", ".join(["?"] * len(df.columns))
            sql = f"INSERT OR REPLACE INTO {tabela} ({colunas}) VALUES ({placeholders})"
            conn.executemany(sql, df.itertuples(index=False, name=None))
            conn.commit()
        return df


# LOGICA DO SISTEMA


class InventorySystem:
    def __init__(self):
        self._bancos = {}
        # Filiais existentes — adicione novas aqui
        for filial in ["sao_jose", "Jaragua", "chapeco"]:
            self._init_filial(filial)

    def get_db(self, filial: str) -> DataBaseManager:
        """Retorna o banco da filial, criando se não existir"""
        if filial not in self._bancos:
            self._init_filial(filial)
        return self._bancos[filial]

    def _init_filial(self, filial: str):
        db = DataBaseManager(f"Estoque_{filial}")
        self._bancos[filial] = db

        db.write('''
            CREATE TABLE IF NOT EXISTS Produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_prod INTEGER UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                quantidade INTEGER DEFAULT 0,
                valor REAL DEFAULT 0,
                localizacao TEXT DEFAULT ''
            )
        ''')
        db.write('''
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

    def registrar_Movimentacao(self, filial, cod_prod, tipo, qtd, valor, user, comentario):
        query = """
            INSERT INTO Movimentacao (cod_prod, tipo, quantidade, valor, User, data, comentario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (cod_prod, tipo, qtd, valor, user,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), comentario)
        try:
            self.get_db(filial).write(query, params)
        except Exception as e:
            st.error(f"Erro ao registrar movimentação: {e}")
