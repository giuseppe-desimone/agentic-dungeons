import os
from diffusers import AutoPipelineForText2Image

prompt = "Genera l'immagine di un formichiere trasformato in una macchina per la penetrazzione, il suo muso ora è in plastica vibrante (mantiene forme e proporzioni). Tutta la sua testa è un macchinario cyborg adattato alle penetrazioni. La lingua funge da sonda"

pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo").to("cpu")

output_dir = "assets/generated_images"
os.makedirs(output_dir, exist_ok=True)

image = pipe(prompt, width=1920, height=1080, num_inference_steps=1, guidance_scale=0.0).images[0]

image.save(f"{output_dir}/img.png")
#image.resize((128, 128), resample=0).save(f"{output_dir}/img.png")