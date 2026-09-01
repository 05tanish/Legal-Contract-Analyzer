from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_contract, name='upload'),
    path('contracts/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:contract_id>/analyze/', views.analyze_contract, name='analyze_contract'),
    path('contracts/<int:contract_id>/text/', views.contract_text, name='contract_text'),
]
