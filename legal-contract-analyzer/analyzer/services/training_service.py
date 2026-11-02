import os
import pandas as pd
import ast
import joblib
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.svm import LinearSVC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import f1_score
from django.conf import settings
from .preprocessing_service import preprocess_text

logger = logging.getLogger(__name__)

def train_and_save_model(csv_path, output_dir):
    """
    Retrains the NLP pipeline safely into a temporary/target directory.
    Re-uses the dataset parsing logic from the notebook.
    Returns evaluation metrics.
    """
    logger.info(f"Loading dataset from {csv_path}")
    df = pd.read_csv(csv_path)
    
    # 1. Melt dataset like in the notebook
    clause_cols = [col for col in df.columns if col + "_answer" in df.columns]
    id_vars = ['filename'] if 'filename' in df.columns else [df.columns[0]]
    
    melted_df = df.melt(id_vars=id_vars, value_vars=clause_cols, var_name='clause', value_name='snippets_str')
    
    def parse_snippets(val):
        if pd.isna(val) or val == '[]' or val == '':
            return []
        try:
            if isinstance(val, str) and val.startswith('['):
                return ast.literal_eval(val)
            return [str(val)]
        except:
            return []

    melted_df['snippets_list'] = melted_df['snippets_str'].apply(parse_snippets)
    exploded = melted_df.explode('snippets_list').rename(columns={'snippets_list': 'text', 'filename': 'document_id'})
    
    # Clean texts
    df_clean = exploded.dropna(subset=['text']).copy()
    df_clean['text'] = df_clean['text'].astype(str).str.strip()
    df_clean = df_clean[df_clean['text'] != ""]
    
    # Group by snippet
    processed_df = df_clean.groupby(['document_id', 'text'])['clause'].apply(lambda x: list(set(x))).reset_index()
    processed_df.rename(columns={'clause': 'labels'}, inplace=True)
    
    # Preprocess text
    processed_df['cleaned_text'] = processed_df['text'].apply(preprocess_text)
    
    # Simple Train Test Split (Random 80/20 for MVP retraining)
    # The actual notebook used GroupShuffleSplit, but standard train_test_split is fine here
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(processed_df['cleaned_text'], processed_df['labels'], test_size=0.2, random_state=42)
    
    # Encoding
    mlb = MultiLabelBinarizer()
    Y_train = mlb.fit_transform(y_train)
    Y_test = mlb.transform(y_test)
    
    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    
    # Train Best Model (Linear SVM via OneVsRest)
    logger.info("Training Linear SVM (OneVsRest)...")
    clf = OneVsRestClassifier(LinearSVC(random_state=42, class_weight='balanced', dual='auto'))
    clf.fit(X_train_vec, Y_train)
    
    # Evaluate
    Y_pred = clf.predict(X_test_vec)
    macro_f1 = f1_score(Y_test, Y_pred, average='macro')
    micro_f1 = f1_score(Y_test, Y_pred, average='micro')
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save artifacts
    logger.info(f"Saving artifacts to {output_dir}")
    joblib.dump(clf, os.path.join(output_dir, 'best_model.joblib'))
    joblib.dump(vectorizer, os.path.join(output_dir, 'tfidf_vectorizer.joblib'))
    joblib.dump(mlb, os.path.join(output_dir, 'clause_categories.joblib'))
    
    # Save default risk config so the risk engine knows about all clauses
    # using the default config as a base
    from .risk_service import DEFAULT_RISK_WEIGHTS
    joblib.dump(DEFAULT_RISK_WEIGHTS, os.path.join(output_dir, 'risk_config.joblib'))
    
    return {
        "macro_f1": macro_f1,
        "micro_f1": micro_f1,
        "classes": len(mlb.classes_)
    }
