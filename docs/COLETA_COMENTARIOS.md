# Coleta de comentários — documentação técnica

**Projeto:** Kwai Collector
**Versão do pacote:** 0.1.0
**Revisão da documentação:** 2.0
**Referência:** 9 de outubro de 2026
**Identificador da entrega:** `A1_Radar`

---

## 1. Visão geral

O Kwai Collector é uma aplicação Python voltada à coleta e normalização de dados públicos, com interface de linha de comando, paginação, controle de frequência, recuperação de falhas e testes automatizados.

A implementação foi estruturada para separar claramente:

- entrada e validação da CLI;
- casos de uso;
- comunicação HTTP;
- preparação de requisições;
- paginação;
- controle de frequência;
- recuperação de falhas;
- persistência de progresso;
- parsing;
- modelos de domínio;
- configuração.

A coleta de comentários trabalha atualmente com **comentários principais** de uma publicação.

Respostas e subcomentários não fazem parte do contrato da versão atual.

Essa decisão é de escopo, e não uma limitação estrutural definitiva. A arquitetura permite incorporar esse recurso futuramente através de um fluxo específico de coleta, parser e normalização, preservando o contrato atual dos comentários principais.

---

## 2. Estado atual

A versão atual possui suporte para:

| Recurso | Estado |
| --- | --- |
| Busca por palavra-chave | Implementado |
| Coleta de postagens de perfil | Implementado |
| Coleta de comentários principais | Implementado |
| Paginação de comentários | Implementado |
| Limite numérico de comentários | Implementado |
| Paginação até condição de término | Implementado |
| Deduplicação | Implementado |
| Retry | Implementado |
| Backoff | Implementado |
| Tratamento de `Retry-After` | Implementado |
| Intervalo configurável entre requisições | Implementado |
| Checkpoint | Implementado |
| Retomada com `--resume` | Implementado |
| Saída JSON normalizada | Implementado |
| Configuração tipada | Implementado |
| Integração mobile por provider | Implementado |
| Subcomentários/respostas | Planejado para evolução futura |

---

## 3. Compatibilidade

O projeto foi construído com alta compatibilidade entre os diferentes fluxos que compõem a coleta.

A lógica de domínio não depende diretamente de uma implementação específica de autenticação, transporte ou origem dos dados.

A camada pública utiliza interfaces e providers para isolar essas responsabilidades.

### 3.1 Ambiente

| Componente | Compatibilidade |
| --- | --- |
| Python | 3.11+ |
| Gerenciamento de dependências | Poetry |
| HTTP | HTTPX |
| HTTP/2 | Suportado pelo cliente mobile |
| Validação | Pydantic |
| Configuração | Pydantic Settings |
| Testes | Pytest |
| Tipagem | Mypy |
| Lint | Ruff |
| CLI | PowerShell e execução via Poetry |

O ambiente principal de desenvolvimento e validação desta entrega utiliza Python 3.11 em Windows com PowerShell.

A maior parte da lógica de aplicação permanece independente do sistema operacional por utilizar Python e bibliotecas multiplataforma.

### 3.2 Compatibilidade de entrada

A aplicação trabalha com diferentes formas de entrada dependendo do comando:

- nome de usuário;
- URL de postagem;
- identificador de postagem;
- palavra-chave.

A resolução de identificadores fica isolada da lógica responsável pela paginação e normalização dos comentários.

### 3.3 Compatibilidade arquitetural

A integração mobile utiliza a abstração `MobileRequestProvider`.

Isso permite substituir a origem autorizada da preparação de requisições sem alterar o restante do fluxo:

```text
CLI
 |
 v
caso de uso
 |
 v
MobileCommentProvider
 |
 v
MobileRequestProvider
 |
 v
cliente HTTP
 |
 v
API
 |
 v
parser
 |
 v
modelo
 |
 v
JSON
```

Essa separação reduz acoplamento e facilita manutenção, testes e adaptação a mudanças futuras.

A compatibilidade descrita nesta documentação refere-se aos contratos e cenários atualmente validados. Mudanças externas na plataforma podem exigir atualização da camada de integração.

---

## 4. Arquitetura

A aplicação utiliza composição entre componentes com responsabilidades específicas.

```text
kwai_collector/
|
|-- clients/
|      comunicação HTTP
|      paginação
|      retry
|      rate limit
|
|-- models/
|      contratos normalizados
|      validação de dados
|
|-- parsers/
|      transformação de respostas externas
|
|-- providers/
|      integração entre clientes e casos de uso
|      checkpoint
|      coleta mobile
|
|-- security/
|      abstrações de preparação de requisição
|      configuração de integração
|
|-- cli.py
|      entry point
|
|-- cli_commands.py
|      comandos de busca e perfil
|
|-- cli_comments.py
|      coleta de uma postagem
|
|-- cli_collect.py
|      coleta agregada
|
|-- cli_builders.py
|      construção de objetos e parâmetros
|
|-- cli_parsers.py
|      definição de argumentos
|
|-- cli_utils.py
|      utilidades da CLI
|
`-- config.py
       configuração tipada
```

---

## 5. Princípios de projeto

A organização atual prioriza:

- responsabilidade única;
- baixo acoplamento;
- dependências explícitas;
- composição em vez de herança;
- validação nas fronteiras;
- funções pequenas;
- nomes orientados à intenção;
- configuração externa;
- tratamento específico de erros;
- testes sem dependência de rede real.

A CLI não concentra regras de protocolo ou paginação.

Da mesma forma, o cliente HTTP não decide como o resultado deve ser apresentado ao usuário.

---

## 6. Fluxo de coleta de comentários

O comando recebe uma URL ou identificador e cria as dependências necessárias para executar a coleta.

Fluxo simplificado:

```text
entrada
  |
  v
validação
  |
  v
resolução do post
  |
  v
seleção do fluxo
  |
  v
provider
  |
  v
cliente HTTP
  |
  v
paginação
  |
  +----> retry / backoff
  |
  +----> rate limit
  |
  +----> checkpoint
  |
  v
deduplicação
  |
  v
parser
  |
  v
Pydantic
  |
  v
JSON
```

Cada responsabilidade pode ser testada isoladamente.

---

## 7. Comentários principais

A versão atual coleta comentários principais.

O fluxo utiliza os registros principais retornados pela fonte de comentários e os normaliza para o modelo público do projeto.

Exemplo:

```json
{
  "id": "1001",
  "postagem_url": "https://www.kwai.com/@usuario/video/1234567890",
  "autor": {
    "usuario": "Usuario",
    "id": "987654"
  },
  "texto": "Comentário de exemplo",
  "curtidas": 12,
  "data": "2026-10-09T12:00:00+00:00",
  "coletado_em": "2026-10-09T15:00:00+00:00"
}
```

Campos indisponíveis na origem podem ser representados como `null` quando permitido pelo modelo.

---

## 8. Subcomentários e respostas

Subcomentários não são coletados nesta versão.

Essa decisão mantém o contrato atual simples e evita misturar dois tipos de entidade com relações hierárquicas diferentes.

Uma futura implementação poderá adicionar suporte a respostas sem alterar o contrato já utilizado pelos comentários principais.

A evolução prevista é:

```text
comentário principal
        |
        +---- identificador do comentário raiz
        |
        v
provider de respostas
        |
        v
paginação própria
        |
        v
parser de subcomentários
        |
        v
modelo hierárquico ou coleção relacionada
```

A extensão deverá possuir:

- endpoint/provider próprio;
- paginação independente;
- deduplicação independente;
- rate limit compartilhável;
- testes específicos;
- modelo de relacionamento com o comentário raiz.

Com isso, alterações futuras poderão incluir subcomentários preservando compatibilidade com consumidores da saída atual.

---

## 9. Paginação

A paginação é controlada pelo cliente responsável pela coleta.

O comando aceita um limite numérico ou:

```text
todos
```

Exemplo:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments 50 `
    --request-interval 2
```

Para continuar enquanto houver paginação reconhecida:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2
```

A implementação considera condições de encerramento reconhecidas pelo cliente e impede loops de cursor.

---

## 10. Deduplicação

Comentários podem aparecer novamente entre páginas.

Para evitar duplicidade na saída, o fluxo mantém controle dos identificadores já processados.

A primeira ocorrência é preservada.

O objetivo é garantir que paginação ou repetição de cursor não resultem automaticamente em duplicatas no resultado normalizado.

---

## 11. Controle de frequência

O intervalo mínimo entre requisições mobile pode ser definido através de:

```text
--request-interval
```

Exemplo:

```powershell
--request-interval 2
```

Também existe configuração por ambiente:

```text
KWAI_MOBILE_PAGE_DELAY
```

O controle de frequência é aplicado pelo cliente responsável pelas chamadas mobile.

Isso evita espalhar chamadas diretas a `sleep` pelas regras de negócio.

---

## 12. Retry e backoff

Falhas temporárias de transporte ou respostas HTTP configuradas como recuperáveis podem ser repetidas.

Configurações:

```text
KWAI_MAX_TENTATIVAS
KWAI_BACKOFF_BASE
```

O backoff cresce entre tentativas e possui limite interno para evitar esperas exponenciais sem controle.

Quando o servidor fornece um `Retry-After` válido, o cliente pode respeitar o prazo informado.

Erros não classificados como transitórios não entram automaticamente em retry.

Essa diferenciação evita mascarar problemas permanentes de entrada, autenticação ou contrato.

---

## 13. Checkpoint

Durante uma coleta paginada, o estado pode ser persistido.

Exemplo de arquivo:

```text
samples/<photo_id>_comentarios.coleta.json
```

O checkpoint pode conter informações necessárias para continuação, como:

- identificação da postagem;
- identificação do autor;
- contexto da listagem;
- próximo cursor;
- comentários já recebidos;
- estado da coleta.

Credenciais de autenticação não fazem parte do contrato de checkpoint.

---

## 14. Retomada

Uma coleta interrompida pode ser retomada:

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2 `
    --resume
```

A retomada:

1. carrega o checkpoint;
2. valida sua compatibilidade com a coleta solicitada;
3. recupera o progresso anterior;
4. continua pelo cursor armazenado;
5. preserva resultados existentes;
6. aplica novamente a deduplicação;
7. remove o checkpoint após conclusão e persistência bem-sucedidas.

O limite solicitado inclui os registros anteriormente recuperados.

---

## 15. Recuperação de falhas

Uma falha durante paginação não precisa invalidar todo o trabalho anterior.

Quando possível, o fluxo preserva:

- comentários já recebidos;
- cursor pendente;
- checkpoint;
- saída parcial.

Isso torna coletas longas mais resilientes e reduz a necessidade de reiniciar todo o processo.

---

## 16. Coleta de perfil

Existem dois comportamentos distintos relacionados a perfil.

### `perfil`

```powershell
poetry run kwai-collector perfil "henriqueejuliano" --delay 2
```

Esse comando percorre as páginas disponíveis do perfil até a condição de término reconhecida.

A paginação não possui o antigo limite interno de cinco páginas.

Os posts são deduplicados durante o processo.

### `coletar`

```powershell
poetry run kwai-collector coletar `
    "henriqueejuliano" `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

Esse fluxo foi deliberadamente limitado a até 10 postagens por execução.

O limite reduz o impacto operacional de uma coleta agregada potencialmente extensa.

Portanto:

```text
perfil   -> coleta das postagens disponíveis
coletar  -> até 10 postagens + comentários
```

---

## 17. Busca por palavra-chave

Exemplo:

```powershell
poetry run kwai-collector buscar "sertanejo" --delay 2
```

Para incluir comentários:

```powershell
poetry run kwai-collector buscar "sertanejo" `
    --with-comments `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

Também é possível definir um limite:

```powershell
poetry run kwai-collector buscar "sertanejo" `
    --with-comments `
    --max-comments 50 `
    --request-interval 2 `
    --delay 2
```

A coleta de comentários reutiliza os mesmos componentes responsáveis por paginação, normalização e controle de frequência.

---

## 18. Configuração mobile

O pacote público trabalha com uma abstração de preparação de requisições.

Uma integração autorizada pode ser configurada através de:

```text
KWAI_MOBILE_AUTH_ENDPOINT
KWAI_MOBILE_AUTH_TOKEN
KWAI_MOBILE_AUTH_TIMEOUT
```

Também existem campos configuráveis:

```text
KWAI_MOBILE_QUERY_FIELDS
KWAI_MOBILE_BODY_FIELDS
KWAI_MOBILE_HEADER_FIELDS
```

O projeto não exige que a regra de autenticação esteja incorporada à camada de coleta.

Essa decisão mantém o código de negócio desacoplado da origem da autorização.

---

## 19. Segurança de configuração

Credenciais reais não devem ser versionadas.

O arquivo:

```text
.env
```

deve permanecer fora do Git.

O repositório público deve utilizar apenas exemplos sem valores reais.

Também não devem ser publicados:

- tokens ativos;
- cookies de sessão;
- URLs autenticadas;
- dumps contendo credenciais;
- backups de configuração;
- artefatos técnicos privados.

---

## 20. Contrato dos comentários

Modelo conceitual:

| Campo | Tipo |
| --- | --- |
| `id` | `str \| None` |
| `postagem_url` | `str` |
| `autor.usuario` | `str \| None` |
| `autor.id` | `str \| None` |
| `texto` | `str` |
| `curtidas` | `int \| None` |
| `data` | ISO 8601 ou `null` |
| `coletado_em` | ISO 8601 |

Campos obrigatórios para a saída normalizada:

```text
postagem_url
texto
coletado_em
```

---

## 21. Persistência

Os resultados são gravados em JSON.

Exemplos:

```text
samples/<photo_id>_comentarios.json
samples/<usuario>_posts.json
samples/<usuario>_comentarios.json
samples/busca_<termo>.json
samples/busca_<termo>_comentarios.json
```

O conteúdo de saída é separado da configuração operacional utilizada para realizar as requisições.

---

## 22. Testabilidade

Os testes automatizados não dependem da disponibilidade da API real.

São utilizados:

- mocks;
- providers falsos;
- transports controlados;
- fixtures;
- dependências injetadas.

Isso permite testar determinísticamente situações como:

- múltiplas páginas;
- fim de paginação;
- cursor repetido;
- comentários duplicados;
- HTTP temporariamente indisponível;
- retry;
- backoff;
- `Retry-After`;
- checkpoint;
- retomada;
- configuração;
- CLI.

---

## 23. Estado de qualidade

Na validação da versão atual:

```text
Ruff
All checks passed!

Mypy
Success: no issues found in 49 source files

Pytest
168 passed
```

Comandos utilizados:

```powershell
poetry run ruff check kwai_collector tests
poetry run mypy kwai_collector
poetry run pytest tests -q
```

Os números acima representam o estado validado desta versão e devem ser atualizados quando a suíte mudar.

---

## 24. Tratamento de erros

O fluxo diferencia erros de acordo com sua natureza.

Exemplos:

```text
entrada inválida
        -> rejeição pela CLI

falha temporária de rede
        -> retry quando aplicável

erro HTTP transitório
        -> retry/backoff quando configurado

erro permanente
        -> interrupção

falha depois de páginas válidas
        -> preservação de progresso quando possível
```

Evitar tratar todos os erros da mesma maneira torna o comportamento da aplicação mais previsível.

---

## 25. Observabilidade

Os logs são utilizados para informar:

- início da operação;
- progresso de páginas;
- quantidade acumulada;
- tentativas;
- espera;
- falhas;
- conclusão;
- caminhos dos arquivos gerados.

Dados sensíveis não devem fazer parte de logs públicos.

---

## 26. Escalabilidade e evolução

A arquitetura atual permite evolução incremental.

Extensões previstas podem incluir:

### Subcomentários

Adicionar respostas utilizando um fluxo dedicado e relacionamento com comentário raiz.

### Persistência de grandes volumes

Substituir progressivamente estruturas inteiramente em memória por persistência incremental quando o volume justificar.

### Rate limit compartilhado

Caso o projeto adote concorrência ou múltiplos workers, o limitador poderá evoluir para coordenação compartilhada.

### Resultado de coleta enriquecido

Um contrato futuro pode registrar explicitamente:

- motivo do término;
- último cursor;
- quantidade bruta;
- quantidade única;
- completude;
- duração;
- estatísticas de retry.

### Providers adicionais

Novos providers podem ser incorporados sem alterar os casos de uso principais.

---

## 27. Decisão sobre subcomentários

A versão atual não retorna respostas de comentários.

A decisão foi mantida para preservar:

1. escopo claro da entrega;
2. consistência do contrato;
3. paginação previsível;
4. menor acoplamento entre entidades;
5. testabilidade.

O suporte futuro a subcomentários deve ser implementado como uma evolução compatível.

A alteração ideal adicionará uma nova responsabilidade sem modificar silenciosamente a semântica de:

```text
--max-comments
```

Hoje esse valor representa comentários principais.

Uma versão futura poderá oferecer uma opção explícita, por exemplo:

```text
incluir respostas
```

mantendo consumidores atuais compatíveis com o formato já entregue.

---

## 28. Limitações conhecidas

Uma documentação técnica deve distinguir comportamento implementado de garantia externa.

As limitações atuais incluem:

- subcomentários ainda não são coletados;
- autenticação/sessão é fornecida externamente;
- mudanças da plataforma podem exigir adaptação da integração;
- rate limit atual é local ao processo/cliente;
- coletas agregadas mantêm limite operacional de posts;
- a completude depende dos critérios de paginação disponíveis na resposta;
- grandes coleções ainda são acumuladas em memória durante determinados fluxos.

Esses pontos são tratados como decisões ou fronteiras explícitas, não como comportamento oculto.

---

## 29. Compatibilidade futura

A principal característica de compatibilidade do projeto está na separação entre contratos internos e detalhes externos.

Mudanças de:

- autenticação;
- transporte;
- headers;
- campos de protocolo;
- origem da requisição;

podem ser absorvidas por providers e clients específicos.

Os modelos, parsers e casos de uso não precisam necessariamente conhecer essas alterações.

Da mesma forma, recursos novos, como subcomentários, podem ser acrescentados por composição em vez de alterar toda a cadeia existente.

Essa abordagem reduz o impacto de mudanças e preserva compatibilidade para quem consome os contratos atuais.

---

## 30. Comandos principais

### Ajuda

```powershell
poetry run kwai-collector --help
```

### Perfil

```powershell
poetry run kwai-collector perfil "henriqueejuliano" --delay 2
```

### Coleta agregada

```powershell
poetry run kwai-collector coletar `
    "henriqueejuliano" `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

### Comentários

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2
```

### Comentários limitados

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments 50 `
    --request-interval 2
```

### Retomada

```powershell
poetry run kwai-collector comentarios `
    "https://www.kwai.com/@stanleyribeiro/video/5205466849377747864" `
    --max-comments todos `
    --request-interval 2 `
    --resume
```

### Busca

```powershell
poetry run kwai-collector buscar "sertanejo" --delay 2
```

### Busca com comentários

```powershell
poetry run kwai-collector buscar "sertanejo" `
    --with-comments `
    --max-comments todos `
    --request-interval 2 `
    --delay 2
```

---

## 31. Validação para entrega

Antes de uma versão ou commit de entrega:

```powershell
poetry run ruff check kwai_collector tests
poetry run mypy kwai_collector
poetry run pytest tests -q
git diff --check
```

Também devem ser revisados:

```text
git status
.gitignore
.env.example
pyproject.toml
poetry.lock
README.md
docs/
```

Nenhum segredo, token ou artefato privado deve ser incluído no commit público.

---

## 32. Conclusão

O estado atual do Kwai Collector prioriza previsibilidade, separação de responsabilidades e capacidade de evolução.

A aplicação oferece um fluxo consistente para busca, perfil e comentários, com:

- paginação;
- deduplicação;
- retry;
- backoff;
- rate limit;
- checkpoint;
- retomada;
- validação;
- tipagem;
- testes automatizados;
- configuração desacoplada.

A arquitetura apresenta alta compatibilidade com os fluxos atualmente suportados porque as responsabilidades externas são isoladas atrás de clients e providers.

A coleta atual é intencionalmente focada em comentários principais.

Subcomentários permanecem fora desta versão, mas foram considerados na evolução arquitetural. Uma implementação futura poderá adicioná-los como uma extensão explícita e testável, sem exigir reescrita do fluxo principal nem quebrar o contrato atual.
