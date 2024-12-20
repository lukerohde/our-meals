from django import forms
from .models import Collection

class CollectionForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text='Optional: Add a description for your collection'
    )
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Give your collection a name'
    )
    photo = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Optional: Add a cover photo'
    )

    class Meta:
        model = Collection
        fields = ['photo', 'title', 'description']