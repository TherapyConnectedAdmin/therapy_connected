from django.contrib import admin
from users.models_profile import TherapistProfile
# Register the through tables for TherapistProfile's many-to-many fields
admin.site.register(TherapistProfile.age_groups.through)
admin.site.register(TherapistProfile.participant_types.through)
from django.contrib import admin
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
from django.contrib import admin
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

from django.contrib import admin
from .models import Subscription, SubscriptionType
from .models_profile import (
    TherapistProfile,
    LicenseType,


)
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

from django.utils.html import format_html

# Inline for lookup models (example: LicenseType)
class LicenseTypeInline(admin.TabularInline):
    model = LicenseType
    extra = 0

# TherapistProfile admin customization
class TherapistProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'onboarding_status_display')
    list_filter = ()
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    # No filter_horizontal fields since none are valid ManyToMany fields on TherapistProfile

    def onboarding_status_display(self, obj):
        return format_html('<span>{}</span>', obj.user.onboarding_status)
    onboarding_status_display.short_description = 'Onboarding Status'

# Lookup model admin customization (example for LicenseType)
class LicenseTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)























# Register models with custom admin only (remove duplicate default registrations)
## Removed duplicate registration of TherapistProfile with TherapistProfileAdmin
## Removed duplicate registration of LicenseType with LicenseTypeAdmin











from .models import TherapistProfileStats

class TherapistProfileStatsAdmin(admin.ModelAdmin):
    list_display = ('therapist', 'date', 'search_impressions', 'search_rank', 'profile_clicks', 'contact_clicks')
    list_filter = ('date', 'therapist')
    search_fields = ('therapist__email',)

admin.site.register(TherapistProfileStats, TherapistProfileStatsAdmin)
