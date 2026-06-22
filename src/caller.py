import requests
from pathlib import Path
from typing import Tuple

def read_file(file_path: Path) -> str:
    """Legge il contenuto di un file di testo."""
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Errore: File non trovato in {file_path}")
        raise

def call_lm_studio(system_prompt: str, input_query: str) -> Tuple[str, str]:
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

def run_pipeline(system_prompt_path: Path, input_query_path: Path) -> Tuple[str, str]:
    """
    Funzione principale da chiamare esternamente.
    Carica i file dai percorsi forniti ed esegue la chiamata a LM Studio.
    """
    print(f"Caricamento prompt da:\n - {system_prompt_path}\n - {input_query_path}")
    
    # Carica i testi dai file markdown
    system_prompt = read_file(system_prompt_path)
    input_query = read_file(input_query_path)

    print("Inviando la richiesta a LM Studio...")
    
    # Esegue la chiamata lineare e restituisce i testi
    return call_lm_studio(system_prompt, input_query)

def main():
    """Esecuzione di default se il file viene lanciato direttamente."""
    current_dir = Path(__file__).resolve().parent
    
    # Esegue la pipeline
    response_message, reasoning = run_pipeline((current_dir / "prompt" / "system_prompt.md"), (current_dir / "prompt" / "input_query.md"))
    
    # Mostra i risultati a schermo
    #if reasoning:
    #    print("\n--- Ragionamento del Modello ---")
    #    print(reasoning)
        
    print("\n--- Risposta Finale ---")
    print(response_message)

if __name__ == "__main__":
    main()