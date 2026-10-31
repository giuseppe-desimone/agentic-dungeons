# DOWNLOAD: https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors
# TODO: Impostare models\sd_turbo.safetensors e models\sd_turbo_config automaticamente se non esistono, scaricandoli da Hugging Face. Per ora, scaricare manualmente e posizionare in models\.
# 
# from huggingface_hub import snapshot_download
# snapshot_download(
#     repo_id="stabilityai/sd-turbo",
#     allow_patterns=["*.json", "*.txt", "**/*.json", "**/*.txt"],
#     local_dir="models/sd_turbo_config",
# )

import os
import time
from pathlib import Path
import torch
from diffusers import StableDiffusionPipeline

# Disabilita completamente qualsiasi interazione o chiamata a Hugging Face
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Percorsi locali e autonomi
BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_PATH = BASE_DIR / "models" / "sd_turbo.safetensors"
CONFIG_DIR = BASE_DIR / "models" / "sd_turbo_config"

# Selezione dispositivo e precisione
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

print(f"Caricamento di {CHECKPOINT_PATH.name} su {device}...")
t_load_start = time.perf_counter()

# Carica direttamente dal singolo file safetensors
pipe = StableDiffusionPipeline.from_single_file(
    str(CHECKPOINT_PATH),
    config=str(CONFIG_DIR),
    torch_dtype=dtype,
    local_files_only=True,
)
pipe.to(device)

t_load_end = time.perf_counter()
print(f"Modello caricato in {t_load_end - t_load_start:.2f}s")

# Prompt per SD-Turbo
prompt = "A dark dungeon corridor with glowing torches, realistic, highly detailed, 8k"

print("Generazione immagine in corso...")
t_gen_start = time.perf_counter()

image = pipe(
    prompt=prompt,
    num_inference_steps=1,  # 1 step per SD-Turbo
    guidance_scale=0.0,     # 0.0 per SD-Turbo ad 1 step
    width=512,
    height=512,
).images[0]

t_gen_end = time.perf_counter()
print(f"Tempo di generazione: {t_gen_end - t_gen_start:.2f}s")

output_path = BASE_DIR / "output.png"
image.save(output_path)
print(f"Immagine salvata in: {output_path}")
