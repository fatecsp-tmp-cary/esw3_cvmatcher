# Documentação de APIs, Endpoints e Normalização de Vagas (MVP)

Este documento especifica a arquitetura de dados, o mapeamento de endpoints de todas as 6 fontes públicas avaliadas, as definições da plataforma escolhida para o MVP e o esquema de **normalização e padronização dos campos** para o banco de dados unificado.

---

##  1. Estratégia de Normalização do Schema (Modelo Unificado)

Como cada API de vagas retorna estruturas de JSON distintas, todos os dados coletados pelos integradores são transformados e mapeados para o seguinte esquema padronizado antes da persistência:

| Campo Normalizado | Tipo de Dado | Descrição / Regra de Transformação | Exemplo de Valor |
| :--- | :--- | :--- | :--- |
| `id_vaga_origem` | `String` (PK) | Identificador único original fornecido pela plataforma | `"MOaYsJOw"` ou `"12577603"` |
| `plataforma` | `String` | Nome da plataforma/API de origem da coleta | `"Meu Padrinho"`, `"Gupy"` |
| `titulo` | `String` | Título do cargo/vaga limpo e formatado | `"Analista de Dados Pleno"` |
| `empresa` | `String` | Nome da empresa contratante ou página de carreira | `"Globo"`, `"Archer Daniels"` |
| `descricao` | `Text` | Texto descritivo completo ou requisitos da vaga | `"Responsável por modelagem..."` |
| `localizacao` | `JSON / Obj` | Objeto padronizado com `cidade`, `estado` e `pais` | `{"cidade": "SP", "estado": "SP"}` |
| `modalidade` | `Enum` | Formato de trabalho (`REMOTO`, `HIBRIDO`, `PRESENCIAL`) | `HIBRIDO` |
| `nivel_senioridade`| `Enum` | Senioridade (`ESTAGIO`, `JUNIOR`, `PLENO`, `SENIOR`) | `PLENO` |
| `tecnologias` | `Array[String]`| Lista de linguagens, frameworks e ferramentas | `["Python", "SQL", "Docker"]` |
| `salario` | `JSON / Obj` | Faixa salarial mapeada quando disponível | `{"min": 5000, "max": 7000}` |
| `url_vaga` | `String` | Link direto para a página de candidatura | `"https://..."` |
| `data_publicacao` | `Timestamp` | Data/hora de publicação padronizada em ISO 8601 | `"2026-09-23T07:04:10Z"` |
| `status` | `Enum` | Estado da vaga no nosso sistema (`ATIVA`, `INATIVA`) | `ATIVA` |

---

##  2. Especificação Técnica e Endpoints de Todas as Fontes

### 2.1 Meu Padrinho / API Vagas Tech ( Fonte Principal MVP)
* **Endpoint Principal:** `GET https://meupadrinho.com.br/api/vagas`
* **Endpoint Detalhes:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}`
* **Endpoint Tecnologias:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}/tecnologias`

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação |
| **Parâmetros** | `page` (paginação), `niveis` (`estagio`, `junior`, `pleno`, `senior`) |
| **Identificador / Título / Empresa** | `nano_id` (ou `id`) \| `titulo_vaga` \| `empresa_nome` |
| **Modalidade / Data Registro** | `forma_trabalho` \| `horario_registro` |
| **Comportamento da Paginação** | Utiliza `page`. Consulta páginas sucessivas (`page=1`, `page=2`...) até retornar lista vazia `[]` ou erro. |
| **Mapeamento de Endpoints Adicionais**| Exige chamadas a `/api/vagas/{nano_id}` (para `descricao`, `salario` e `localizacao`) e `/tecnologias` (para array de `skills`). |

---

### 2.2 Gupy (Portal Público de Empregabilidade)
* **Endpoint Principal:** `GET https://employability-portal.gupy.io/api/v1/jobs`
* **Exemplo de Chamada:** `GET https://employability-portal.gupy.io/api/v1/jobs?jobName=Analista%20de%20Dados&limit=100&offset=0`

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação |
| **Parâmetros** | `jobName` (busca por termo), `limit` (máx. 100), `offset` (deslocamento) |
| **Campos Retornados** | `id`, `name` (título), `careerPageName` (empresa), `description` (completa), `city`, `state`, `country`, `workplaceType`, `publishedDate`, `jobUrl` |
| **Comportamento da Paginação** | Utiliza `offset` + `limit`. Avança o `offset` de 100 em 100 até receber `results: []`. |

---

### 2.3 InHire (Portal Público por Tenant)
* **Endpoint Principal:** `GET https://api.inhire.app/job-posts/public/pages`
* **Header Obrigatório:** `X-Tenant: <nome_empresa>` (Ex: `X-Tenant: magalu`)

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação |
| **Campos Retornados** | `jobId`, `displayName` (título), `tenantName` (empresa), `workplaceType`, `location` |
| **Comportamento / Limitação** | Não possui paginação nem busca global por termo. Retorna todas as vagas ativas vinculadas ao `X-Tenant` informado. Exige conhecimento prévio das empresas. |

---

### 2.4 Solides
* **Endpoint Principal:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies`
* **Exemplo de Chamada:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies?title=Analista%20de%20Dados&page=1&take=25`

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação |
| **Parâmetros** | `title` (termo de busca), `page` (página), `take` (limite por página, padrão `25`) |
| **Campos Retornados** | ID, título, empresa, descrição, localização, modalidade, data de publicação, link direto |
| **Comportamento da Paginação** | Utiliza `page` + `take`. Incrementa `page` mantendo `take=25` até o fim dos registros. |

---

### 2.5 Trampos.co
* **Endpoint Principal:** `GET https://trampos.co/api/v2/opportunities`
* **Exemplo de Chamada:** `GET https://trampos.co/api/v2/opportunities?tr=Analista%20de%20Dados&lc=Sao%20Paulo&page=1`

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação pública |
| **Parâmetros** | `tr` (termo de pesquisa), `lc` (localização), `page` (página) |
| **Campos Retornados** | ID, título, empresa, localização, modalidade, link da vaga (descrição vem parcial) |
| **Comportamento da Paginação** | A resposta traz a chave `pagination.total_pages`. O coletor lê o total e agenda as chamadas de `page=1` até `total_pages`. |

---

### 2.6 Quero Vagas Tech
* **Endpoint Principal:** `GET https://querovagastech.com.br/api/jobs`
* **Endpoint Detalhado:** `GET https://querovagastech.com.br/api/jobs/{id}`
* **Exemplo de Chamada:** `GET https://querovagastech.com.br/api/jobs?page=1&pageSize=100&sort=postedAt:desc`

| Parâmetro / Atributo | Detalhe Técnico / Valor |
| :--- | :--- |
| **Método / Formato / Autenticação** | `GET` \| `JSON` \| Não exige autenticação |
| **Parâmetros** | `page` (página), `pageSize` (máx. 100), `sort` (ordenação, ex: `postedAt:desc`) |
| **Campos Retornados** | `id`, título, empresa, `postedAt`, modalidade, localização |
| **Comportamento da Paginação** | Utiliza `page` + `pageSize`. Para obter a descrição completa e dados extras, executa chamada secundária a `/api/jobs/{id}`. |

---

## 📊 3. Matriz Comparativa Resumida

| Critério / API | Meu Padrinho | Gupy | InHire | Solides | Trampos.co | Quero Vagas Tech |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Método HTTP** | `GET` | `GET` | `GET` | `GET` | `GET` | `GET` |
| **Resposta JSON** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Autenticação Exigida** | ❌ Não | ❌ Não | ❌ Não | ❌ Não | ❌ Não | ❌ Não |
| **Limite por Requisição** | Não ident. | 100 | N/A | 25 (`take`) | Não ident. | 100 |
| **Mecanismo Paginação** | `page` | `offset` | N/A | `page` | `page` | `page` |
| **Busca por Palavra-Chave**| ❌ | ✅ `jobName` | ❌ | ✅ `title` | ✅ `tr` | ❌ |
| **Filtro Senioridade** | ✅ `niveis` | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Descrição Inclusa** | Endpoint extra | ✅ | ❌ | ✅ | Parcial | Endpoint extra |
| **Identificador Único** | `nano_id` | `id` | `jobId` | ID | ID | `id` |
| **Principal Limitação** | Endpoints separ. | Nenhuma grave | Exige Tenant | Limite `take=25` | Desc. parcial | Sem busca txt |

---

## ⚙️ 4. Fluxo de Coleta e Engenharia de Dados (Pipeline)

1. **Ingestão da Listagem:** O coletor realiza chamadas sequenciais para a fonte principal (**Meu Padrinho**) incrementando a paginação (`page=1`, `page=2`...).
2. **Coleta de Detalhes e Skills:** Para cada vaga, o sistema extrai o `nano_id` e faz chamadas paralelas para `/api/vagas/{nano_id}` (descrição, localização, salário) e `/api/vagas/{nano_id}/tecnologias`.
3. **Normalização dos Dados:** Todos os atributos retornados são convertidos para o **Schema Normalizado** (seção 1).
4. **Desduplicação Incremental (Upsert):**
   * O sistema valida o `nano_id` no banco de dados.
   * Se já existir, atualiza os dados da vaga.
   * Se for novo, insere o registro com status `ATIVA`.
5. **Inativação:** Vagas que deixarem de constar nas varreduras sucessivas são marcadas como `INATIVA`.
