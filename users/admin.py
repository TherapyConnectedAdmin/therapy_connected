
from django.contrib import admin
from .models import Subscription, SubscriptionType
from .models_profile import (
    TherapistProfile,
    LicenseType, StateBoard, TelehealthPlatform, CityCounty, ZipCode,
    PracticeAreaTag, TreatmentApproach, ClientPopulation, Language,
    ProfessionalAssociation, Insurance, MultilingualMaterial
)
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

# Extend UserAdmin to show onboarding_status
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ('onboarding_status',)
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('onboarding_status',)}),
    )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class SubscriptionTypeAdmin(admin.ModelAdmin):
    formfield_overrides = {
        SubscriptionType.description.field: {'widget': CKEditorWidget},
    }



admin.site.register(Subscription, )
admin.site.register(SubscriptionType, SubscriptionTypeAdmin)

from django.utils.html import format_html

# Inline for lookup models (example: LicenseType)
class LicenseTypeInline(admin.TabularInline):
    model = LicenseType
    extra = 0

# TherapistProfile admin customization
class TherapistProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_type', 'onboarding_status_display')
    list_filter = ('license_type',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    # Add only valid ManyToMany fields below. Adjust as needed for your model:
    filter_horizontal = ('treatment_approaches', 'client_populations', 'professional_associations', 'multilingual_materials')

    def onboarding_status_display(self, obj):
        return format_html('<span>{}</span>', obj.user.onboarding_status)
    onboarding_status_display.short_description = 'Onboarding Status'

# Lookup model admin customization (example for LicenseType)
class LicenseTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class StateBoardAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class TelehealthPlatformAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class CityCountyAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class ZipCodeAdmin(admin.ModelAdmin):
    search_fields = ('code',)
    list_display = ('code',)

class PracticeAreaTagAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class TreatmentApproachAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class ClientPopulationAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class ProfessionalAssociationAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class InsuranceAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

class MultilingualMaterialAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

# Register models with custom admin only (remove duplicate default registrations)
admin.site.register(TherapistProfile, TherapistProfileAdmin)
admin.site.register(LicenseType, LicenseTypeAdmin)
admin.site.register(StateBoard, StateBoardAdmin)
admin.site.register(TelehealthPlatform, TelehealthPlatformAdmin)
admin.site.register(CityCounty, CityCountyAdmin)
admin.site.register(ZipCode, ZipCodeAdmin)
admin.site.register(PracticeAreaTag, PracticeAreaTagAdmin)
admin.site.register(TreatmentApproach, TreatmentApproachAdmin)
admin.site.register(ClientPopulation, ClientPopulationAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(ProfessionalAssociation, ProfessionalAssociationAdmin)
admin.site.register(Insurance, InsuranceAdmin)
admin.site.register(MultilingualMaterial, MultilingualMaterialAdmin)
