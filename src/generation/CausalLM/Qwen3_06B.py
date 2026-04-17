from transformers import AutoModelForCausalLM, AutoTokenizer

class Qwen3_06b:
    def __init__(self, model_name="Qwen/Qwen3-0.6B"):
        """
        Inizializza la classe caricando il tokenizer e il modello una sola volta.
        """
        print(f"Caricamento del modello {model_name} in corso...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )
        print("Modello caricato con successo!")

    def generate(self, prompt, max_new_tokens=32768, enable_thinking=True):
        """
        Riceve un prompt e restituisce una tupla contenente (thinking_content, content).
        """
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Prepara l'input
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        # Genera il testo
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens
        )
        
        # Estrai solo i token generati
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

        # Parsing del contenuto di thinking
        try:
            # Trova l'indice del token 151668 (</think>)
            index = len(output_ids) - output_ids[::-1].index(151668)
        except ValueError:
            index = 0

        # Decodifica le due parti
        thinking_content = self.tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
        content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

        return thinking_content, content