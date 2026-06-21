import requests
from pathlib import Path

def read_file(file_path: Path) -> str:
    """Legge il contenuto di un file di testo."""
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Errore: File non trovato in {file_path}")
        raise

def call_lm_studio(system_prompt: str, input_query: str):
    """Effettua la chiamata diretta a LM Studio."""
    url = "http://localhost:1234/api/v1/chat"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": "google/gemma-4-12b",
        "system_prompt": system_prompt if system_prompt else "You are a helpful assistant.",
        "input": input_query,
    }
    
    # Invio della richiesta HTTP POST
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    # Estrazione dei dati dalla risposta
    message_content = ""
    reasoning_content = ""
    
    for output in data.get("output", []):
        if output.get("type") == "message":
            message_content = output.get("content")
        elif output.get("type") == "reasoning":
            reasoning_content = output.get("content")
            
    return message_content, reasoning_content

def main():
    # Trova la cartella corrente in cui si trova questo script
    current_dir = Path(__file__).resolve().parent
    
    # Costruisce i percorsi per i prompt
    input_query_path = current_dir / "prompt" / "input_query.md"
    system_prompt_path = current_dir / "prompt" / "system_prompt.md"

    # Carica i testi dai file markdown
    input_query = read_file(input_query_path)
    system_prompt = read_file(system_prompt_path)

    print("Inviando la richiesta a LM Studio...")
    
    # Esegue la chiamata lineare
    response_message, reasoning = call_lm_studio(system_prompt, input_query)
    
    # Mostra i risultati a schermo
    if reasoning:
        print("\n--- Ragionamento del Modello ---")
        print(reasoning)
        
    print("\n--- Risposta Finale ---")
    print(response_message)

if __name__ == "__main__":
    main()