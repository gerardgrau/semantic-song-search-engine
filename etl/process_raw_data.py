import pandas as pd

def process_csv(input_path: str, output_path: str):
    print(f"Llegint dades des de {input_path}...")
    # Llegir el CSV. Pot trigar si l'arxiu és gran.
    df = pd.read_csv(input_path)
    
    # El format de text_embedding és:
    # "Artista: <Nom> | Cançó: <Títol> | Lletra: <Lletra de la cançó>"
    
    print("Processant la columna text_embedding...")
    # Expression regular per extreure les dades:
    pattern = r"Artista:\s*(?P<artista>.*?)\s*\|\s*Cançó:\s*(?P<titol2>.*?)\s*\|\s*Lletra:\s*(?P<lletra>.*)"
    extracted = df['text_embedding'].str.extract(pattern)
    
    # Crear el nou DataFrame amb les columnes sol·licitades
    processed_df = pd.DataFrame({
        'titol': df['titol_canco'],    # Utilitzem la columna originària per al títol
        'artista': extracted['artista'],
        'lletra': extracted['lletra']
    })
    
    print(f"Guardant dades processades a {output_path}...")
    # Guardem el resultat al directori processed com a nou CSV
    processed_df.to_csv(output_path, index=False)
    print("Procés completat correctament!")

if __name__ == "__main__":
    input_file = 'data/raw/contingut_embeddings.csv'
    output_file = 'data/processed/cancons_processades.csv'
    process_csv(input_file, output_file)
