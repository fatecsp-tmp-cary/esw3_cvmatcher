# Product charter

CV-Match is an open-source REST API that accepts an already structured CV as
JSON and returns job openings ranked by compatibility. CV parsing is supplied
externally and is out of scope. The product is local-first and must not require
paid LLM, embedding APIs, or paid infrastructure.

The initial source selection prioritizes Brazilian opportunities; this is a
source-selection constraint, not geographic eligibility filtering. See the
[scope](scope.md), [architecture overview](../architecture/overview.md), and
[MVP feature spec](../../specs/feature-001-mvp/spec.md).
