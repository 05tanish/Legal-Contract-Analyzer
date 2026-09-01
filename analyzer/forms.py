from django import forms
from .models import Contract
import os

class ContractUploadForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["file"]
        
    def clean_file(self):
        file = self.cleaned_data.get('file', False)
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            if ext != '.pdf':
                raise forms.ValidationError("Please upload a PDF contract.")
            
            # Simple size limit: 50MB
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 50MB.")
        else:
            raise forms.ValidationError("Please upload a file.")
            
        return file
