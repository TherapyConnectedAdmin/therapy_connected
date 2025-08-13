from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from users.models_profile import TherapistProfile

class TherapistProfileSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return (TherapistProfile.objects
                .filter(user__is_active=True, user__onboarding_status='active')
                .exclude(slug__exact='')
               )

    def location(self, obj: TherapistProfile):
        # Use new /therapists/<slug>/ path for SEO clarity
        return reverse('therapist_profile_public_slug', kwargs={'slug': obj.slug})

    def lastmod(self, obj: TherapistProfile):
        # Fallback to user's last_login or None (sitemap omits if None)
        return getattr(obj.user, 'last_login', None)
