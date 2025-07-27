from django.db import models
from django.conf import settings
from users.models_profile import TherapistProfile
from users.models_blog import BlogPost

class FeaturedTherapistHistory(models.Model):
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE)
    date = models.DateField(unique=True)
    cycle = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.therapist} on {self.date} (cycle {self.cycle})"

class FeaturedBlogPostHistory(models.Model):
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    date = models.DateField(unique=True)
    cycle = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.blog_post} on {self.date} (cycle {self.cycle})"
