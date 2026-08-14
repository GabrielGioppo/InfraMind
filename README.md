# InfraMind

**Plataforma Inteligente para Monitoramento e Otimização de Infraestruturas Sustentáveis**

> Projeto Interdisciplinar III — Sistemas de Informação | FHO — Fundação Hermínio Ometto | 5º A / 2026

---

## Sobre o Projeto

O **InfraMind** é uma plataforma web de gestão de ocorrências urbanas que permite que cidadãos registrem problemas de infraestrutura (buracos, falhas na iluminação, acúmulo de resíduos, etc.) e que gestores públicos acompanhem, validem, priorizem e gerenciem essas demandas por meio de um painel administrativo.

O sistema está alinhado à **ODS 9 — Indústria, Inovação e Infraestrutura**, promovendo o uso de tecnologia para modernizar a gestão urbana com dados confiáveis e transparentes.

---

## Equipe

| RA | Nome |
|----|------|
| 116919 | Gabriel Gioppo de Farias |
| 117032 | Vinicius Peres |
| 113244 | Luciano dos Santos Lima da Silva |
| 116345 | Matheus Augusto Kilian |
| 117255 | Davi do Amaral de Araujo |
| 117439 | Vinicius Antonio de Assis |

---

## Funcionalidades

- Cadastro e autenticação de usuários (JWT)
- Diferenciação de perfis: **Cidadão** e **Administrador**
- Registro de ocorrências com descrição, categoria, localização geográfica e imagens
- Validação comunitária de ocorrências por outros usuários
- Identificação de ocorrências duplicadas por proximidade geográfica
- Cálculo de prioridade dinâmica (validações + criticidade + tempo)
- Definição de nível de importância pelo administrador (Verde = Normal / Amarelo = Um pouco importante / Vermelho = Importante)
- Painel administrativo com indicadores de desempenho e estatísticas
- Histórico completo de alterações de status
- Logs técnicos com IP e dispositivo do usuário (audit trail)
- Feedback dos cidadãos após resolução
- **Inteligência Artificial via Google Gemini** (análise de urgência, sugestão de descrição e detecção de duplicatas)

---

## Tecnologias

### Backend
- **Python 3.10+** + **Django 6.0.4**
- **Django REST Framework 3.17.1**
- **Simple JWT 5.5.0** — autenticação via tokens JWT
- **django-cors-headers 4.9.0** — controle de CORS
- **PostgreSQL** — banco de dados (via `psycopg2-binary`)
- **Pillow 11.3.0** — processamento de imagens
- **python-dotenv** — gerenciamento de variáveis de ambiente
- **Google Gemini 2.5 Flash** (`google-genai`) — análise inteligente de ocorrências

### Frontend
- **HTML5 / CSS3 / JavaScript** (vanilla)
- Comunicação com a API via `fetch`

---

## Estrutura do Projeto

```
InfraMind/
├── backend/
│   ├── app/                 # Configurações do Django (settings, urls)
│   ├── authentication/      # Login por e-mail e tokens JWT
│   ├── users/               # Cadastro e gerenciamento de usuários
│   ├── occurrences/         # Registro e gestão de ocorrências
│   ├── categories/          # Categorias de problemas
│   ├── images/              # Upload de imagens
│   ├── validations/         # Validação comunitária
│   ├── feedbacks/           # Feedbacks de resolução
│   ├── history/             # Histórico de alterações de status
│   ├── logs/                # Logs de auditoria
│   ├── statistics_api/      # Estatísticas e indicadores do painel
│   ├── gemini_api/          # Integração com Google Gemini
│   ├── manage.py
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── app.js
    ├── styles.css
    ├── admin.html
    ├── admin.js
    └── admin.css
```

---

## Como Rodar o Projeto

### Pré-requisitos
- Python 3.10+
- PostgreSQL instalado e rodando
- Git

### 1. Clone o repositório

```bash
git clone https://github.com/GabrielGioppo/InfraMind.git
cd InfraMind
```

### 2. Configure as variáveis de ambiente

Dentro da pasta `backend/`, copie o arquivo de exemplo e preencha com seus dados:

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
SECRET_KEY=django-insecure-troque-esta-chave-em-producao
DEBUG=True
DB_NAME=inframind_db
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=sua_chave_gemini_aqui
```

### 3. Configure o Banco de Dados

Crie o banco de dados no PostgreSQL:

```sql
CREATE DATABASE inframind_db;
```

### 4. Configure o Backend

```bash
cd backend

# Crie e ative o ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Aplique as migrations
python manage.py migrate

# Crie um superusuário (administrador)
python manage.py createsuperuser

# Inicie o servidor (porta padrão 8000)
python manage.py runserver

# Ou em uma porta específica
python manage.py runserver 9000
```

O backend estará disponível em: `http://127.0.0.1:8000`

### 5. Configure o Frontend

Abra o arquivo `frontend/index.html` com o **Live Server** do VS Code (clique com botão direito → *Open with Live Server*).

> Não abra o `index.html` clicando duas vezes — isso causa bloqueio de CORS pelo navegador.

O frontend estará disponível em: `http://127.0.0.1:5500`

> **Atenção:** Se o Live Server abrir em outra porta (ex: 5501), adicione essa porta em `CORS_ALLOWED_ORIGINS` no `backend/app/settings.py`.

### 6. Ajuste a URL da API no Frontend

No arquivo `frontend/app.js`, linha 4, confirme a porta onde o backend está rodando:

```js
const API_BASE = 'http://127.0.0.1:8000'; // altere a porta se necessário
```

---

## Inteligência Artificial — Google Gemini

O InfraMind utiliza o **Google Gemini 2.5 Flash** para enriquecer automaticamente as ocorrências registradas. O módulo `gemini_api/client.py` implementa quatro funções principais:

| Função | Descrição |
|--------|-----------|
| `get_occurrence_ai_suggestion` | Gera uma descrição técnica para a ocorrência com base no título e categoria |
| `get_category_ai_description` | Gera uma descrição automática ao criar uma nova categoria |
| `analyze_occurrence_urgency` | Analisa e pontua a urgência da ocorrência (score 0–100, níveis: low / medium / high / critical) |
| `detect_duplicate_occurrences` | Verifica se a nova ocorrência é duplicata de alguma existente na mesma área |

> Todas as funções possuem **fallback local** — se a chave do Gemini não estiver configurada, o sistema continua funcionando com análise por palavras-chave (urgência) e similaridade Jaccard (duplicatas).

### Obtendo a chave da API Gemini

1. Acesse [aistudio.google.com](https://aistudio.google.com) e gere uma chave gratuita em **"Get API Key"**
2. Adicione a chave no arquivo `backend/.env`:

```env
GEMINI_API_KEY=sua_chave_aqui
```

3. Reinicie o servidor Django

### Testando a IA

Com o servidor rodando, execute no terminal (dentro de `backend/` com o venv ativado):

```bash
python -c "
from gemini_api.client import (
    get_occurrence_ai_suggestion,
    get_category_ai_description,
    analyze_occurrence_urgency,
    detect_duplicate_occurrences,
)
import json

print('=== 1. Sugestão de descrição ===')
print(get_occurrence_ai_suggestion('Buraco na pista', 'Infraestrutura'))

print('\n=== 2. Descrição de categoria ===')
print(get_category_ai_description('Iluminação Pública'))

print('\n=== 3. Análise de urgência ===')
print(json.dumps(analyze_occurrence_urgency('Acidente com feridos', 'Dois carros colidiram, há feridos no local'), indent=2, ensure_ascii=False))

print('\n=== 4. Detecção de duplicatas ===')
existentes = [
    {'id': 1, 'title': 'Buraco na Rua A', 'description': 'Buraco grande no asfalto'},
]
print(json.dumps(detect_duplicate_occurrences('Buraco enorme na Rua A', 'Buraco no meio da rua', existentes), indent=2, ensure_ascii=False))
"
```

---

## Autenticação no Postman

O sistema utiliza **JWT (Bearer Token)** para autenticação.

### Obtendo o Token

**Admin:**

```
POST http://127.0.0.1:8000/authentication/token/
Content-Type: application/json

{
    "username": "admin",
    "password": "sua_senha"
}
```

**Cidadão — primeiro cadastre o usuário:**

```
POST http://127.0.0.1:8000/api/v1/users/register/
Content-Type: application/json

{
    "username": "user",
    "password": "Senha123!",
    "email": "user@email.com",
    "first_name": "User",
    "last_name": "Oliveira"
}
```

Depois faça login na mesma rota `/authentication/token/` com as credenciais criadas e copie o campo `access`.

### Usando o Token

Na aba **Authorization** do Postman, selecione **Bearer Token** e cole o valor copiado.

> O token expira em **60 minutos**. Use `/authentication/token/refresh/` com o `refresh` token para renová-lo.

### Dica — Variáveis de Ambiente no Postman

| Variable | Value |
|----------|-------|
| `token_admin` | *(cole o access do admin)* |
| `token_user` | *(cole o access do user)* |

Use `{{token_admin}}` ou `{{token_user}}` no campo Bearer Token.

---

## Endpoints da API

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/v1/users/register/` | Cadastro de novo usuário | Público |
| POST | `/authentication/token/` | Login — obtém token JWT | Público |
| POST | `/authentication/token/refresh/` | Renova o token de acesso | Público |
| POST | `/authentication/token/verify/` | Verifica validade do token | Público |
| POST | `/authentication/login/` | Login alternativo por e-mail | Público |
| GET | `/api/v1/users/` | Lista todos os usuários | Token |
| GET/PUT/DELETE | `/api/v1/users/<id>/` | Detalhe, edição e exclusão | Token |
| GET/POST | `/api/v1/occurrences/` | Lista e cria ocorrências | Token |
| GET/PUT/DELETE | `/api/v1/occurrences/<id>/` | Detalhe, edição e exclusão | Token |
| GET | `/api/v1/occurrences/nearby/<lat>/<lng>/` | Ocorrências próximas | Token |
| GET | `/api/v1/occurrences/<id>/history/` | Histórico de alterações | Token |
| POST | `/api/v1/occurrences/ai-analyze/` | Análise de urgência via IA | Token |
| GET | `/api/v1/occurrences/ai-prioritized/` | Lista priorizada pela IA (Admin) | Token (Admin) |
| GET/POST | `/api/v1/categories/` | Lista e cria categorias | Token |
| GET/PUT/DELETE | `/api/v1/categories/<id>/` | Detalhe, edição e exclusão | Token |
| GET/POST | `/api/v1/images/` | Lista e faz upload de imagens | Token |
| GET/PUT/DELETE | `/api/v1/images/<id>/` | Detalhe, edição e exclusão | Token |
| GET/POST | `/api/v1/validations/` | Lista e cria validações | Token |
| POST | `/api/v1/validations/occurrence/<id>/` | Valida uma ocorrência específica | Token |
| GET/POST | `/api/v1/feedbacks/` | Lista e cria feedbacks | Token |
| GET/PUT/DELETE | `/api/v1/feedbacks/<id>/` | Detalhe, edição e exclusão | Token |
| GET | `/api/v1/logs/` | Lista logs de auditoria | Token (Admin) |
| GET | `/api/v1/statistics/` | Indicadores e estatísticas do painel | Token (Admin) |

### Exemplos

**Cadastro de usuário:**
```bash
POST /api/v1/users/register/
Content-Type: application/json

{
  "username": "user_exemplo",
  "password": "SuaSenha123!",
  "email": "user@email.com",
  "first_name": "User",
  "last_name": "Exemplo"
}
```

**Registro de ocorrência:**
```bash
POST /api/v1/occurrences/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Buraco na Rua das Flores",
  "description": "Buraco de grande porte no meio da via",
  "category": 1,
  "latitude": -23.5505,
  "longitude": -46.6333,
  "address": "Rua das Flores, 100"
}
```

**Definir nível de importância (Admin):**
```bash
PATCH /api/v1/occurrences/<id>/
Authorization: Bearer <token_admin>
Content-Type: application/json

{
  "importance_color": "red"
}
```

---

## Banco de Dados

O sistema utiliza **PostgreSQL** com as seguintes tabelas:

| Tabela | Descrição |
|--------|-----------|
| `Usuario` | Dados e perfis dos usuários (cidadão / administrador) |
| `Ocorrencia` | Registros de problemas urbanos com geolocalização |
| `Categoria` | Tipos de problemas (buraco, iluminação, lixo, etc.) |
| `Imagem` | Evidências fotográficas vinculadas às ocorrências |
| `Validacao` | Confirmações comunitárias com tipo e comentário |
| `Feedback` | Avaliações pós-resolução com nota e tempo real de solução |
| `Historico_Ocorrencia` | Rastreabilidade completa de alterações de status |
| `Log` | Auditoria técnica com IP e dispositivo do usuário |

**Relacionamentos principais:**
- `Usuario` 1:N `Ocorrencia`
- `Categoria` 1:N `Ocorrencia`
- `Ocorrencia` 1:N `Imagem`
- `Usuario` N:N `Ocorrencia` (via `Validacao`)
- `Ocorrencia` 1:N `Historico_Ocorrencia`
- `Usuario` 1:N `Log`

**Regras de negócio:**
- Um usuário não pode validar sua própria ocorrência
- Cada usuário pode validar uma ocorrência apenas uma vez
- A prioridade é calculada dinamicamente (validações + criticidade da categoria + tempo sem resolução)
- Ocorrências duplicadas são vinculadas a uma "Ocorrência Pai" e somam validações ao registro principal
- O tempo real de solução é calculado automaticamente ao marcar status como `resolved`

---

## Nível de Importância das Ocorrências

O campo `importance_color` é definido **exclusivamente pelo administrador** após análise da ocorrência.

| Valor | Cor | Significado |
|-------|-----|-------------|
| `green` | 🟢 Verde | Normal |
| `yellow` | 🟡 Amarelo | Um pouco importante |
| `red` | 🔴 Vermelho | Importante |

---

## Segurança

- Senhas criptografadas com **PBKDF2**
- Autenticação via **JWT** (Bearer Token, expira em 60 min)
- Controle de acesso por perfil (**RBAC**)
- Logs de auditoria com IP e metadados do dispositivo
- Campo `importance_color` restrito a administradores
- Variáveis sensíveis gerenciadas via `.env` (nunca versionadas)

---

## Links do Projeto

- **Repositório:** [github.com/GabrielGioppo/InfraMind](https://github.com/GabrielGioppo/InfraMind)
- **Cronograma:** [github.com/users/GabrielGioppo/projects/1](https://github.com/users/GabrielGioppo/projects/1)

---

## Licença

Projeto acadêmico desenvolvido para o Projeto Interdisciplinar III — Sistemas de Informação — FHO 2026.
