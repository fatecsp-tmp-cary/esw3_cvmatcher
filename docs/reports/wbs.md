# WBS do CV-Match
## 1. Gerenciamento
### 1.1 Gestão do Projeto
#### 1.1.1 Escopo do Projeto
 - 1.1.1.1 Definição do escopo do MVP
 - 1.1.1.2 Delimitação do MVP
 - 1.1.1.3 Definição do escopo excluído
 - 1.1.1.4 Critérios de aceite
 - 1.1.1.5 Definição da conclusão da entrega
 - 1.1.1.6 Termo de abertura de projeto

#### 1.1.2 Planejamento do Projeto
 - 1.1.2.1 *Roadmap*
 - 1.1.2.2 Cronograma
 - 1.1.2.3 Distribuição de Responsabilidades
 - 1.1.2.4 Definição de Marcos
 - 1.1.2.5 Estrutura Analítica do Projeto

#### 1.1.3 Monitoramento do Projeto
 - 1.1.3.1 Indentificação dos indicadores de progresso
 - 1.1.3.2 Planejamento de relatórios de acompanhamento
 - 1.1.3.3 Registro de bloqueios
 - 1.1.3.4 Registro de decisões

#### 1.1.4 Gestão de Riscos
 - 1.1.4.1 Registro de riscos
 - 1.1.4.2 Identificação dos riscos regulatórios
 - 1.1.4.3 Identificação dos riscos de fontes
 - 1.1.4.4 Identificação dos riscos de infraestrutura
 - 1.1.4.5 Planos de resposta

#### 1.1.5 Gestão de Código
 - 1.1.5.1 Estrutura de diretórios
 - 1.1.5.2 Template de *PR*
 - 1.1.5.3 Template de *Issues*
 - 1.1.5.4 `PLAN.md` com definição do projeto
##### 1.1.5.5 Repositório no *GitHub*
 - 1.1.5.5.1 Definição de equipes
 - 1.1.5.5.2 *Workflow* para padronização de nomenclatura de *branches*
 - 1.1.5.5.3 *Workflow* para padronização de ciclo de vida de *PR*
 - 1.1.5.5.4 *Ruleset* que impõe regramento para revisão de *PR*
 - 1.1.5.5.5 Restrição de escopo de edição entre diferentes *CODEOWNER*s (equipes)
 - 1.1.5.5.6 *Planner + Board Kanban + Cronograma*

### 1.2 Arquitetura
#### 1.2.1 Arquitetura da Solução
 - 1.2.1.1 Componentes arquiteturais
 - 1.2.1.2 Limites entre componentes
 - 1.2.1.3 Fluxo ponta a ponta

#### 1.2.2 Modelo de Domínio
 - 1.2.2.1 Entidades de domínio
 - 1.2.2.2 Estados de domínio
 - 1.2.2.3 Relacionamentos de domínio

#### 1.2.3 Padrões Arquiteturais
 - 1.2.3.1 Separação de ingestão e *matching*
 - 1.2.3.2 Separação de busca textual e semântica
 - 1.2.3.3 Persistência centralizada em *PostgreSQL*
 - 1.2.3.4 Processamento assíncrono

#### 1.2.4 Decisões Arquiteturais
 - 1.2.4.1 Registro de decisões arquiteturais
 - 1.2.4.2 Restrições tecnológicas

### 1.3 Entregas e Documentação
#### 1.3.1 Documentação do Produto
 - 1.3.1.1 *README*
 - 1.3.1.2 *CONTRIBUTING*
 - 1.3.1.3 Licença
 - 1.3.1.4 Guia de execução local
 - 1.3.1.5 Documentação de configuração

#### 1.3.2 Documentação das Interfaces
 - 1.3.2.1 Contratos de *API*
 - 1.3.2.2 *OpenAPI* publicado
 - 1.3.2.3 Contratos de fontes

#### 1.3.3 Releases
 - 1.3.3.1 Escolha de versionamento
 - 1.3.3.2 Artefato de release
 - 1.3.3.3 Padronização de notas de release

---
## 2. Coleta
### 2.1 Fontes de Vagas
#### 2.1.1 Inventário de Fontes
##### 2.1.1.1 Pesquisa de fontes brasileiras
 - 2.1.1.1.1 Características das fontes registradas
 - 2.1.1.1.2 Restrições das fontes registradas

##### 2.1.1.1 Pesquisa de fontes internacionais
 - 2.1.1.1.1 Características das fontes registradas
 - 2.1.1.1.2 Restrições das fontes registradas

#### 2.1.2 Viabilidade das Fontes
 - 2.1.2.1 Viabilidade técnica
 - 2.1.2.2 Viabilidade operacional
 - 2.1.2.3 Avaliação das restrições de uso
 - 2.1.2.4 Viabilidade de fontes estrageiras para vagas brasileiras

#### 2.1.3 Seleção das Fontes
 - 2.1.3.1 Seleção de fontes para MVP
 - 2.1.3.2 Listagem de fontes futuras

### 2.2 Conectores de Ingestão
#### 2.2.1 Contrato de Ingestão
 - 2.2.1.1 Interface `JobSource`
 - 2.2.1.2 Contrato de descoberta
 - 2.2.1.3 Contrato de obtenção
 - 2.2.1.4 Contrato de normalização

#### 2.2.2 Conectores
 - 2.2.2.1 Conector MVP implementado
 - 2.2.2.2 Adaptadores de *APIs* públicas
 - 2.2.2.3 Adaptadores ATS (opcional)
 - 2.2.2.4 Adaptadores *webscrap* (opcional)

#### 2.2.3 Estratégias de Coleta e Identidade
 - 2.2.3.1 Modo `INCREMENTAL` (paginado)
 - 2.2.3.2 Modo `SNAPSHOT`
 - 2.2.3.3 Identidade `source + source_job_id`

### 2.3 Coordenação da Ingestão
#### 2.3.1 Execução da Coleta
 - 2.3.1.1 *Scheduler*
 - 2.3.1.2 *Worker*
 - 2.3.1.3 *Polling*
 - 2.3.1.4 Bloqueio de execução concorrente

#### 2.3.2 Histórico das Execuções de Fonte
 - 2.3.2.1 Registro `source_runs`
 - 2.3.2.2 Registro de resultado da execução
 - 2.3.2.3 Registro de falhas da execução
 - 2.3.2.4 Registro de evidência de snapshot completo

### 2.4 Normalização
#### 2.4.1 Conteúdo das Vagas
 - 2.4.1.1 Normalização textual
 - 2.4.1.2 Normalização HTML
 - 2.4.1.3 Normalização Unicode
 - 2.4.1.4 Identificação das seções da vaga

#### 2.4.2 habilidades
 - 2.4.2.1 Taxonomia de habilidades
 - 2.4.2.2 Aliases de habilidades
 - 2.4.2.3 Normalização das habilidades das vagas
 - 2.4.2.4 Normalização das habilidades dos candidatos

#### 2.4.3 Requisitos
 - 2.4.3.1 Extração de requisitos
 - 2.4.3.2 Classificação `REQUIRED`
 - 2.4.3.3 Classificação `PREFERRED`
 - 2.4.3.4 Classificação `NICE_TO_HAVE`

#### 2.4.4 Candidato
 - 2.4.4.1 Validação de `CandidateProfile`
 - 2.4.4.2 Normalização de `CandidateProfile`
 - 2.4.4.3 Implementação de `CandidateProfile` transitório

#### 2.4.5 Localização e Modalidade
 - 2.4.5.1 Normalização de localizações
 - 2.4.5.2 Normalização de modalidades de emprego

### 2.5 Ciclo de Vida das Vagas
#### 2.5.1 Estados
 - 2.5.1.1 Estado `DISCOVERED`
 - 2.5.1.2 Estado `ACTIVE`
 - 2.5.1.3 Estado `STALE`
 - 2.5.1.4 Estado `EXPIRED`

#### 2.5.2 Detecção de Alterações
 - 2.5.2.1 Cálculo de `content_hash`
 - 2.5.2.2 Lógica de detecção de alteração
 - 2.5.2.3 Garantia de preservação de conteúdo inalterado

#### 2.5.3 Expiração e Reativação
 - 2.5.3.1 Critérios de expiração configuráveis
 - 2.5.3.2 Expiração por `source_expires_at`
 - 2.5.3.3 Expiração por ausência configurável
 - 2.5.3.4 Reativação por redescoberta
 - 2.5.3.5 Proteção contra falso desaparecimento

#### 2.5.4 Histórico
 - 2.5.4.1 *Timestamps* de ciclo de vida
 - 2.5.4.2 Histórico de vagas expiradas preservado
 - 2.5.4.3 Exclusão física de vagas fora do MVP

### 2.6 Ambiente de Coleta
#### 2.6.1 Conteinerização
 - 2.6.1.1 Imagem de coleta
 - 2.6.1.2 Configuração de coleta conteinerizada

#### 2.6.2 Ambiente Executável
 - 2.6.2.1 Ambiente local de coleta configurado
 - 2.6.2.2 Dependências de coleta

---
## 3. *Match*
### 3.1 Estratégia Semântica
#### 3.1.1 Modelos Candidatos
 - 3.1.1.1 Seleção de modelos *PT/EN* candidatos
 - 3.1.1.2 Avaliação de viabilidade
 - 3.1.1.3 Escolha de modelo candidato

#### 3.1.2 Comparadores Semânticos
 - 3.1.2.1 Avaliação de estratégias de similaridade
 - 3.1.2.2 Seleção de estratégia de similaridade

#### 3.1.3 Estratégia de Representação
 - 3.1.3.1 Representação de vaga
 - 3.1.3.2 Representação de candidato
 - 3.1.3.3 Tratamento de localização e modalidade

#### 3.1.4 Modelo Selecionado
 - 3.1.4.1 Modelo de *embedding*
 - 3.1.4.2 Versionamento do modelo

### 3.2 Indexação
#### 3.2.1 Índice Textual
 - 3.2.1.1 Implementação de índice FTS
 - 3.2.1.2 Indexação de campos textuais
 - 3.2.1.3 Implementação de restrição a vagas `ACTIVE`

#### 3.2.2 Índice Vetorial
 - 3.2.2.1 Índice *pgvector*
 - 3.2.2.2 Persistência de *embeddings* de vagas
 - 3.2.2.3 Exclusão de *embeddings* inválidos

#### 3.2.3 Regeneração
 - 3.2.3.1 Invalidação por alteração de conteúdo
 - 3.2.3.2 Invalidação por alteração de modelo
 - 3.2.3.3 Regeneração assíncrona
 - 3.2.3.4 Atualização do índice vetorial

### 3.3 *Matching*
#### 3.3.1 Elegibilidade
 - 3.3.1.1 Filtros de incompatibilidades certas
 - 3.3.1.2 Avaliação de requisitos obrigatórios
 - 3.3.1.3 Incerteza tratada por pontuação
 - 3.3.1.4 Elegibilidade de *matching*

#### 3.3.2 Recuperação de Candidatos
 - 3.3.2.1 Recuperação textual
 - 3.3.2.2 Recuperação semântica
 - 3.3.2.3 Exclusão de vagas sem *embedding* válido

#### 3.3.3 Comparação Estruturada
 - 3.3.3.1 Comparação de habilidades
 - 3.3.3.2 Comparação de senioridade
 - 3.3.3.3 Comparação de experiência
 - 3.3.3.4 Comparação de modalidade de contrato
 - 3.3.3.5 Comparação de idiomas

#### 3.3.4 Resultado do *Matching*
 - 3.3.4.1 Correspondência de habilidades
 - 3.3.4.2 Requisitos faltantes
 - 3.3.4.3 Elegibilidade

### 3.4 Ranqueamento
#### 3.4.1 Pontuação
 - 3.4.1.1 Normalização de pontuação textual
 - 3.4.1.2 Normalização de pontuação semântica
 - 3.4.1.3 Normalização de pontuação estruturada
 - 3.4.1.4 Pontuação final de compatibilidade

#### 3.4.2 Ranqueamento determinístico

#### 3.4.3 Versionamento
 - 3.4.3.1 Registro de versão do algoritmo
 - 3.4.3.2 Registro de versão do modelo

#### 3.4.4 Resultado do Ranqueamento
 - 3.4.4.1 `MatchResult`
 - 3.4.4.2 Ranqueamento configurável
 - 3.4.4.3 Definição de pesos padrão

### 3.5 Ambiente de Match
#### 3.5.1 Conteinerização
 - 3.5.1.1 Imagem de *matching*
 - 3.5.1.2 Configuração de *matching* conteinerizada

#### 3.5.2 Ambiente Executável
 - 3.5.2.1 Disponibilização de modelo local
 - 3.5.2.2 Configuração de ambiente local de *matching*

---
## 4. Integração
### 4.1 Persistência
#### 4.1.1 Modelo de Dados
 - 4.1.1.1 Persistência de entidades
 - 4.1.1.2 Persistência de relacionamentos
 - 4.1.1.3 Mapeamento da entidade `Job`

#### 4.1.2 Integridade
 - 4.1.2.1 Restrições de integridade
 - 4.1.2.2 Identidade `source` + `source_job_id`
 - 4.1.2.3 Integridade referencial

#### 4.1.3 Migrações
 - 4.1.3.1 Migrações iniciais
 - 4.1.3.2 Migrações de evolução

#### 4.1.4 Privacidade e Compliance LGPD
 - 4.1.4.1 Minimização da coleta de dados pessoais
 - 4.1.4.2 Proteções de acesso ao banco

### 4.2 *API*
#### 4.2.1 *API* de *Matching*
 - 4.2.1.1 *Endpoint* *POST* `/matches`
 - 4.2.1.2 Contrato de entrada
 - 4.2.1.3 Contrato de saída

#### 4.2.2 *API* Operacional
 - 4.2.2.1 *Endpoint* `/health`

#### 4.2.3 Validação
 - 4.2.3.1 Validação *Pydantic*
 - 4.2.3.2 Tratamento de erros
 - 4.2.3.3 Padronização das respostas de erro

#### 4.2.4 Segurança
 - 4.2.4.1 Credenciais externalizadas
 - 4.2.4.2 Proteção de *endpoints*
 - 4.2.4.3 Garantia de exclusão do dados de candidato de logs
 - 4.2.4.4 *HTTPS* preparado para produção

### 4.3 Infraestrutura
#### 4.3.1 Estratégia de provisionamento
 - 4.3.1.1 Estratégia local
 - 4.3.1.2 Estratégia em plataforma gratuita
 - 4.3.1.3 Requisitos de persistência

#### 4.3.2 Provisionamento
 - 4.3.2.1 *Docker Compose*
 - 4.3.2.2 Provisionamento local
 - 4.3.2.3 Configuração em plataforma gratuita
 - 4.3.2.4 *GitHub Actions*

#### 4.3.3 Configuração
 - 4.3.3.1 Variáveis de ambiente
 - 4.3.3.2 Configuração de *secrets*
 - 4.3.3.3 Configuração de produção

### 4.4 Orquestração
#### 4.4.1 Ambiente Integrado
 - 4.4.1.1 *API* integrada ao *PostgreSQL*
 - 4.4.1.2 Integração *PostgreSQL* + *pgvector*
 - 4.4.1.3 *Worker*
 - 4.4.1.4 *Scheduler*

#### 4.4.2 Integração dos Ambientes
 - 4.4.2.1 *Pipeline* de coleta
 - 4.4.2.2 *Pipeline* de indexação
 - 4.4.2.3 *Pipeline* de *embedding*
 - 4.4.2.4 *Pipeline* de *matching*

#### 4.4.3 Execução Ponta a Ponta
 - 4.4.3.1 Fluxo CV -> `CandidateProfile`
 - 4.4.3.2 Fluxo fonte -> `Job`
 - 4.4.3.3 Fluxo `Job` -> índice
 - 4.4.3.4 Fluxo `CandidateProfile` -> ranqueamento

### 4.5 Observabilidade Transversal
#### 4.5.1 Métricas
 - 4.5.1.1 Métricas de processamento
 - 4.5.1.2 Métricas de *matching*
 - 4.5.1.3 Métricas de desempenho

#### 4.5.2 Falhas
 - 4.5.2.1 Registro de falhas de processamento
 - 4.5.2.2 Registro de falhas de indexação
 - 4.5.2.3 Registro de falhas de *embedding*
 - 4.5.2.4 Registro de falhas de *matching*

---
## 5. QA
### 5.1 Testes Unitários
#### 5.1.1 Domínio
 - 5.1.1.1 Testes de identidade
 - 5.1.1.2 Testes de *hash*
 - 5.1.1.3 Testes de ciclo de vida

#### 5.1.2 Coleta
 - 5.1.2.1 Testes de normalização
 - 5.1.2.2 Testes de taxonomia
 - 5.1.2.3 Testes de requisitos
 - 5.1.2.4 Testes de modos de coleta

#### 5.1.3 Match
 - 5.1.3.1 Testes de filtros
 - 5.1.3.2 Testes de pontuação
 - 5.1.3.3 Testes de ranqueamento
 - 5.1.3.4 Testes de determinismo

### 5.2 Testes de Integração
#### 5.2.1 *Pipeline* de Coleta
 - 5.2.1.1 Testes fonte -> ingestão
 - 5.2.1.2 Testes ingestão -> normalização
 - 5.2.1.3 Testes normalização -> banco

#### 5.2.2 Fontes Externas
 - 5.2.2.1 Testes de integração contra fontes reais

#### 5.2.3 Componentes de *Matching*
 - 5.2.3.1 Testes FTS
 - 5.2.3.2 Testes *pgvector*
 - 5.2.3.3 Testes de regeneração

### 5.3 Testes de Sistema
#### 5.3.1 *API*
 - 5.3.1.1 Testes do endpoint `/matches`
 - 5.3.1.2 Testes de validação
 - 5.3.1.3 Testes de erros

#### 5.3.2 Ingestão
 - 5.3.2.1 Testes de *polling*
 - 5.3.2.2 Testes de *upsert*
 - 5.3.2.3 Testes de falha de *polling*

#### 5.3.3 Ciclo de Vida
 - 5.3.3.1 Testes de *snapshot*
 - 5.3.3.2 Testes de expiração
 - 5.3.3.3 Testes de reativação
 - 5.3.3.4 Testes de "falso desaparecimento"

#### 5.3.4 *Matching*
 - 5.3.4.1 Testes de ranqueamento
 - 5.3.4.2 Testes de requisitos ausentes

#### 5.3.5 *Embeddings*
 - 5.3.5.1 Testes de invalidação por conteúdo
 - 5.3.5.2 Testes de invalidação por modelo
 - 5.3.5.3 Testes de regeneração

### 5.4 Regressão e Validação
#### 5.4.1 *Dataset* de Regressão
 - 5.4.1.1 *Dataset* consolidado
 - 5.4.1.2 Casos de referência

#### 5.4.2 Não-Regressão
 - 5.4.2.1 Testes de não-deduplicação
 - 5.4.2.2 Testes de determinismo

#### 5.4.3 Validação de Modelos
 - 5.4.3.1 Validação do modelo de *embedding*
 - 5.4.3.2 Validação de regeneração
 - 5.4.3.3 Validação de versionamento

#### 5.4.4 Validação Final
 - 5.4.4.1 Validação do *pipeline* ponta a ponta
 - 5.4.4.2 Validação de critérios de aceite
 - 5.4.4.3 Validação da conclusão da entrega
