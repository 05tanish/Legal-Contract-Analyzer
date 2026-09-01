from django.db import models

class Contract(models.Model):
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="contracts/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    page_count = models.PositiveIntegerField(default=0)
    extraction_status = models.CharField(max_length=30, default="pending")
    latest_analysis = models.ForeignKey(
        "AnalysisRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    
    def __str__(self):
        return f"{self.original_filename} (ID: {self.id})"

class ContractPage(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    page_number = models.PositiveIntegerField()
    text = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('contract', 'page_number')
        
    def __str__(self):
        return f"Page {self.page_number} - {self.contract.original_filename}"

class ContractSummary(models.Model):
    contract = models.OneToOneField(
        Contract,
        on_delete=models.CASCADE,
        related_name="summary",
    )
    overview = models.TextField(blank=True)
    contract_type = models.CharField(max_length=255, blank=True)
    parties = models.JSONField(default=list)
    key_obligations = models.JSONField(default=list)
    key_restrictions = models.JSONField(default=list)
    payment_terms = models.JSONField(default=list)
    term_and_renewal = models.JSONField(default=list)
    termination_terms = models.JSONField(default=list)
    confidentiality_terms = models.JSONField(default=list)
    intellectual_property_terms = models.JSONField(default=list)
    liability_terms = models.JSONField(default=list)
    insurance_terms = models.JSONField(default=list)
    governing_law_terms = models.JSONField(default=list)
    important_dates = models.JSONField(default=list)
    notable_risks = models.JSONField(default=list)
    missing_or_unclear_items = models.JSONField(default=list)
    summary_text = models.TextField(blank=True)
    model_version = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SummaryEvidence(models.Model):
    summary = models.ForeignKey(
        ContractSummary,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    section_name = models.CharField(max_length=255)
    page_number = models.PositiveIntegerField()
    text = models.TextField()
    score = models.FloatField(null=True, blank=True)

class AnalysisRun(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="analysis_runs",
    )
    model_version = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=30, default="pending")
    total_score = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    pages_analyzed = models.PositiveIntegerField(default=0)
    clauses_detected = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

class DetectedClause(models.Model):
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="detected_clauses",
    )
    clause_key = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    risk_weight = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    pages = models.JSONField(default=list)

class Evidence(models.Model):
    detected_clause = models.ForeignKey(
        DetectedClause,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    page_number = models.PositiveIntegerField()
    text = models.TextField()
    score = models.FloatField(null=True, blank=True)
