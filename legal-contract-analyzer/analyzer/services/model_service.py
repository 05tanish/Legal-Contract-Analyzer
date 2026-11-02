import os
import joblib
import logging
from django.conf import settings
from .preprocessing_service import preprocess_text

logger = logging.getLogger(__name__)

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.vectorizer = None
            cls._instance.mlb = None
            cls._instance.model_version = None
        return cls._instance

    def load_artifacts(self):
        if self.model is not None and self.vectorizer is not None and self.mlb is not None:
            return  # Already loaded

        base_path = os.path.join(settings.BASE_DIR, 'models')
        model_path = os.path.join(base_path, 'best_model.joblib')
        vectorizer_path = os.path.join(base_path, 'tfidf_vectorizer.joblib')
        mlb_path = os.path.join(base_path, 'clause_categories.joblib')

        try:
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            self.mlb = joblib.load(mlb_path)
            
            # Simple versioning: modified time of the model
            mtime = os.path.getmtime(model_path)
            import datetime
            dt = datetime.datetime.fromtimestamp(mtime)
            self.model_version = f"best_model_{dt.strftime('%Y_%m_%d_%H%M%S')}"
            
            logger.info(f"Loaded NLP model artifacts. Version: {self.model_version}")
        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            raise RuntimeError("Model files were not found or corrupted.") from e

    def get_version(self):
        self.load_artifacts()
        return self.model_version

    def predict_chunks(self, chunks, threshold=0.5):
        """
        Takes a list of chunk dicts `[{'page': 1, 'text': '...'}]`.
        Returns the original list with a 'detected_clauses' key added to each.
        """
        if not chunks:
            return []

        self.load_artifacts()
        
        # 1. Preprocess
        raw_texts = [c['text'] for c in chunks]
        cleaned_texts = [preprocess_text(t) for t in raw_texts]

        # 2. Vectorize
        X = self.vectorizer.transform(cleaned_texts)

        # 3. Predict
        # We check if it supports predict_proba or decision_function
        predictions_matrix = None
        
        if hasattr(self.model, "predict_proba"):
            probas = self.model.predict_proba(X)
            # If probas is a list (often from OneVsRest with non-sparse targets)
            import numpy as np
            if isinstance(probas, list):
                predictions_matrix = np.array([p[:, 1] for p in probas]).T >= threshold
            else:
                predictions_matrix = probas >= threshold
        elif hasattr(self.model, "decision_function"):
            scores = self.model.decision_function(X)
            predictions_matrix = scores > 0
        else:
            predictions_matrix = self.model.predict(X)

        # 4. Convert Binary Matrix to Label Names
        # If mlb is actually a MultiLabelBinarizer
        if hasattr(self.mlb, "inverse_transform"):
            label_tuples = self.mlb.inverse_transform(predictions_matrix)
            for i, chunk in enumerate(chunks):
                chunk['detected_clauses'] = list(label_tuples[i])
        else:
            # Fallback if clause_categories is just a list of strings
            import numpy as np
            clause_names = np.array(self.mlb)
            for i, chunk in enumerate(chunks):
                # Ensure predictions_matrix[i] is boolean
                row_mask = np.array(predictions_matrix[i], dtype=bool)
                chunk['detected_clauses'] = clause_names[row_mask].tolist()

        return chunks
