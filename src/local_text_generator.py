# Modello: Mistral-7B-Instruct-v0.3 (quantizzazione Q6_K in formato GGUF)
# Eseguito localmente tramite llama-cpp-python in modalità 100% offline.

import os
import sys
import time
from pathlib import Path
import torch
from llama_cpp import Llama

# Assicura il corretto rendering dei caratteri accentati su console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Percorsi locali e autonomi
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "Mistral-7B-Instruct-v0.3-Q6_K.gguf"

# Selezione dispositivo (identica a image_generator.py)
device = "cuda" if torch.cuda.is_available() else "cpu"


class TextGenerator:
    """Generatore di testo basato su Mistral-7B GGUF tramite llama-cpp."""

    def __init__(
        self,
        model_path: Path | str = MODEL_PATH,
        device: str | None = None,
        n_ctx: int = 2048,
        n_threads: int | None = None,
        verbose: bool = False,
    ):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"File modello non trovato in: {model_path}")

        # Se non specificato, controlla se CUDA è disponibile, altrimenti ripiega su CPU
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device.lower()

        # Con CUDA scarica tutti i layer (-1) sulla GPU, su CPU imposta 0
        self.n_gpu_layers = -1 if self.device == "cuda" else 0

        print(f"Caricamento di {model_path.name} su {self.device}...")
        t_load_start = time.perf_counter()

        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_threads=n_threads or os.cpu_count(),
            verbose=verbose,
        )

        t_load_end = time.perf_counter()
        print(f"Modello caricato in {t_load_end - t_load_start:.2f}s")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "Sei il Dungeon Master di un'avventura dark fantasy.",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = True,
    ) -> str:
        """Genera una risposta testuale dato un prompt, con supporto allo streaming in tempo reale."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t_gen_start = time.perf_counter()

        if stream:
            response_chunks = []
            response_stream = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )
            for chunk in response_stream:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    print(content, end="", flush=True)
                    response_chunks.append(content)
            print()
            full_text = "".join(response_chunks)
        else:
            response = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
            )
            full_text = response["choices"][0]["message"]["content"]
            print(full_text)

        t_gen_end = time.perf_counter()
        print(f"\nTempo di generazione: {t_gen_end - t_gen_start:.2f}s")
        return full_text


if __name__ == "__main__":
    generator = TextGenerator()

    prompt_test = (
        "Descrivi una stanza segreta nascosta dietro una libreria polverosa in un dungeon sotterraneo."
    )

    print(f"\nPrompt: {prompt_test}\n")
    print("--- Generazione in corso (streaming) ---")
    generator.generate(prompt=prompt_test, max_tokens=150)
