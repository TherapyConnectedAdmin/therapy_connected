from django import forms
from .models_blog import BlogPost, BlogTag


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class BlogPostForm(forms.ModelForm):
    # New: allow multiple media uploads (images/videos), up to 8
    media = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={'multiple': True, 'accept': 'image/*,video/*', 'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'}),
        help_text='Attach up to 8 images or videos.'
    )
    media_meta = forms.CharField(required=False, widget=forms.HiddenInput())
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'image', 'tags', 'published', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'}),
            'content': forms.Textarea(attrs={'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]', 'rows': 8}),
            'tags': forms.SelectMultiple(attrs={'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'}),
            'published': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-[#89B0AE] focus:ring-[#89B0AE] border-[#BEE3DB] rounded'}),
            'visibility': forms.Select(attrs={'class': 'border border-gray-300 rounded px-3 py-2 w-full bg-[#FAF9F9] text-[#555B6E]'}),
        }
