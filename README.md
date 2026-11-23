# InfraMind

**Plataforma Inteligente para Monitoramento e Otimização de Infraestruturas Sustentáveis**

> Projeto Interdisciplinar IV — Sistemas de Informação | FHO — Fundação Hermínio Ometto | 6º A / 2026

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

- Cadastro com **CPF e endereço** (CEP preenchido pelo ViaCEP) e autenticação por **JWT**
- Recuperação de senha por e-mail
- Perfil do usuário com edição dos dados e foto
- Perfis **Cidadão** e **Administrador** (Gestor Público e Equipe Técnica estão previstos nos UC-08 e UC-09)
- Registro de ocorrências com descrição, categoria, localização no mapa (Leaflet / OpenStreetMap) e imagens, inclusive **sem login** (a ocorrência anônima pode ser vinculada à conta depois)
- Ocorrências por cidade: o cidadão vê as da cidade em que mora
- **Inteligência Artificial (Google Gemini)**: análise de urgência, sugestão de descrição, análise da foto e da descrição antes de salvar e detecção de duplicatas
- Validação comunitária de ocorrências por outros usuários
- Identificação de ocorrências duplicadas por proximidade geográfica
- Cálculo de prioridade dinâmica (validações + criticidade + tempo)
- Nível de importância definido pelo administrador (Verde / Amarelo / Vermelho)
- **Prazo (SLA)** com data e hora definido pelo administrador, com indicador *no prazo / próximo / estourado*
- **Notificações** por e-mail e push (padrão Factory Method), com sino no cabeçalho e rotina agendável `processar_prazos` (UC-14)
- Painel administrativo com indicadores, estatísticas, gestão de usuários, denúncias e logs
- Histórico completo de alterações de status e de prazo
- Logs de auditoria com IP e dispositivo (login, alterações e envio de notificações)
- Feedback dos cidadãos após a resolução
- Suporte e denúncias de conteúdo, com aviso no sino dos administradores
- Backup e restauração dos dados

---

## Tecnologias

### Backend
- **Python 3.12+** (exigência do Django 6) + **Django 6.0.4**
- **Django REST Framework 3.17.1**
- **Simple JWT 5.5.0** — autenticação via tokens JWT
- **django-cors-headers 4.9.0** — controle de CORS
- **SQLite** (padrão, desenvolvimento) ou **PostgreSQL** (`USE_POSTGRES=True`, via `psycopg[binary]`)
- **Pillow 11.3.0** — processamento de imagens
- **python-dotenv** — variáveis de ambiente
- **Google Gemini 2.5 Flash** (`google-genai`) — análise inteligente de ocorrências
- **Nominatim / OpenStreetMap** — geocodificação, acessada pelo backend (padrão Adapter)

### Frontend
- **HTML5 / CSS3 / JavaScript** (vanilla), comunicação com a API via `fetch`
- **Leaflet** + OpenStreetMap — mapas
- **ViaCEP** — preenchimento do endereço no cadastro

### Padrões de projeto
- **Singleton** — `GeminiClient` (`gemini_api/client.py`)
- **Façade** — `IAProcessamentoFacade` (`gemini_api/facade.py`)
- **Adapter** — `OpenStreetMapAdapter` (`geo/adapter.py`)
- **Factory Method** — `NotificacaoFactory`, `EmailNotifFactory` e `PushNotifFactory` (`notifications/factory.py`)

---

## Estrutura do Projeto

```
InfraMind/
├── backend/
│   ├── app/                 # Configurações do Django (settings, urls)
│   ├── authentication/      # Login (token e por e-mail) e recuperação de senha
│   ├── users/               # Cadastro (CPF e endereço) e gerenciamento de usuários
│   ├── occurrences/         # Ocorrências, prazo/SLA (sla.py) e visibilidade por cidade
│   ├── categories/          # Categorias de problemas
│   ├── images/              # Upload de imagens
│   ├── validations/         # Validação comunitária e análise de IA
│   ├── feedbacks/           # Feedbacks de resolução
│   ├── history/             # Histórico de alterações
│   ├── logs/                # Logs de auditoria
│   ├── statistics_api/      # Estatísticas e indicadores
│   ├── gemini_api/          # Google Gemini (Singleton) e Façade de IA
│   ├── geo/                 # Geocodificação (Adapter para o Nominatim)
│   ├── notifications/       # Notificações (Factory Method) e comando processar_prazos
│   ├── denuncias/           # Denúncias de conteúdo e suporte (UC-13)
│   ├── scripts/             # Backup e agendamento (backup.py, instalar_cron.sh)
│   ├── manage.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── landing.html         # Página inicial pública (registro anônimo e login)
│   ├── index.html           # Portal do cidadão
│   ├── como-funciona.html   # Página informativa
│   ├── perfil.html          # Perfil do usuário (dados e foto)
│   ├── redefinir-senha.html # Redefinição de senha pelo link do e-mail
│   ├── admin.html           # Painel administrativo
│   ├── JavaScript/          # landing, index, admin, perfil, cadastro, forgot-password, drawer, como-funciona
│   ├── CSS/                 # Estilos de cada página
│   └── Images/
└── *.pdf                    # TAP, EAP, Diagrama de Rede e Matriz RACI
```

---

## Como Rodar o Projeto

### Pré-requisitos
- Python 3.12+
- Git
- PostgreSQL (opcional — por padrão o projeto usa SQLite)

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
USE_POSTGRES=False
SECRET_KEY=django-insecure-troque-esta-chave-em-producao
DEBUG=True
DB_NAME=inframind_db
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=sua_chave_gemini_aqui
```

> Com `USE_POSTGRES=False` (padrão) o banco é um arquivo SQLite (`backend/db.sqlite3`) e as variáveis `DB_*` são ignoradas. Sem `GEMINI_API_KEY` a IA usa o fallback local. E-mail e `FRONTEND_URL` são opcionais; veja as seções abaixo.

### 3. Configure o Banco de Dados (somente com PostgreSQL)

Se for usar PostgreSQL, defina `USE_POSTGRES=True` no `.env` e crie o banco:

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
```

O backend estará disponível em: `http://127.0.0.1:8000`

> O superusuário acessa o Django admin (`/admin/`). Para que ele use o painel administrativo do InfraMind (`admin.html`), defina `user_type = admin` no cadastro dele no Django admin.

### 5. Configure o Frontend

Abra a **pasta raiz do projeto** no VS Code e, em `frontend/landing.html`, clique com o botão direito → *Open with Live Server*.

> Não abra os arquivos `.html` clicando duas vezes — isso causa bloqueio de CORS pelo navegador.

O frontend estará disponível em: `http://127.0.0.1:5500/frontend/landing.html`. Depois do login, o cidadão vai para `index.html` e o administrador para `admin.html`.

> **Atenção:** se o Live Server abrir em outra porta (ex: 5501), adicione essa porta em `CORS_ALLOWED_ORIGINS` no `backend/app/settings.py`.

### 6. Confira a URL da API no Frontend

Cada script em `frontend/JavaScript/` (`index.js`, `landing.js`, `admin.js` e `como-funciona.js`) define a URL do backend na linha 4 (ou 5):

```js
const API = 'http://127.0.0.1:8000'; // altere a porta se necessário
```

### 7. Rode os testes

Dentro de `backend/`, com o venv ativado:

```bash
python manage.py test
```

---

## Inteligência Artificial — Google Gemini

O InfraMind utiliza o **Google Gemini 2.5 Flash** para enriquecer automaticamente as ocorrências registradas. O módulo `gemini_api/client.py` implementa cinco funções principais:

| Função | Descrição |
|--------|-----------|
| `get_occurrence_ai_suggestion` | Gera uma descrição técnica para a ocorrência com base no título e categoria |
| `get_category_ai_description` | Gera uma descrição automática ao criar uma nova categoria |
| `analyze_occurrence_urgency` | Analisa e pontua a urgência da ocorrência (score 0–100, níveis: low / medium / high / critical) |
| `detect_duplicate_occurrences` | Verifica se a nova ocorrência é duplicata de alguma existente na mesma área |
| `analyze_occurrence_description_and_photo` | Compara a foto com a descrição do cidadão **antes de salvar** a ocorrência |

> O timeout de rede do Gemini é de **30 segundos** por padrão (mínimo aceito: 10). Erros de rede ou timeout acionam o fallback local. Ajuste com `GEMINI_TIMEOUT_SECONDS` no `backend/.env`.

> Todas as funções possuem **fallback local** — se a chave do Gemini não estiver configurada, o sistema continua funcionando com análise por palavras-chave (urgência) e similaridade Jaccard (duplicatas).

### Análise da foto e da descrição

Ao registrar uma ocorrência (logada ou anônima), a IA analisa a foto junto com o texto. O resultado fica em `description_analysis_status`, o texto original do cidadão em `original_description` e uma dica opcional em `description_suggestion`:

| Status | Significado |
|--------|-------------|
| `MANTIDA` | A descrição combina com a foto e foi mantida |
| `CORRIGIDA` | A descrição foi ajustada com base na foto |
| `SUBSTITUIDA` | A descrição não combinava com a foto e foi substituída |
| `GERADA` | Não havia descrição e a IA a gerou a partir da foto |
| `FOTO_INSUFICIENTE` | A foto não permite identificar o problema; o app pede uma foto mais nítida |
| `FALHA` | A IA ficou indisponível ou estourou o tempo; vale a descrição do cidadão |
| `NA` | Sem análise (por exemplo, ocorrências antigas) |

A ocorrência é sempre salva, mesmo que a análise falhe.

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

## Cadastro e ocorrências por cidade

O cadastro pede **CPF** (validado pelos dígitos verificadores e único) e **endereço**: CEP, rua, número, complemento (opcional), bairro, cidade e UF. Na tela, o CEP preenche rua, bairro e cidade sozinho pelo ViaCEP; sem internet, é só digitar.

- O **cidadão** vê as ocorrências da cidade onde mora (cidade + UF do cadastro) e as que ele mesmo registrou. O **administrador** vê todas.
- A cidade de cada ocorrência vem da localização marcada no mapa; sem ela, vale a cidade do cadastro de quem registrou.
- O cadastro público sempre cria **cidadão**. Administradores são criados pelo Django admin (`python manage.py createsuperuser`, depois `user_type = admin`).
- CPF e endereço só aparecem para o próprio usuário e para administradores.
- Usuários e ocorrências criados **antes** deste recurso não têm cidade: o cidadão antigo só vê as próprias ocorrências até um administrador preencher a cidade e a UF dele no Django admin, e as ocorrências antigas só aparecem para quem as criou e para administradores.

---

## Prazo (SLA) das ocorrências

O administrador define o **prazo para resolver** ao editar a ocorrência no painel: uma data e, opcionalmente, um horário. **Sem horário, o prazo vai até 23:59:59** do dia escolhido. Para remover o prazo, é só limpar os campos.

- O prazo fica em `prazo_definido` (data e hora). Quando não há `prazo_definido`, vale o tempo estimado em horas (`estimated_time`) contado a partir da criação; sem nenhum dos dois, a ocorrência não tem prazo.
- Cada alteração de prazo entra no histórico da ocorrência (ex.: `Prazo alterado: sem prazo → 21/10/2026 18:00`).
- A API devolve `sla_deadline` (limite) e `sla_status`: `ok`, `proximo` (80% do prazo já consumido) ou `estourado`. Ocorrências resolvidas, fechadas ou sem prazo vêm com `sla_status` nulo.
- O painel administrativo mostra a coluna **Prazo** nas tabelas e um alerta vermelho no dashboard quando há ocorrências com prazo estourado.
- Os horários seguem o fuso `America/Sao_Paulo`.

Exemplo para definir o prazo (Admin):

```bash
PATCH /api/v1/occurrences/<id>/
Authorization: Bearer <token_admin>
Content-Type: application/json

{ "prazo_definido": "2026-10-21T18:00" }
```

Enviar só a data (`"2026-10-21"`) equivale a `23:59:59` desse dia; `null` remove o prazo.

---

## E-mail e rotina de prazos (UC-14)

Sem configuração, os e-mails são **simulados**: aparecem no console do servidor. Para enviar de verdade, preencha no `backend/.env` (modelo em `.env.example`). Exemplo com Gmail, usando uma [senha de app](https://myaccount.google.com/apppasswords) (exige verificação em duas etapas):

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu_email@gmail.com
EMAIL_HOST_PASSWORD=sua_senha_de_app
DEFAULT_FROM_EMAIL=InfraMind <seu_email@gmail.com>
```

Reinicie o servidor e teste, dentro de `backend/` com o venv ativado:

```bash
python manage.py shell -c "from django.core.mail import send_mail; print(send_mail('Teste InfraMind', 'Funcionou!', None, ['seu_email@gmail.com']))"
```

Resultado `1` é e-mail enviado. Um erro de autenticação indica usuário ou senha de app errados.

### Agendar a verificação de prazos

A rotina `python manage.py processar_prazos` avisa sobre prazos estourados, prazos em 80% e mudanças de status, e reenvia o que falhou. Para rodar sozinha a cada 30 minutos no Linux/Mac:

```bash
bash scripts/instalar_cron.sh                # a cada 30 minutos
bash scripts/instalar_cron.sh "0 * * * *"    # outra frequência (formato do cron)
bash scripts/instalar_cron.sh --remover      # tira o agendamento
```

A saída fica em `backend/processar_prazos.log`. No Windows, crie uma tarefa no Agendador de Tarefas que execute `venv\Scripts\python.exe manage.py processar_prazos` dentro de `backend`.

### Notificações e Factory Method

As notificações são criadas pelo padrão **Factory Method** (`notifications/factory.py`): `NotificacaoFactory` define `criar_notificacao()` e `notificar()`, e `EmailNotifFactory` e `PushNotifFactory` fornecem cada canal. O **e-mail** é enviado por SMTP (ou simulado no console); o **push** é simulado no console.

| Tipo | Quando é criada |
|------|-----------------|
| `prazo_estourado` | O prazo da ocorrência passou sem ela ser resolvida |
| `aviso_prazo` | 80% do prazo consumido |
| `status_change` | O status da ocorrência mudou (avisa o dono) |
| `recuperacao_senha` | Pedido de recuperação de senha |
| `geral` | Nova denúncia: avisa no sino todos os administradores (canal push), menos quem a abriu |

- O aviso de **prazo estourado** vai para os administradores e para o dono da ocorrência (sem repetir quem é as duas coisas); o **aviso de 80%** vai só para os administradores. Enquanto Gestor Público e Equipe Técnica não existirem como perfis, quem recebe é todo administrador.
- Cada envio e cada falha são gravados no log de auditoria (`notification_sent` e `notification_failed`), e a falha não interrompe o fluxo; a rotina reenvia as que falharam.
- `GET /api/v1/notifications/` lista as notificações do usuário e `POST /api/v1/notifications/<id>/read/` marca como lida. O sino no cabeçalho do portal exibe essas notificações.

---

## Recuperação de senha

Na tela de login, **Esqueci minha senha** pede o e-mail da conta e envia um link que vale por 1 hora e só funciona uma vez.

| Endpoint | Corpo | O que faz |
|----------|-------|-----------|
| `POST /authentication/password-reset/` | `{"email"}` | Envia o link. A resposta é sempre a mesma, exista o e-mail ou não. Limite de 10 pedidos por hora por IP. |
| `POST /authentication/password-reset/confirm/` | `{"uid", "token", "password"}` | Define a nova senha (passa pelas regras de senha do Django). |

O link aponta para `FRONTEND_URL` (padrão `http://127.0.0.1:5500/frontend/index.html`). O `index.html` e o `redefinir-senha.html` leem os parâmetros `reset_uid` e `reset_token` do link. Se o frontend rodar em outro endereço, ajuste `FRONTEND_URL` no `.env`. Com o e-mail simulado, o link aparece no console do servidor.

---

## Suporte e denúncias

O menu **Suporte / Denúncia** abre um formulário para relatar um problema técnico (`bug`). Na página de uma ocorrência, **Denunciar conteúdo** registra um `conteudo_inadequado` apontando para ela.

| Endpoint | O que faz |
|----------|-----------|
| `GET /api/v1/denuncias/` | O cidadão vê as suas; o administrador vê todas |
| `POST /api/v1/denuncias/` | Registra `{"tipo", "descricao", "occurrence"}` (a ocorrência só é obrigatória em conteúdo inadequado) |
| `PATCH /api/v1/denuncias/<id>/` | Só administrador: muda o `status` (`aberta`, `em_analise`, `resolvida`) |

Cada denúncia nova gera um aviso no sino de todos os administradores (exceto de quem a abriu). O administrador também acompanha e altera as denúncias pelo Django admin (`/admin/`).

---

## Backup e restauração

O script `backend/scripts/backup.py` (RNF09) cria uma pasta `backup_AAAAMMDD_HHMMSS/` com:

| Item | Conteúdo |
|------|----------|
| `dados.json` | Todos os dados do banco, gerados com `dumpdata` (SQLite ou PostgreSQL) |
| `media/` | Cópia das imagens enviadas pelos usuários |

### Gerar um backup

Dentro de `backend/`, com o venv ativado:

```bash
python scripts/backup.py                       # grava em backend/backups/
python scripts/backup.py --destino /mnt/disco  # grava em outra pasta
```

Para rodar todo dia às 03:00 no Linux/Mac, adicione ao `crontab -e`:

```
0 3 * * * cd /caminho/InfraMind/backend && venv/bin/python scripts/backup.py
```

> A pasta `backend/backups/` está no `.gitignore`: o backup contém e-mails e hashes de senha e **não deve ir para o GitHub**. Guarde uma cópia fora do computador do projeto.

### Restaurar um backup

Com o banco já criado e vazio (`python manage.py migrate`):

```bash
python manage.py loaddata backups/backup_AAAAMMDD_HHMMSS/dados.json
cp -r backups/backup_AAAAMMDD_HHMMSS/media/. media/
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
    "last_name": "Oliveira",
    "cpf": "52998224725",
    "cep": "13500000",
    "numero": "100",
    "bairro": "Centro",
    "cidade": "Rio Claro",
    "uf": "SP"
}
```

> O cadastro exige CPF válido, CEP, número, bairro, cidade e UF; a senha deve ter ao menos 8 caracteres.

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
| POST | `/api/v1/users/register/` | Cadastro de cidadão (exige CPF e endereço) | Público |
| POST | `/authentication/token/` | Login — obtém token JWT | Público |
| POST | `/authentication/token/refresh/` | Renova o token de acesso | Público |
| POST | `/authentication/token/verify/` | Verifica validade do token | Público |
| POST | `/authentication/login/` | Login alternativo por e-mail | Público |
| POST | `/authentication/password-reset/` | Envia o link de recuperação de senha | Público |
| POST | `/authentication/password-reset/confirm/` | Define a nova senha | Público |
| GET | `/api/v1/users/` | Lista usuários | Token |
| GET/PUT/DELETE | `/api/v1/users/<id>/` | Detalhe, edição e exclusão | Token |
| GET/PATCH | `/api/v1/users/me/` | Perfil do próprio usuário (inclui `profile_picture`; `user_type` é somente leitura) | Token |
| GET/POST | `/api/v1/occurrences/` | Lista e cria ocorrências | Token |
| GET/PUT/PATCH/DELETE | `/api/v1/occurrences/<id>/` | Detalhe, edição e exclusão | Token |
| GET | `/api/v1/occurrences/nearby/<lat>/<lng>/` | Ocorrências próximas | Token |
| POST | `/api/v1/occurrences/geocode/` | Endpoint legado: só valida o campo `address` (a geocodificação real está em `/api/v1/geo/`) | Token |
| POST | `/api/v1/occurrences/anonymous/` | Registra ocorrência sem login | Público |
| POST | `/api/v1/occurrences/anonymous/claim/` | Vincula ocorrências anônimas à conta | Token |
| GET | `/api/v1/occurrences/<id>/history/` | Histórico de alterações | Token |
| GET/POST | `/api/v1/categories/` | Lista e cria categorias | Público |
| GET/PUT/DELETE | `/api/v1/categories/<id>/` | Detalhe, edição e exclusão | Público |
| GET/POST | `/api/v1/images/` | Lista e faz upload de imagens | Token |
| GET/PUT/DELETE | `/api/v1/images/<id>/` | Detalhe, edição e exclusão | Token |
| POST | `/api/v1/images/anonymous/` | Upload de imagem de ocorrência anônima | Público |
| GET/POST | `/api/v1/validations/` | Lista e cria validações | Token |
| POST | `/api/v1/validations/occurrence/<id>/` | Valida uma ocorrência específica | Token |
| POST | `/api/v1/validations/ai-analyze/` | Análise de urgência via IA | Token |
| GET | `/api/v1/validations/ai-prioritized/` | Lista priorizada pela IA | Token (Admin) |
| GET/POST | `/api/v1/feedbacks/` | Lista e cria feedbacks | Token |
| GET/PUT/DELETE | `/api/v1/feedbacks/<id>/` | Detalhe, edição e exclusão | Token |
| GET | `/api/v1/geo/reverse/` | Geocodificação reversa (coordenadas → endereço) | Público |
| GET | `/api/v1/geo/search/` | Geocodificação direta (endereço → coordenadas) | Público |
| GET | `/api/v1/notifications/` | Notificações do usuário | Token |
| POST | `/api/v1/notifications/<id>/read/` | Marca a notificação como lida | Token |
| GET/POST | `/api/v1/denuncias/` | Lista e registra denúncias | Token |
| PATCH | `/api/v1/denuncias/<id>/` | Altera o status da denúncia | Token (Admin) |
| GET | `/api/v1/logs/` | Lista logs de auditoria | Token (Admin) |
| GET | `/api/v1/statistics/` | Contagens gerais (usuários, ocorrências e categorias) | Público |

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
  "last_name": "Exemplo",
  "cpf": "52998224725",
  "cep": "13500000",
  "numero": "100",
  "bairro": "Centro",
  "cidade": "Rio Claro",
  "uf": "SP"
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

Para enviar uma foto na criação, use `multipart/form-data` com o campo `image`; a IA analisa a foto e a descrição antes de salvar.

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

Por padrão o sistema usa **SQLite**; com `USE_POSTGRES=True` usa **PostgreSQL**. As migrations (`python manage.py migrate`) criam as tabelas a partir dos modelos:

| Modelo (app) | Descrição |
|--------------|-----------|
| `User` (`users`) | Usuários e perfis (cidadão / administrador), com CPF, endereço e foto de perfil |
| `Occurrence` (`occurrences`) | Problemas urbanos com geolocalização, cidade/UF, prazo, urgência e análise da IA |
| `Category` (`categories`) | Tipos de problemas (buraco, iluminação, lixo, etc.) |
| `Image` (`images`) | Fotos vinculadas às ocorrências |
| `Validation` (`validations`) | Confirmações comunitárias |
| `Feedback` (`feedbacks`) | Avaliações pós-resolução com nota e tempo real de solução |
| `OccurrenceHistory` (`history`) | Rastreabilidade das alterações de status, prioridade e prazo |
| `Log` (`logs`) | Auditoria técnica com IP e dispositivo |
| `Notificacao` (`notifications`) | Notificações por canal (e-mail / push), tipo e status de envio |
| `Denuncia` (`denuncias`) | Denúncias de conteúdo e relatos de problemas técnicos |

**Relacionamentos principais:**
- `User` 1:N `Occurrence`
- `Category` 1:N `Occurrence`
- `Occurrence` 1:N `Image`
- `User` N:N `Occurrence` (via `Validation`)
- `Occurrence` 1:N `OccurrenceHistory`
- `Occurrence` N:1 `Occurrence` (`duplicate_of`, ocorrência original)
- `User` 1:N `Notificacao` (a ocorrência é opcional)
- `User` 1:N `Denuncia` (a ocorrência é opcional)
- `User` 1:N `Log`

**Regras de negócio:**
- Um usuário não pode validar sua própria ocorrência
- Cada usuário pode validar uma ocorrência apenas uma vez
- A prioridade é calculada dinamicamente (validações + criticidade da categoria + tempo sem resolução)
- Ocorrências duplicadas são vinculadas a uma "Ocorrência Pai" e somam validações ao registro principal
- O tempo real de solução é calculado automaticamente ao marcar status como `resolved`
- O cidadão só vê ocorrências da própria cidade e as que ele registrou; o administrador vê todas
- O prazo (`prazo_definido`) tem prioridade sobre o tempo estimado em horas

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
- Autenticação via **JWT** (Bearer Token; acesso expira em 60 min e o refresh token em 1 dia)
- Controle de acesso por perfil (**RBAC**): logs, estatísticas administrativas, denúncias (alteração de status) e ocorrências priorizadas pela IA são restritos a administradores
- CPF e endereço visíveis apenas para o próprio usuário e para administradores
- Logs de auditoria com IP e metadados do dispositivo (inclui login e envio de notificações)
- Recuperação de senha com link de uso único e validade de 1 hora, limitada a 10 pedidos por hora por IP
- Campo `importance_color` restrito a administradores
- Variáveis sensíveis gerenciadas via `.env` (nunca versionadas); backups fora do Git

---

## Links do Projeto

- **Repositório:** [github.com/GabrielGioppo/InfraMind](https://github.com/GabrielGioppo/InfraMind)
- **Cronograma:** [github.com/users/GabrielGioppo/projects/3](https://github.com/users/GabrielGioppo/projects/3)

## Documentação

- [📄 TAP – InfraMind](./TAP_InfraMind_Final_.pdf)
- [📄 EAP – InfraMind](./EAP_InfraMind_.pdf)
- [📄 Diagrama de Rede PDM – InfraMind](./Diagrama_de_Rede_PDM_InfraMind.pdf)
- [📄 Matriz RACI – InfraMind](./Matriz%20RACI.pdf)

---

## Licença

Projeto acadêmico desenvolvido para o Projeto Interdisciplinar IV — Sistemas de Informação — FHO 2026.
