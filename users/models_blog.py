from django.db import models
from django.conf import settings

class BlogTag(models.Model):
    name = models.CharField(max_length=32, unique=True)
    def __str__(self):
        return self.name

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    VISIBILITY_CHOICES = [
        ('public', 'Public (site-wide)'),
        ('members', 'Members only'),
        ('both', 'Both Public and Members'),
    ]
    visibility = models.CharField(max_length=12, choices=VISIBILITY_CHOICES, default='public')
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    image_meta = models.JSONField(blank=True, null=True, default=dict)
    tags = models.ManyToManyField(BlogTag, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class BlogMedia(models.Model):
    TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='blog_media/%Y/%m/')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    meta = models.JSONField(blank=True, null=True, default=dict)
    position = models.PositiveIntegerField(default=0, help_text='Ordering of media within the post')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f"BlogMedia {self.type} for post {self.post_id}"
