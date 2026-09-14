# Kwai Collector

Coletor de dados do Kwai desenvolvido em Python, com foco em organização de código, tipagem, validação de dados, testes automatizados, paginação e resiliência em requisições HTTP.

O projeto permite:

- Buscar postagens por palavra-chave.
- Coletar postagens de um perfil específico.
- Extrair comentários de uma postagem.
- Paginar resultados.
- Remover resultados duplicados.
- Aplicar retry e backoff em falhas HTTP.
- Configurar delay entre requisições.
- Validar os dados coletados com Pydantic.
- Utilizar configurações tipadas através de variáveis de ambiente.
- Executar todas as funcionalidades através de uma CLI.

---

## Funcionalidades

### Busca por palavra-chave

Realiza buscas de postagens públicas do Kwai utilizando uma palavra-chave.

A coleta suporta:

- múltiplas páginas;
- deduplicação por ID da postagem;
- delay entre páginas;
- retry automático;
- backoff exponencial;
- tratamento de HTTP 429;
- tratamento de erros HTTP 5xx;
- tratamento de falhas de conexão.

---

### Coleta de postagens de perfil

Permite coletar as postagens publicadas por um perfil específico do Kwai.

A paginação utiliza o cursor retornado pela própria plataforma.

Também são aplicados:

- paginação;
- deduplicação;
- delay entre páginas;
- retry;
- backoff exponencial;
- tratamento de falhas HTTP.

---

### Coleta de comentários

A coleta de comentários possui dois providers.

#### AdbCommentProvider

É o provider utilizado para coleta automática através de um dispositivo Android conectado via ADB.

O fluxo funciona da seguinte forma:

```text
URL da postagem
        ↓
ADB abre o aplicativo Kwai
        ↓
abre automaticamente o vídeo
        ↓
captura a interface da postagem
        ↓
localiza o botão de comentários
        ↓
calcula a posição do botão
        ↓
abre os comentários
        ↓
captura a hierarquia da interface
        ↓
parser dos comentários
        ↓
validação Pydantic
        ↓
JSON
```

O botão de comentários não utiliza coordenadas fixas.

O collector localiza o elemento da interface através de seu `resource-id`, obtém seus `bounds` e calcula dinamicamente o centro do botão antes de executar o clique.

#### XmlCommentProvider

Também existe um provider baseado em XML.

Ele pode ser usado como fallback quando já existe um arquivo `window.xml` contendo a hierarquia da interface do Kwai.

Essa separação utiliza uma abstração `CommentProvider`, permitindo que novas estratégias de coleta de comentários sejam adicionadas futuramente sem alterar os modelos ou a CLI.

---

## Tecnologias

- Python 3.11+
- Poetry
- HTTPX
- Pydantic
- Pydantic Settings
- Pytest
- Ruff
- Mypy
- ADB
- UIAutomator
- XML ElementTree

---

## Estrutura do projeto

```text
kwai-project/
├── kwai_collector/
│   ├── clients/
│   │   ├── kwai_client.py
│   │   ├── profile_client.py
│   │   └── comment_client.py
│   │
│   ├── models/
│   │   ├── postagem.py
│   │   └── comentario.py
│   │
│   ├── parsers/
│   │   ├── post_parser.py
│   │   ├── comment_parser.py
│   │   └── ui_comments.py
│   │
│   ├── providers/
│   │   ├── comment_provider.py
│   │   └── adb_comment_provider.py
│   │
│   ├── cli.py
│   └── config.py
│
├── samples/
│   ├── tecnologia.json
│   ├── perfil_cli.json
│   └── comentarios_cli.json
│
├── tests/
├── .gitignore
├── README.md
├── poetry.lock
└── pyproject.toml
```

---

## Requisitos

Para busca e coleta de perfis:

- Python 3.11 ou superior
- Poetry
- conexão com a internet

Para a coleta automática de comentários também é necessário:

- dispositivo Android;
- aplicativo Kwai instalado;
- ADB instalado no computador;
- depuração USB habilitada;
- computador autorizado pelo dispositivo Android.

---

## Instalação

Clone o repositório:

```bash
git clone <URL_DO_REPOSITORIO>
```

Entre na pasta:

```bash
cd kwai-project
```

Instale as dependências:

```bash
poetry install
```

Verifique o ambiente:

```bash
poetry run python --version
```

---

# CLI

Para visualizar todos os comandos disponíveis:

```bash
poetry run python -m kwai_collector.cli --help
```

---

## Buscar postagens

Busca simples:

```bash
poetry run python -m kwai_collector.cli buscar "tecnologia"
```

Definindo a quantidade máxima de páginas:

```bash
poetry run python -m kwai_collector.cli buscar "tecnologia" --paginas 3
```

Utilizando delay entre páginas:

```bash
poetry run python -m kwai_collector.cli buscar "tecnologia" --paginas 3 --delay 0.5
```

Definindo arquivo de saída:

```bash
poetry run python -m kwai_collector.cli buscar "tecnologia" --output samples/tecnologia.json
```

Exemplo de fluxo:

```text
"tecnologia"
      ↓
search_all_posts()
      ↓
paginação
      ↓
deduplicação
      ↓
parse_post()
      ↓
Postagem
      ↓
JSON
```

---

## Coletar postagens de um perfil

Exemplo:

```bash
poetry run python -m kwai_collector.cli perfil "@betrobort"
```

Coletando três páginas:

```bash
poetry run python -m kwai_collector.cli perfil "@betrobort" --paginas 3
```

Adicionando delay:

```bash
poetry run python -m kwai_collector.cli perfil "@betrobort" --paginas 3 --delay 0.5
```

Definindo arquivo de saída:

```bash
poetry run python -m kwai_collector.cli perfil "@betrobort" --output samples/perfil_cli.json
```

O cursor retornado pela página anterior é utilizado para buscar a página seguinte.

Exemplo:

```text
Página 1
   ↓
cursor
   ↓
Página 2
   ↓
cursor
   ↓
Página 3
```

Os IDs já encontrados são armazenados para evitar postagens duplicadas.

---

# Comentários

## Coleta automática via ADB

Primeiro confirme que o Android está conectado:

```bash
adb devices
```

O resultado deve apresentar um dispositivo com status:

```text
device
```

Depois execute apenas:

```bash
poetry run python -m kwai_collector.cli comentarios "https://www.kwai.com/@usuario/video/123456789"
```

O collector executará automaticamente:

```text
abre o Kwai
      ↓
abre a URL
      ↓
localiza comment_button
      ↓
abre comentários
      ↓
executa UIAutomator
      ↓
captura window.xml
      ↓
extrai comentários
      ↓
salva JSON
```

Por padrão, o resultado será salvo em:

```text
samples/comentarios_cli.json
```

Também é possível definir outro arquivo:

```bash
poetry run python -m kwai_collector.cli comentarios "URL_DO_POST" --output samples/comentarios.json
```

---

## Coleta utilizando XML

Caso já exista um arquivo XML capturado da interface:

```bash
poetry run python -m kwai_collector.cli comentarios "URL_DO_POST" --xml window.xml
```

Nesse caso será utilizado o:

```text
XmlCommentProvider
```

em vez do:

```text
AdbCommentProvider
```

---

# Configuração

O projeto utiliza `pydantic-settings` para configurações tipadas.

As variáveis disponíveis são:

```text
KWAI_MAX_TENTATIVAS
KWAI_BACKOFF_BASE
KWAI_DELAY
KWAI_ADB_PATH
KWAI_KWAI_PACKAGE
```

Valores padrão:

```text
KWAI_MAX_TENTATIVAS=3
KWAI_BACKOFF_BASE=1.0
KWAI_DELAY=0.0
KWAI_ADB_PATH=adb
KWAI_KWAI_PACKAGE=com.kwai.video
```

---

## Configurando no PowerShell

Exemplo:

```powershell
$env:KWAI_MAX_TENTATIVAS="5"
$env:KWAI_BACKOFF_BASE="2.0"
$env:KWAI_DELAY="0.5"
```

Caso o ADB não esteja disponível diretamente no `PATH`:

```powershell
$env:KWAI_ADB_PATH="C:\platform-tools\platform-tools\adb.exe"
```

Para conferir:

```powershell
$env:KWAI_ADB_PATH
```

Também pode ser validado pelo projeto:

```bash
poetry run python -c "from kwai_collector.config import settings; print(settings.adb_path)"
```

---

# Resiliência HTTP

Os clients HTTP possuem mecanismos para reduzir falhas durante a coleta.

São tratados:

```text
falha de conexão
HTTP 429
HTTP 5xx
```

O retry utiliza backoff exponencial.

Com os valores padrão:

```text
1ª falha
   ↓
espera 1 segundo

2ª falha
   ↓
espera 2 segundos

3ª tentativa
   ↓
erro é propagado caso a falha continue
```

A quantidade de tentativas e o tempo inicial podem ser configurados.

---

# Rate Limit

O collector permite definir um intervalo entre páginas.

Exemplo:

```bash
--delay 0.5
```

Isso significa aproximadamente:

```text
requisição
   ↓
espera 0.5s
   ↓
próxima requisição
```

Também pode ser definido pela variável:

```text
KWAI_DELAY
```

---

# Modelos de dados

Os dados coletados são validados com Pydantic antes de serem gravados em JSON.

## Postagem

Estrutura aproximada:

```json
{
  "id": "123456789",
  "url": "https://www.kwai.com/@usuario/video/123456789",
  "autor": {
    "usuario": "Nome do usuário",
    "id": null,
    "url_perfil": "https://www.kwai.com/@usuario"
  },
  "texto": "Texto da postagem",
  "data_publicacao": "2025-09-24T22:20:59",
  "engajamento": {
    "curtidas": 23,
    "comentarios": 3,
    "compartilhamentos": 1,
    "visualizacoes": 650
  },
  "coletado_em": "2026-09-10T00:00:00Z"
}
```

---

## Comentário

Estrutura aproximada:

```json
{
  "id": null,
  "postagem_url": "https://www.kwai.com/@usuario/video/123456789",
  "autor": {
    "usuario": "Usuario Teste",
    "id": null
  },
  "texto": "Comentário de exemplo",
  "curtidas": 3,
  "data": "2025-09-09T00:00:00",
  "coletado_em": "2026-09-10T00:00:00Z"
}
```

Quando determinados dados não estão disponíveis de forma confiável na interface, eles permanecem `null` em vez de serem inventados.

---

# Samples

A pasta `samples/` contém exemplos reais do formato de saída.

```text
samples/
├── tecnologia.json
├── perfil_cli.json
└── comentarios_cli.json
```

### tecnologia.json

Exemplo de coleta por palavra-chave.

### perfil_cli.json

Exemplo de coleta das postagens de um perfil.

### comentarios_cli.json

Exemplo de comentários extraídos.

---

# Testes

Execute todos os testes:

```bash
poetry run pytest
```

Modo detalhado:

```bash
poetry run pytest -v
```

Testar somente a CLI:

```bash
poetry run pytest tests/test_cli.py -v
```

Testar o client de perfil:

```bash
poetry run pytest tests/test_profile_client.py -v
```

Testar o provider ADB:

```bash
poetry run pytest tests/test_adb_comment_provider.py -v
```

Os testes utilizam mocks, fakes e `monkeypatch` para evitar dependência da rede ou de um dispositivo Android durante a suíte automatizada.

---

# Qualidade de código

## Ruff

Executar lint:

```bash
poetry run ruff check .
```

Correções automáticas quando aplicável:

```bash
poetry run ruff check . --fix
```

---

## Mypy

Executar verificação de tipos:

```bash
poetry run mypy .
```

---

## Pytest

Executar testes:

```bash
poetry run pytest
```

---

# Verificação antes de commit

Antes de enviar alterações:

```bash
poetry run ruff check .
poetry run mypy .
poetry run pytest
```

Os três comandos devem finalizar sem erros.

---

# Arquitetura

O projeto separa responsabilidades em diferentes camadas:

```text
CLI
 │
 ├── Clients
 │      ├── Search Client
 │      ├── Profile Client
 │      └── Comment Client
 │
 ├── Providers
 │      ├── AdbCommentProvider
 │      └── XmlCommentProvider
 │
 ├── Parsers
 │      ├── Post Parser
 │      ├── Comment Parser
 │      └── UI Comment Parser
 │
 └── Models
        ├── Postagem
        └── Comentario
```

Essa organização evita concentrar requisições, parsing, validação e interface de linha de comando no mesmo módulo.

---

# Estratégia de comentários

Durante o desenvolvimento foi identificada uma diferença de comportamento entre as interfaces do Kwai.

A rota web de comentários utilizada pelo desktop pode responder com sucesso HTTP sem necessariamente disponibilizar a lista de comentários.

Por esse motivo, a implementação atual utiliza a interface acessível do aplicativo Android através de ADB/UIAutomator como provider de coleta.

O `AdbCommentProvider` é isolado das demais camadas para que uma futura implementação HTTP, API oficial ou outro provider possa ser adicionada sem alterar o restante da aplicação.

---

# Limitações

A coleta depende das interfaces disponibilizadas pelo Kwai.

Alterações feitas pela plataforma podem exigir atualizações nos endpoints, campos retornados ou identificadores da interface Android.

A coleta automática de comentários via `AdbCommentProvider` depende atualmente de:

```text
Android conectado
ADB autorizado
Kwai instalado
interface compatível com os resource-ids utilizados
```

O projeto não presume que comentários inexistentes tenham zero curtidas ou outros valores quando essa informação não pode ser determinada com segurança.

---

# Segurança

Não devem ser versionados:

```text
.env
cookies
tokens
credenciais
sessões autenticadas
arquivos temporários do ADB
```

O projeto não necessita armazenar cookies ou tokens pessoais para as funcionalidades atualmente implementadas.

---

# Desenvolvimento

Fluxo recomendado:

```text
alteração
   ↓
Ruff
   ↓
Mypy
   ↓
Pytest
   ↓
teste manual quando necessário
   ↓
commit
```

Comandos:

```bash
poetry run ruff check .
poetry run mypy .
poetry run pytest
```

---

# Status

Atualmente implementado:

```text
Busca por palavra-chave          ✅
Paginação da busca               ✅
Deduplicação                     ✅
Posts de perfil                  ✅
Paginação por cursor             ✅
Comentários                      ✅
Automação ADB                    ✅
Fallback XML                     ✅
Retry                            ✅
Backoff                          ✅
Delay                            ✅
Configuração tipada              ✅
Pydantic                         ✅
CLI                              ✅
Pytest                           ✅
Ruff                             ✅
Mypy                             ✅
```

---

## Observação

Este projeto foi desenvolvido para fins de desafio técnico e estudo de coleta estruturada de dados.

O uso deve respeitar as regras da plataforma, as permissões de acesso aos dados e a legislação aplicável.