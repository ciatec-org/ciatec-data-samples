#!/usr/bin/env python3
"""
gerar_grapho_v2.py

Gera a Ontology View: grafo conceitual enriquecido com
Classes + ObjectProperties (arestas) + DatatypeProperties tipadas (dentro dos nós).

Uso:
    python gerar_grapho_v2.py
    python gerar_grapho_v2.py ciatec_basquete.ttl

Por padrão só imprime estatísticas. O HTML entra no painel_ontologia via
explorar_ontologia.py. Opcional: --output arquivo.html
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, URIRef
from pyvis.network import Network

ROOT = Path(__file__).resolve().parent

XSD_SHORT = {
    XSD.integer: "integer",
    XSD.int: "integer",
    XSD.long: "integer",
    XSD.float: "float",
    XSD.double: "float",
    XSD.decimal: "decimal",
    XSD.string: "string",
    XSD.boolean: "boolean",
    XSD.date: "date",
    XSD.dateTime: "dateTime",
}

CENTER_FIT_JS = """
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
        setTimeout(centerGraph, 50);
        setTimeout(centerGraph, 300);
        setTimeout(centerGraph, 800);
        clearInterval(timer);
      }
      if (tries > 40) clearInterval(timer);
    }, 50);
  });

  window.addEventListener("message", function (event) {
    if (event.data === "fit" || (event.data && event.data.type === "fit")) {
      centerGraph();
    }
  });
  window.addEventListener("resize", centerGraph);
})();
</script>
"""

FULLSCREEN_CSS = """
<style id="fullscreen-fix">
  html, body { margin: 0 !important; padding: 0 !important; height: 100% !important; width: 100% !important; overflow: hidden !important; }
  body > center, center { display: none !important; }
  .card { width: 100% !important; height: 100% !important; margin: 0 !important; border: 0 !important; box-shadow: none !important; }
  .card-body { padding: 0 !important; height: 100% !important; }
  #mynetwork { width: 100% !important; height: 100vh !important; height: 100dvh !important; border: 0 !important; float: none !important; }
  #loadingBar { width: 100% !important; height: 100vh !important; height: 100dvh !important; }
</style>
"""


def local_name(uri) -> str:
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def datatype_label(graph: Graph, range_node) -> str:
    """Resolve rdfs:range to a short type name (integer, float, string…)."""
    if isinstance(range_node, URIRef):
        if range_node in XSD_SHORT:
            return XSD_SHORT[range_node]
        return local_name(range_node)

    if isinstance(range_node, BNode):
        on_type = graph.value(range_node, OWL.onDatatype)
        if on_type is not None:
            return datatype_label(graph, on_type)

    return "literal"


def class_panel_label(name: str, attrs: list[tuple[str, str]]) -> str:
    """
    Label multilinha estilo painel:
      ClassName
      ─────────
      prop : type
    """
    if not attrs:
        return name

    width = max(len(name), *(len(f"{p} : {t}") for p, t in attrs))
    rule = "─" * max(width, 12)
    lines = [name, rule]
    for prop, dtype in attrs:
        lines.append(f"{prop} : {dtype}")
    return "\n".join(lines)


def _finalize_html(html: str) -> str:
    if 'id="fullscreen-fix"' not in html:
        html = (
            html.replace("</head>", FULLSCREEN_CSS + "\n</head>", 1)
            if "</head>" in html
            else FULLSCREEN_CSS + html
        )
    if 'id="center-fit"' not in html:
        html = (
            html.replace("</body>", CENTER_FIT_JS + "\n</body>", 1)
            if "</body>" in html
            else html + CENTER_FIT_JS
        )
    html = html.replace("height: 850px;", "height: 100vh;")
    html = html.replace("height: 900px;", "height: 100vh;")
    return html


def build_ontology_html(ttl_path: Path | None = None) -> tuple[str, dict]:
    """Monta o HTML da Ontology View e devolve (html, stats)."""
    ttl_path = Path(ttl_path) if ttl_path else ROOT / "ciatec_basquete.ttl"
    if not ttl_path.is_absolute():
        ttl_path = (ROOT / ttl_path).resolve()

    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    classes = {
        c for c in graph.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)
    }

    object_properties = {
        p
        for p in graph.subjects(RDF.type, OWL.ObjectProperty)
        if isinstance(p, URIRef)
    }

    datatype_properties = {
        p
        for p in graph.subjects(RDF.type, OWL.DatatypeProperty)
        if isinstance(p, URIRef)
    }

    datatype_by_class: dict = {cls: [] for cls in classes}
    for prop in datatype_properties:
        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))
        dtype = datatype_label(graph, ranges[0]) if ranges else "literal"
        prop_name = local_name(prop)
        for domain in domains:
            if domain in classes:
                datatype_by_class[domain].append((prop_name, dtype))

    for cls in classes:
        datatype_by_class[cls].sort(key=lambda x: x[0].lower())

    net = Network(
        height="100%",
        width="100%",
        directed=True,
        bgcolor="#f7f9fb",
        font_color="#1c2430",
    )

    net.set_options(
        """
    {
      "layout": {
        "improvedLayout": true,
        "randomSeed": 42
      },
      "physics": {
        "enabled": true,
        "stabilization": {
          "enabled": true,
          "iterations": 450,
          "fit": true
        },
        "barnesHut": {
          "gravitationalConstant": -16000,
          "centralGravity": 0.4,
          "springLength": 220,
          "springConstant": 0.04,
          "damping": 0.9,
          "avoidOverlap": 0.8
        }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true,
        "dragNodes": true,
        "zoomView": true
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.7
          }
        },
        "font": {
          "size": 12,
          "strokeWidth": 4,
          "align": "middle",
          "color": "#334155"
        },
        "smooth": {
          "type": "dynamic"
        },
        "color": {
          "color": "#64748b",
          "highlight": "#1f4e79"
        }
      },
      "nodes": {
        "font": {
          "size": 13,
          "face": "Consolas, Monaco, monospace",
          "align": "left",
          "multi": false
        },
        "margin": 12,
        "borderWidth": 1.5,
        "shapeProperties": {
          "borderRadius": 6
        }
      }
    }
    """
    )

    for cls in classes:
        name = local_name(cls)
        attrs = datatype_by_class.get(cls, [])
        label = class_panel_label(name, attrs)

        if attrs:
            title = (
                f"<b>{name}</b><br><br><b>Datatype properties</b><br>"
                + "<br>".join(f"{p} : {t}" for p, t in attrs)
            )
            color = {
                "background": "#e8f0f7",
                "border": "#1f4e79",
                "highlight": {"background": "#d5e6f4", "border": "#163a5c"},
            }
        else:
            title = f"<b>{name}</b><br><i>sem DatatypeProperty</i>"
            color = {
                "background": "#f1f5f9",
                "border": "#64748b",
                "highlight": {"background": "#e2e8f0", "border": "#475569"},
            }

        net.add_node(
            str(cls),
            label=label,
            shape="box",
            title=title,
            color=color,
            font={
                "face": "Consolas, Monaco, monospace",
                "size": 13,
                "align": "left",
                "color": "#1c2430",
            },
            margin=14,
        )

    for child, parent in graph.subject_objects(RDFS.subClassOf):
        if child in classes and parent in classes:
            net.add_edge(
                str(child),
                str(parent),
                label="subClassOf",
                arrows="to",
                dashes=True,
                color={"color": "#94a3b8"},
                font={"color": "#64748b", "size": 11, "strokeWidth": 3},
            )

    for prop in object_properties:
        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))

        for domain in domains:
            for range_ in ranges:
                if domain in classes and range_ in classes:
                    net.add_edge(
                        str(domain),
                        str(range_),
                        label=local_name(prop),
                        arrows="to",
                        color={"color": "#1f4e79"},
                        font={"color": "#1f4e79", "size": 12, "strokeWidth": 4},
                        width=1.6,
                    )

    with tempfile.TemporaryDirectory(prefix="ciatec_onto_") as tmp:
        out = Path(tmp) / "ontology_view.html"
        net.write_html(str(out), open_browser=False)
        html = _finalize_html(out.read_text(encoding="utf-8"))

    n_attrs = sum(len(v) for v in datatype_by_class.values())
    stats = {
        "classes": len(classes),
        "object_properties": len(object_properties),
        "datatype_properties": len(datatype_properties),
        "attrs": n_attrs,
        "ttl": str(ttl_path),
    }
    return html, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ontology View (conceitual).")
    parser.add_argument(
        "ttl",
        nargs="?",
        default="ciatec_basquete.ttl",
        help="TTL de entrada (padrão: ciatec_basquete.ttl).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Opcional: grava HTML avulso (uso normal: só painel_ontologia).",
    )
    args = parser.parse_args()

    html, stats = build_ontology_html(args.ttl)
    print()
    print(f"TTL: {stats['ttl']}")
    print(f"Classes: {stats['classes']}")
    print(f"ObjectProperties: {stats['object_properties']}")
    print(
        f"DatatypeProperties: {stats['datatype_properties']} "
        f"({stats['attrs']} atributos nos painéis)"
    )
    if args.output is not None:
        args.output.write_text(html, encoding="utf-8")
        print(f"HTML: {args.output}")
    else:
        print("HTML da Ontology View: use explorar_ontologia.py (painel único).")


if __name__ == "__main__":
    main()
