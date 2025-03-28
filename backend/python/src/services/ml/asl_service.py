# backend/services/asl_service.py
import base64
import os
import string
import datetime
import json

import cv2
import numpy as np
from asl import ASLPreprocessor

# Import from your ASL package
from asl import HandDetector
from asl import CoordsModel
from asl import ASLPipeline


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

        # Create letter mapping
        self.letter_mapping = self._create_letter_mapping()

    def _create_letter_mapping(self):
        # Map class indices to letters
        mapping = {0: "0"}  # Class 0 is blank/neutral
        for i, letter in enumerate(string.ascii_uppercase):
            mapping[i + 1] = letter
        return mapping

    def process_image(self, image_data):
        """Process base64 encoded image and return prediction"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, flags=cv2.IMREAD_COLOR)

            if image is None:
                return {"error": "Invalid image data"}

            # Process image through pipeline
            prediction, landmarks, _ = self.pipeline.process_image(image)

            if prediction is None:
                return {"detected": False}

            # Get letter from class index
            class_idx = prediction["class_index"]
            letter = self.letter_mapping.get(class_idx, f"Unknown ({class_idx})")

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
            
            # Print shape information for debugging
            print(f"Landmark array shape: {landmarks_array.shape}")
            
            # Preprocess landmarks using the available methods
            if self.preprocessor.normalize:
                normalized_landmarks = self.preprocessor.normalize_landmarks(landmarks_array)
            else:
                normalized_landmarks = landmarks_array
            
            if self.preprocessor.flatten:
                preprocessed = self.preprocessor.flatten_landmarks(normalized_landmarks)
            else:
                preprocessed = normalized_landmarks
            
            # Print preprocessed shape
            print(f"Preprocessed shape: {preprocessed.shape}")
            
            # Get model prediction
            prediction = self.model.predict(preprocessed)
            
            # Debug: Print the prediction to see what's coming back
            print(f"Raw prediction: {prediction}")
            print(f"Prediction type: {type(prediction)}")
            
            # Handle different prediction formats
            if isinstance(prediction, dict) and 'class_index' in prediction:
                # Our model already returns a dict with class_index
                label_idx = prediction['class_index']
                confidence = prediction['confidence']
            elif isinstance(prediction, (np.ndarray, list)) and len(prediction) > 0:
                # Model returns array of probabilities
                label_idx = np.argmax(prediction)
                confidence = float(prediction[label_idx])
            else:
                # Unexpected format
                return {
                    "error": f"Unexpected prediction format: {prediction}"
                }
            
            # Map to letter
            letter = self.letter_mapping.get(label_idx, f"Unknown ({label_idx})")
            
            # Ensure confidence is a simple float for JSON serialization
            if isinstance(confidence, (np.float32, np.float64)):
                confidence = float(confidence)
            
            return {
                "letter": letter,
                "confidence": confidence,
                "landmarks": landmarks.copy()  # Copy to ensure it's a simple list
            }
        except Exception as e:
            print(f"Error processing landmarks: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def store_contribution(self, landmarks, label):
        """Store contributed landmark data for future model training"""
        try:
            # Create directory if it doesn't exist
            contributions_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'contributions')
            os.makedirs(contributions_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{label}_{timestamp}.json"
            filepath = os.path.join(contributions_dir, filename)
            
            # Store the data
            data = {
                "landmarks": landmarks,
                "label": label,
                "timestamp": timestamp,
                "source": "user_contribution"
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error storing contribution: {e}")
            return False
