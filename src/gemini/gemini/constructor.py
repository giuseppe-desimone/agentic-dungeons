import os
from dotenv import find_dotenv, load_dotenv
from google import genai

load_dotenv(find_dotenv())

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

def send_prompt(prompt: str, model: str = "gemini-3.5-flash-lite") -> str:
    """Invia il testo grezzo all'API di Gemini e restituisce la risposta."""
    interaction = client.interactions.create(
        model=model,
        input=prompt
    )
    return interaction.output_text

if __name__ == "__main__":
    print(send_prompt("RISPONDI OK"))