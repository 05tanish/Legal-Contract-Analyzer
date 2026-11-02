import os
import django
from django.core.files import File

# 1. Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 2. Create Dummy PDF
import pymupdf
doc = pymupdf.open()
page = doc.new_page()
text = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is made and entered into on this 1st day of January 2025, by and between Company LLC ("Employer") and John Doe ("Employee").

1. Term. The term of this Agreement shall commence on the Effective Date and shall continue for a period of one (1) year.

2. Non-Compete. During the term of this Agreement and for a period of two (2) years thereafter, Employee agrees not to engage in any business that competes with Employer.

3. Exclusivity. Employee agrees to work exclusively for Employer.

4. Governing Law. This Agreement shall be governed by the laws of the State of California.

5. Insurance. Employer shall maintain general liability insurance in the amount of $1,000,000.
"""
page.insert_text((50, 50), text, fontsize=12)
doc.save("sample_contract.pdf")

# 3. Test Pipeline
from analyzer.models import Contract, ContractPage
from analyzer.services.pdf_service import extract_pdf_pages
from analyzer.services.chunking_service import create_chunks
from analyzer.services.model_service import ModelManager
from analyzer.services.risk_service import aggregate_clauses_and_calculate_risk
from analyzer.services.summarization_service import generate_summary

print("Starting test...")
contract = Contract(original_filename="sample_contract.pdf")
with open("sample_contract.pdf", "rb") as f:
    contract.file.save("sample_contract.pdf", File(f))
contract.save()

pages_data = extract_pdf_pages(contract.file.path)
for p in pages_data:
    ContractPage.objects.create(contract=contract, page_number=p['page'], text=p['text'])

print(f"Extracted {len(pages_data)} pages.")

model_mgr = ModelManager()
print(f"Model version: {model_mgr.get_version()}")

chunks = create_chunks(pages_data)
chunks_with_preds = model_mgr.predict_chunks(chunks)

total_score, risk_level, aggregated_clauses = aggregate_clauses_and_calculate_risk(chunks_with_preds)
print(f"Total Risk Score: {total_score}, Level: {risk_level}")
print("Detected Clauses:", list(aggregated_clauses.keys()))

summary_data = generate_summary(chunks_with_preds, aggregated_clauses)
print("Summary Overview:", summary_data["overview"])

print("Test completed successfully.")
