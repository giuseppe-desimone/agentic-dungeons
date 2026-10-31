from pathlib import Path
from typing import Union
from gemini.constructor import send_prompt


class Caller:

    def __call__(self, prompt_input: Union[str, Path]) -> str:
        # Se l'input corrisponde a un file (es. 'prompt.md'), ne legge il testo
        path = Path(prompt_input)
        if path.is_file():
            text = path.read_text(encoding="utf-8")
        else:
            text = str(prompt_input)

        return send_prompt(text)


if __name__ == "__main__":
    ask = Caller()
    print(ask("RISPONDI OK"))
    # print(ask("path/to/prompt.md"))