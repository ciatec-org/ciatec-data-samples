import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD
from rdflib.namespace import FOAF, DCTERMS, DCAT, PROV

def convert_to_fair_linked_data():
    # 1. Inicialização do Grafo RDF
    g = Graph()

    # 2. Definição de Namespaces
    BASE_URI = "http://example.org/data/"
    EX = Namespace("http://example.org/ontology#")
    SCHEMA = Namespace("https://schema.org/")

    g.bind("ex", EX)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)
    g.bind("prov", PROV)
    g.bind("rdfs", RDFS)

    # 3. Leitura das fontes de dados (Princípio FAIR: Acessibilidade a dados estruturados)
    users_df = pd.read_excel("../pc_basketball_2024/users.xlsx", sheet_name="users")
    matches_df = pd.read_excel("../pc_basketball_2024/matches.xlsx", sheet_name="matches")
    balls_df = pd.read_excel("../pc_basketball_2024/balls.xlsx", sheet_name="balls")

    # Metadados do Dataset (R1 - Licenciamento aberto e Proveniência)
    dataset_uri = EX["dataset/motor-performance"]
    g.add((dataset_uri, RDF.type, DCAT.Dataset))
    g.add((dataset_uri, DCTERMS.title, Literal("Motor Performance and Ball Shooting Dataset", lang="en")))
    g.add((dataset_uri, DCTERMS.license, Literal("https://creativecommons.org/licenses/by/4.0/")))
    g.add((dataset_uri, PROV.wasGeneratedBy, Literal("Python FAIR Data Transformation Pipeline")))

    # 4. Mapeamento de Participantes (Users)
    for _, row in users_df.iterrows():
        user_id = int(row['id_user'])
        user_uri = EX[f"participant/{user_id}"]
        
        g.add((user_uri, RDF.type, EX.Participant))
        g.add((user_uri, SCHEMA.identifier, Literal(user_id, datatype=XSD.integer)))
        
        if pd.notna(row.get('sex')):
            g.add((user_uri, SCHEMA.gender, Literal(row['sex'])))
        if pd.notna(row.get('age')):
            g.add((user_uri, SCHEMA.age, Literal(int(row['age']), datatype=XSD.integer)))
        if pd.notna(row.get('group')):
            g.add((user_uri, EX.studyGroup, Literal(str(row['group']))))

    # 5. Mapeamento de Partidas (Matches)
    for _, row in matches_df.iterrows():
        match_id = int(row['id_match'])
        user_id = int(row['id_user'])
        
        match_uri = EX[f"match/{match_id}"]
        user_uri = EX[f"participant/{user_id}"]
        
        g.add((match_uri, RDF.type, EX.Match))
        g.add((match_uri, SCHEMA.identifier, Literal(match_id, datatype=XSD.integer)))
        g.add((user_uri, EX.hasMatch, match_uri))
        
        if pd.notna(row.get('hit_rate')):
            g.add((match_uri, EX.hitRate, Literal(float(row['hit_rate']), datatype=XSD.float)))
        if pd.notna(row.get('total_time')):
            g.add((match_uri, EX.totalTime, Literal(float(row['total_time']), datatype=XSD.float)))

    # 6. Mapeamento de Arremessos (Balls/Shots) - amostra representativa para performance
    for _, row in balls_df.head(500).iterrows():
        ball_id = int(row['id_ball'])
        ball_uri = EX[f"shot/{ball_id}"]
        
        g.add((ball_uri, RDF.type, EX.ShotAttempt))
        g.add((ball_uri, SCHEMA.identifier, Literal(ball_id, datatype=XSD.integer)))
        
        if pd.notna(row.get('is_hit')):
            is_hit_bool = bool(row['is_hit'])
            g.add((ball_uri, EX.isHit, Literal(is_hit_bool, datatype=XSD.boolean)))
        if pd.notna(row.get('total_time')):
            g.add((ball_uri, EX.totalTime, Literal(float(row['total_time']), datatype=XSD.float)))

    # 7. Serialização em formatos abertos exigidos pelas 5 Estrelas do Linked Data
    g.serialize(destination="linked_data_fair.ttl", format="turtle")
    g.serialize(destination="linked_data_fair.jsonld", format="json-ld")
    
    print("Conversão concluída com sucesso! Arquivos gerados: 'linked_data_fair.ttl' e 'linked_data_fair.jsonld'.")

if __name__ == "__main__":
    convert_to_fair_linked_data()