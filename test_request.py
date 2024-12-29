import requests
import os
from PIL import Image
import io
from datetime import datetime

# Add this before using timestamp
timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")

def test_image_processing(image_path, server_url):
    """
    Send image to server and save processed result
    
    Args:
        image_path (str): Path to input image
        server_url (str): Ngrok URL of the server
    """
    # Verify input image exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found at {image_path}")
    
    # Prepare the URL
    url = f"{server_url.rstrip('/')}/process_image"
    
    # Prepare the files payload
    files = {
        'image': ('test.jpg', open(image_path, 'rb'), 'image/jpeg')
    }
    
    try:
        # Send POST request
        print(f"Sending request to {url}")
        response = requests.post(url, files=files)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Check if response is an image
        if 'image' in response.headers.get('Content-Type', ''):
            # Create output filename
            output_path = 'processed_' + timestamp +os.path.basename(image_path)
            
            # Save the image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Processed image saved as {output_path}")
            
            # Optionally display the before/after images
            try:
                original = Image.open(image_path)
                processed = Image.open(output_path)
                
                print("Original image size:", original.size)
                print("Processed image size:", processed.size)
            except Exception as e:
                print(f"Could not open images for comparison: {e}")
                
        else:
            print("Warning: Response does not appear to be an image")
            print("Response content:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
    finally:
        # Close the file
        files['image'][1].close()

if __name__ == "__main__":
    # Replace with your ngrok URL (without trailing slash)
    SERVER_URL = "https://37aa-34-134-75-134.ngrok-free.app"  # e.g., "http://abc123.ngrok.io"
    
    # Path to test image
    IMAGE_PATH = "test.jpg"
    
    test_image_processing(IMAGE_PATH, SERVER_URL) 