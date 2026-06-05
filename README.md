# 📦 Gerenciador de Estoque ASTEC

Sistema de gerenciamento de estoque multi-filial desenvolvido com Python e Streamlit. Permite controle de produtos, movimentações de entrada e saída, importação/exportação de dados e autenticação de usuários com controle de acesso por perfil.

---

## 🚀 Funcionalidades

- **Autenticação de usuários** com controle de acesso por perfil (admin/viewer)
- **Multi-filial** — cada usuário acessa apenas o banco de dados da sua filial
- **Estoque Geral** — visualização de todos os produtos com métricas
- **Cadastro de Produtos** — adicionar novos itens ao estoque
- **Registro de Entrada** — entrada de produtos com registro de movimentação
- **Registro de Saída** — saída de produtos com validação de quantidade disponível
- **Histórico de Movimentações** — log completo de entradas e saídas
- **Edição de Itens** — atualização de dados dos produtos
- **Importação de CSV** — importação em lote de produtos via arquivo CSV
- **Exportação de CSV** — exportação do estoque ou movimentações
- **Leitura de Código de Barras** — leitura via câmera com `pyzbar`
- **Bloqueio por tentativas** — usuário bloqueado após excesso de tentativas de login
- **Backup automático** — envio periódico para OneDrive via rclone
- **Deploy com Docker** — containerização completa da aplicação
- **Auto-deploy** — monitoramento do repositório Git e rebuild automático

---

## 🗂️ Estrutura do Projeto

```
Gerenciador_de_estoque/
├── Main.py                  # Ponto de entrada, autenticação e navegação
├── Assist_prod.py           # Telas e lógica de interface
├── dbManager.py             # Gerenciamento de banco de dados e lógica do sistema
├── config.yaml              # Credenciais e configurações (não versionar)
├── config.example.yaml      # Modelo de configuração para novos ambientes
├── requirements.txt         # Dependências Python
├── Dockerfile               # Imagem Docker
├── docker-compose.yml       # Orquestração dos containers
├── .dockerignore            # Arquivos ignorados no build Docker
├── .gitignore               # Arquivos ignorados no Git
├── auto_pull.sh             # Script de monitoramento e auto-deploy
└── DB/                      # Bancos de dados SQLite (não versionar)
    ├── Estoque1.db
    ├── Estoque2.db
    └── Estoque3.db
```

---

## ⚙️ Pré-requisitos

- Python 3.11+
- pip
- Git
- (Opcional) Docker e Docker Compose

---

## 🖥️ Como Rodar Localmente

### 1. Clone o repositório

```bash
git clone https://github.com/JoaoFelipe-rosa/Gerenciador_de_estoque.git
cd Gerenciador_de_estoque
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o arquivo de credenciais

```bash
cp config.example.yaml config.yaml
```

Edite o `config.yaml` com seus usuários e filiais. Para gerar senhas com hash bcrypt:

```python
import streamlit_authenticator as stauth
hashed = stauth.Hasher(["sua_senha"]).generate()
print(hashed)
```

### 5. Rode a aplicação

```bash
streamlit run Main.py
```

Acesse em `http://localhost:8501`

---

## 🐳 Como Rodar com Docker

### 1. Clone o repositório

```bash
git clone https://github.com/JoaoFelipe-rosa/Gerenciador_de_estoque.git
cd Gerenciador_de_estoque
```

### 2. Configure os dados persistentes

```bash
mkdir -p /home/$USER/dados/DB
cp config.yaml /home/$USER/dados/config.yaml
```

### 3. Ajuste o `docker-compose.yml`

```yaml
services:
  estoque:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - /home/$USER/dados/DB:/DB
      - /home/$USER/dados/config.yaml:/config.yaml
    restart: unless-stopped
```

### 4. Build e inicialização

```bash
# Primeira vez
docker compose up --build -d

# Verificar logs
docker compose logs -f

# Parar
docker compose down

# Reiniciar
docker compose restart
```

Acesse em `http://localhost:8501`

---

## 🔄 Auto-deploy com Git (Servidor)

O script `auto_pull.sh` monitora o repositório e faz rebuild automático ao detectar mudanças:

```bash
# Instalar como serviço
sudo nano /etc/systemd/system/auto-pull.service
```

```ini
[Unit]
Description=Auto Pull Git
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/home/joao/auto_pull.sh
Restart=always
User=joao

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable auto-pull
sudo systemctl start auto-pull
```

---

## 🔐 Configuração do `config.yaml`

```yaml
cookie:
  expiry_days: 0.25        # Expiração da sessão (0.25 = 6 horas)
  key: sua_chave_secreta   # Mínimo 32 caracteres
  name: estoque_cookie

credentials:
  usernames:
    joao:
      name: João Felipe
      password: $2b$12$HASH_BCRYPT
      email: joao@email.com
      failed_login_attempts: 0
      logged_in: false
      roles:
        - admin
    maria:
      name: Maria Costa
      password: $2b$12$HASH_BCRYPT
      email: maria@email.com
      failed_login_attempts: 0
      logged_in: false
      roles:
        - viewer

filiais:
  joao: sao_jose
  maria: jaragua
```

---

## 📦 Bibliotecas Utilizadas

| Biblioteca | Uso |
|---|---|
| `streamlit` | Framework principal da interface web |
| `streamlit-authenticator` | Autenticação de usuários com hash bcrypt e controle de sessão |
| `streamlit-antd-components` | Componentes visuais avançados (menu lateral, etc.) |
| `pandas` | Manipulação de dados, leitura de CSV e queries SQL |
| `pyyaml` | Leitura e escrita do arquivo de configuração `config.yaml` |
| `pyzbar` | Leitura de códigos de barras via câmera |
| `bcrypt` | Hash seguro de senhas (dependência do streamlit-authenticator) |
| `sqlite3` | Banco de dados embutido (stdlib Python) |
| `python-dotenv` | Gerenciamento de variáveis de ambiente sensíveis |
| `validators` | Validação de emails e outros campos de entrada |
| `bleach` | Sanitização de inputs do usuário contra XSS |
| `plotly` | Gráficos interativos no dashboard (opcional) |

---

## 🗄️ Estrutura do Banco de Dados

### Tabela `Produtos`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Chave primária autoincrement |
| `cod_prod` | INTEGER UNIQUE | Código interno do produto |
| `nome` | TEXT | Nome do produto |
| `quantidade` | INTEGER | Quantidade em estoque |
| `valor` | REAL | Valor unitário |
| `localizacao` | TEXT | Localização física no estoque |

### Tabela `Movimentacao`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Chave primária autoincrement |
| `cod_prod` | INTEGER | Código do produto |
| `tipo` | TEXT | `Entrada` ou `Saida` |
| `quantidade` | INTEGER | Quantidade movimentada |
| `valor` | REAL | Valor no momento da movimentação |
| `User` | TEXT | Usuário responsável |
| `data` | TEXT | Data e hora da movimentação |

---

## 🔒 Segurança

- Senhas armazenadas com hash bcrypt
- Bloqueio automático após tentativas excessivas de login
- Controle de acesso por perfil (admin/viewer)
- `config.yaml` e banco de dados fora do repositório Git
- Proteção contra SQL injection via parâmetros `?` nas queries
- Firewall UFW com apenas as portas necessárias abertas
- Fail2ban para proteção contra ataques de força bruta no SSH

---

## 💾 Backup Automático

O sistema utiliza `rclone` para envio automático dos bancos de dados para o OneDrive, agendado via cron:

```bash
# Executa todo dia às 2h da manhã
0 2 * * * /home/joao/backup.sh
```

---

## 📄 Licença

Este projeto é de uso interno. Todos os direitos reservados.
