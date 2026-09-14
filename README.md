# Kwai Collector

Coletor de comentários públicos do Kwai desenvolvido em Python.

O projeto recebe a URL de uma postagem do Kwai, identifica automaticamente o `photo_id`, consulta o endpoint de comentários e salva os resultados em JSON.

## Principais recursos

- Recebe URL do Kwai diretamente
- Extrai o `photo_id` automaticamente
- Coleta até 20 comentários por postagem
- Exibe os comentários no terminal
- Salva o resultado em JSON
- Aceita também o `photo_id` diretamente
- Possui CLI própria
- Código tipado com Mypy
- Lint com Ruff
- Testes automatizados com Pytest

---

## Fluxo

```text
URL do Kwai
    ↓
extração automática do photo_id
    ↓
requisição HTTP
    ↓
comentários
    ↓
JSON
```

O fluxo principal funciona diretamente via HTTP.

**Não é necessário conectar celular ou utilizar ADB.**

---

# Tecnologias

- Python 3.11+
- Poetry
- HTTPX
- Pydantic
- Pydantic Settings
- Pytest
- Ruff
- Mypy

---

# Estrutura do projeto

```text
kwai-project/
├── kwai_collector/
│   ├── clients/
│   │   ├── comment_client.py
│   │   ├── kwai_client.py
│   │   ├── mobile_comment_client.py
│   │   └── profile_client.py
│   │
│   ├── models/
│   │   ├── comentario.py
│   │   └── postagem.py
│   │
│   ├── parsers/
│   │   ├── comment_parser.py
│   │   ├── post_parser.py
│   │   └── ui_comments.py
│   │
│   ├── providers/
│   ├── cli.py
│   └── config.py
│
├── tests/
├── samples/
├── .env.example
├── .gitignore
├── README.md
├── poetry.lock
└── pyproject.toml
```

---

# Instalação

Clone o repositório:

```bash
git clone <URL_DO_REPOSITORIO>
cd kwai-project
```

Instale as dependências:

```bash
poetry install
```

Verifique a CLI:

```bash
kwai-collector --help
```

Saída esperada:

```text
usage: kwai-collector [-h] {buscar,comments,comentarios,perfil} ...

Coletor de dados do Kwai
```

---

# Coletar comentários

## Usando uma URL

```bash
kwai-collector comments "https://m.kwai.com/photo/150001691804174/5253599077813406650"
```

A aplicação identifica automaticamente:

```text
5253599077813406650
```

como `photo_id`.

Exemplo de saída:

```text
INFO - Photo ID identificado: 5253599077813406650
INFO - Total de comentários extraídos: 20
INFO - 01. Usuario: Comentário...
INFO - 02. Usuario: Comentário...
...
INFO - Resultados gerados em: samples\comentarios_tiny.json
INFO - Execução concluída com sucesso.
```

---

## Usando somente o photo_id

Também é possível informar diretamente o ID:

```bash
kwai-collector comments 5253599077813406650
```

---

## Definindo outro arquivo de saída

```bash
kwai-collector comments \
  "https://m.kwai.com/photo/150001691804174/5253599077813406650" \
  --output samples/meus_comentarios.json
```

No PowerShell:

```powershell
kwai-collector comments "https://m.kwai.com/photo/150001691804174/5253599077813406650" --output samples/meus_comentarios.json
```

---

## Modo debug

Para visualizar informações adicionais da requisição:

```bash
kwai-collector comments 5253599077813406650 --debug
```

---

# Formato da saída

Exemplo simplificado:

```json
[
  {
    "commentId": 215913794581299780,
    "content": "Comentário de exemplo",
    "commentTime": 1787967912575,
    "userId": 150001761635871,
    "userName": "Usuario",
    "commentLikeCount": 12
  }
]
```

O arquivo padrão é:

```text
samples/comentarios_tiny.json
```

---

# Limite atual

A versão atual coleta até:

```text
20 comentários por postagem
```

A paginação de comentários não faz parte do escopo atual da entrega.

Pode ser adicionada futuramente sem alterar o fluxo principal da CLI.

---

# Outros comandos

## Buscar postagens

```bash
kwai-collector buscar "tecnologia"
```

Com mais páginas:

```bash
kwai-collector buscar "tecnologia" --paginas 3
```

Com delay:

```bash
kwai-collector buscar "tecnologia" --paginas 3 --delay 0.5
```

---

## Coletar postagens de perfil

```bash
kwai-collector perfil "@usuario"
```

Com mais páginas:

```bash
kwai-collector perfil "@usuario" --paginas 3
```

---

# Arquitetura

O projeto separa as responsabilidades em módulos:

```text
CLI
 │
 ├── Clients
 │     ├── Comment Client
 │     ├── Search Client
 │     └── Profile Client
 │
 ├── Parsers
 │
 ├── Models
 │
 └── Providers
```

## Clients

Responsáveis pelas requisições HTTP.

## Parsers

Responsáveis pela transformação dos dados recebidos.

## Models

Responsáveis pela estrutura e validação dos dados.

## CLI

Responsável pela interface de linha de comando.

Essa separação evita concentrar toda a lógica em um único arquivo.

---

# Testes

Execute:

```bash
pytest -q
```

Ou:

```bash
poetry run pytest -q
```

---

# Qualidade de código

## Ruff

```bash
ruff check kwai_collector
```

## Mypy

```bash
mypy kwai_collector
```

## Pytest

```bash
pytest -q
```

Antes de uma entrega:

```bash
ruff check kwai_collector
mypy kwai_collector
pytest -q
```

---

# Exemplo rápido

```bash
poetry install
```

```bash
kwai-collector comments "https://m.kwai.com/photo/150001691804174/5253599077813406650"
```

Resultado:

```text
URL
 ↓
photo_id
 ↓
20 comentários
 ↓
samples/comentarios_tiny.json
```

---

# Status

| Recurso | Status |
|---|---|
| Entrada por URL | ✅ |
| Extração automática de photo_id | ✅ |
| Entrada por photo_id | ✅ |
| Comentários via HTTP | ✅ |
| Até 20 comentários | ✅ |
| Saída JSON | ✅ |
| CLI `kwai-collector` | ✅ |
| Busca por palavra-chave | ✅ |
| Posts de perfil | ✅ |
| Ruff | ✅ |
| Mypy | ✅ |
| Pytest | ✅ |
| Paginação de comentários | 🔜 |

---

# Objetivo

Este projeto foi desenvolvido como desafio técnico, com foco em:

- integração HTTP;
- organização de código;
- CLI;
- tipagem estática;
- testes automatizados;
- tratamento de dados;
- versionamento com Git;
- qualidade de software.

---

## Uso responsável

O uso do projeto deve respeitar as regras da plataforma, as permissões de acesso aos dados e a legislação aplicável.