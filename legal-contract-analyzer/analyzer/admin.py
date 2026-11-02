from django.contrib import admin
from .models import (
    Contract, ContractPage, ContractSummary, SummaryEvidence,
    AnalysisRun, DetectedClause, Evidence
)

class ContractPageInline(admin.TabularInline):
    model = ContractPage
    extra = 0
    fields = ('page_number', 'text')
    readonly_fields = ('text',)

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'uploaded_at', 'page_count', 'extraction_status')
    list_filter = ('extraction_status',)
    inlines = [ContractPageInline]

@admin.register(ContractSummary)
class ContractSummaryAdmin(admin.ModelAdmin):
    list_display = ('contract', 'contract_type', 'model_version', 'updated_at')

@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ('contract', 'status', 'risk_level', 'total_score', 'created_at')
    list_filter = ('status', 'risk_level')

@admin.register(DetectedClause)
class DetectedClauseAdmin(admin.ModelAdmin):
    list_display = ('analysis_run', 'display_name', 'risk_level', 'risk_weight')
    list_filter = ('risk_level',)

admin.site.register(SummaryEvidence)
admin.site.register(Evidence)
