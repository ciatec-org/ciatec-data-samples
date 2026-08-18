import streamlit as st
import streamlit.components.v1 as components
import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF, DCTERMS, PROV
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CIATec - OntoGame & LLM Builder",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada para visual de Jogo Interativo
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .hypothesis-card {
        background-color: #1a2332;
        border-left: 6px solid #00d4b1;
        border-radius: 8px;
        padding: 18px 22px;
        margin-top: 10px;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .game-card {
        background-color: #1e222d;
        border-radius: 12px;
        padding: 20px;
        border: 2px solid #2e364f;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
    }
    .level-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .score-box {
        background-color: #262730;
        border-left: 5px solid #00d4b1;
        padding: 10px 15px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO DO ESTADO DA SESSÃO (GAME STATE)
# -----------------------------------------------------------------------------
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'ontology_config' not in st.session_state:
    st.session_state.ontology_config = {
        "domain": "Cerebral Palsy Rehabilitation",
        "vocabularies": ["BFO", "PROV-O", "FOAF", "Schema.org", "DUA"],
        "domains_selected": [],
        "digital_twin_levels": [],
        "llm_strategy": "Graph-RAG with Grounding"
    }

# -----------------------------------------------------------------------------
# BARRA LATERAL (SIDEBAR) - HUD DO JOGO
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🎮 CIATec Game HUD")
    st.markdown("---")
    st.markdown(f"**Pontuação FAIR:** `{st.session_state.score} XP`")
    st.progress(st.session_state.score / 100)
    
    st.markdown("### 🏆 Status da Missão")
    stages_labels = [
        "1. Domínio & Vocabulários FAIR",
        "2. Os 3 Domínios do CIATec",
        "3. Digital Twin Sensorimotor",
        "4. Geração de Ontologia & LLM"
    ]
    for i, label in enumerate(stages_labels, 1):
        if i < st.session_state.stage:
            st.markdown(f"✅ ~~{label}~~")
        elif i == st.session_state.stage:
            st.markdown(f"👉 **{label}**")
        else:
            st.markdown(f"🔒 {label}")
            
    st.markdown("---")
    if st.button("🔄 Reiniciar Missão"):
        st.session_state.stage = 1
        st.session_state.score = 0
        st.session_state.ontology_config = {
            "domain": "Cerebral Palsy Rehabilitation",
            "vocabularies": ["BFO", "PROV-O", "FOAF", "Schema.org", "DUA"],
            "domains_selected": [],
            "digital_twin_levels": [],
            "llm_strategy": "Graph-RAG with Grounding"
        }
        st.rerun()

# -----------------------------------------------------------------------------
# CABEÇALHO PRINCIPAL E HIPÓTESE DA POC
# -----------------------------------------------------------------------------
st.title("🧩 CIATec: OntoGame & LLM Architect")
st.caption("Construção interativa de Ontologias FAIR e integração com LLMs para Reabilitação Virtual e Tecnologias Inclusivas (CIATec / HINT 2026)")

# Bloco em Destaque: Hipótese Central a ser Validada
st.markdown("""
<div class='hypothesis-card'>
    <h4 style='color: #00d4b1; margin-top: 0;'>🧪 Hipótese Central a ser Validada (PoC)</h4>
    <p style='font-size: 1.05em; line-height: 1.5; color: #e0e0e0;'>
    <i>"A integração de dados sensoriotores multimodais (capturados via webcam, sensores inerciais e telemetria do jogo) 
    em um <b>Gêmeo Digital (Digital Twin)</b> estruturado por uma <b>Ontologia alinhada aos Princípios FAIR</b> e combinada com um <b>LLM via Graph-RAG</b> 
    é capaz de predizer o estado funcional do jogador e executar adaptações dinâmicas em tempo real com alta precisão e sem alucinações clínicas."</i>
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FASE 1: DEFINIÇÃO DE VOCABULÁRIOS FAIR & INFRAESTRUTURA
# -----------------------------------------------------------------------------
if st.session_state.stage == 1:
    st.markdown("<span class='level-badge'>FASE 1 DE 4</span>", unsafe_allow_html=True)
    st.subheader("🎯 Definindo os Vocabulários e Ontologias FAIR")
    
    st.write("""
    Bem-vindo, Pesquisador! Para validar nossa hipótese e atender aos princípios **FAIR** (Findable, Accessible, Interoperable, Reusable)[cite: 1], 
    devemos mapear o projeto **CIATec** utilizando ontologias e vocabulários ontológicos consolidados e abertos.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Vocabulários Padrão Propostos:")
        v1 = st.checkbox("BFO / OBO Foundry (Basic Formal Ontology - Saúde/Anatomia)", value=True)
        v2 = st.checkbox("PROV-O (W3C Provenance Ontology - Rastreabilidade de Tentativas e Dados)", value=True)
        v3 = st.checkbox("FOAF / Schema.org (Perfil do Participante e Metadados)", value=True)
        v4 = st.checkbox("DUA / UDL (Desenho Universal para Aprendizagem - Acessibilidade)", value=True)
    
    with col2:
        st.info("""
        💡 **Por que aplicar FAIR?**
        Garante a interoperabilidade entre exames clínicos (ex: GMFCS, MACS), 
        sensores cinemáticos (MediaPipe/Inerciais) e eventos dos jogos sérios (ex: Basquete Virtual)[cite: 1].
        """)
    
    if st.button("Avançar para Fase 2 ➡️"):
        selected_vocabs = []
        if v1: selected_vocabs.append("BFO")
        if v2: selected_vocabs.append("PROV-O")
        if v3: selected_vocabs.append("FOAF/Schema.org")
        if v4: selected_vocabs.append("DUA")
        
        st.session_state.ontology_config["vocabularies"] = selected_vocabs
        st.session_state.score = 25
        st.session_state.stage = 2
        st.rerun()

# -----------------------------------------------------------------------------
# FASE 2: TRÊS DOMÍNIOS DO FRAMEWORK GAMEPLAY CIATEC
# -----------------------------------------------------------------------------
elif st.session_state.stage == 2:
    st.markdown("<span class='level-badge'>FASE 2 DE 4</span>", unsafe_allow_html=True)
    st.subheader("🏀 Os Três Domínios do Framework de Gameplay CIATec")
    
    st.write("""
    Com base na arquitetura do CIATec[cite: 1], os determinantes do desempenho do jogo sério são divididos em 3 domínios dinâmicos.
    Selecione quais classes e propriedades devem ser mapeadas na ontologia para suportar a hipótese:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 1. Participant Domain")
        p1 = st.checkbox("Severidade Funcional (GMFCS/MACS)", value=True)
        p2 = st.checkbox("Idade e Sexo", value=True)
        p3 = st.checkbox("Perfil Cognitivo/Sócio-emocional", value=True)
        
    with col2:
        st.markdown("#### 2. Performance Domain")
        f1 = st.checkbox("Exposição Prática (Practice Exposure)", value=True)
        f2 = st.checkbox("Tempo de Retenção de Bola (Ball-Holding)", value=True)
        f3 = st.checkbox("Métricas Cinemáticas (SPARC/Jerk)", value=True)
        
    with col3:
        st.markdown("#### 3. Game-Related Domain")
        g1 = st.checkbox("Velocidade do Oponente / Obstáculo", value=True)
        g2 = st.checkbox("Posição do Arremesso (Esquerda/Centro/Direita)", value=True)
        g3 = st.checkbox("Tempo Restante da Sessão", value=True)

    if st.button("Avançar para Fase 3 ➡️"):
        domains = []
        if p1 or p2 or p3: domains.append("Participant-Related Domain")
        if f1 or f2 or f3: domains.append("Performance-Related Domain")
        if g1 or g2 or g3: domains.append("Game-Related Domain")
        
        st.session_state.ontology_config["domains_selected"] = domains
        st.session_state.score = 50
        st.session_state.stage = 3
        st.rerun()

# -----------------------------------------------------------------------------
# FASE 3: ESTRUTURAÇÃO DO SENSORIMOTOR PHYSICAL-DIGITAL TWIN
# -----------------------------------------------------------------------------
elif st.session_state.stage == 3:
    st.markdown("<span class='level-badge'>FASE 3 DE 4</span>", unsafe_allow_html=True)
    st.subheader("🤖 Sensorimotor Physical-Digital Twin & Estrutura Multimodal")
    
    st.write("""
    Para atualizar o **Digital Twin** em tempo real e realimentar os algoritmos adaptativos do jogo (testando a hipótese central), 
    selecione os níveis de coleta de dados multimodais que serão integrados no Triplestore RDF:
    """)
    
    dt_l1 = st.checkbox("Nível Basal: Dados Clínicos e Demográficos", value=True)
    dt_l2 = st.checkbox("Nível Sessão: Data, Dispositivo, Exames e Ambiente", value=True)
    dt_l3 = st.checkbox("Nível Tentativa (Attempt): Sensores Cinemáticos Sincronizados (MediaPipe/Acelerômetro)", value=True)
    dt_l4 = st.checkbox("Nível Evento: Colisão, Toque, Acerto, Erro", value=True)
    dt_l5 = st.checkbox("Nível Fenótipo: Vetor de Desempenho Funcional Atualizado", value=True)
    
    st.markdown("---")
    st.markdown("### Estratégia de Ancoragem para LLM (Grounding & Graph-RAG)")
    rag_option = st.radio(
        "Como o LLM utilizará a Ontologia para validar a hipótese?",
        ["Graph-RAG com Validação Ontológica (Impede Alucinações Clínicas)",
         "Geração de Relatórios Preditivos com Grounding em SPARQL",
         "Ajuste Adaptativo de Dificuldade do Jogo em Tempo Real"]
    )
    
    if st.button("Finalizar Configuração e Gerar Ontologia / Prompt LLM 🚀"):
        dt_levels = []
        if dt_l1: dt_levels.append("Basal")
        if dt_l2: dt_levels.append("Sessão")
        if dt_l3: dt_levels.append("Tentativa")
        if dt_l4: dt_levels.append("Evento")
        if dt_l5: dt_levels.append("Fenótipo")
        
        st.session_state.ontology_config["digital_twin_levels"] = dt_levels
        st.session_state.ontology_config["llm_strategy"] = rag_option
        st.session_state.score = 100
        st.session_state.stage = 4
        st.rerun()

# -----------------------------------------------------------------------------
# FASE 4: RESULTADO - GERAÇÃO DA ONTOLOGIA RDF/TURTLE, PROMPT E VISUALIZAÇÃO DE GRAFO
# -----------------------------------------------------------------------------
elif st.session_state.stage == 4:
    st.markdown("<span class='level-badge'>FASE 4 DE 4 - CONCLUÍDO</span>", unsafe_allow_html=True)
    st.balloons()
    st.subheader("🎉 Ontologia FAIR e Integração LLM Geradas com Sucesso!")
    
    tab1, tab2, tab3 = st.tabs(["📄 Ontologia RDF/Turtle (FAIR)", "🧠 Prompt & Contexto LLM (Graph-RAG)", "📊 Resumo da PoC"])
    
    # Construção do Grafo RDF no RDFLib para reaproveitamento nos componentes
    g = Graph()
    CIATEC = Namespace("http://www.ciatec.org/ontology/rehab#")
    BFO = Namespace("http://purl.obolibrary.org/obo/bfo.owl#")
    
    g.bind("ciatec", CIATEC)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("bfo", BFO)
    
    # Classes Principais
    g.add((CIATEC.Participant, RDF.type, OWL.Class))
    g.add((CIATEC.Participant, RDFS.subClassOf, FOAF.Person))
    g.add((CIATEC.Participant, RDFS.label, Literal("Participant", lang="en")))
    
    g.add((CIATEC.GameplayAttempt, RDF.type, OWL.Class))
    g.add((CIATEC.GameplayAttempt, RDFS.subClassOf, PROV.Activity))
    g.add((CIATEC.GameplayAttempt, RDFS.label, Literal("GameplayAttempt", lang="en")))
    
    g.add((CIATEC.DigitalTwinState, RDF.type, OWL.Class))
    g.add((CIATEC.DigitalTwinState, RDFS.label, Literal("DigitalTwinState", lang="en")))
    
    # Propriedades
    g.add((CIATEC.hasGMFCSLevel, RDF.type, OWL.DatatypeProperty))
    g.add((CIATEC.hasGMFCSLevel, RDFS.domain, CIATEC.Participant))
    g.add((CIATEC.hasGMFCSLevel, RDFS.range, XSD.integer))
    
    g.add((CIATEC.ballHoldingTime, RDF.type, OWL.DatatypeProperty))
    g.add((CIATEC.ballHoldingTime, RDFS.domain, CIATEC.GameplayAttempt))
    g.add((CIATEC.ballHoldingTime, RDFS.range, XSD.float))
    
    g.add((CIATEC.opponentSpeed, RDF.type, OWL.DatatypeProperty))
    g.add((CIATEC.opponentSpeed, RDFS.domain, CIATEC.GameplayAttempt))
    g.add((CIATEC.opponentSpeed, RDFS.range, XSD.float))
    
    g.add((CIATEC.hasShotSuccess, RDF.type, OWL.DatatypeProperty))
    g.add((CIATEC.hasShotSuccess, RDFS.domain, CIATEC.GameplayAttempt))
    g.add((CIATEC.hasShotSuccess, RDFS.range, XSD.boolean))
    
    # Instâncias (Amostra FAIR)
    p1 = URIRef(CIATEC + "Participant_001")
    g.add((p1, RDF.type, CIATEC.Participant))
    g.add((p1, CIATEC.hasGMFCSLevel, Literal(2, datatype=XSD.integer)))
    g.add((p1, FOAF.age, Literal(14, datatype=XSD.integer)))
    
    att1 = URIRef(CIATEC + "Attempt_10691")
    g.add((att1, RDF.type, CIATEC.GameplayAttempt))
    g.add((att1, PROV.wasAssociatedWith, p1))
    g.add((att1, CIATEC.ballHoldingTime, Literal(1.42, datatype=XSD.float)))
    g.add((att1, CIATEC.opponentSpeed, Literal(2.5, datatype=XSD.float)))
    g.add((att1, CIATEC.hasShotSuccess, Literal(True, datatype=XSD.boolean)))
    
    dt1 = URIRef(CIATEC + "DigitalTwin_001")
    g.add((dt1, RDF.type, CIATEC.DigitalTwinState))
    g.add((dt1, PROV.wasDerivedFrom, att1))

    # -------------------------------------------------------------------------
    # TAB 1: GERAÇÃO RDF/TURTLE COM RDFLIB
    # -------------------------------------------------------------------------
    with tab1:
        st.markdown("### Ontologia OWL/RDF Serializada em Turtle (`.ttl`)")
        st.caption("Instanciada dinamicamente utilizando RDFLib segundo os padrões W3C, BFO e PROV-O")
        
        turtle_data = g.serialize(format="turtle")
        st.code(turtle_data, language="ttl")
        
        st.download_button(
            label="💾 Baixar Arquivo da Ontologia (.ttl)",
            data=turtle_data,
            file_name="ciatec_fair_ontology.ttl",
            mime="text/turtle"
        )

    # -------------------------------------------------------------------------
    # TAB 2: PROMPT CONTEXTUALIZADO PARA LLM (GRAPH-RAG / GROUNDING)
    # -------------------------------------------------------------------------
    with tab2:
        st.markdown("### System Prompt / Contexto para Integração com LLM")
        st.write("""
        Para validar a hipótese sem risco de alucinações funcionais ou clínicas, 
        o LLM é instruído a responder **estritamente ancorado (*grounded*)** nas triplas do Grafo de Conhecimento[cite: 1]:
        """)
        
        prompt_template = f"""SYSTEM PROMPT - CIATec ADAPTIVE AI ENGINE

Você é um assistente especialista em neurodesenvolvimento, acessibilidade e análise de sérious games, atuando no âmbito do projeto CIATec / HINT 2026.

HIPÓTESE EM VALIDAÇÃO:
A fusão de dados sensoriotores multimodais em um Gêmeo Digital ontológico FAIR permite predizer o estado funcional e ajustar adaptativamente o jogo sem alucinações.

REGRAS DE CONDUTA E GROUNDING:
1. Suas respostas devem ser estritamente fundamentadas na Ontologia FAIR do CIATec (vocabulários BFO, PROV-O, DUA).
2. NUNCA alucine dados clínicos ou métricas do participante.
3. Utilize os 3 domínios para interpretação dos dados:
   - Participant-Related Domain (GMFCS, idade)
   - Performance-Related Domain (tempo de retenção de bola, exposição prática)
   - Game-Related Domain (velocidade do oponente, posição do arremesso)

ESTRATÉGIA SELECIONADA: {st.session_state.ontology_config['llm_strategy']}
NÍVEIS DE COLETA DIGITAL TWIN: {', '.join(st.session_state.ontology_config['digital_twin_levels'])}

EXEMPLO DE CONSULTA CONTEXTUAL (SPARQL GROUNDING):
PREFIX ciatec: <http://www.ciatec.org/ontology/rehab#>
SELECT ?participant ?gmfcs ?successRate WHERE {{
  ?participant ciatec:hasGMFCSLevel ?gmfcs .
  ...
}}

TAREFA: Analise o vetor do Digital Twin do participante e sugira a adaptação no jogo (ex: alterar velocidade do oponente) mantendo o alinhamento com as diretrizes do Desenho Universal para a Aprendizagem (DUA).
"""
        st.code(prompt_template, language="markdown")

    # -------------------------------------------------------------------------
    # TAB 3: RESUMO DA PROVA DE CONCEITO
    # -------------------------------------------------------------------------
    with tab3:
        st.markdown("### 📊 Relatório da Prova de Conceito (PoC)")
        st.json(st.session_state.ontology_config)
        st.success("Protótipo finalizado com pontuação máxima de alinhamento FAIR (100 XP)!")

    # -------------------------------------------------------------------------
    # VISUALIZAÇÃO DA ONTOLOGIA (GRAFO DIRECIONADO E ROTULADO)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🌐 Visualização Interativa da Ontologia (Grafo Direcionado e Rotulado)")
    st.write("Explore as conexões ontológicas entre participantes, métricas do Digital Twin e conceitos RDF/PROV-O instanciados.")

    def render_pyvis_graph(rdf_graph):
        net = Network(height="550px", width="100%", bgcolor="#0e1117", font_color="#ffffff", directed=True)
        
        # Formatação das arestas direcionadas
        net.heading = "Ontologia CIATec"
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -3000,
              "centralGravity": 0.3,
              "springLength": 120
            }
          },
          "edges": {
            "arrows": {
              "to": { "enabled": true, "scaleFactor": 0.7 }
            },
            "font": { "size": 11, "align": "middle", "color": "#888888" },
            "color": { "color": "#00d4b1", "highlight": "#ff4b4b" },
            "smooth": { "type": "continuous" }
          }
        }
        """)

        # Adicionar Nós e Arestas do Grafo RDF ao PyVis Network
        for s, p, o in rdf_graph:
            # Extrair rótulos limpos dos URIs/Literais
            s_label = s.split("#")[-1] if "#" in str(s) else str(s).split("/")[-1]
            p_label = p.split("#")[-1] if "#" in str(p) else str(p).split("/")[-1]
            o_label = o.split("#")[-1] if "#" in str(o) else str(o).split("/")[-1]

            # Estilização condicional de nós
            s_color = "#00d4b1" if "Participant" in str(s) else ("#ff4b4b" if "Attempt" in str(s) else "#4da6ff")
            o_color = "#00d4b1" if "Participant" in str(o) else ("#ff4b4b" if "Attempt" in str(o) else ("#e0e0e0" if isinstance(o, Literal) else "#4da6ff"))

            net.add_node(str(s), label=s_label, title=str(s), color=s_color)
            net.add_node(str(o), label=o_label, title=str(o), color=o_color)
            net.add_edge(str(s), str(o), label=p_label)

        # Salvar e Renderizar como HTML temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            net.write_html(tmp_file.name)
            tmp_path = tmp_file.name

        with open(tmp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        os.remove(tmp_path)
        return html_content

    graph_html = render_pyvis_graph(g)
    components.html(graph_html, height=580, scrolling=False)