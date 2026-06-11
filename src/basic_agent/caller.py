from pathlib import Path
from orchestrator import orchestrator_app

def read_file(file_path: Path) -> str:
    """Legge il contenuto di un file di testo."""
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Errore: File non trovato in {file_path}")
        raise

def main():
    # Trova la cartella 'basic_agent' in cui si trova questo file
    current_dir = Path(__file__).resolve().parent
    
    # Costruisce i percorsi puntando alla cartella 'prompt' interna
    input_query_path = current_dir / "prompt" / "input_query.md"
    system_prompt_path = current_dir / "prompt" / "system_prompt.md"

    # Carica i testi
    input_query = read_file(input_query_path)
    system_prompt = read_file(system_prompt_path)

    # Stato iniziale per il grafo
    initial_state = {
        "input_query": input_query,
        "system_prompt": system_prompt,
        "response_message": "",
        "reasoning": ""
    }

    # Invocazione del grafo
    final_state = orchestrator_app.invoke(initial_state)
    print(final_state.get("response_message"))

if __name__ == "__main__":
    main()