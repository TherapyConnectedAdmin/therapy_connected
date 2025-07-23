from django import forms
from .models_profile import TherapistProfile

class TherapistProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input_classes = 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E]'
        base_select_classes = 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E] focus:outline-none focus:ring-2 focus:ring-[#89B0AE] hover:border-[#89B0AE] transition duration-150 ease-in-out'
        base_checkbox_classes = 'h-4 w-4 text-[#89B0AE] focus:ring-[#89B0AE] border-gray-300 rounded'
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.TextInput) or isinstance(widget, forms.Textarea) or isinstance(widget, forms.EmailInput) or isinstance(widget, forms.URLInput):
                widget.attrs.setdefault('class', base_input_classes)
            elif isinstance(widget, forms.Select) or isinstance(widget, forms.SelectMultiple):
                widget.attrs.setdefault('class', base_select_classes)
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault('class', base_input_classes)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', base_checkbox_classes)
    class Meta:
        model = TherapistProfile
        exclude = ['user']
        widgets = {
            'short_bio': forms.Textarea(attrs={
                'rows': 3,
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E]'
            }),
            'tagline': forms.Textarea(attrs={
                'rows': 2,
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E]'
            }),
            'office_hours': forms.TextInput(attrs={
                'placeholder': 'e.g., M–F 9 am–5 pm',
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E]'
            }),
            'cancellation_policy': forms.Textarea(attrs={
                'rows': 3,
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E]'
            }),
            # Example for dropdowns/multi-selects:
            'license_type': forms.Select(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'issuing_state_board': forms.Select(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'practice_areas_tags': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'treatment_approaches': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'client_populations': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'languages_spoken': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'professional_associations': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'insurances_accepted': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'multilingual_materials': forms.SelectMultiple(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            # Example for file/image fields:
            'profile_photo': forms.ClearableFileInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'license_upload': forms.ClearableFileInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'practice_logo': forms.ClearableFileInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
            'certificate_logos': forms.ClearableFileInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'
            }),
        }
