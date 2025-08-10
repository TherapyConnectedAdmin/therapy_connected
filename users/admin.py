from django.contrib import admin
from django.utils.html import format_html
from users.models_profile import TherapistProfile
from .models_featured import FeaturedTherapistHistory, FeaturedBlogPostHistory

from .models_profile import (
    TherapistProfile, Title, TherapyType, TherapyTypeSelection, AreasOfExpertise,
    PaymentMethod, PaymentMethodSelection, Gender, RaceEthnicity, Faith, LGBTQIA, OtherIdentity,
    InsuranceProvider, LicenseType, RaceEthnicitySelection, FaithSelection, LGBTQIASelection,
    OtherIdentitySelection, Credential, VideoGallery, Location, Education, AdditionalCredential,
    Specialty, SpecialtyLookup, OtherTreatmentOption, GalleryImage, InsuranceDetail,
    ProfessionalInsurance, OtherTherapyType
)
from .models_profile import ParticipantType, AgeGroup

## Removed duplicate registration of TherapistProfile
registered_models = set()
for model in [
    TherapistProfile, Title, TherapyType, TherapyTypeSelection, AreasOfExpertise,
    PaymentMethod, PaymentMethodSelection, Gender, RaceEthnicity, Faith, LGBTQIA, OtherIdentity,
    InsuranceProvider, LicenseType, RaceEthnicitySelection, FaithSelection, LGBTQIASelection,
    OtherIdentitySelection, Credential, VideoGallery, Location, Education, AdditionalCredential,
    Specialty, SpecialtyLookup, OtherTreatmentOption, GalleryImage, InsuranceDetail,
    ProfessionalInsurance, OtherTherapyType
]:
    if model not in registered_models:
        admin.site.register(model)
        registered_models.add(model)
admin.site.register(ParticipantType)
admin.site.register(AgeGroup)
class FeaturedTherapistHistoryAdmin(admin.ModelAdmin):
    list_display = ("therapist", "date", "cycle")
    list_filter = ("cycle",)
    search_fields = ("therapist__first_name", "therapist__last_name")

@admin.register(FeaturedBlogPostHistory)
class FeaturedBlogPostHistoryAdmin(admin.ModelAdmin):
    list_display = ("blog_post", "date", "cycle")
    list_filter = ("cycle",)
    search_fields = ("blog_post__title",)
from .models_blog import BlogPost, BlogTag
# Blog admin
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published', 'created_at')
    list_filter = ('published', 'created_at', 'tags')
    search_fields = ('title', 'content', 'author__email')
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ('tags',)

class BlogTagAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(BlogTag, BlogTagAdmin)

from .models import Subscription, SubscriptionType
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

# Extend UserAdmin to show onboarding_status
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ('onboarding_status',)
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('onboarding_status',)}),
    )

admin.site.register(User, UserAdmin)


class SubscriptionTypeAdmin(admin.ModelAdmin):
    formfield_overrides = {
        SubscriptionType.description.field: {'widget': CKEditorWidget},
    }



admin.site.register(Subscription, )
admin.site.register(SubscriptionType, SubscriptionTypeAdmin)

"""Admin customizations and bulk lookup maintenance actions."""

# Inline for lookup models (example: LicenseType)
class LicenseTypeInline(admin.TabularInline):
    model = LicenseType
    extra = 0

# TherapistProfile admin customization
class PhotoFlagFilter(admin.SimpleListFilter):
    title = 'photo flag'
    parameter_name = 'photo_flag'

    def lookups(self, request, model_admin):
        return [
            ('low_res', 'Low Res'),
            ('blurry', 'Blurry'),
            ('rejected', 'Rejected'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            # JSON list contains lookup
            return queryset.filter(profile_photo_meta__flags__contains=[val])
        return queryset


class PhotoPipelineVersionFilter(admin.SimpleListFilter):
    title = 'photo pipeline version'
    parameter_name = 'photo_pipeline_version'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request).exclude(profile_photo_meta__pipeline_version__isnull=True)
        versions = sorted({m.profile_photo_meta.get('pipeline_version') for m in qs if isinstance(m.profile_photo_meta, dict) and m.profile_photo_meta.get('pipeline_version') is not None})
        return [(str(v), f"v{v}") for v in versions]

    def queryset(self, request, queryset):
        v = self.value()
        if v is not None:
            return queryset.filter(profile_photo_meta__pipeline_version=int(v))
        return queryset


class TherapistProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'first_name', 'last_name', 'onboarding_status_display',
        'photo_low_res', 'photo_blurry', 'photo_rejected', 'photo_pipeline_version'
    )
    list_filter = (PhotoFlagFilter, PhotoPipelineVersionFilter)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

    def onboarding_status_display(self, obj):
        return format_html('<span>{}</span>', obj.user.onboarding_status)
    onboarding_status_display.short_description = 'Onboarding Status'

    def photo_low_res(self, obj):
        return obj.photo_is_low_res
    photo_low_res.boolean = True
    def photo_blurry(self, obj):
        return obj.photo_is_blurry
    photo_blurry.boolean = True
    def photo_rejected(self, obj):
        return obj.photo_is_rejected
    photo_rejected.boolean = True
    def photo_pipeline_version(self, obj):
        return obj.photo_pipeline_version

admin.site.unregister(TherapistProfile)
admin.site.register(TherapistProfile, TherapistProfileAdmin)

#############################################
# Lookup purge actions (operate across lookups)
#############################################
from .models_profile import (
    Faith, Gender, InsuranceProvider, LGBTQIA, LicenseType, PaymentMethod,
    RaceEthnicity, TherapyType, Title, SpecialtyLookup, OtherIdentity, LookupMaintenance
)
import subprocess, sys, os

@admin.action(description="Run lookup purge DRY-RUN (simulated)")
def purge_lookup_dry_run(modeladmin, request, queryset):
    env = os.environ.copy()
    env['LOOKUP_PURGE'] = '1'
    env['LOOKUP_PURGE_DRY_RUN'] = '1'
    subprocess.run([sys.executable, 'manage.py', 'shell'], input=open('seed_lookups.py', 'rb').read(), env=env)
    modeladmin.message_user(request, "Dry-run purge completed. Check server logs for details.")

@admin.action(description="Execute lookup purge (DESTRUCTIVE)")
def purge_lookup_execute(modeladmin, request, queryset):
    env = os.environ.copy()
    env['LOOKUP_PURGE'] = '1'
    env['LOOKUP_PURGE_DRY_RUN'] = '0'
    subprocess.run([sys.executable, 'manage.py', 'shell'], input=open('seed_lookups.py', 'rb').read(), env=env)
    modeladmin.message_user(request, "Lookup purge executed. Review logs.")

class LicenseTypeAdmin(admin.ModelAdmin):
    search_fields = ('name', 'short_description')
    list_display = ('name', 'short_description', 'category', 'sort_order')
    list_filter = ('category',)

class LookupMaintenanceAdmin(admin.ModelAdmin):
    change_list_template = 'admin/lookup_maintenance_changelist.html'
    actions = [purge_lookup_dry_run, purge_lookup_execute]
    list_display = ('name', 'short_description', 'category', 'sort_order')
    search_fields = ('name', 'short_description')
    list_filter = ('category',)

    def get_queryset(self, request):
        # Show a small representative queryset (all LicenseType rows as base proxy)
        return super().get_queryset(request)

admin.site.register(LookupMaintenance, LookupMaintenanceAdmin)

from .models import TherapistProfileStats

class TherapistProfileStatsAdmin(admin.ModelAdmin):
    list_display = ('therapist', 'date', 'search_impressions', 'search_rank', 'profile_clicks', 'contact_clicks')
    list_filter = ('date', 'therapist')
    search_fields = ('therapist__email',)

admin.site.register(TherapistProfileStats, TherapistProfileStatsAdmin)
