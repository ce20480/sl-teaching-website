# Simplified asl_service.py
import os
import numpy as np
from sl_detection import ASLPreprocessor, HandDetector, CoordsModel, ASLPipeline
from sl_detection import ContributionManager, create_asl_letter_mapping, get_letter_from_prediction

class ASLService:
    def __init__(self, model_path):
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
            
            prediction, landmarks, _ = self.pipeline.process_image(image)
            
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
            # Convert landmarks to numpy array
            landmarks_array = np.array(landmarks).reshape(-1, 3)
            
            # Process through pipeline
            prediction = self.pipeline.process_landmarks(landmarks_array)
            
            # Get letter from prediction
            letter = get_letter_from_prediction(prediction, self.letter_mapping)
            
            return {
                "letter": letter,
                "confidence": float(prediction["confidence"]),
                "landmarks": landmarks
            }
        except Exception as e:
            print(f"Error processing landmarks: {e}")
            return {"error": str(e)}

    def store_contribution(self, landmarks, label):
        """Store contributed landmark data for future model training"""
        return self.contribution_manager.store_contribution(landmarks, label)