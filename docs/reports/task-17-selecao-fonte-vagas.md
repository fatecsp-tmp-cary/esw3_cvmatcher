# Task #17 — Seleção da Fonte de Dados de Vagas

## Fontes avaliadas
Com base no documento "Análise de Fontes de Dados e APIs de Vagas para MVP" (Vitória), foram testadas 3 fontes:

1. **Meu Padrinho / API Vagas Tech** — agregador focado em vagas de tecnologia.
2. **Gupy** — endpoint público de busca por palavra-chave.
3. **InHire** — API pública por empresa (tenant).

## Endpoints principais
| Fonte | Endpoint | Autenticação |
|---|---|---|
| Meu Padrinho | GET /api/vagas (+ /vagas/{id} e /vagas/{id}/tecnologias) | Não exigida |
| Gupy | GET https://employability-portal.gupy.io/api/v1/jobs | Não exigida |
| InHire | GET https://api.inhire.app/job-posts/public/pages | Não exigida (requer header X-Tenant) |

## Recomendação (conforme documento da Vitória)
Combinar **Gupy** (busca ampla por palavra-chave, cobertura nacional) com **Meu
Padrinho** (filtro por senioridade e tecnologias) como fontes principais.
**InHire** deve ser usada de forma complementar, restrita a empresas
predefinidas (ex: Magazine Luiza), pois exige consulta individual por tenant
e não permite busca global entre empresas.

## Estrutura de dados (resumo comparativo)
| Campo | Meu Padrinho | Gupy | InHire |
|---|---|---|---|
| Busca por termo livre | Não (endpoint principal) | jobName | Não |
| Filtro de senioridade | niveis (estagio, junior, pleno, senior) | Não disponível | Não disponível |
| Paginação | page | offset + limit | Não identificada |
| Descrição completa da vaga | Endpoint separado (/tecnologias) | Incluída no JSON | Não disponível |
| Localização | Endpoint de detalhe separado | city, state, country | location |

## Limitações conhecidas
- **Meu Padrinho:** sem busca por termo livre no endpoint principal; requer chamadas extras para descrição e tecnologias.
- **Gupy:** sem filtro nativo de senioridade.
- **InHire:** sem busca global entre empresas; consulta restrita por tenant (X-Tenant obrigatório); sem dados de descrição, requisitos ou tecnologias.

## Pendências (a confirmar com a autora da pesquisa)
- **Modo de ingestão (incremental vs. snapshot):** o documento não especifica se Gupy e Meu Padrinho retornam apenas registros novos/alterados a cada consulta, ou a listagem completa. Este é um requisito de teste explícito do CONTRIBUTING.md do projeto.
- **Rate limits:** não há informação sobre limite de chamadas (por minuto/dia) em nenhuma das três fontes testadas. O CONTRIBUTING.md exige respeitar rate limits das fontes de dados.
- **Fontes do Documento de Requisitos original não avaliadas nesta pesquisa:** apinfo, Programathor, Coodesh, Indeed, Solides, Portal Emprega Brasil, PCD. A confirmar se foram descartadas formalmente ou se a pesquisa focou diretamente nas três fontes acima.

## Fonte
Documento: "Análise de Fontes de Dados e APIs de Vagas para MVP" — Vitória.