# TERMO DE ABERTURA DO PROJETO (TAP)

## 1. Identificação do Projeto

| Campo | Informação |
|---|---|
| **Nome do projeto** | CV-Match |
| **Disciplina** | Engenharia de Software 3 |
| **Instituição** | FATEC São Paulo |
| **Professor/Patrocinador** | Victor A. T. Troitiño |
| **Gerente do projeto** | Carybé Gonçalves Silva |
| **Data de emissão** | [08/08/2026] |
| **Versão** | [1.0] |

---

## 2. Integrantes

| Integrante                            | R.A.          |
|:------------------------------------- | :------------ |
| 1. Aline de Souza Barbosa             | 1110482323053 |
| 2. Carybé Gonçalves Silva             | 0020482523039 |
| 3. Davi Campaner Fernandes            | 0020482512029 |
| 4. Esthefano Esteves                  | 0020482413100 |
| 5. Fabíola Girotti Garcia             | 0020482423055 |
| 6. Gustavo Conceição Lacerda          | 1110482322010 |
| 7. Henrique Yamaguchi                 | 0020482413102 |
| 8. Kauan Baptiston Gassi              | 0020482521044 |
| 9. Ricardo Massanobu Sakugawa         | 0020482323095 |
| 10. Roger Hokama Paixão               | 0020482413079 |
| 11. Vitória Cristina Vicente da Silva | 0020482423091 |
| 12. Yuri Guedes Umeda                 | 0020482413023 |

---

## 3. Justificativa do Projeto

O processo de identificação de oportunidades profissionais compatíveis com um currículo apresenta elevado esforço manual, especialmente quando envolve múltiplas plataformas de empregos, diferentes estruturas de dados e grande volume de vagas.

O projeto surge da oportunidade de desenvolver uma solução capaz de **coletar, normalizar, indexar e comparar vagas de emprego com informações de um currículo**, permitindo identificar e retornar as oportunidades de maior compatibilidade.

A solução poderá reduzir o esforço necessário para busca de vagas e proporcionar maior objetividade na priorização das oportunidades, por meio da aplicação combinada de técnicas de recuperação de informação, correspondência textual e processamento de linguagem natural.

---

## 4. Finalidade do Projeto

Desenvolver um **MVP de uma API de recomendação e ranqueamento de vagas**, capaz de receber um currículo e retornar um conjunto ordenado de oportunidades profissionais da base de dados de acordo com seu grau de compatibilidade.

---

## 5. Objetivo do Projeto

### 5.1 Objetivo geral

Desenvolver e validar, até **10/11/2026**, uma API capaz de identificar e ranquear vagas de emprego com maior compatibilidade em relação a um currículo estruturado, utilizando uma base de vagas coletadas e normalizadas e técnicas de busca e similaridade textual.

### 5.2 Objetivos específicos

* Desenvolver módulos para ingestão de vagas provenientes de APIs públicas ou fontes de dados autorizadas, complementados, quando aplicável, por mecanismos de coleta automatizada.
* Implementar processo de normalização, validação e persistência das informações das vagas em banco de dados.
* Desenvolver mecanismo de busca e ranqueamento utilizando técnicas como **fuzzy matching, ou comparadores semânticos baseados em transformadores**.
* Disponibilizar uma API REST para consulta das vagas mais compatíveis com um currículo estruturado.
* Implementar testes automatizados, testes de integração e critérios de qualidade que permitam validar o funcionamento do MVP.

---

## 6. Descrição do Projeto

O projeto será desenvolvido como uma solução modular composta, em alto nível, por:

1. **Camada de ingestão:** submódulos com workers responsáveis pela obtenção e atualização de vagas a partir de APIs e fontes autorizadas.
2. **Camada de normalização:** padronização de campos, tratamento de inconsistências e enriquecimento dos dados.
3. **Camada de armazenamento e indexação:** persistência em banco de dados e indexação para recuperação eficiente.
4. **Pipeline de Match:** processamento das informações do currículo e comparação com os atributos das vagas, combinando busca textual e técnicas de similaridade semântica.
5. **API:** exposição dos resultados de compatibilidade por meio de endpoints REST.
6. **Qualidade e integração:** testes unitários, integração entre componentes, validação dos resultados e documentação.

A execução será organizada de forma incremental, com integração contínua dos componentes e validações periódicas.

---

## 7. Requisitos

Os principais requisitos identificados para o projeto são:

* A solução deverá receber um **currículo estruturado** como entrada.
* Deverá existir uma base de vagas coletadas, normalizadas e persistidas.
* As vagas deverão possuir estrutura padronizada contendo, quando disponível, informações como cargo, descrição, requisitos, competências, faixa salarial, localização e modalidade.
* O sistema deverá realizar busca e ranqueamento das vagas considerando a compatibilidade com o currículo.
* A API deverá retornar um conjunto ordenado de vagas, acompanhado de um indicador ou pontuação de compatibilidade.
* A arquitetura deverá permitir a execução independente dos módulos de ingestão, processamento/match e API.
* O sistema deverá possuir testes automatizados e de integração para os componentes críticos.

---

## 8. Entregas Principais

| Entrega                           | Descrição                                                       | Critério de aceite                                                           |
| --------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Pipeline de ingestão**          | Workers para coleta de vagas a partir das fontes selecionadas   | Vagas coletadas e processadas de forma automatizada                             |
| **Base normalizada de vagas**     | Banco de dados contendo vagas padronizadas e indexadas          | Dados persistidos, consistentes e recuperáveis                                  |
| **Motor de Match**                | Mecanismo de busca, comparação e ranqueamento currículo × vaga  | Retorno ordenado conforme critérios de compatibilidade definidos                |
| **API de recomendação**           | API REST para consulta das vagas compatíveis                    | Endpoints funcionais, documentados e integrados ao motor de Match               |
| **Pacote de testes e integração** | Testes unitários, integração e validação do fluxo ponta a ponta | Critérios mínimos de cobertura e funcionamento definidos pelo projeto atendidos |
| **Documentação técnica**          | Documentação da arquitetura, APIs, execução e componentes       | Documentação suficiente para instalação, execução e manutenção do MVP           |

---

## 9. Escopo

### Incluído no escopo

* Desenvolvimento da API de recomendação de vagas.
* Desenvolvimento dos módulos de ingestão e normalização.
* Persistência e indexação das vagas.
* Desenvolvimento do mecanismo de comparação e ranqueamento.
* Integração entre ingestão, armazenamento, Match e API.
* Implementação de testes e validação do fluxo ponta a ponta.
* Documentação técnica e arquitetural do MVP.

### Fora do escopo

* Desenvolvimento de uma aplicação web ou aplicativo mobile completo para usuários finais.
* Criação de um sistema completo de recrutamento ou gestão de processos seletivos.
* Cadastro e manutenções manuais no agregador de vagas.
* Automação de candidatura às vagas.
* Aquisição de bases de dados proprietárias ou serviços pagos de recrutamento.
* Garantia de disponibilidade ou cobertura de todas as plataformas de empregos existentes.
* Adequação do currículo do candidato à vagas pretendidas.
* Filtragem de vagas de acordo com atributos das mesmas.
---

## 10. Premissas

Consideram-se, inicialmente, as seguintes premissas:

* As fontes selecionadas disponibilizarão dados por APIs públicas ou por mecanismos de coleta de forma viável.
* O currículo utilizado como entrada estará estruturado em formato previamente definido pelo projeto 1.
* Os dados coletados apresentarão informações suficientes para permitir a normalização e comparação.
* A equipe terá conhecimento suficiente para implementar os componentes previstos ou realizar a capacitação necessária durante o projeto.
* O MVP será orientado à demonstração da viabilidade técnica, não constituindo produto comercial definitivo.

---

## 11. Restrições

As principais restrições do projeto são:

* **Orçamento:** estimativa de **R$ 77.033**, incluindo mão de obra, infraestrutura em nuvem e reserva gerencial.
* **Prazo:** **01/09/2026 a 10/11/2026**.
* **Recursos:** utilização prioritária de tecnologias open source e recursos de infraestrutura em nuvem.
* **Equipe:** **12 integrantes**.
* **Tecnologia:** a solução deverá ser implementada preferencialmente com tecnologias compatíveis com Python/FastAPI, mecanismos de busca/indexação e modelos de similaridade textual.
* **Serviços:** não serão contratados serviços de assinatura, exceto infraestrutura em nuvem necessária à execução.
* **Escopo:** alterações significativas de escopo deverão ser submetidas à avaliação e aprovação do patrocinador.

---

## 12. Orçamento

Para fins de estimativa, foi considerado o período de **10 semanas** de execução e uma dedicação média de **7 h/semana por integrante**, totalizando aproximadamente **70 horas por integrante**.

### Estimativa de mão de obra

| Integrante/Função     |  Qtde. | Custo-hora estimado | Salário mensal equivalente* | Custo no projeto |
| --------------------- | -----: | ------------------: | --------------------------: | ---------------: |
| Gerente de Projetos   |      1 |               R$ 80 |                    R$ 2.425 |         R$ 6.160 |
| Tech Lead             |      1 |              R$ 100 |                    R$ 3.031 |         R$ 7.700 |
| Lead Data Engineer    |      1 |               R$ 85 |                    R$ 2.576 |         R$ 6.545 |
| Lead Match            |      1 |               R$ 85 |                    R$ 2.576 |         R$ 6.545 |
| Lead QA               |      1 |               R$ 85 |                    R$ 2.576 |         R$ 6.545 |
| Eng. Data/Backend     |      2 |               R$ 65 |                    R$ 1.970 |        R$ 10.010 |
| Eng. Match/ML         |      2 |               R$ 65 |                    R$ 1.970 |        R$ 10.010 |
| Eng. QA/Integração    |      2 |               R$ 65 |                    R$ 1.970 |        R$ 10.010 |
| Eng. DevOps/Infra     |      1 |               R$ 65 |                    R$ 1.970 |         R$ 5.005 |
| **Total mão de obra** | **12** |                     |                             |    **R$ 68.530** |

*Valor mensal equivalente calculado a partir do custo-hora estimado e da dedicação média prevista para o projeto; não representa necessariamente remuneração contratual efetiva.

### Orçamento consolidado

| Categoria                      | Valor previsto |
| ------------------------------ | -------------: |
| Infraestrutura em nuvem        |       R$ 1.500 |
| Mão de obra                    |      R$ 68.530 |
| Reserva gerencial/contingência |       R$ 7.003 |
| **Total**                      |  **R$ 77.033** |

### Estratégia para manutenção do orçamento

O orçamento será controlado por meio do acompanhamento periódico dos custos de mão de obra e consumo da infraestrutura em nuvem. Será priorizado o uso de tecnologias open source, evitando contratação de licenças ou assinaturas adicionais. A reserva prevista será utilizada somente mediante ocorrência de riscos ou necessidades previamente avaliadas e aprovadas.

---

## 13. Cronograma de Marcos

| Marco                                   | Data prevista |
| --------------------------------------- | ------------- |
| Início do projeto                       | 01/09/2026    |
| Definição do escopo e requisitos        | 08/09/2026    |
| Arquitetura e modelo de dados definidos | 10/09/2026    |
| Pipeline de ingestão e base inicial     | 17/09/2026    |
| Primeiro protótipo do Match             | 06/10/2026    |
| Integração API + Match + base           | 20/10/2026    |
| Validação e testes finais               | 03/11/2026    |
| Entrega principal                       | 10/11/2026    |
| Apresentação/avaliação                  | 10/11/2026    |
| Encerramento do projeto                 | 10/11/2026    |

---

## 14. Riscos

| Risco                                                 | Probabilidade | Impacto | Resposta inicial                                                                        |
| --- | --- | --- | --- |
| Alteração ou indisponibilidade das fontes de vagas    | Alta          | Alto    | Utilizar múltiplas fontes e desacoplar os ingestores                                    |
| Baixa qualidade ou inconsistência dos dados coletados | Alta          | Alto    | Implementar normalização, validação e tratamento de dados                               |
| Desempenho ou baixa precisão do algoritmo de Match    | Média         | Alto    | Avaliar diferentes estratégias de busca e similaridade e utilizar conjunto de validação |
| Dificuldade de integração entre os módulos            | Média         | Alto    | Definir contratos de API, modelos de dados e testes de integração antecipadamente       |
| Consumo de infraestrutura acima do estimado  | Média         | Médio   | Monitorar custos, utilizar limites de recursos e otimizar processamento                 |
| Indisponibilidade de integrantes em etapas críticas   | Média         | Alto    | Documentação, divisão de responsabilidades e compartilhamento de conhecimento           |

---

## 15. Critérios de Aceite

As entregas serão consideradas aceitas quando atenderem aos critérios definidos e forem validadas pelo responsável técnico e pelo gerente do projeto.

De forma geral:

* **Ingestão:** deverá ser possível executar os workers e obter vagas das fontes selecionadas, com tratamento dos dados conforme o modelo definido.
* **Base de dados:** as vagas deverão estar armazenadas em estrutura padronizada e disponíveis para consulta/indexação.
* **Motor de Match:** deverá receber os atributos do currículo e produzir uma lista ordenada de vagas, com respectiva pontuação ou indicador de compatibilidade.
* **API:** deverá disponibilizar endpoints documentados, responder às requisições previstas e integrar-se corretamente ao mecanismo de Match.
* **Integração:** deverá ser demonstrado o fluxo completo **currículo → busca/Match → vagas ranqueadas**.
* **Qualidade:** os testes definidos para os componentes críticos deverão ser executados com resultado satisfatório.
* **Documentação:** arquitetura, instalação, configuração, endpoints e principais decisões técnicas deverão estar documentados.
* **Entrega final:** o MVP deverá estar disponível para demonstração até **10/11/2026**.

---

## 16. Governança e Controle de Mudanças


Alterações que impliquem mudança relevante de **escopo, prazo, orçamento ou requisitos** deverão ser formalizadas e avaliadas pelo gerente do projeto e pelo Tech Lead, quando envolverem aspectos técnicos, sendo submetidas ao orientador/patrocinador para aprovação quando excederem a autoridade da equipe.

A linha de base aprovada deverá ser utilizada como referência para o acompanhamento do projeto e para avaliação de eventuais solicitações de mudança.

---

## 17. Aprovação do Termo de Abertura

A aprovação deste Termo de Abertura autoriza formalmente o início do projeto e estabelece os limites iniciais de escopo, prazo, orçamento, responsabilidades e critérios de sucesso. Alterações relevantes nesses elementos deverão seguir o processo de controle de mudanças definido para o projeto.

| Nome | Papel | Assinatura | Data |
|---|---|---|---|
| Carybé Gonçalves Silva | Gerente do projeto | __________________ | 08/08/2026 |
| Victor A. T. Troitiño  | Professor(a)/Patrocinador(a) | __________________ | 08/08/2026 |

---

## 18. Controle de Versão

| Versão | Data  | Descrição da alteração |
|---|---|---|
| 1.0 | 03/08/2026 | Emissão inicial |

<!-- | 1.1 | [Data] | [Nome] | [Alteração] |  -->
