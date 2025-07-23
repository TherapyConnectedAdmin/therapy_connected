from django.db import models
from django.conf import settings


# Lookup models
class LicenseType(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class StateBoard(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class TelehealthPlatform(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class CityCounty(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class ZipCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    def __str__(self): return self.code

class PracticeAreaTag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class TreatmentApproach(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class ClientPopulation(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class Language(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class ProfessionalAssociation(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class Insurance(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class MultilingualMaterial(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

# TherapistProfile model
class TherapistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Basic Information
    full_name = models.CharField(max_length=128)
    credentials = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128, blank=True)
    tagline = models.CharField(max_length=256, blank=True)
    short_bio = models.TextField()
    # License & Verification
    license_number = models.CharField(max_length=64)
    license_type = models.ForeignKey(LicenseType, on_delete=models.SET_NULL, null=True)
    issuing_state_board = models.ForeignKey(StateBoard, on_delete=models.SET_NULL, null=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    license_verified = models.BooleanField(default=False)
    license_upload = models.FileField(upload_to='licenses/', blank=True, null=True)
    # Location & Contact
    primary_office_address = models.CharField(max_length=256)
    additional_locations = models.TextField(blank=True)
    phone_number = models.CharField(max_length=32)
    email_address = models.EmailField()
    website_url = models.URLField(blank=True)
    contact_form_toggle = models.BooleanField(default=True)
    # Service Modalities & Availability
    in_person_sessions = models.BooleanField(default=True)
    telehealth = models.BooleanField(default=True)
    telehealth_platforms = models.ManyToManyField(TelehealthPlatform, blank=True)
    office_hours = models.CharField(max_length=128, blank=True)
    external_scheduling_link = models.URLField(blank=True)
    secure_document_upload = models.BooleanField(default=False)
    # Areas Served
    cities_counties = models.ManyToManyField(CityCounty, blank=True)
    zip_codes = models.ManyToManyField(ZipCode, blank=True)
    # Specialties & Practice Details
    practice_areas_tags = models.ManyToManyField(PracticeAreaTag)
    treatment_approaches = models.ManyToManyField(TreatmentApproach, blank=True)
    client_populations = models.ManyToManyField(ClientPopulation, blank=True)
    languages_spoken = models.ManyToManyField(Language, blank=True)
    trauma_informed_training = models.BooleanField(default=False)
    neurodiversity_training = models.BooleanField(default=False)
    # Media & Branding
    profile_photo = models.ImageField(upload_to='profile_photos/')
    intro_video_url = models.URLField(blank=True)
    practice_logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    certificate_logos = models.ImageField(upload_to='certificates/', blank=True, null=True)
    # Education & Credentials
    degrees_institutions = models.CharField(max_length=256, blank=True)
    graduation_years = models.CharField(max_length=32, blank=True)
    professional_associations = models.ManyToManyField(ProfessionalAssociation, blank=True)
    continuing_ed_certifications = models.CharField(max_length=256, blank=True)
    # Pricing & Policies
    session_fee_package_rates = models.CharField(max_length=128)
    insurances_accepted = models.ManyToManyField(Insurance, blank=True)
    sliding_scale_scholarship = models.BooleanField(default=False)
    sliding_scale_description = models.CharField(max_length=256, blank=True)
    free_consultation_offer = models.BooleanField(default=False)
    cancellation_policy = models.TextField(blank=True)
    # Accessibility & Inclusivity
    wheelchair_access = models.BooleanField(default=False)
    wheelchair_access_description = models.CharField(max_length=256, blank=True)
    multilingual_materials = models.ManyToManyField(MultilingualMaterial, blank=True)
    # Technology & Tools
    client_portal_demo_link = models.URLField(blank=True)
    digital_homework_worksheets = models.FileField(upload_to='homework/', blank=True, null=True)
    # Professional Development & Community
    publications_books_podcasts = models.CharField(max_length=256, blank=True)
    workshops_group_programs = models.CharField(max_length=256, blank=True)
    pro_bono_community_outreach = models.BooleanField(default=False)
    pro_bono_description = models.CharField(max_length=256, blank=True)
    memberships_awards = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.full_name
