import os
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import (
    Contract, ContractPage, ContractSummary, SummaryEvidence,
    AnalysisRun, DetectedClause, Evidence
)
from .forms import ContractUploadForm

from .services.pdf_service import extract_pdf_pages
from .services.chunking_service import create_chunks
from .services.model_service import ModelManager
from .services.risk_service import aggregate_clauses_and_calculate_risk
from .services.summarization_service import generate_summary

def upload_contract(request):
    if request.method == 'POST':
        form = ContractUploadForm(request.POST, request.FILES)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.original_filename = request.FILES['file'].name
            contract.save()
            
            # Extract PDF Text synchronously for MVP
            try:
                pages_data = extract_pdf_pages(contract.file.path)
                if not pages_data:
                    contract.extraction_status = 'no_text'
                    contract.save()
                    messages.warning(request, "No readable text found. This MVP currently works with text-based PDFs.")
                else:
                    pages_to_create = [
                        ContractPage(contract=contract, page_number=p['page'], text=p['text'])
                        for p in pages_data
                    ]
                    ContractPage.objects.bulk_create(pages_to_create)
                    
                    contract.page_count = len(pages_data)
                    contract.extraction_status = 'completed'
                    contract.save()
                    
            except Exception as e:
                contract.extraction_status = 'failed'
                contract.save()
                messages.error(request, "Failed to extract text from PDF.")
                
            return redirect('contract_detail', contract_id=contract.id)
    else:
        form = ContractUploadForm()
        
    return render(request, 'analyzer/upload.html', {'form': form})


def contract_detail(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    return render(request, 'analyzer/contract_detail.html', {'contract': contract})

@require_POST
def analyze_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    
    if contract.extraction_status != 'completed':
        messages.error(request, "Cannot analyze contract. Text extraction failed or found no text.")
        return redirect('contract_detail', contract_id=contract.id)
        
    run = AnalysisRun.objects.create(
        contract=contract,
        status='running'
    )
    
    try:
        with transaction.atomic():
            model_mgr = ModelManager()
            model_version = model_mgr.get_version()
            run.model_version = model_version
            
            # Load pages
            pages = contract.pages.all().order_by('page_number')
            pages_data = [{"page": p.page_number, "text": p.text} for p in pages]
            
            if not pages_data:
                raise ValueError("No pages found in database for this contract.")
                
            # Create chunks
            chunks = create_chunks(pages_data)
            
            # Predict
            chunks_with_preds = model_mgr.predict_chunks(chunks)
            
            # Calculate Risk
            total_score, risk_level, aggregated_clauses = aggregate_clauses_and_calculate_risk(chunks_with_preds)
            
            # Generate Summary
            summary_data = generate_summary(chunks_with_preds, aggregated_clauses)
            
            # Save Analysis Results
            run.total_score = total_score
            run.risk_level = risk_level
            run.pages_analyzed = len(pages_data)
            run.clauses_detected = len(aggregated_clauses)
            run.status = 'completed'
            run.save()
            
            for c_key, c_data in aggregated_clauses.items():
                d_clause = DetectedClause.objects.create(
                    analysis_run=run,
                    clause_key=c_key,
                    display_name=c_data['display_name'],
                    risk_weight=c_data['risk_weight'],
                    risk_level=c_data['risk_level'],
                    pages=c_data['pages']
                )
                
                evidence_objects = [
                    Evidence(
                        detected_clause=d_clause,
                        page_number=ev['page'],
                        text=ev['text'],
                        score=ev.get('score')
                    ) for ev in c_data['evidence']
                ]
                Evidence.objects.bulk_create(evidence_objects)
                
            # Update Contract latest analysis
            contract.latest_analysis = run
            contract.save()
            
            # Save/Update Summary
            summary_obj, created = ContractSummary.objects.get_or_create(contract=contract)
            summary_obj.overview = summary_data["overview"]
            summary_obj.contract_type = summary_data["contract_type"]
            summary_obj.parties = summary_data["parties"]
            summary_obj.key_obligations = summary_data["key_obligations"]
            summary_obj.key_restrictions = summary_data["key_restrictions"]
            summary_obj.payment_terms = summary_data["payment_terms"]
            summary_obj.term_and_renewal = summary_data["term_and_renewal"]
            summary_obj.termination_terms = summary_data["termination_terms"]
            summary_obj.confidentiality_terms = summary_data["confidentiality_terms"]
            summary_obj.intellectual_property_terms = summary_data["intellectual_property_terms"]
            summary_obj.liability_terms = summary_data["liability_terms"]
            summary_obj.insurance_terms = summary_data["insurance_terms"]
            summary_obj.governing_law_terms = summary_data["governing_law_terms"]
            summary_obj.important_dates = summary_data["important_dates"]
            summary_obj.notable_risks = summary_data["notable_risks"]
            summary_obj.missing_or_unclear_items = summary_data["missing_or_unclear_items"]
            summary_obj.model_version = model_version
            summary_obj.save()
            
            # Clear old summary evidence if any, then bulk create new
            SummaryEvidence.objects.filter(summary=summary_obj).delete()
            sum_ev_objs = [
                SummaryEvidence(
                    summary=summary_obj,
                    section_name=ev["section_name"],
                    page_number=ev["page_number"],
                    text=ev["text"],
                    score=ev["score"]
                ) for ev in summary_data["evidence_links"]
            ]
            SummaryEvidence.objects.bulk_create(sum_ev_objs)
            
            messages.success(request, "Analysis completed successfully.")
            
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Analysis failed: {traceback.format_exc()}")
        run.status = 'failed'
        run.error_message = str(e)
        run.save()
        messages.error(request, f"Analysis failed: {str(e)}")
        
    return redirect('contract_detail', contract_id=contract.id)

def contract_text(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    page_num = request.GET.get('page', 1)
    
    try:
        page_num = int(page_num)
    except ValueError:
        page_num = 1
        
    page = contract.pages.filter(page_number=page_num).first()
    return render(request, 'analyzer/contract_text.html', {
        'contract': contract,
        'page': page,
        'current_page': page_num,
        'total_pages': contract.page_count
    })
