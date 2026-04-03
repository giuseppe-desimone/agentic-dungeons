import os
from diffusers import AutoPipelineForText2Image

prompt = open('src/image_generation/portrait.md', 'r').read().strip()

pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo").to("cpu")

output_dir = "assets/generated_images"
os.makedirs(output_dir, exist_ok=True)

image = pipe(prompt, width=512, height=512, num_inference_steps=1, guidance_scale=0.0).images[0]

image.save(f"{output_dir}/img.png")
image.resize((128, 128), resample=0).save(f"{output_dir}/img.png")