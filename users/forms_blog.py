from django import forms
from .models_blog import BlogPost, BlogTag

class BlogPostForm(forms.ModelForm):
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
