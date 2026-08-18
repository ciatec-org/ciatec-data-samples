# 🧩 CIATec: OntoGame & LLM Architect

An interactive Streamlit application designed for building FAIR-aligned (Findable, Accessible, Interoperable, Reusable) ontologies and integrating them with Large Language Models (LLMs) via Graph-RAG. This project supports Virtual Rehabilitation and Inclusive Technologies under the CIATec / HINT 2026 framework.

---

## 🧪 Central Hypothesis (PoC)

> *"Integrating multimodal sensorimotor data (captured via webcams, inertial sensors, and game telemetry) into a **Physical-Digital Twin** structured by a **FAIR-aligned Ontology** and combined with an **LLM via Graph-RAG** can accurately predict a player's functional state and execute dynamic real-time game adaptations without clinical hallucinations."*

---

## ✨ Features

- **🎮 Game HUD & Interactive Workflow:** Step-by-step 4-phase guided mission for constructing FAIR domain ontologies.
- **📚 FAIR Vocabulary Mapping:** Integrates standard ontologies including BFO, PROV-O, FOAF, Schema.org, and UDL/DUA.
- **🏀 Multi-Domain Coverage:** Maps attributes across the **Participant**, **Performance**, and **Game-Related** domains.
- **🤖 Physical-Digital Twin Architecture:** Multi-level telemetry structure from basal clinical data to event-level kinematic sensors.
- **🧠 Graph-RAG Grounding:** Generates tailored system prompts grounded in SPARQL queries to eliminate LLM hallucinations.
- **🌐 Interactive Directed Graph Visualization:** Uses `pyvis` and `networkx` to render a labeled, interactive directed graph of the generated ontology directly within the browser.
- **💾 Export Capabilities:** Serializes and downloads the constructed ontology in standard RDF/Turtle (`.ttl`) format using `rdflib`.

---

## 🛠️ Tech Stack

- **Frontend / Framework:** [Streamlit](https://streamlit.io/)
- **Semantic Web & RDF:** [rdflib](https://rdflib.readthedocs.io/)
- **Graph Processing & Visualization:** [NetworkX](https://networkx.org/), [PyVis](https://pyvis.readthedocs.io/)
- **Ontology Standards:** RDF, RDFS, OWL, PROV-O, BFO, FOAF, DCTERMS

---

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.9 or higher installed.

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/your-username/ciatec-ontogame.git](https://github.com/your-username/ciatec-ontogame.git)
cd ciatec-ontogame

```


2. **Create a virtual environment (optional but recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```


3. **Install dependencies:**
```bash
pip install streamlit rdflib networkx pyvis

```

## 🏃 Running the Application

Launch the Streamlit app with the following command:

```bash
streamlit run app.py

```

Open your browser and navigate to `http://localhost:8501`.

---

## 📁 Project Structure

```text
├── app.py              # Main Streamlit application
├── README.md           # Project documentation
└── ciatec_fair_ontology.ttl  # Exported RDF/Turtle ontology sample

```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

```

```