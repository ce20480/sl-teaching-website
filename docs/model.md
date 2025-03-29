# Sign Language Detection Model Integration

This document explains how we integrated the `sl_detection` package into our ASL teaching application to enable real-time sign language translation.

## Model Overview

We use a custom-built Sign Language Detection package (`sl_detection`) to power our translation capabilities. This package implements a coordinate-based neural network model that processes hand landmarks to predict ASL letters.

- **Repository**: [https://github.com/ce20480/SignLanguageDetection](https://github.com/ce20480/SignLanguageDetection)
- **PyPI Package**: [https://pypi.org/project/sl-detection/](https://pypi.org/project/sl-detection/)

## Architecture

Our model integration follows a three-tier architecture:

1. **Frontend (React/TypeScript)**: Handles hand landmark detection using MediaPipe
2. **Express Middleware**: Routes API requests between the frontend and backend
3. **Python Backend (FastAPI)**: Processes landmarks and generates predictions using our model

![ASL Detection Architecture](../assets/images/architecture.png)

## Integration with `sl_detection`

We've integrated the `sl_detection` package through our `ASLService` class, which acts as a bridge between our API routes and the ML components:

```python
# backend/python/src/services/ml/asl_service.py
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
```

## Key Components

The integration leverages several key components from the `sl_detection` package:

### 1. HandDetector

Responsible for detecting hands and extracting landmarks from images. In our application, we use MediaPipe on the frontend for this task to improve performance.

### 2. ASLPreprocessor

Processes hand landmarks to prepare them for the model:

- Normalizes coordinates to ensure consistent scaling
- Flattens 3D landmarks into a 1D feature vector

### 3. CoordsModel

A neural network model that takes processed landmarks and outputs ASL letter predictions:

- Input: 63 features (21 landmarks × 3 coordinates)
- Output: Letter predictions with confidence scores

### 4. ASLPipeline

Ties everything together into a cohesive workflow:

- Takes landmarks from the frontend
- Preprocesses them using the ASLPreprocessor
- Passes them through the CoordsModel
- Returns predictions and confidence scores

## Data Flow

1. Frontend detects hand landmarks using MediaPipe
2. Landmarks are sent to the backend API
3. Backend processes landmarks through the ASLService
4. Predictions are returned to the frontend for display

## Model Training and Contribution

Our application includes a contribution feature that allows users to add training data:

```python
def store_contribution(self, landmarks, label):
    """Store contributed landmark data for future model training"""
    return self.contribution_manager.store_contribution(landmarks, label)
```

This data is stored for future model training, enabling continuous improvement of our recognition accuracy.

## Updating the Package

To update the `sl_detection` package:

1. **Add a Collaborator on PyPI**:

   - Go to the package page on PyPI: [https://pypi.org/project/sl-detection/](https://pypi.org/project/sl-detection/)
   - Click "Manage" on the project
   - Under "Collaborators", invite colleagues by their PyPI username
   - Choose role: Maintainer (can upload and manage releases)

2. **Update Process**:

   - Clone the repository: `git clone https://github.com/ce20480/SignLanguageDetection.git`
   - Update the version in `setup.py` and `sl_detection/__init__.py`
   - Build the new version:
     ```bash
     pip install build twine
     rm -rf dist/
     python -m build
     twine upload dist/*
     ```
   - Log in with PyPI credentials when prompted

3. **Update in Project**:
   - Update the dependency in your project: `pip install sl-detection==X.Y.Z`
   - Or use Poetry: `poetry add sl-detection@^X.Y.Z`

## Customizing the Model

To customize the model parameters:

1. Adjust the `HandDetector` confidence threshold for different detection sensitivity
2. Modify the `min_confidence` parameter in `SignLanguagePredictor` to filter predictions
3. Update the model path in `settings.model_path` to use a different model file

See the [sl_detection repository](https://github.com/ce20480/SignLanguageDetection) for more customization options.
