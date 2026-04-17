# Importa la classe dal file che abbiamo creato
from generation.CausalLM.Qwen3_06B import Qwen3_06b

def main():
    # 1. Inizializza il generatore (questa operazione richiede qualche secondo 
    # perché carica i pesi del modello nella GPU/CPU)
    llm = Qwen3_06b(model_name="Qwen/Qwen3-0.6B")

    # 2. Prepara i tuoi prompt
    prompts = [
        "A description of a dark crypt, in which a necromancer resides",
        "Write a short poem about a mechanical dragon."
    ]

    # 3. Genera le risposte
    for prompt in prompts:
        print(f"\n--- Prompt: {prompt} ---")
        
        # Chiamata pulita al metodo
        thinking, response = llm.generate(prompt)
        
        print(f"[THINKING]:\n{thinking}\n")
        print(f"[RISPOSTA]:\n{response}\n")

if __name__ == "__main__":
    main()