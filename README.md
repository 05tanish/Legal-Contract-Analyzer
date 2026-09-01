# Legal Contract Risk Analyzer

A fully functional MVP application using Django that provides ML-based legal contract analysis, clause detection, deterministic extractive summarization, and heuristic risk scoring. Built for the CUAD dataset model pipeline.

## Features
- **PDF Extraction**: Upload a PDF and extract text while retaining page numbers using PyMuPDF.
- **Contract Summarization**: Generates an extractive, plain-language summary based on legal keywords and clause detections.
- **NLP Clause Detection**: Uses a pre-trained ML model (Linear SVM via OneVsRest) to detect clauses in document chunks.
- **Heuristic Risk Engine**: Calculates a custom risk score and risk level based on the severity of the detected clauses.
- **Evidence Referencing**: Highlights exactly which page and text triggered a risk or summary section.
- **Retraining Workflow**: Includes a dedicated management command to safely retrain the model and save new artifacts without crashing the live server.
- **Secure Storage**: Stores all metadata, extraction history, and analysis runs inside NeonDB (or local PostgreSQL/SQLite fallback).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Configure your variables:
```env
SECRET_KEY=replace-this-secret-key-in-production
DEBUG=True
DATABASE_URL=postgresql://username:password@host/database?sslmode=require
ALLOWED_HOSTS=127.0.0.1,localhost
```
*Note: If `DATABASE_URL` is empty, it safely falls back to a local SQLite database for development.*

## Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

## Run the Application

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` to use the analyzer.

## Retrain the NLP Pipeline

You can securely retrain the active model with a new dataset by using the training command:

```bash
python manage.py train_model --data data/CUAD_combined.csv --output models/
```

This command will:
1. Parse and melt the dataset.
2. Train Candidate Models (Linear SVM).
3. Validate artifacts.
4. Replace the live models only on success.
5. Save a `training_report.json` with F1 metrics.

## Limitations & Disclaimers
- **Text-based PDFs only**: Scanned/image-only PDFs require OCR (not included).
- **Not Legal Advice**: This is a heuristic tool. The generated risk scores and summaries do not constitute legal advice.
- **Extractive Summary**: Summarization extracts sentences based on density of legal keywords; it does not "understand" legal intent.
- **Storage**: Uploaded contracts are stored in the server's configured storage and database. Do not upload strictly confidential information unless deployed on a compliant environment.
