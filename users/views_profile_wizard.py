from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from formtools.wizard.views import SessionWizardView
from .forms_profile import TherapistProfileForm
from .models_profile import TherapistProfile
from django.core.files.storage import FileSystemStorage
from django.conf import settings

# Load profile_fields.json and group fields by section
import json, os
from users.field_map import FIELD_MAP
PROFILE_FIELDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'profile_fields.json')
with open(PROFILE_FIELDS_PATH) as f:
    profile_fields = json.load(f)

sections = []
section_fields = {}
for field in profile_fields:
    section = field['section']
    if section not in sections:
        sections.append(section)
        section_fields[section] = []
    section_fields[section].append(field)

# Dynamically create a form for each section using FIELD_MAP
from django import forms
from .models_profile import TherapistProfile


class SectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input_classes = 'border border-[#BEE3DB] rounded-lg px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#89B0AE] bg-[#FAF9F9] text-[#555B6E] shadow-sm'
        base_select_classes = 'border border-[#BEE3DB] rounded-lg px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E] focus:outline-none focus:ring-2 focus:ring-[#FF9950] hover:border-[#FF9950] transition duration-150 ease-in-out shadow-sm appearance-none'
        base_checkbox_classes = 'h-4 w-4 text-[#89B0AE] focus:ring-[#89B0AE] border-[#BEE3DB] rounded'
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
        fields = []

section_form_classes = {}
for section, fields in section_fields.items():
    mapped_fields = []
    for f in fields:
        mapped = FIELD_MAP.get(f['field'])
        if mapped:
            if isinstance(mapped, list):
                mapped_fields.extend(mapped)
            else:
                mapped_fields.append(mapped)
    attrs = {'Meta': type('Meta', (), {'model': TherapistProfile, 'fields': mapped_fields})}
    section_form_classes[section] = type(f'{section.replace(" ", "")}Form', (SectionForm,), attrs)

FORMS = [(section, section_form_classes[section]) for section in sections]
TEMPLATES = "users/profile_wizard.html"

@method_decorator(login_required, name='dispatch')
class TherapistProfileWizard(SessionWizardView):
    def process_step(self, form):
        # Save partial data to TherapistProfile after each step
        user = self.request.user
        profile, _ = TherapistProfile.objects.get_or_create(user=user)
        for field, value in form.cleaned_data.items():
            setattr(profile, field, value)
        profile.save()
        # Set a flag in the session to show progress saved message
        self.request.session['profile_progress_saved'] = True
        return super().process_step(form)
    form_list = [form for _, form in FORMS]
    template_name = TEMPLATES
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'wizard_uploads'))

    def get_form_instance(self, step):
        user = self.request.user
        try:
            return TherapistProfile.objects.get(user=user)
        except TherapistProfile.DoesNotExist:
            return None

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_section = sections[int(self.steps.current)]
        context['section_title'] = current_section
        # Section description: first field with 'description' in section, else blank
        section_fields_list = section_fields[current_section]
        section_description = None
        for f in section_fields_list:
            if 'description' in f:
                section_description = f['description']
                break
        context['section_description'] = section_description or ''
        context['section_notes_list'] = [f.get('notes', '') for f in section_fields_list if f.get('notes')]
        # Show progress saved message if flag is set
        context['progress_saved'] = self.request.session.pop('profile_progress_saved', False)
        # Add choices for select/multiselect fields for Alpine.js
        for field in form.visible_fields():
            widget = field.field.widget
            if hasattr(widget, 'choices'):
                # Exclude the empty label if present
                choices = [c for c in widget.choices if c[0] != '']
                field.alpine_choices = [[str(c[0]), str(c[1])] for c in choices]
        # Defensive: ensure step_number and total_steps are always present and valid
        context['step_number'] = int(self.steps.step0) + 1 if hasattr(self.steps, 'step0') else 1
        context['total_steps'] = len(sections) if sections else 1
        context['progress_percent'] = int(((context['step_number'] - 1) / context['total_steps']) * 100) if context['total_steps'] > 0 else 0
        return context

    def done(self, form_list, **kwargs):
        user = self.request.user
        profile, created = TherapistProfile.objects.get_or_create(user=user)
        for form in form_list:
            for field, value in form.cleaned_data.items():
                setattr(profile, field, value)
        profile.save()
        user.onboarding_status = 'active'
        user.save(update_fields=['onboarding_status'])
        messages.success(self.request, 'Profile completed!')
        return redirect('dashboard')
