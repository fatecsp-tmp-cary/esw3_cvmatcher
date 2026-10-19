#!/usr/bin/env python3
"""
md_to_block_diagram.py
=======================

Converte uma estrutura hierárquica em Markdown (níveis = seções "#", "##",
"###", ... / folhas = itens de lista "- ") em um diagrama mermaid do tipo
`block`, seguindo o estilo visual do exemplo fornecido:

  * Folhas do mesmo pai são organizadas VERTICALMENTE, em uma coluna
    reservada de largura fixa (2 colunas: uma âncora invisível + o rótulo
    da folha), usando o truque do "barramento vertical": uma âncora "hop"
    logo abaixo do pai se conecta por uma única aresta até a âncora da
    ÚLTIMA folha da lista; cada âncora intermediária (mesma coluna, uma por
    linha) se conecta horizontalmente ao rótulo da folha correspondente.
    Como as âncoras intermediárias são invisíveis e estão exatamente na
    mesma coluna, a aresta longa "salta" por cima delas e dá a ilusão de um
    barramento contínuo com ramificações em cada folha.

  * Nós internos com mais de um filho (sejam eles sub-nós ou grupos de
    folhas, em qualquer combinação/ordem) usam um "pente" horizontal: uma
    linha de âncoras invisíveis (uma por filho, ocupando a mesma largura do
    filho), o pai se conecta a uma âncora central e as âncoras das pontas
    (esquerda/direita) se conectam entre si formando a barra horizontal.

  * Nós com um único filho conectam-se diretamente a ele (sem barramento),
    o que evita linhas vazias em cadeias longas e desbalanceadas
    (ex.: 3 -> 3.1 -> 3.1.1 -> 3.1.1.1 -> ...).

  * A árvore NÃO precisa ser balanceada: um mesmo nó pode ter, ao mesmo
    tempo, filhos que são sub-seções (headers) e filhos que são itens de
    lista (folhas), em qualquer ordem; grupos de folhas interrompidos por
    um header viram grupos verticais separados.

  * Nenhuma folha é conectada a um nível que não seja o do seu pai direto.

Nota de projeto
----------------
O exemplo original (balanceado, 3x3x4) usa espaçamentos ajustados à mão que,
ao serem examinados com cuidado, não formam uma fórmula perfeitamente
consistente para árvores arbitrárias (ex.: o "gap" entre âncoras do nível 1
não corresponde exatamente à largura somada dos filhos do nível 2). Este
script adota uma convenção PRÓPRIA, simples e consistente, que preserva
todas as regras estruturais e visuais pedidas (barramento vertical para
folhas, pente horizontal para nós internos, centralização dos rótulos,
nenhuma aresta cruzando níveis), mas calcula a largura de cada sub-árvore
de forma determinística (bottom-up), com 1 coluna de espaçamento entre
irmãos. Isso garante que o diagrama gerado seja válido e coerente para
QUALQUER árvore, balanceada ou não.

Uso
---
    python md_to_block_diagram.py entrada.md -o saida.mmd
    python md_to_block_diagram.py entrada.md            # imprime no stdout
    cat entrada.md | python md_to_block_diagram.py       # lê do stdin
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 1. Modelo de dados / parsing do markdown
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """Um nó interno (criado por um header markdown)."""

    label: str
    level: int
    # filhos, na ordem em que apareceram no arquivo. Cada item é:
    #   ('node', Node)               -> um sub-nó (header)
    #   ('leafgroup', List[str])     -> um grupo contíguo de itens de lista
    children: list[tuple[str, Node | list[str]]] = field(default_factory=list)


HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*\S)\s*$")


def parse_markdown(text: str) -> Node:
    """Converte o texto markdown em uma árvore de Node.

    Regra: o nível de um nó é definido pelo número de '#'. Um item de lista
    ('- item') sempre vira folha do header mais profundo aberto no momento
    (o topo da pilha), independentemente da indentação do próprio item.
    Itens de lista consecutivos (sem um novo header entre eles) formam um
    único grupo de folhas; se um header aparecer no meio, um NOVO grupo de
    folhas é iniciado quando novos itens de lista voltarem a aparecer sob o
    mesmo pai.
    """
    stack: list[Node] = []
    top_level_nodes: list[Node] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        m = HEADER_RE.match(line)
        if m:
            level = len(m.group(1))
            label = m.group(2).strip()
            node = Node(label=label, level=level)
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(("node", node))
            else:
                top_level_nodes.append(node)
            stack.append(node)
            continue

        m2 = LIST_ITEM_RE.match(line)
        if m2:
            label = m2.group(1).strip()
            if not stack:
                raise ValueError(f"Item de lista encontrado antes de qualquer header: {line!r}")
            parent = stack[-1]
            if parent.children and parent.children[-1][0] == "leafgroup":
                parent.children[-1][1].append(label)
            else:
                parent.children.append(("leafgroup", [label]))
            continue

        # linha ignorada (texto solto, comentários, etc.)

    if not top_level_nodes:
        raise ValueError("Nenhum header encontrado no markdown de entrada.")
    if len(top_level_nodes) == 1:
        return top_level_nodes[0]

    # Mais de um header de nível mínimo: cria uma raiz sintética para
    # manter o diagrama com uma única raiz.
    synthetic_root = Node(label="", level=0)
    synthetic_root.children = [("node", n) for n in top_level_nodes]
    return synthetic_root


# ---------------------------------------------------------------------------
# 2. Construção do diagrama (layout + geração de ids/arestas)
# ---------------------------------------------------------------------------

Cell = tuple[int, tuple[str, str] | None]  # (span, (id, label) | None)
RowMap = dict[int, list[Cell]]

GAP = 1  # colunas de espaçamento entre irmãos
LEAF_GROUP_WIDTH = 2  # âncora + rótulo


class DiagramBuilder:
    def __init__(self) -> None:
        self._counter = 0
        self.edges: list[tuple[str, str]] = []
        self.invisible_ids: list[str] = []

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"


def _merge_rows_side_by_side(
    slots_rows: list[RowMap], slots_widths: list[int], start_row: int
) -> RowMap:
    """Combina as linhas de vários filhos lado a lado (com GAP entre eles),
    alinhando por índice relativo de linha, preenchendo com espaço em branco
    onde um filho não tiver conteúdo naquela linha."""
    if not slots_rows:
        return {}
    max_rel = max((max(r.keys()) + 1 if r else 0) for r in slots_rows)
    merged: RowMap = {}
    for rel in range(max_rel):
        cells: list[Cell] = []
        for i, (rows, width) in enumerate(zip(slots_rows, slots_widths, strict=True)):
            if rel in rows:
                cells.extend(rows[rel])
            else:
                cells.append((width, None))
            if i < len(slots_rows) - 1:
                cells.append((GAP, None))
        merged[start_row + rel] = cells
    return merged


def render_leafgroup(labels: list[str], b: DiagramBuilder) -> tuple[int, RowMap, str, int]:
    """Renderiza um grupo de folhas de um mesmo pai como uma pilha vertical.

    Layout (largura fixa = 2 colunas, coluna-conectora = coluna 0):
        linha 0:  [hop âncora invisível] [espaço]      <- ponto de conexão com o pai
        linha 1:  [âncora folha 1]      [rótulo folha 1]
        linha 2:  [âncora folha 2]      [rótulo folha 2]
        ...

    Uma única aresta liga o hop diretamente à âncora da ÚLTIMA folha,
    formando o "barramento vertical" que passa visualmente por cima das
    âncoras intermediárias (invisíveis, mesma coluna). O hop e todas as
    âncoras de folha ficam sempre na coluna 0 (a primeira das 2), o que é
    a própria coluna-conectora reportada ao pai.
    """
    width = LEAF_GROUP_WIDTH
    rows: RowMap = {}
    anchor_ids: list[str] = []

    for i, label in enumerate(labels):
        aid = b.new_id("a")
        lid = b.new_id("l")
        b.invisible_ids.append(aid)
        rows[i + 1] = [(1, (aid, " ")), (1, (lid, label))]
        anchor_ids.append(aid)
        b.edges.append((aid, lid))

    hop_id = b.new_id("a")
    b.invisible_ids.append(hop_id)
    rows[0] = [(1, (hop_id, " ")), (1, None)]
    if anchor_ids:
        b.edges.append((hop_id, anchor_ids[-1]))

    connector_col = 0
    return width, rows, hop_id, connector_col


def render_node(node: Node, b: DiagramBuilder) -> tuple[int, RowMap, str, int]:
    """Renderiza um nó interno (e recursivamente seus filhos).

    Retorna (largura_total, linhas, id_do_nó, coluna_conectora):
      * `id_do_nó` é o id que o PAI deste nó deve usar para se conectar
        a ele (a aresta parte desse id);
      * `coluna_conectora` é a coluna (0-indexada, relativa à largura
        retornada) em que esse id efetivamente fica posicionado. É o
        contrato que garante alinhamento vertical exato: quem for
        desenhar uma âncora logo acima ou abaixo deste nó DEVE colocá-la
        nessa mesma coluna, nunca numa coluna "aproximada"/centralizada
        por conta própria.
    """
    own_id = b.new_id("n")

    # --- caso base: nó sem nenhum filho (nem sub-nó, nem folha) ---
    if not node.children:
        rows: RowMap = {0: [(1, (own_id, node.label))]}
        return 1, rows, own_id, 0

    # renderiza cada filho (sub-nó ou grupo de folhas), na ordem original
    slots: list[tuple[int, RowMap, str, int]] = []
    for kind, payload in node.children:
        if kind == "node":
            slots.append(render_node(payload, b))  # type: ignore[arg-type]
        else:
            slots.append(render_leafgroup(payload, b))  # type: ignore[arg-type]

    widths = [w for w, _, _, _ in slots]
    conn_ids = [cid for _, _, cid, _ in slots]
    conn_cols = [cc for _, _, _, cc in slots]  # coluna-conectora de cada filho,
    # DENTRO da sua própria largura

    # --- caso 1 filho: conecta direto, sem linha de barramento.
    # own_id fica posicionado EXATAMENTE na mesma coluna que a coluna-
    # conectora do filho, garantindo uma aresta vertical (sem diagonal),
    # e repassa essa mesma coluna adiante como a sua própria.
    if len(slots) == 1:
        width, child_rows, child_id, child_conn_col = slots[0]
        left, right = child_conn_col, width - 1 - child_conn_col
        row0: list[Cell] = []
        if left:
            row0.append((left, None))
        row0.append((1, (own_id, node.label)))
        if right:
            row0.append((right, None))

        rows = {0: row0}
        for rel, cells in child_rows.items():
            rows[1 + rel] = cells

        b.edges.append((own_id, child_id))
        return width, rows, own_id, child_conn_col

    # --- caso >1 filhos: barramento horizontal (pente) ---
    # Cada filho ocupa uma região de `widths[i]` colunas. Dentro dessa
    # região, a âncora-do-filho é colocada em UMA ÚNICA coluna: exatamente
    # a coluna-conectora que o próprio filho reportou (`conn_cols[i]`).
    # Isso garante, por construção, que a aresta âncora->filho seja
    # sempre vertical (mesma coluna acima e abaixo).
    total_width = sum(widths) + GAP * (len(widths) - 1)

    anchor_ids: list[str] = []
    row1: list[Cell] = []
    for i, (w, cc) in enumerate(zip(widths, conn_cols, strict=True)):
        aid = b.new_id("a")
        b.invisible_ids.append(aid)
        anchor_ids.append(aid)

        pad_before, pad_after = cc, w - 1 - cc
        if pad_before:
            row1.append((pad_before, None))
        row1.append((1, (aid, " ")))
        if pad_after:
            row1.append((pad_after, None))
        if i < len(widths) - 1:
            row1.append((GAP, None))

    # O nó pai deve ficar centralizado na coluna aritmética exata de
    # `total_width` (não em uma âncora de filho escolhida "à sorte"),
    # priorizando centralização/equidistância. Se essa coluna central
    # coincidir com a âncora de algum filho (caso simétrico), reaproveita
    # essa âncora como hub. Caso contrário (splits desbalanceados), cria
    # uma âncora dedicada — sem aresta própria para as pontas do
    # barramento — que fica ali só para dar ao pai uma descida vertical
    # reta; a barra horizontal continua sendo desenhada pela aresta entre
    # as âncoras das pontas, que passa visualmente por essa coluna.
    hub_col = (total_width - 1) // 2
    hub_id: str | None = None
    col = 0
    for idx, (span, content) in enumerate(row1):
        if col <= hub_col < col + span:
            if content is not None:
                hub_id = content[0]  # coincide com a âncora de um filho: reaproveita
            else:
                before = hub_col - col
                after = span - before - 1
                hub_id = b.new_id("a")
                b.invisible_ids.append(hub_id)
                replacement: list[Cell] = []
                if before:
                    replacement.append((before, None))
                replacement.append((1, (hub_id, " ")))
                if after:
                    replacement.append((after, None))
                row1[idx : idx + 1] = replacement
            break
        col += span

    assert hub_id is not None
    b.edges.append((own_id, hub_id))
    # aresta ligando as âncoras das pontas (forma a barra horizontal)
    b.edges.append((anchor_ids[0], anchor_ids[-1]))
    # cada âncora-de-filho desce até o filho correspondente (mesma coluna)
    for aid, cid in zip(anchor_ids, conn_ids, strict=True):
        b.edges.append((aid, cid))

    # linha 0: rótulo do próprio nó, centralizado na mesma coluna do hub.
    left, right = hub_col, total_width - 1 - hub_col
    row0: list[Cell] = []
    if left:
        row0.append((left, None))
    row0.append((1, (own_id, node.label)))
    if right:
        row0.append((right, None))

    rows = {0: row0, 1: row1}
    child_rows_list = [r for _, r, _, _ in slots]
    rows.update(_merge_rows_side_by_side(child_rows_list, widths, start_row=2))

    return total_width, rows, own_id, hub_col


# ---------------------------------------------------------------------------
# 3. Geração do texto mermaid
# ---------------------------------------------------------------------------


def _escape(label: str) -> str:
    return label.replace('"', "#quot;")


def _cell_to_str(span: int, content: tuple[str, str] | None) -> str:
    if content is None:
        return f"space:{span}" if span > 1 else "space"
    node_id, label = content
    box = f'{node_id}["{_escape(label)}"]'
    if span > 1:
        box += f":{span}"
    return box


def _merge_adjacent_spaces(cells: list[Cell]) -> list[Cell]:
    """Combina células de espaço consecutivas (ex.: dois `space` seguidos,
    um vindo do padding final de um grupo e outro do gap entre irmãos) em
    uma única célula `space:N`, apenas para deixar a saída mais limpa."""
    merged: list[Cell] = []
    for span, content in cells:
        if content is None and merged and merged[-1][1] is None:
            prev_span, _ = merged[-1]
            merged[-1] = (prev_span + span, None)
        else:
            merged.append((span, content))
    return merged


def validate_rows(rows: RowMap, columns: int) -> None:
    for row_idx, cells in rows.items():
        total = sum(span for span, _ in cells)
        if total != columns:
            raise AssertionError(
                f"Linha {row_idx}: soma dos spans ({total}) != columns ({columns})"
            )


def generate_mermaid(root: Node) -> str:
    b = DiagramBuilder()
    columns, rows, _root_id, _root_conn_col = render_node(root, b)
    validate_rows(rows, columns)

    lines: list[str] = ["block", f"    columns {columns}", ""]

    for row_idx in sorted(rows.keys()):
        cells = _merge_adjacent_spaces(rows[row_idx])
        line = "    " + " ".join(_cell_to_str(span, content) for span, content in cells)
        lines.append(line)

    lines.append("")
    for a, c in b.edges:
        lines.append(f"    {a} --- {c}")

    if b.invisible_ids:
        lines.append("")
        lines.append("    classDef invisible fill:none,stroke:none,width:0")
        lines.append("    class " + ",".join(b.invisible_ids) + " invisible")

    return "\n".join(lines) + "\n"


def markdown_to_block_diagram(markdown_text: str) -> str:
    root = parse_markdown(markdown_text)
    return generate_mermaid(root)


# ---------------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Converte uma estrutura hierárquica em Markdown para um "
        "diagrama mermaid do tipo 'block'."
    )
    parser.add_argument(
        "input", nargs="?", default=None, help="Arquivo markdown de entrada (padrão: stdin)"
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Arquivo de saída .mmd (padrão: stdout)"
    )
    args = parser.parse_args(argv)

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    output = markdown_to_block_diagram(text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
