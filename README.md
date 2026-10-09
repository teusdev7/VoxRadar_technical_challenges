# Kwai Collector

Coletor de dados públicos do Kwai desenvolvido em Python, com foco em organização de código, tipagem estática, tratamento de falhas, paginação e testes automatizados.

O projeto disponibiliza uma interface de linha de comando para:

- buscar postagens por palavra-chave;
- coletar postagens públicas de um perfil;
- coletar comentários principais de uma publicação;
- executar coletas agregadas de postagens e comentários.

Os resultados são normalizados e armazenados em JSON.

---

## Requisitos

- Python 3.11+
- Poetry

Principais bibliotecas utilizadas:

- HTTPX
- Pydantic
- Pydantic Settings
- Pytest
- Ruff
- Mypy

---

## Instalação

Clone o repositório e acesse a pasta do projeto:

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
poetry run kwai-collector --help
```

---

## Uso

A aplicação possui quatro comandos principais:

```text
buscar
perfil
comentarios
coletar
```

### Buscar postagens

Busca postagens relacionadas a uma palavra-chave:

```powershell
poetry run kwai-collector buscar "sertanejo" --delay 2
```

Também é possível coletar os comentários das postagens encontradas:

```powershell
poetry run kwai-collector buscar "sertanejo" `
    --with-comments `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

Para limitar a quantidade de comentários por postagem:

```powershell
poetry run kwai-collector buscar "sertanejo" `
    --with-comments `
    --max-comments 50 `
    --request-interval 2 `
    --delay 2
```

---

### Coletar postagens de um perfil

Coleta as postagens públicas disponíveis para um perfil:

```powershell
poetry run kwai-collector perfil "henriqueejuliano" --delay 2
```

O fluxo percorre as páginas disponíveis até o encerramento indicado pela fonte de dados e remove postagens duplicadas durante a coleta.

---

### Coletar comentários

Recebe a URL de uma publicação e coleta seus comentários principais:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments 50 `
    --request-interval 2
```

Para seguir a paginação até o fim reconhecido:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2
```

`--max-comments` aceita um inteiro positivo ou:

```text
todos
```

O valor representa um limite máximo. Caso existam menos comentários disponíveis, a coleta termina com a quantidade encontrada.

A contagem considera comentários principais.

---

### Retomar uma coleta

Durante uma coleta paginada, o progresso pode ser salvo em checkpoint.

Caso a execução seja interrompida:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2 `
    --resume
```

A retomada:

- utiliza o cursor salvo;
- preserva comentários já coletados;
- remove registros duplicados;
- continua a partir do progresso disponível.

Após uma conclusão bem-sucedida, o checkpoint correspondente é removido.

---

### Coleta agregada

O comando `coletar` reúne postagens e comentários em uma única execução:

```powershell
poetry run kwai-collector coletar `
    "henriqueejuliano" `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

Esse fluxo processa até 10 postagens por execução.

Para coletar somente as postagens disponíveis de um perfil, utilize `perfil`.

---

## Fluxo de comentários

Para coletas maiores, retomadas ou paginação completa, o projeto utiliza uma abstração de preparação de requisições mobile.

O código público não implementa mecanismos privados de autenticação da plataforma.

A preparação da requisição é delegada à interface `MobileRequestProvider`, permitindo utilizar uma integração autorizada sem acoplar o restante da aplicação ao mecanismo de autenticação.

Fluxo simplificado:

```text
CLI
 |
 v
MobileCommentProvider
 |
 v
MobileRequestProvider
 |
 v
LiveCommentClient
 |
 v
HTTP
 |
 v
Parser
 |
 v
JSON
```

---

## Configuração mobile

Uma fonte autorizada de preparação de requisições pode ser configurada por variáveis de ambiente:

```text
KWAI_MOBILE_AUTH_ENDPOINT
KWAI_MOBILE_AUTH_TOKEN
KWAI_MOBILE_AUTH_TIMEOUT
```

Exemplo:

```powershell
$env:KWAI_MOBILE_AUTH_ENDPOINT = "http://localhost:8000/prepare"
$env:KWAI_MOBILE_AUTH_TOKEN = "TOKEN_DO_SERVICO"
```

O token é utilizado somente para autenticar o coletor junto ao serviço configurado.

Credenciais reais não devem ser versionadas.

---

## Campos adicionais

Campos adicionais podem ser configurados para query, body e headers:

```text
KWAI_MOBILE_QUERY_FIELDS
KWAI_MOBILE_BODY_FIELDS
KWAI_MOBILE_HEADER_FIELDS
```

Os valores devem ser objetos JSON compostos por strings.

Exemplo:

```powershell
$env:KWAI_MOBILE_QUERY_FIELDS = '{"language":"pt-br"}'
$env:KWAI_MOBILE_BODY_FIELDS = '{"os":"android"}'
$env:KWAI_MOBILE_HEADER_FIELDS = '{"Accept":"application/json"}'
```

Use somente dados e integrações para os quais exista autorização de acesso.

---

## Rate limit e retry

O intervalo entre requisições pode ser controlado pela CLI:

```text
--request-interval 2
```

ou por configuração:

```text
KWAI_MOBILE_PAGE_DELAY
```

O projeto também possui retry com backoff para falhas temporárias.

Variáveis disponíveis:

```text
KWAI_MAX_TENTATIVAS
KWAI_BACKOFF_BASE
```

Exemplo:

```powershell
$env:KWAI_MAX_TENTATIVAS = "3"
$env:KWAI_BACKOFF_BASE = "1"
```

Quando disponível, um cabeçalho `Retry-After` válido pode ser considerado antes de uma nova tentativa.

---

## Saídas

Os arquivos são armazenados por padrão em:

```text
samples/
```

Exemplos:

```text
samples/busca_sertanejo.json
samples/busca_sertanejo_comentarios.json
samples/<usuario>_posts.json
samples/<usuario>_comentarios.json
samples/<photo_id>_comentarios.json
```

Durante uma coleta paginada também pode existir temporariamente:

```text
samples/<photo_id>_comentarios.coleta.json
```

Esse arquivo representa o checkpoint da coleta.

---

## Estrutura do projeto

```text
kwai-project/
|
|-- kwai_collector/
|   |-- clients/
|   |-- models/
|   |-- parsers/
|   |-- providers/
|   |-- security/
|   |-- cli.py
|   |-- cli_builders.py
|   |-- cli_collect.py
|   |-- cli_commands.py
|   |-- cli_comments.py
|   |-- cli_parsers.py
|   |-- cli_utils.py
|   |-- config.py
|   `-- keyword_comment_collection.py
|
|-- tests/
|-- samples/
|-- docs/
|-- .env.example
|-- .gitignore
|-- README.md
|-- poetry.lock
`-- pyproject.toml
```

---

## Arquitetura

O projeto separa as principais responsabilidades da aplicação.

### CLI

Responsável por:

- interpretação dos argumentos;
- validação de entrada;
- orquestração dos comandos;
- mensagens e códigos de retorno.

### Clients

Responsáveis pela comunicação HTTP e obtenção dos dados brutos.

### Providers

Concentram abstrações relacionadas à coleta, preparação de requisições, rate limit e checkpoints.

### Parsers

Transformam as respostas recebidas em estruturas utilizadas pela aplicação.

### Models

Representam e validam os dados normalizados.

Essa separação reduz acoplamento e facilita testes, manutenção e evolução do projeto.

---

## Exemplo de postagem normalizada

```json
{
  "url": "https://www.kwai.com/@usuario/video/123",
  "texto": "Texto da postagem",
  "autor": {
    "usuario": "usuario"
  },
  "engajamento": {
    "curtidas": 100,
    "comentarios": 20,
    "visualizacoes": 5000
  }
}
```

---

## Exemplo de comentário normalizado

```json
{
  "id": "123456",
  "postagem_url": "https://www.kwai.com/@usuario/video/123",
  "autor": {
    "usuario": "usuario",
    "id": "987654"
  },
  "texto": "Comentário de exemplo",
  "curtidas": 10,
  "data": null,
  "coletado_em": "2026-10-09T00:00:00+00:00"
}
```

Campos que não estejam disponíveis na resposta original podem ser representados como `null`.

---

## Qualidade de código

### Ruff

```bash
poetry run ruff check kwai_collector tests
```

### Mypy

```bash
poetry run mypy kwai_collector
```

### Pytest

```bash
poetry run pytest tests -q
```

Estado validado durante a preparação desta versão:

```text
Ruff: All checks passed
Mypy: Success: no issues found
Pytest: 168 passed
```

---

## Testes

A suíte utiliza mocks, providers falsos e transports controlados para não depender de chamadas reais à rede.

Entre os comportamentos cobertos estão:

- parsing;
- paginação;
- deduplicação;
- retry;
- backoff;
- rate limit;
- checkpoint;
- retomada de coleta;
- configuração;
- CLI;
- providers.

Execução:

```powershell
poetry run pytest tests -q
```

---

## Validação antes da entrega

Execute:

```powershell
poetry run ruff check kwai_collector tests
poetry run mypy kwai_collector
poetry run pytest tests -q
git diff --check
```

---

## Uso responsável

O projeto foi desenvolvido como desafio técnico, com foco em engenharia de software aplicada à coleta de dados públicos.

Seu uso deve respeitar:

- termos e regras da plataforma;
- permissões de acesso;
- privacidade dos usuários;
- limites de requisição;
- legislação aplicável.

Utilize somente dados e integrações que você esteja autorizado a acessar.

---

## Objetivo técnico

O projeto demonstra conhecimentos em:

- Python;
- HTTP e APIs;
- coleta e tratamento de dados;
- web scraping;
- paginação;
- retry e backoff;
- CLI;
- Pydantic;
- tipagem estática;
- testes automatizados;
- Clean Code;
- Git e versionamento.

O foco principal é manter uma base de código legível, testável e preparada para evolução.
