import os
import shutil
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from analyzer.services.training_service import train_and_save_model

class Command(BaseCommand):
    help = 'Retrains the NLP models and replaces the active artifacts safely.'

    def add_arguments(self, parser):
        parser.add_argument('--data', type=str, default='data/CUAD_combined.csv',
                            help='Path to the CUAD CSV dataset.')
        parser.add_argument('--output', type=str, default='models/',
                            help='Directory to store the final model files.')

    def handle(self, *args, **options):
        data_path = os.path.join(settings.BASE_DIR, options['data'])
        final_output_dir = os.path.join(settings.BASE_DIR, options['output'])
        
        if not os.path.exists(data_path):
            self.stdout.write(self.style.ERROR(f"Dataset not found at: {data_path}"))
            return
            
        temp_dir = os.path.join(settings.BASE_DIR, 'models_temp')
        
        self.stdout.write(self.style.NOTICE('Loading CUAD dataset...'))
        self.stdout.write(self.style.NOTICE('Cleaning text and preparing labels...'))
        
        try:
            metrics = train_and_save_model(data_path, temp_dir)
            
            self.stdout.write(self.style.SUCCESS('Evaluating models...'))
            self.stdout.write(self.style.SUCCESS(f"Macro F1: {metrics['macro_f1']:.4f}"))
            self.stdout.write(self.style.SUCCESS(f"Micro F1: {metrics['micro_f1']:.4f}"))
            self.stdout.write(self.style.SUCCESS(f"Number of Clause Classes: {metrics['classes']}"))
            
            # Validation Step
            expected_files = ['best_model.joblib', 'tfidf_vectorizer.joblib', 'clause_categories.joblib', 'risk_config.joblib']
            missing = [f for f in expected_files if not os.path.exists(os.path.join(temp_dir, f))]
            
            if missing:
                raise Exception(f"Missing expected output artifacts: {missing}")
                
            # Safely move from temp to final
            os.makedirs(final_output_dir, exist_ok=True)
            for f in expected_files:
                shutil.move(os.path.join(temp_dir, f), os.path.join(final_output_dir, f))
                
            # Save Report
            report_path = os.path.join(final_output_dir, 'training_report.json')
            import datetime
            report = {
                "macro_f1": metrics['macro_f1'],
                "micro_f1": metrics['micro_f1'],
                "training_timestamp": datetime.datetime.now().isoformat(),
                "dataset_path": data_path
            }
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=4)
                
            self.stdout.write(self.style.SUCCESS('Saving model artifacts...'))
            self.stdout.write(self.style.SUCCESS('Training completed successfully. New active models are in place.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Training failed: {e}"))
            self.stdout.write(self.style.WARNING("Active models were not modified."))
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
