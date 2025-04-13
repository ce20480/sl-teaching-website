# Simplified asl_service.py
import os
import numpy as np
from sl_detection import ASLPreprocessor, HandDetector, CoordsModel, ASLPipeline
from sl_detection import ContributionManager, create_asl_letter_mapping, get_letter_from_prediction
from ...core.config import settings
import argparse
import logging

logger = logging.getLogger(__name__)

class ASLService:
    def __init__(self, model_path=settings.MODEL_PATH):
        # Check if model exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")

        # Initialize components
        self.detector = HandDetector(min_detection_confidence=0.7)
        self.preprocessor = ASLPreprocessor(normalize=True, flatten=True)
        self.model = CoordsModel.load(model_path)
        self.pipeline = ASLPipeline(self.detector, self.preprocessor, self.model)
        self.contribution_manager = ContributionManager()
        
        # Create letter mapping
        self.letter_mapping = create_asl_letter_mapping()

    def process_image(self, image_data):
        """Process base64 encoded image and return prediction"""
        try:
            # Decode and process image through pipeline
            # [Your existing image decoding code]
            
            prediction, landmarks, _ = self.pipeline.process_image(image_data)
            
            if prediction is None:
                return {"detected": False}
                
            # Get letter from prediction
            letter = get_letter_from_prediction(prediction, self.letter_mapping)
            
            # Convert landmarks to list for JSON serialization
            landmarks_list = None
            if landmarks is not None:
                landmarks_list = landmarks.tolist()
                
            return {
                "detected": True,
                "letter": letter,
                "confidence": float(prediction["confidence"]),
                "landmarks": landmarks_list,
            }
        except Exception as e:
            return {"error": str(e)}

    def process_landmarks(self, landmarks):
        """Process hand landmarks and return prediction"""
        try:
            if landmarks is None:
                return {
                    "success": False,
                    "message": "No landmarks provided"
                }
                
            # Convert landmarks to numpy array
            try:
                landmarks_array = np.array(landmarks)
                
                # Check if we have the right shape
                if landmarks_array.size == 1:
                    return {
                        "success": False,
                        "message": "Invalid landmarks format: Empty or single value"
                    }
                
                # Ensure we have the correct shape (21 landmarks with 3 coordinates each)
                if len(landmarks_array) % 3 == 0:
                    # If flat array, reshape to (n, 3)
                    num_landmarks = len(landmarks_array) // 3
                    landmarks_array = landmarks_array.reshape(num_landmarks, 3)
                elif len(landmarks_array.shape) == 1:
                    # If it's still a 1D array but not divisible by 3, we have a problem
                    return {
                        "success": False,
                        "message": f"Invalid landmarks format: Cannot reshape array of size {landmarks_array.size} into landmarks"
                    }
            except Exception as reshape_error:
                return {
                    "success": False,
                    "message": f"Failed to process landmarks format: {str(reshape_error)}"
                }
            
            # Process through pipeline this function does not exist
            # prediction = self.pipeline.process_landmarks(landmarks_array)

            # Preprocess landmarks
            if self.preprocessor.normalize:
                normalized_landmarks = self.preprocessor.normalize_landmarks(landmarks_array)
            else:
                normalized_landmarks = landmarks_array
            
            if self.preprocessor.flatten:
                features = self.preprocessor.flatten_landmarks(normalized_landmarks)
            else:
                features = normalized_landmarks
            
            # Make prediction
            prediction = self.model.predict(features)
            
            # Get letter from prediction
            letter = get_letter_from_prediction(prediction, self.letter_mapping)
            
            # Calculate a confidence score for evaluation (0.0-1.0)
            confidence = float(prediction["confidence"])
            score = min(1.0, confidence / 0.7)  # Normalize to 0-1 scale
            
            # Ensure landmarks are returned as a flat list of floats, not a nested list
            # This is what the PredictionResponse model expects
            flat_landmarks = landmarks_array.flatten().tolist()
            
            return {
                "success": True,
                "letter": letter,
                "confidence": confidence,
                "score": score,
                "landmarks": flat_landmarks
            }
        except Exception as e:
            logger.error(f"Error processing landmarks: {e}")
            return {
                "success": False,
                "message": f"Error processing landmarks: {str(e)}"
            }

    def store_contribution(self, landmarks, label):
        """Store contributed landmark data for future model training"""
        return self.contribution_manager.store_contribution(landmarks, label)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
        help="path to input image")
    args = vars(ap.parse_args())
    # convert image to bytes
    with open(args["image"], "rb") as image_file:
        image_bytes = image_file.read()
    
    print(ASLService().process_image(image_bytes))
