import cv2
import tempfile
import argparse
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

class BlurService:

    def __init__(self):
        pass

    def variance_of_laplacian_from_path(self, image_path):
        # Check if file exists
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image file {image_path} not found")
        
        # Load the image and check if it was loaded successfully
        cv2_image = cv2.imread(image_path)
        if cv2_image is None:
            raise ValueError(f"Failed to load image {image_path}. Check if it's a valid image format.")
            
        # compute the Laplacian of the image and then return the focus measure
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        return fm

    def create_temp_file_from_bytes(self, image_bytes):
        # Convert bytes to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_bytes)
            temp_file_path = temp_file.name
            
        return temp_file_path

    def variance_of_laplacian_from_bytes(self, image_bytes):
        try: 
            # Convert bytes to a numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            # Decode image
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                # If decoding fails, try the temporary file approach
                logger.debug("Direct decoding failed, using temp file approach")
                temp_file_path = self.create_temp_file_from_bytes(image_bytes)
                try:
                    fm = self.variance_of_laplacian_from_path(temp_file_path)
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                return fm
            
            # Process the image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            fm = cv2.Laplacian(gray, cv2.CV_64F).var()
            return fm
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise ValueError(f"Failed to process image bytes: {str(e)}")

    def is_blurry(self, fm, threshold=100):
        if fm < threshold:
            return "blurry"
        return "not blurry"

    def is_blurry_from_path(self, image_path, threshold=100):
        fm = self.variance_of_laplacian_from_path(image_path)
        return self.is_blurry(fm, threshold)

    def is_blurry_from_bytes(self, image_bytes, threshold=100):
        fm = self.variance_of_laplacian_from_bytes(image_bytes)
        return self.is_blurry(fm, threshold)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
        help="path to input image")
    ap.add_argument("-t", "--threshold", type=float, default=100.0,
        help="focus measures that fall below this value will be considered 'blurry'")
    args = vars(ap.parse_args())
    # convert image to bytes
    with open(args["image"], "rb") as image_file:
        image_bytes = image_file.read()
    
    try:
        fm = BlurService().variance_of_laplacian_from_bytes(image_bytes)
        print(f"Focus measure: {fm}")
        print(BlurService().is_blurry(fm, args["threshold"]))
    except Exception as e:
        print(f"Error: {e}")

    # for imagePath in paths.list_images(args["images"]):
    #     fm = variance_of_laplacian(imagePath)
    #     text = "Blurry" if fm < args["threshold"] else "Not Blurry"
    #     cv2.putText(image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
    #     cv2.imshow("Image", image)
    #     key = cv2.waitKey(0) & 0xFF