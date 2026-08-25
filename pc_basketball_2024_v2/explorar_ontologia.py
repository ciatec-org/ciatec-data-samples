#!/usr/bin/env python3
"""
explorar_ontologia.py

Builds the unified panel (single HTML) with 3 tabs:
  1. Data Graph     → embedded
  2. Ontology View  → embedded
  3. Instance View  → semantic case tree + analytical charts

Usage:
  python explorar_ontologia.py
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
from pathlib import Path

import pandas as pd

from gerar_grafo import (
    BALLS_XLSX,
    MATCHES_XLSX,
    USERS_XLSX,
    build_rdf,
    graph_to_html_string,
    link_balls_to_matches,
)
from gerar_grapho_v2 import build_ontology_html

ROOT = Path(__file__).resolve().parent
OUTPUT_HTML = ROOT / "painel_ontologia.html"
INSTANCE_JSON = ROOT / "instancias_basquete.json"
ONTOLOGY_TTL = ROOT / "ciatec_basquete.ttl"

POS_LABEL = {1: "Left", 2: "Centre", 3: "Right"}
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}


def _num(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and float(value).is_integer():
        return int(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _level_label(prefix: str, value) -> str | None:
    n = _num(value)
    if n not in ROMAN:
        return None
    return f"{prefix}_{ROMAN[n]}"


def build_instance_data() -> dict:
    users = pd.read_excel(USERS_XLSX, sheet_name="users")
    matches = pd.read_excel(MATCHES_XLSX, sheet_name="matches")
    balls = pd.read_excel(BALLS_XLSX, sheet_name="balls")

    ball_to_match = link_balls_to_matches(balls, matches)
    balls = balls.copy()
    balls["id_match"] = balls["id_ball"].map(ball_to_match)

    shots_by_match: dict[int, list] = {}
    for row in balls.itertuples(index=False):
        mid = row.id_match
        if pd.isna(mid):
            continue
        mid = int(mid)
        shots_by_match.setdefault(mid, []).append(
            {
                "id": f"Shot_{int(row.id_ball)}",
                "current_position": POS_LABEL.get(_num(row.current_position)),
                "previous_position": POS_LABEL.get(_num(row.previous_position)),
                "is_same_position": bool(_num(row.is_same_position))
                if _num(row.is_same_position) is not None
                else None,
                "time_between": _num(row.time_between),
                "time_remaining": _num(row.time_remaining),
                "is_hit": bool(_num(row.is_hit)) if _num(row.is_hit) is not None else None,
                "outcome_id": f"Outcome_{int(row.id_ball)}",
            }
        )

    matches_by_user: dict[int, list] = {}
    for row in matches.itertuples(index=False):
        uid = int(row.id_user)
        mid = int(row.id_match)
        day = _num(row.day)
        matches_by_user.setdefault(uid, []).append(
            {
                "id": f"Match_{mid:03d}",
                "id_match": mid,
                "day": day,
                "speed": _num(row.speed),
                "hit_rate": _num(row.hit_rate),
                "n_shots": _num(row.n_shots),
                "total_time": _num(row.total_time),
                "shots": shots_by_match.get(mid, []),
            }
        )

    participants = []
    for row in users.sort_values("id_user").itertuples(index=False):
        uid = int(row.id_user)
        group = str(row.group).strip().lower() if not pd.isna(row.group) else None
        health = None
        if group == "cp":
            health = {
                "type": "CerebralPalsy",
                "gmfcs": _level_label("GMFCS", row.gmfcs),
                "macs": _level_label("MACS", row.macs),
            }

        user_matches = sorted(
            matches_by_user.get(uid, []),
            key=lambda m: (m["day"] is None, m["day"], m["id_match"]),
        )
        sessions: dict[int, dict] = {}
        for match in user_matches:
            day = match["day"] if match["day"] is not None else 0
            if day not in sessions:
                sessions[day] = {
                    "id": f"Session_{uid:03d}_D{day}",
                    "day": day,
                    "matches": [],
                }
            sessions[day]["matches"].append(match)

        participants.append(
            {
                "id": f"Participant_{uid:03d}",
                "id_user": uid,
                "age": _num(row.age),
                "sex": str(row.sex).strip().lower() if not pd.isna(row.sex) else None,
                "group": "CerebralPalsyGroup"
                if group == "cp"
                else ("ControlGroup" if group == "control" else None),
                "health": health,
                "sessions": [sessions[k] for k in sorted(sessions)],
            }
        )

    return {"participants": participants}


def build_embedded_graphs() -> tuple[str, str]:
    """Gera Data Graph e Ontology View em memória (sem HTML avulso)."""
    print("Generating Data Graph ...")
    g, linked, n_shots = build_rdf(user_id=2, max_matches=5, max_shots=40)
    data_html, n_nodes, n_edges = graph_to_html_string(g)
    print(f"  nodes={n_nodes} edges={n_edges} linked_shots={linked}/{n_shots}")

    print("Generating Ontology View ...")
    onto_html, stats = build_ontology_html(ONTOLOGY_TTL)
    print(
        f"  classes={stats['classes']} "
        f"objectProps={stats['object_properties']} "
        f"dataProps={stats['datatype_properties']}"
    )
    return data_html, onto_html


def _iframe_srcdoc(graph_html: str, title: str) -> str:
    escaped = html_lib.escape(graph_html, quote=True)
    return f'<iframe srcdoc="{escaped}" title="{title}"></iframe>'


def render_panel(data: dict, data_graph_html: str, ontology_html: str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    panel = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CIATec Basketball Ontology — Panel</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --panel: #ffffff;
      --ink: #1c2430;
      --muted: #5b6775;
      --line: #d7dde5;
      --accent: #1f4e79;
      --accent-soft: #e8f0f7;
      --ok: #1b7f4a;
      --miss: #a33b3b;
      --chip: #eef2f6;
      --court: #f3e6c8;
      --court-line: #c4a574;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      height: 100%;
      overflow: hidden;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    .app {{
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100%;
      height: 100dvh;
    }}
    header {{
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 8px 16px 0;
    }}
    header h1 {{
      margin: 0;
      font-size: 1rem;
      font-weight: 650;
      display: inline;
    }}
    header p {{
      display: inline;
      margin: 0 0 0 10px;
      color: var(--muted);
      font-size: 0.8rem;
    }}
    .tabs {{ display: flex; gap: 4px; margin-top: 8px; }}
    .tab {{
      border: 1px solid transparent;
      border-bottom: none;
      background: transparent;
      color: var(--muted);
      padding: 8px 14px;
      border-radius: 10px 10px 0 0;
      cursor: pointer;
      font: inherit;
      font-weight: 600;
    }}
    .tab.active {{
      background: var(--bg);
      color: var(--accent);
      border-color: var(--line);
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: end;
      flex-wrap: wrap;
      padding: 10px 16px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      flex: 0 0 auto;
    }}
    label {{
      display: grid;
      gap: 4px;
      font-size: 0.78rem;
      color: var(--muted);
      font-weight: 600;
    }}
    select {{
      min-width: 180px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }}
    main {{ min-height: 0; height: 100%; padding: 0; overflow: hidden; }}
    .pane {{ display: none; height: 100%; min-height: 0; }}
    .pane.active {{ display: flex; flex-direction: column; }}
    .pane iframe {{
      flex: 1 1 auto;
      width: 100%;
      height: 100%;
      min-height: 0;
      border: 0;
      background: #fff;
    }}
    .instance-layout {{
      display: grid;
      grid-template-columns: minmax(340px, 1fr) minmax(360px, 1fr);
      flex: 1 1 auto;
      min-height: 0;
      height: 100%;
    }}
    .tree-col, .charts-col {{
      min-height: 0;
      overflow: auto;
    }}
    .tree-col {{
      border-right: 1px solid var(--line);
      padding: 14px 16px 24px;
      background: linear-gradient(180deg, #f7f9fb 0%, #eef2f6 100%);
    }}
    .charts-col {{
      padding: 14px 16px 24px;
      background: var(--panel);
    }}
    .col-title {{
      margin: 0 0 10px;
      font-size: 0.82rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
    }}
    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .meta-row span {{
      background: var(--chip);
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.78rem;
    }}
    .node {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      margin: 8px 0;
      box-shadow: 0 1px 0 rgba(28,36,48,0.03);
    }}
    .node h3 {{
      margin: 0 0 6px;
      font-size: 0.95rem;
      color: var(--accent);
    }}
    .props {{ display: grid; gap: 4px; font-size: 0.84rem; }}
    .props code {{
      background: var(--accent-soft);
      color: var(--accent);
      padding: 1px 6px;
      border-radius: 999px;
      font-size: 0.78rem;
    }}
    .children {{
      margin-left: 18px;
      border-left: 2px solid #c9d5e3;
      padding-left: 14px;
    }}
    .edge {{
      font-size: 0.75rem;
      color: var(--muted);
      margin: 8px 0 2px;
      font-weight: 650;
      letter-spacing: 0.02em;
    }}
    .hit {{ color: var(--ok); font-weight: 700; }}
    .miss {{ color: var(--miss); font-weight: 700; }}
    .empty {{ color: var(--muted); padding: 18px 4px; font-size: 0.92rem; }}
    .chart-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 12px;
      background: #fff;
    }}
    .chart-card h4 {{
      margin: 0 0 10px;
      font-size: 0.9rem;
      color: var(--accent);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 10px;
    }}
    .metric {{
      background: var(--chip);
      border-radius: 10px;
      padding: 10px;
      text-align: center;
    }}
    .metric .k {{ font-size: 0.72rem; color: var(--muted); font-weight: 650; }}
    .metric .v {{ font-size: 1.05rem; font-weight: 700; margin-top: 2px; }}
    .hit-bar {{
      height: 14px;
      background: #e6ebf0;
      border-radius: 999px;
      overflow: hidden;
      margin-top: 6px;
    }}
    .hit-bar > i {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #1b7f4a, #2ea864);
    }}
    .legend {{
      display: flex;
      gap: 12px;
      font-size: 0.78rem;
      color: var(--muted);
      margin-top: 8px;
    }}
    .legend i {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 4px;
    }}
    .legend .h {{ background: var(--ok); }}
    .legend .m {{ background: var(--miss); }}
    .legend .sel {{
      width: 12px;
      height: 12px;
      border: 2px solid var(--accent);
      background: transparent;
      border-radius: 50%;
      vertical-align: -2px;
    }}
    svg.chart {{ width: 100%; height: 160px; display: block; }}
    svg.court {{ width: 100%; height: 180px; display: block; }}
    .shot-dot {{ cursor: pointer; }}
    @media (max-width: 980px) {{
      .instance-layout {{ grid-template-columns: 1fr; }}
      .tree-col {{ border-right: 0; border-bottom: 1px solid var(--line); max-height: 45vh; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header>
      <h1>CIATec Basketball Ontology</h1>
      <p>Data graph · conceptual model · populated case</p>
      <div class="tabs" role="tablist">
        <button class="tab active" data-tab="data" type="button">1. Data Graph</button>
        <button class="tab" data-tab="ontology" type="button">2. Ontology View</button>
        <button class="tab" data-tab="instance" type="button">3. Instance View</button>
      </div>
    </header>

    <main>
      <section class="pane active" id="pane-data">
        @@DATA_GRAPH_IFRAME@@
      </section>
      <section class="pane" id="pane-ontology">
        @@ONTOLOGY_IFRAME@@
      </section>
      <section class="pane" id="pane-instance">
        <div class="toolbar" id="instanceToolbar">
          <label>Participant
            <select id="participantSelect"></select>
          </label>
          <label>Session (day)
            <select id="sessionSelect"></select>
          </label>
          <label>Match
            <select id="matchSelect"></select>
          </label>
          <label>Shot
            <select id="shotSelect"></select>
          </label>
        </div>
        <div class="instance-layout">
          <div class="tree-col">
            <p class="col-title">Semantic case</p>
            <div class="meta-row" id="sideMeta"></div>
            <div id="tree"></div>
          </div>
          <div class="charts-col">
            <p class="col-title">Match performance</p>
            <div id="charts"></div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const DATA = {payload};

    const tabs = document.querySelectorAll('.tab');
    const panes = {{
      data: document.getElementById('pane-data'),
      ontology: document.getElementById('pane-ontology'),
      instance: document.getElementById('pane-instance'),
    }};

    tabs.forEach(btn => {{
      btn.addEventListener('click', () => {{
        tabs.forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        Object.values(panes).forEach(p => p.classList.remove('active'));
        panes[btn.dataset.tab].classList.add('active');

        if (btn.dataset.tab === 'ontology' || btn.dataset.tab === 'data') {{
          const iframe = panes[btn.dataset.tab].querySelector('iframe');
          const ping = () => {{
            try {{ iframe.contentWindow.postMessage('fit', '*'); }} catch (e) {{}}
          }};
          requestAnimationFrame(() => {{
            ping();
            setTimeout(ping, 80);
            setTimeout(ping, 250);
            setTimeout(ping, 600);
          }});
        }}
      }});
    }});

    const participantSelect = document.getElementById('participantSelect');
    const sessionSelect = document.getElementById('sessionSelect');
    const matchSelect = document.getElementById('matchSelect');
    const shotSelect = document.getElementById('shotSelect');
    const tree = document.getElementById('tree');
    const sideMeta = document.getElementById('sideMeta');
    const charts = document.getElementById('charts');

    function esc(v) {{
      return String(v ?? '—')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}

    function prop(label, value, cls='') {{
      if (value === null || value === undefined || value === '') return '';
      const klass = cls ? ` class="${{cls}}"` : '';
      return `<div><code>${{esc(label)}}</code> → <span${{klass}}>${{esc(value)}}</span></div>`;
    }}

    function pct(v) {{
      if (v === null || v === undefined) return '—';
      return Math.round(Number(v) * 100) + '%';
    }}

    function currentParticipant() {{
      return DATA.participants.find(p => p.id === participantSelect.value);
    }}
    function currentSession() {{
      const p = currentParticipant();
      return (p?.sessions || []).find(s => s.id === sessionSelect.value);
    }}
    function currentMatch() {{
      const s = currentSession();
      return (s?.matches || []).find(m => m.id === matchSelect.value);
    }}
    function currentShot() {{
      const m = currentMatch();
      return (m?.shots || []).find(sh => sh.id === shotSelect.value);
    }}

    function fillParticipants() {{
      participantSelect.innerHTML = DATA.participants.map(p => {{
        const tag = p.group === 'CerebralPalsyGroup' ? 'CP' : 'Control';
        return `<option value="${{p.id}}">${{p.id}} (${{tag}}, ${{p.age ?? '?'}}y)</option>`;
      }}).join('');
      const preferred = DATA.participants.find(p => p.id_user === 2) || DATA.participants[0];
      if (preferred) participantSelect.value = preferred.id;
    }}

    function fillSessions() {{
      const p = currentParticipant();
      sessionSelect.innerHTML = (p?.sessions || []).map(s =>
        `<option value="${{s.id}}">Day ${{s.day}} — ${{s.id}}</option>`
      ).join('');
    }}

    function fillMatches() {{
      const s = currentSession();
      matchSelect.innerHTML = (s?.matches || []).map(m =>
        `<option value="${{m.id}}">${{m.id}} (hit rate ${{pct(m.hit_rate)}})</option>`
      ).join('');
    }}

    function fillShots() {{
      const m = currentMatch();
      shotSelect.innerHTML = (m?.shots || []).map(sh => {{
        const hit = sh.is_hit ? 'hit' : 'miss';
        return `<option value="${{sh.id}}">${{sh.id}} (${{hit}})</option>`;
      }}).join('');
    }}

    function renderMeta(p) {{
      if (!p) {{
        sideMeta.innerHTML = '';
        return;
      }}
      sideMeta.innerHTML = `
        <span><strong>${{esc(p.id)}}</strong></span>
        <span>${{esc(p.group)}}</span>
        <span>${{esc(p.sex)}} / ${{esc(p.age)}}y</span>
        <span>${{esc(p.health?.type || 'no health condition')}}</span>
        <span>${{esc(p.health?.gmfcs || '—')}} / ${{esc(p.health?.macs || '—')}}</span>
      `;
    }}

    function renderTree() {{
      const p = currentParticipant();
      const s = currentSession();
      const m = currentMatch();
      const sh = currentShot();
      renderMeta(p);

      if (!p) {{
        tree.innerHTML = '<div class="empty">No participant available.</div>';
        return;
      }}

      const healthBlock = p.health ? `
        <div class="edge">hasHealthCondition</div>
        <div class="node">
          <h3>${{esc(p.health.type)}}</h3>
          <div class="props">
            ${{prop('hasGMFCS', p.health.gmfcs)}}
            ${{prop('hasMACS', p.health.macs)}}
          </div>
        </div>` : '';

      const shotBlock = sh ? `
        <div class="edge">containsShot</div>
        <div class="node">
          <h3>${{esc(sh.id)}} <small style="color:var(--muted)">ShotAttempt</small></h3>
          <div class="props">
            ${{prop('hasCurrentPosition', sh.current_position)}}
            ${{prop('hasPreviousPosition', sh.previous_position)}}
            ${{prop('isSamePosition', sh.is_same_position)}}
            ${{prop('hasTimeBetween', sh.time_between)}}
            ${{prop('hasTimeRemaining', sh.time_remaining)}}
          </div>
          <div class="edge">hasOutcome</div>
          <div class="children">
            <div class="node">
              <h3>${{esc(sh.outcome_id)}} <small style="color:var(--muted)">GameOutcome</small></h3>
              <div class="props">
                ${{prop('isHit', sh.is_hit, sh.is_hit ? 'hit' : 'miss')}}
              </div>
            </div>
          </div>
        </div>` : '<div class="empty">No shots in this match.</div>';

      const matchBlock = m ? `
        <div class="edge">containsMatch</div>
        <div class="node">
          <h3>${{esc(m.id)}} <small style="color:var(--muted)">Match</small></h3>
          <div class="props">
            ${{prop('hasSpeed', m.speed)}}
            ${{prop('hasHitRate', m.hit_rate)}}
            ${{prop('hasNShots', m.n_shots)}}
            ${{prop('hasTotalTime', m.total_time)}}
          </div>
          <div class="children">${{shotBlock}}</div>
        </div>` : '<div class="empty">No matches in this session.</div>';

      const sessionBlock = s ? `
        <div class="edge">participatesIn</div>
        <div class="node">
          <h3>${{esc(s.id)}} <small style="color:var(--muted)">GameSession</small></h3>
          <div class="props">${{prop('hasDay', s.day)}}</div>
          <div class="children">${{matchBlock}}</div>
        </div>` : '<div class="empty">No sessions for this participant.</div>';

      tree.innerHTML = `
        <div class="node">
          <h3>${{esc(p.id)}} <small style="color:var(--muted)">Participant</small></h3>
          <div class="props">
            ${{prop('hasAge', p.age)}}
            ${{prop('hasSex', p.sex)}}
            ${{prop('belongsToGroup', p.group)}}
          </div>
          ${{healthBlock}}
          <div class="children">${{sessionBlock}}</div>
        </div>
      `;
    }}

    function renderTimeline(m, selectedId) {{
      const shots = m?.shots || [];
      if (!shots.length) return '<div class="empty">No shot timeline available.</div>';

      const times = shots.map(s => Number(s.time_remaining)).filter(v => !Number.isNaN(v));
      const tMax = Math.max(...times, Number(m.total_time) || 45);
      const tMin = 0;
      const W = 520, H = 160, padL = 36, padR = 16, padT = 18, padB = 28;
      const innerW = W - padL - padR;
      const innerH = H - padT - padB;

      const xOf = (t) => padL + ((tMax - t) / (tMax - tMin || 1)) * innerW;
      const yBase = padT + innerH * 0.55;

      const dots = shots.map(s => {{
        const x = xOf(Number(s.time_remaining));
        const y = yBase + (s.is_hit ? -18 : 18);
        const fill = s.is_hit ? '#1b7f4a' : '#a33b3b';
        const selected = s.id === selectedId;
        const r = selected ? 8 : 5;
        const ring = selected
          ? `<circle cx="${{x}}" cy="${{y}}" r="12" fill="none" stroke="#1f4e79" stroke-width="2.5"></circle>`
          : '';
        return `${{ring}}<circle class="shot-dot" data-shot="${{esc(s.id)}}" cx="${{x}}" cy="${{y}}" r="${{r}}" fill="${{fill}}" stroke="#fff" stroke-width="1.5">
          <title>${{esc(s.id)}} · remaining ${{esc(s.time_remaining)}}s · ${{s.is_hit ? 'hit' : 'miss'}}</title>
        </circle>`;
      }}).join('');

      return `
        <svg class="chart" viewBox="0 0 ${{W}} ${{H}}" preserveAspectRatio="xMidYMid meet">
          <line x1="${{padL}}" y1="${{padT + innerH}}" x2="${{padL + innerW}}" y2="${{padT + innerH}}" stroke="#c9d5e3"></line>
          <text x="${{padL}}" y="${{H - 8}}" font-size="11" fill="#5b6775">start (${{tMax}}s)</text>
          <text x="${{padL + innerW}}" y="${{H - 8}}" font-size="11" fill="#5b6775" text-anchor="end">end (0s)</text>
          <text x="8" y="${{yBase - 18}}" font-size="10" fill="#1b7f4a">hit</text>
          <text x="8" y="${{yBase + 22}}" font-size="10" fill="#a33b3b">miss</text>
          ${{dots}}
        </svg>
        <div class="legend">
          <span><i class="h"></i>hit</span>
          <span><i class="m"></i>miss</span>
          <span><i class="sel"></i>selected shot</span>
        </div>`;
    }}

    function renderCourt(m, selectedId) {{
      const shots = m?.shots || [];
      if (!shots.length) return '<div class="empty">No position data available.</div>';

      const W = 520, H = 180;
      const zones = {{
        Left: {{ x: 70, y: 95 }},
        Centre: {{ x: 260, y: 70 }},
        Right: {{ x: 450, y: 95 }},
      }};
      const jitter = {{}};
      const dots = shots.map((s, idx) => {{
        const key = s.current_position || 'Centre';
        jitter[key] = (jitter[key] || 0) + 1;
        const base = zones[key] || zones.Centre;
        const angle = jitter[key] * 0.9;
        const x = base.x + Math.cos(angle) * (8 + (jitter[key] % 4) * 5);
        const y = base.y + Math.sin(angle) * (6 + (jitter[key] % 3) * 4);
        const fill = s.is_hit ? '#1b7f4a' : '#a33b3b';
        const selected = s.id === selectedId;
        const r = selected ? 8 : 5;
        const ring = selected
          ? `<circle cx="${{x}}" cy="${{y}}" r="12" fill="none" stroke="#1f4e79" stroke-width="2.5"></circle>`
          : '';
        return `${{ring}}<circle class="shot-dot" data-shot="${{esc(s.id)}}" cx="${{x}}" cy="${{y}}" r="${{r}}" fill="${{fill}}" stroke="#fff" stroke-width="1.5">
          <title>${{esc(s.id)}} · ${{esc(key)}} · ${{s.is_hit ? 'hit' : 'miss'}}</title>
        </circle>`;
      }}).join('');

      const counts = {{ Left: 0, Centre: 0, Right: 0 }};
      shots.forEach(s => {{ if (counts[s.current_position] !== undefined) counts[s.current_position]++; }});

      return `
        <svg class="court" viewBox="0 0 ${{W}} ${{H}}" preserveAspectRatio="xMidYMid meet">
          <rect x="20" y="20" width="480" height="140" rx="10" fill="var(--court)" stroke="var(--court-line)" stroke-width="2"></rect>
          <line x1="173" y1="20" x2="173" y2="160" stroke="var(--court-line)" stroke-dasharray="4 4"></line>
          <line x1="347" y1="20" x2="347" y2="160" stroke="var(--court-line)" stroke-dasharray="4 4"></line>
          <text x="95" y="40" text-anchor="middle" font-size="12" fill="#5b6775">Left (${{counts.Left}})</text>
          <text x="260" y="40" text-anchor="middle" font-size="12" fill="#5b6775">Centre (${{counts.Centre}})</text>
          <text x="425" y="40" text-anchor="middle" font-size="12" fill="#5b6775">Right (${{counts.Right}})</text>
          <circle cx="260" cy="28" r="8" fill="none" stroke="#c45c26" stroke-width="2"></circle>
          ${{dots}}
        </svg>`;
    }}

    function renderCharts() {{
      const m = currentMatch();
      const sh = currentShot();
      if (!m) {{
        charts.innerHTML = '<div class="empty">Select a match to inspect performance.</div>';
        return;
      }}

      const rate = Number(m.hit_rate || 0);
      const ratePct = Math.round(rate * 100);
      charts.innerHTML = `
        <div class="chart-card">
          <h4>Match performance · ${{esc(m.id)}}</h4>
          <div><strong>Hit rate</strong> ${{ratePct}}%</div>
          <div class="hit-bar"><i style="width:${{ratePct}}%"></i></div>
          <div class="metrics">
            <div class="metric"><div class="k">hasNShots</div><div class="v">${{esc(m.n_shots)}}</div></div>
            <div class="metric"><div class="k">hasTotalTime</div><div class="v">${{esc(m.total_time)}}s</div></div>
            <div class="metric"><div class="k">hasSpeed</div><div class="v">${{esc(m.speed)}}</div></div>
          </div>
        </div>
        <div class="chart-card">
          <h4>Shots over time</h4>
          ${{renderTimeline(m, sh?.id)}}
        </div>
        <div class="chart-card">
          <h4>Shot position distribution</h4>
          ${{renderCourt(m, sh?.id)}}
        </div>
      `;

      charts.querySelectorAll('.shot-dot').forEach(el => {{
        el.addEventListener('click', () => {{
          const id = el.getAttribute('data-shot');
          if (!id) return;
          shotSelect.value = id;
          renderAll();
        }});
      }});
    }}

    function renderAll() {{
      renderTree();
      renderCharts();
    }}

    function refreshFromParticipant() {{
      fillSessions();
      fillMatches();
      fillShots();
      renderAll();
    }}
    function refreshFromSession() {{
      fillMatches();
      fillShots();
      renderAll();
    }}
    function refreshFromMatch() {{
      fillShots();
      renderAll();
    }}

    participantSelect.addEventListener('change', refreshFromParticipant);
    sessionSelect.addEventListener('change', refreshFromSession);
    matchSelect.addEventListener('change', refreshFromMatch);
    shotSelect.addEventListener('change', renderAll);

    fillParticipants();
    refreshFromParticipant();
  </script>
</body>
</html>
"""
    return (
        panel.replace("@@DATA_GRAPH_IFRAME@@", _iframe_srcdoc(data_graph_html, "Data Graph"))
        .replace("@@ONTOLOGY_IFRAME@@", _iframe_srcdoc(ontology_html, "Ontology View"))
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified basketball ontology panel (single HTML, 3 tabs)."
    )
    parser.parse_args()

    for path, label in (
        (USERS_XLSX, "users.xlsx"),
        (MATCHES_XLSX, "matches.xlsx"),
        (BALLS_XLSX, "balls.xlsx"),
        (ONTOLOGY_TTL, "ciatec_basquete.ttl"),
    ):
        if not path.exists():
            raise SystemExit(f"Arquivo não encontrado: {path} ({label})")

    data_graph_html, ontology_html = build_embedded_graphs()

    print("Building Instance View (all participants)...")
    data = build_instance_data()
    INSTANCE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    OUTPUT_HTML.write_text(
        render_panel(data, data_graph_html, ontology_html), encoding="utf-8"
    )
    n_part = len(data["participants"])
    n_match = sum(len(s["matches"]) for p in data["participants"] for s in p["sessions"])
    n_shots = sum(
        len(match["shots"])
        for p in data["participants"]
        for s in p["sessions"]
        for match in s["matches"]
    )
    print(f"Panel: {OUTPUT_HTML}")
    print(f"Participants: {n_part} | Matches: {n_match} | Shots: {n_shots}")
    print("Open painel_ontologia.html in your browser.")


if __name__ == "__main__":
    main()
