from flask import Flask, request, send_file
import torch
from PIL import Image
from nudenet import NudeDetector
from diffusers import StableDiffusionInpaintPipeline
import io
import os
from werkzeug.utils import secure_filename
from pyngrok import ngrok

app = Flask(_name_)

# Initialize ngrok
port_no = 5000
public_url = ngrok.connect(port_no).public_url
print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port_no}\"")

class ClothingGenerator:
    def _init_(self):
        # Initialize NudeNet detector
        self.nude_detector = NudeDetector()

        # Initialize Stable Diffusion pipeline
        self.pipe = StableDiffusionInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-inpainting",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )

        # Move to GPU if available
        if torch.cuda.is_available():
            self.pipe = self.pipe.to("cuda")

        # Classes we want to detect and replace
        self.target_classes = [
            "ANUS_EXPOSED",
            "BUTTOCKS_EXPOSED", 
            "FEMALE_BREAST_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "FEMALE_GENITALIA_COVERED",
            "FEMALE_BREAST_COVERED",
            "FEMALE_GENITALIA_EXPOSED"
        ]

        self.confidence_threshold = 0.50
        
        self.clothing_prompts = {
            "FEMALE_BREAST_EXPOSED": "wearing a casual T-shirt",
            "FEMALE_BREAST_COVERED": "wearing a casual T-shirt", 
            "BUTTOCKS_EXPOSED": "wearing casual jeans",
            "FEMALE_GENITALIA_EXPOSED": "wearing full-length jeans",
            "FEMALE_GENITALIA_COVERED": "wearing full-length jeans",
            "MALE_GENITALIA_EXPOSED": "wearing casual jeans",
            "ANUS_EXPOSED": "wearing casual jeans"
        }

    def create_mask_from_detections(self, image, detections):
        mask = Image.new('RGB', image.size, 'black')
        draw = ImageDraw.Draw(mask)

        for detection in detections:
            if (detection['class'] in self.target_classes and
                detection['score'] >= self.confidence_threshold):
                x0, y0, w, h = detection['box']
                x1, y1 = x0 + w, y0 + h
                draw.rectangle([x0, y0, x1, y1], fill='white')

        return mask

    def expand_box(self, box, image_size, margin=20):
        x0, y0, w, h = box
        x1, y1 = x0 + w, y0 + h

        x0 = max(0, x0 - margin)
        y0 = max(0, y0 - margin)
        x1 = min(image_size[0], x1 + margin)
        y1 = min(image_size[1], y1 + margin)

        return [x0, y0, x1 - x0, y1 - y0]

    def process_image(self, image_path):
        # Load image
        image = Image.open(image_path).convert('RGB')

        # Get detections
        detections = self.nude_detector.detect(image_path)

        # Filter and process detections
        filtered_detections = []
        for detection in detections:
            if (detection['class'] in self.target_classes and
                detection['score'] >= self.confidence_threshold):
                detection['box'] = self.expand_box(detection['box'], image.size)
                filtered_detections.append(detection)

        if not filtered_detections:
            return image

        # Create mask for inpainting
        mask = self.create_mask_from_detections(image, filtered_detections)

        # Generate appropriate prompt based on detections
        prompt_parts = []
        for detection in filtered_detections:
            prompt_parts.append(self.clothing_prompts[detection['class']])
        base_prompt = "professional photograph of a person " + ", ".join(set(prompt_parts))
        prompt = f"{base_prompt}, high quality, detailed, natural lighting"

        # Run inpainting
        output = self.pipe(
            prompt=prompt,
            negative_prompt="nude, naked, revealing, inappropriate, low quality, blurry",
            image=image,
            mask_image=mask,
            num_inference_steps=50,
            guidance_scale=7.5
        ).images[0]

        return output

# Initialize the generator
generator = ClothingGenerator()

# Configure upload folder
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process_image', methods=['POST'])
def process_image():
    try:
        # Check if image file is present in request
        if 'image' not in request.files:
            return 'No image file provided', 400

        file = request.files['image']
        
        # Check if file is selected
        if file.filename == '':
            return 'No selected file', 400

        # Check if file type is allowed
        if not allowed_file(file.filename):
            return 'File type not allowed', 400

        # Save the uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)

        try:
            # Process the image
            processed_image = generator.process_image(temp_path)

            # Convert the processed image to bytes
            img_byte_arr = io.BytesIO()
            processed_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            # Clean up the temporary file
            os.remove(temp_path)

            # Return the processed image
            return send_file(
                img_byte_arr,
                mimetype='image/png',
                as_attachment=True,
                download_name='processed_image.png'
            )

        except Exception as e:
            # Clean up the temporary file in case of processing error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    except Exception as e:
        return str(e), 500

if _name_ == '_main_':
    # Run the Flask app
    app.run(port=port_no)