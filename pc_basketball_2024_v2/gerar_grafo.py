"""
Popula a ontologia ciatec_basquete.ttl com dados das planilhas
users.xlsx, matches.xlsx e balls.xlsx, e gera um grafo HTML.

Uso:
  python gerar_grafo.py
  python gerar_grafo.py --user-id 2 --max-matches 3 --max-shots 20
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
from rdflib.term import Node

ROOT = Path(__file__).resolve().parent
ONTOLOGY_TTL = ROOT / "ciatec_basquete.ttl"
DATA_DIR = ROOT / "data"
USERS_XLSX = DATA_DIR / "users.xlsx"
MATCHES_XLSX = DATA_DIR / "matches.xlsx"
BALLS_XLSX = DATA_DIR / "balls.xlsx"
OUTPUT_TTL = ROOT / "ciatec_basquete_populada.ttl"

CIATEC = Namespace("http://www.ciatec.org/ontology/basketball#")

POSITION = {1: CIATEC.Left, 2: CIATEC.Centre, 3: CIATEC.Right}
GMFCS = {1: CIATEC.GMFCS_I, 2: CIATEC.GMFCS_II, 3: CIATEC.GMFCS_III, 4: CIATEC.GMFCS_IV, 5: CIATEC.GMFCS_V}
MACS = {1: CIATEC.MACS_I, 2: CIATEC.MACS_II, 3: CIATEC.MACS_III, 4: CIATEC.MACS_IV, 5: CIATEC.MACS_V}


def _roman(n: int) -> str:
    return {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}[n]


def _safe_int(value) -> int | None:
    if pd.isna(value):
        return None
    return int(value)


def _safe_float(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _ensure_levels(g: Graph) -> None:
    """Garante instâncias GMFCS/MACS I–V (o TTL de exemplo só traz o nível I)."""
    for n in range(1, 6):
        gmfcs = GMFCS[n]
        macs = MACS[n]
        if (gmfcs, RDF.type, None) not in g:
            g.add((gmfcs, RDF.type, CIATEC.GMFCSLevel))
            g.add((gmfcs, RDFS.label, Literal(f"GMFCS Level {_roman(n)}")))
        if (macs, RDF.type, None) not in g:
            g.add((macs, RDF.type, CIATEC.MACSLevel))
            g.add((macs, RDFS.label, Literal(f"MACS Level {_roman(n)}")))

    for uri, label in (
        (CIATEC.CerebralPalsyGroup, "Cerebral Palsy Group"),
        (CIATEC.ControlGroup, "Control Group"),
    ):
        if (uri, RDF.type, None) not in g:
            g.add((uri, RDF.type, CIATEC.ParticipantGroup))
            g.add((uri, RDFS.label, Literal(label)))


def add_users(g: Graph, users: pd.DataFrame) -> None:
    for row in users.itertuples(index=False):
        uid = int(row.id_user)
        participant = CIATEC[f"Participant_{uid:03d}"]
        g.add((participant, RDF.type, CIATEC.Participant))

        age = _safe_int(row.age)
        if age is not None:
            g.add((participant, CIATEC.hasAge, Literal(age, datatype=XSD.integer)))

        sex = str(row.sex).strip().lower() if not pd.isna(row.sex) else None
        if sex in {"male", "female"}:
            g.add((participant, CIATEC.hasSex, Literal(sex)))

        group = str(row.group).strip().lower() if not pd.isna(row.group) else None
        if group == "cp":
            g.add((participant, CIATEC.belongsToGroup, CIATEC.CerebralPalsyGroup))
            condition = CIATEC[f"CP_{uid:03d}"]
            g.add((condition, RDF.type, CIATEC.CerebralPalsy))
            g.add((participant, CIATEC.hasHealthCondition, condition))

            gmfcs = _safe_int(row.gmfcs)
            if gmfcs in GMFCS:
                g.add((condition, CIATEC.hasGMFCS, GMFCS[gmfcs]))

            macs = _safe_int(row.macs)
            if macs in MACS:
                g.add((condition, CIATEC.hasMACS, MACS[macs]))
        elif group == "control":
            g.add((participant, CIATEC.belongsToGroup, CIATEC.ControlGroup))


def add_matches(g: Graph, matches: pd.DataFrame) -> set[tuple[int, int]]:
    """Adiciona partidas/sessões. Retorna pares (id_user, day) criados."""
    sessions: set[tuple[int, int]] = set()

    for row in matches.itertuples(index=False):
        uid = int(row.id_user)
        mid = int(row.id_match)
        day = _safe_int(row.day)
        participant = CIATEC[f"Participant_{uid:03d}"]
        match = CIATEC[f"Match_{mid:03d}"]

        g.add((match, RDF.type, CIATEC.Match))
        g.add((match, CIATEC.hasParticipant, participant))

        speed = _safe_int(row.speed)
        if speed is not None:
            g.add((match, CIATEC.hasSpeed, Literal(speed, datatype=XSD.integer)))

        hit_rate = _safe_float(row.hit_rate)
        if hit_rate is not None:
            g.add((match, CIATEC.hasHitRate, Literal(hit_rate, datatype=XSD.float)))

        n_shots = _safe_int(row.n_shots)
        if n_shots is not None:
            g.add((match, CIATEC.hasNShots, Literal(n_shots, datatype=XSD.integer)))

        total_time = _safe_float(row.total_time)
        if total_time is not None:
            g.add((match, CIATEC.hasTotalTime, Literal(total_time, datatype=XSD.float)))

        if day is not None:
            session = CIATEC[f"Session_{uid:03d}_D{day}"]
            if (uid, day) not in sessions:
                g.add((session, RDF.type, CIATEC.GameSession))
                g.add((session, CIATEC.hasDay, Literal(day, datatype=XSD.integer)))
                g.add((participant, CIATEC.participatesIn, session))
                sessions.add((uid, day))
            g.add((session, CIATEC.containsMatch, match))

    return sessions


def _ball_groups(balls: pd.DataFrame) -> pd.DataFrame:
    """Agrupa arremessos em partidas: cada is_first_shot=1 inicia um bloco."""
    ordered = balls.sort_values("id_ball").reset_index(drop=True)
    starts = ordered.index[ordered["is_first_shot"] == 1].tolist()
    groups = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(ordered)
        block = ordered.iloc[start:end]
        groups.append(
            {
                "g_idx": i,
                "n_shots": len(block),
                "n_hits": int(block["is_hit"].sum()),
                "total_time": int(block["total_time"].iloc[0]),
                "tb1": round(float(block["time_between"].iloc[0]), 2),
                "tb_mean": round(float(block["time_between"].mean()), 4),
                "tb_median": round(float(block["time_between"].median()), 4),
                "same_mean": round(float(block["is_same_position"].mean()), 4),
                "id_balls": tuple(int(x) for x in block["id_ball"]),
            }
        )
    return pd.DataFrame(groups)


def link_balls_to_matches(balls: pd.DataFrame, matches: pd.DataFrame) -> dict[int, int]:
    """
    balls.xlsx não traz id_match. Reconstrói o join:
    790 blocos (is_first_shot) ↔ 790 partidas, por fingerprint das estatísticas.
    Retorna {id_ball: id_match}.
    """
    gdf = _ball_groups(balls)
    m = matches.copy()
    m["tb1"] = m["time_between_1st_shot"].round(2)
    m["tb_mean"] = m["time_between_mean"].round(4)
    m["tb_median"] = m["time_between_median"].round(4)
    m["same_mean"] = m["same_position_mean"].round(4)

    remaining_g = gdf.copy()
    remaining_m = m.copy()
    group_to_match: dict[int, int] = {}

    def claim(keys: list[str]) -> None:
        nonlocal remaining_g, remaining_m
        if remaining_g.empty:
            return
        merged = remaining_g.merge(
            remaining_m[["id_match"] + keys],
            on=keys,
            how="inner",
        )
        gc = merged.groupby("g_idx").size()
        mc = merged.groupby("id_match").size()
        uniq = merged[(merged.g_idx.map(gc) == 1) & (merged.id_match.map(mc) == 1)]
        for row in uniq.itertuples(index=False):
            group_to_match[int(row.g_idx)] = int(row.id_match)
        remaining_g = remaining_g[~remaining_g["g_idx"].isin(uniq["g_idx"])].copy()
        remaining_m = remaining_m[~remaining_m["id_match"].isin(uniq["id_match"])].copy()

    for keys in (
        ["n_shots", "n_hits", "total_time", "tb1", "tb_mean", "same_mean"],
        ["n_shots", "n_hits", "total_time", "tb1", "tb_median"],
        ["n_shots", "n_hits", "total_time", "tb1"],
        # Alguns blocos do Excel têm metade dos arremessos; tb_mean/same_mean ainda casam.
        ["tb_mean", "same_mean"],
    ):
        claim(list(keys))

    ball_to_match: dict[int, int] = {}
    for row in gdf.itertuples(index=False):
        mid = group_to_match.get(int(row.g_idx))
        if mid is None:
            continue
        for bid in row.id_balls:
            ball_to_match[int(bid)] = mid

    return ball_to_match


def add_shots(
    g: Graph,
    balls: pd.DataFrame,
    ball_to_match: dict[int, int],
) -> int:
    """Adiciona arremessos e liga cada um à partida via ciatec:containsShot."""
    linked = 0
    for row in balls.itertuples(index=False):
        bid = int(row.id_ball)
        shot = CIATEC[f"Shot_{bid}"]
        outcome = CIATEC[f"Outcome_{bid}"]

        g.add((shot, RDF.type, CIATEC.ShotAttempt))
        g.add((outcome, RDF.type, CIATEC.GameOutcome))
        g.add((shot, CIATEC.hasOutcome, outcome))

        mid = ball_to_match.get(bid)
        if mid is not None:
            g.add((CIATEC[f"Match_{mid:03d}"], CIATEC.containsShot, shot))
            linked += 1

        is_hit = _safe_int(row.is_hit)
        if is_hit is not None:
            g.add((outcome, CIATEC.isHit, Literal(bool(is_hit), datatype=XSD.boolean)))

        cur = _safe_int(row.current_position)
        if cur in POSITION:
            g.add((shot, CIATEC.hasCurrentPosition, POSITION[cur]))

        prev = _safe_int(row.previous_position)
        if prev in POSITION:
            g.add((shot, CIATEC.hasPreviousPosition, POSITION[prev]))

        same = _safe_int(row.is_same_position)
        if same is not None:
            g.add((shot, CIATEC.isSamePosition, Literal(bool(same), datatype=XSD.boolean)))

        time_between = _safe_float(row.time_between)
        if time_between is not None:
            g.add((shot, CIATEC.hasTimeBetween, Literal(time_between, datatype=XSD.float)))

        time_remaining = _safe_float(row.time_remaining)
        if time_remaining is not None:
            g.add((shot, CIATEC.hasTimeRemaining, Literal(time_remaining, datatype=XSD.float)))

    return linked


def _strip_example_abox(g: Graph) -> None:
    """
    Remove instâncias de exemplo do TTL (Participant_002, Match_060, Shot_18848…).
    Mantém o esquema e o vocabulário fixo (posições, grupos, níveis).
    """
    example_prefixes = (
        "Participant_",
        "CP_",
        "Session_",
        "Match_",
        "Shot_",
        "Outcome_",
    )

    def is_example(node) -> bool:
        local = str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        return any(local.startswith(pref) for pref in example_prefixes)

    for s, p, o in list(g):
        if is_example(s) or is_example(o):
            g.remove((s, p, o))


def build_rdf(
    user_id: int | None,
    max_matches: int | None,
    max_shots: int | None,
) -> tuple[Graph, int, int]:
    g = Graph()
    g.parse(ONTOLOGY_TTL, format="turtle")
    g.bind("ciatec", CIATEC)
    _strip_example_abox(g)
    _ensure_levels(g)


    users = pd.read_excel(USERS_XLSX, sheet_name="users")
    matches_all = pd.read_excel(MATCHES_XLSX, sheet_name="matches")
    balls_all = pd.read_excel(BALLS_XLSX, sheet_name="balls")

    # Join completo antes dos filtros, para não perder o fingerprint.
    ball_to_match = link_balls_to_matches(balls_all, matches_all)
    balls_all = balls_all.copy()
    balls_all["id_match"] = balls_all["id_ball"].map(ball_to_match)

    if user_id is not None:
        users = users[users["id_user"] == user_id]
        matches = matches_all[matches_all["id_user"] == user_id]
        if users.empty:
            raise SystemExit(f"Nenhum usuário com id_user={user_id}")
    else:
        matches = matches_all

    if max_matches is not None:
        matches = matches.head(max_matches)

    match_ids = set(matches["id_match"].astype(int))
    balls = balls_all[balls_all["id_match"].isin(match_ids)]
    if max_shots is not None:
        balls = balls.head(max_shots)

    add_users(g, users)
    add_matches(g, matches)
    linked = add_shots(g, balls, ball_to_match)
    return g, linked, len(balls)


def short_label(node: Node) -> str:
    text = str(node)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rsplit("/", 1)[-1]


def graph_to_html(g: Graph, html_path: Path) -> tuple[int, int]:
    """Data Graph: only populated instances (A-box). Schema stays in Ontology View."""
    import networkx as nx
    from pyvis.network import Network
    from rdflib import Literal as RDFLiteral
    from rdflib import OWL

    nxg = nx.MultiDiGraph()
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))

    for s, p, o in g:
        if p in obj_props:
            nxg.add_node(s, label=short_label(s), kind="entity")
            nxg.add_node(o, label=short_label(o), kind="entity")
            nxg.add_edge(s, o, label=short_label(p), kind="object_property")
        elif p in data_props:
            nxg.add_node(s, label=short_label(s), kind="entity")
            lit = str(o) if isinstance(o, RDFLiteral) else short_label(o)
            lit_id = f"{s}|{p}|{lit}"
            nxg.add_node(lit_id, label=lit, kind="datatype")
            nxg.add_edge(s, lit_id, label=short_label(p), kind="datatype_property")

    net = Network(height="100vh", width="100%", directed=True, notebook=False)
    net.set_options(
        """
{
  "layout": {"improvedLayout": true, "randomSeed": 7},
  "physics": {
    "enabled": true,
    "stabilization": {"enabled": true, "iterations": 300, "fit": true},
    "barnesHut": {
      "gravitationalConstant": -8000,
      "centralGravity": 0.45,
      "springLength": 120,
      "springConstant": 0.045,
      "damping": 0.85,
      "avoidOverlap": 0.3
    }
  },
  "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
  "edges": {
    "arrows": {"to": {"enabled": true, "scaleFactor": 0.7}},
    "smooth": {"type": "dynamic"}
  }
}
"""
    )

    colors = {
        "entity": "#2e7d32",
        "datatype": "#f9a825",
    }
    font_colors = {
        "entity": "#ffffff",
        "datatype": "#1c2430",
    }
    for node, attrs in nxg.nodes(data=True):
        kind = attrs.get("kind", "entity")
        net.add_node(
            str(node),
            label=attrs.get("label", short_label(node)),
            title=f"{kind}: {attrs.get('label', short_label(node))}",
            color=colors.get(kind, "#607d8b"),
            font={"color": font_colors.get(kind, "#ffffff")},
            shape="ellipse" if kind == "datatype" else "dot",
            size=16 if kind == "datatype" else 22,
        )

    for u, v, attrs in nxg.edges(data=True):
        net.add_edge(str(u), str(v), label=attrs.get("label", ""), title=attrs.get("label", ""))

    net.write_html(str(html_path), open_browser=False)
    _finalize_graph_html(html_path)
    return nxg.number_of_nodes(), nxg.number_of_edges()


def graph_to_html_string(g: Graph) -> tuple[str, int, int]:
    """Gera o HTML do Data Graph em memória (sem arquivo permanente)."""
    with tempfile.TemporaryDirectory(prefix="ciatec_grafo_") as tmp:
        html_path = Path(tmp) / "data_graph.html"
        n_nodes, n_edges = graph_to_html(g, html_path)
        return html_path.read_text(encoding="utf-8"), n_nodes, n_edges


def _finalize_graph_html(html_path: Path) -> None:
    """Force full viewport height and centre the layout after load."""
    html = html_path.read_text(encoding="utf-8")
    css = """
<style id="fullscreen-fix">
  html, body { margin: 0 !important; padding: 0 !important; height: 100% !important; width: 100% !important; overflow: hidden !important; }
  body > center, center { display: none !important; }
  .card { width: 100% !important; height: 100% !important; margin: 0 !important; border: 0 !important; box-shadow: none !important; }
  .card-body { padding: 0 !important; height: 100% !important; }
  #mynetwork { width: 100% !important; height: 100vh !important; height: 100dvh !important; border: 0 !important; float: none !important; }
  #loadingBar { width: 100% !important; height: 100vh !important; height: 100dvh !important; }
</style>
"""
    js = """
<script id="center-fit">
(function () {
  function centerGraph() {
    if (typeof network === "undefined" || !network) return;
    try {
      network.redraw();
      network.fit({ animation: false, padding: 40 });
    } catch (e) {}
  }
  document.addEventListener("DOMContentLoaded", function () {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (typeof network !== "undefined" && network) {
        network.once("stabilizationIterationsDone", function () {
          centerGraph();
          network.setOptions({ physics: { enabled: false } });
        });
        network.on("stabilized", centerGraph);
        setTimeout(centerGraph, 80);
        setTimeout(centerGraph, 400);
        clearInterval(timer);
      }
      if (tries > 40) clearInterval(timer);
    }, 50);
  });
  window.addEventListener("message", function (event) {
    if (event.data === "fit" || (event.data && event.data.type === "fit")) centerGraph();
  });
  window.addEventListener("resize", centerGraph);
})();
</script>
"""
    if 'id="fullscreen-fix"' not in html:
        html = html.replace("</head>", css + "\n</head>", 1) if "</head>" in html else css + html
    if 'id="center-fit"' not in html:
        html = html.replace("</body>", js + "\n</body>", 1) if "</body>" in html else html + js
    html = html.replace("height: 850px;", "height: 100vh;")
    html = html.replace("height: 900px;", "height: 100vh;")
    html_path.write_text(html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Popula ciatec_basquete.ttl com Excel e gera grafo HTML."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=2,
        help="Filtra um participante (padrão: 2, como no exemplo da ontologia).",
    )
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Usa todos os participantes (pode gerar grafo muito grande).",
    )
    parser.add_argument("--max-matches", type=int, default=5, help="Limite de partidas.")
    parser.add_argument("--max-shots", type=int, default=30, help="Limite de arremessos.")
    parser.add_argument(
        "--full-data",
        action="store_true",
        help="Sem limites de matches/shots (ainda respeita --user-id, salvo --all-users).",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Opcional: grava Data Graph neste caminho (uso normal: só painel_ontologia).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_id = None if args.all_users else args.user_id
    max_matches = None if args.full_data else args.max_matches
    max_shots = None if args.full_data else args.max_shots

    print(f"Carregando ontologia: {ONTOLOGY_TTL.name}")
    print(f"Planilhas: {DATA_DIR}")
    g, linked_shots, n_shots = build_rdf(
        user_id=user_id, max_matches=max_matches, max_shots=max_shots
    )
    g.serialize(destination=OUTPUT_TTL, format="turtle")
    print(f"TTL populado: {OUTPUT_TTL.name} ({len(g)} triplas)")
    print(f"Arremessos ligados a partidas: {linked_shots}/{n_shots}")

    if args.html is not None:
        n_nodes, n_edges = graph_to_html(g, args.html)
        print(f"Grafo HTML: {args.html} ({n_nodes} nós, {n_edges} arestas)")
    else:
        print("HTML do Data Graph: use explorar_ontologia.py (painel único).")


if __name__ == "__main__":
    main()
