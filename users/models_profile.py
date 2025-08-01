# NOTE: TherapistProfile is the canonical therapist model for all assignments (age groups, participant types, etc.).
# Legacy assignment tables may use 'therapist' as a ForeignKey, but all new relationships should use TherapistProfile for consistency.

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator

# ...existing code...

# Specialty lookup model
class SpecialtyLookup(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator

# TherapyType lookup model for types_of_therapy
class TherapyType(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self): return self.name

# Selection model for therapist therapy types
class TherapyTypeSelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='types_of_therapy')
    therapy_type = models.ForeignKey('TherapyType', on_delete=models.CASCADE)
    def __str__(self): return self.therapy_type.name

# Areas of Expertise (custom multi-value)
class AreasOfExpertise(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='areas_of_expertise')
    expertise = models.CharField(max_length=32)
    def __str__(self): return self.expertise

# Top Specialties (up to 5)


# Title lookup model for therapist title dropdown
class Title(models.Model):
    name = models.CharField(max_length=16, unique=True)
    def __str__(self): return self.name

# PaymentMethod model for accepted payment methods
class PaymentMethod(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

# Selection model for therapist payment methods
class PaymentMethodSelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='accepted_payment_methods')
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.CASCADE)
    def __str__(self): return self.payment_method.name

# Lookup models for identity fields
class Gender(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self): return self.name

class RaceEthnicity(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class Faith(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class LGBTQIA(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

class OtherIdentity(models.Model):
    name = models.CharField(max_length=128, unique=True)
    def __str__(self): return self.name

# InsuranceProvider model for in-network insurance choices
class InsuranceProvider(models.Model):
    name = models.CharField(max_length=256, unique=True)
    def __str__(self):
        return self.name


# Lookup models
class LicenseType(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=256, blank=True, default="")
    def __str__(self): return self.name


# TherapistProfile model
class RaceEthnicitySelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='race_ethnicities')
    race_ethnicity = models.ForeignKey('RaceEthnicity', on_delete=models.CASCADE)
    def __str__(self): return self.race_ethnicity.name
class FaithSelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='faiths')
    faith = models.ForeignKey('Faith', on_delete=models.CASCADE)
    def __str__(self): return self.faith.name
class LGBTQIASelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='lgbtqia_identities')
    lgbtqia = models.ForeignKey('LGBTQIA', on_delete=models.CASCADE)
    def __str__(self): return self.lgbtqia.name
class OtherIdentitySelection(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='other_identities')
    other_identity = models.ForeignKey('OtherIdentity', on_delete=models.CASCADE)
    def __str__(self): return self.other_identity.name

class TherapistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=64, default="")
    middle_name = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=64, default="")
    title = models.ForeignKey('Title', on_delete=models.SET_NULL, blank=True, null=True, related_name='therapists')
    display_title = models.BooleanField(default=False)
    personal_statement_q1 = models.TextField(max_length=500, blank=True)
    personal_statement_q2 = models.TextField(max_length=500, blank=True)
    personal_statement_q3 = models.TextField(max_length=500, blank=True)
    practice_name = models.CharField(max_length=128, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    phone_extension = models.CharField(max_length=8, blank=True)
    receive_calls_from_client = models.BooleanField(default=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    receive_texts_from_clients = models.BooleanField(default=True)
    @property
    def practice_email(self):
        return self.user.email
    office_email = models.EmailField(max_length=128, blank=True)
    receive_emails_from_clients = models.BooleanField(default=True)
    receive_emails_when_client_calls = models.BooleanField(default=True)
    intro_statement = models.TextField(max_length=500, blank=True)
    therapy_delivery_method = models.CharField(max_length=32, blank=True)
    accepting_new_clients = models.CharField(max_length=16, default="Yes")
    offers_intro_call = models.BooleanField(default=False)
    individual_session_cost = models.CharField(max_length=16, blank=True)
    couples_session_cost = models.CharField(max_length=16, blank=True)
    sliding_scale_pricing_available = models.BooleanField(default=False)
    finance_note = models.CharField(max_length=128, blank=True)
    credentials_note = models.TextField(max_length=500, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    practice_website_url = models.CharField(max_length=256, blank=True)
    facebook_url = models.CharField(max_length=256, blank=True)
    instagram_url = models.CharField(max_length=256, blank=True)
    linkedin_url = models.CharField(max_length=256, blank=True)
    twitter_url = models.CharField(max_length=256, blank=True)
    tiktok_url = models.CharField(max_length=256, blank=True)
    youtube_url = models.CharField(max_length=256, blank=True)
    therapy_types_note = models.TextField(max_length=500, blank=True)
    specialties_note = models.TextField(max_length=500, blank=True)
    mental_health_role = models.CharField(max_length=16, blank=True)
    license_type = models.ForeignKey('LicenseType', on_delete=models.SET_NULL, blank=True, null=True, related_name='therapists')
    license_number = models.CharField(max_length=32, blank=True, unique=True)
    license_expiration = models.CharField(max_length=7, blank=True)
    license_state = models.CharField(max_length=2, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.ForeignKey('Gender', on_delete=models.SET_NULL, blank=True, null=True, related_name='therapists')
    participant_types = models.ManyToManyField('ParticipantType', related_name='therapists', blank=True)
    age_groups = models.ManyToManyField('AgeGroup', related_name='therapists', blank=True)
    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

# Credential model for multi-value therapist credentials
class Credential(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='credentials')
    license_type = models.ForeignKey('LicenseType', on_delete=models.CASCADE, related_name='credentials', null=True, blank=True)
    def __str__(self):
        return str(self.license_type)

# VideoGallery model for therapist video uploads
class VideoGallery(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='video_gallery')
    video = models.FileField(upload_to='video_gallery/')
    caption = models.CharField(max_length=128, blank=True)
    def __str__(self):
        return self.caption or str(self.video)

# Location model for multiple therapist locations
class Location(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='locations')
    practice_name = models.CharField(max_length=128, blank=True)
    street_address = models.CharField(max_length=128, blank=True)
    address_line_2 = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=32, blank=True)
    zip = models.CharField(max_length=16, blank=True)
    hide_address_from_public = models.BooleanField(default=False)
    is_primary_address = models.BooleanField(default=False)
    # ...phone and email fields removed, only on TherapistProfile...
    def __str__(self):
        return f"{self.practice_name} ({self.city}, {self.state})"


class Education(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='educations')
    school = models.CharField(max_length=64)
    degree_diploma = models.CharField(max_length=32)
    year_graduated = models.CharField(max_length=4)
    year_began_practice = models.CharField(max_length=4, blank=True)
    def __str__(self): return f"{self.degree_diploma} from {self.school}"

class AdditionalCredential(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='additional_credentials')
    organization_name = models.CharField(max_length=64)
    id_number = models.CharField(max_length=32, blank=True)
    year_issued = models.CharField(max_length=4)
    def __str__(self): return f"{self.organization_name} ({self.id_number})"

class Specialty(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='specialties')
    specialty = models.ForeignKey('SpecialtyLookup', on_delete=models.CASCADE, null=True, default=None)
    is_top_specialty = models.BooleanField(default=False)
    def __str__(self): return str(self.specialty)




# Lookup model for participant type
class ParticipantType(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self):
        return self.name

# Lookup model for age group
class AgeGroup(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self):
        return self.name

# Add to TherapistProfile: many-to-many for participant types and age groups
## Removed duplicate TherapistProfile definition. All fields are now in the single class above.

# Remove ClientFocusSelection if it exists





# Custom model for user-defined therapy types
class OtherTherapyType(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='other_therapy_types')
    therapy_type = models.CharField(max_length=64)
    def __str__(self): return self.therapy_type

class OtherTreatmentOption(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='other_treatment_options')
    option_text = models.CharField(max_length=64)
    def __str__(self): return self.option_text

class GalleryImage(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=128, blank=True)
    def __str__(self): return self.caption or str(self.image)

class InsuranceDetail(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='insurance_details')
    provider = models.ForeignKey('InsuranceProvider', on_delete=models.CASCADE, related_name='insurance_details')
    out_of_network = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.provider.name} (Out of Network: {self.out_of_network})"

class ProfessionalInsurance(models.Model):
    therapist = models.ForeignKey('TherapistProfile', on_delete=models.CASCADE, related_name='professional_insurances')
    npi_number = models.CharField(max_length=10, blank=True, unique=True)
    malpractice_carrier = models.CharField(max_length=64, blank=True)
    malpractice_expiration_date = models.CharField(max_length=7, blank=True)
    def __str__(self):
        return self.npi_number

