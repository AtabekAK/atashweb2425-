# st/forms.py
from django import forms
from .models import TechType, Product # Добавим Product

class TechTypeForm(forms.ModelForm):
    class Meta:
        model = TechType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название типа техники'}),
        }
        labels = {
            'name': 'Название типа',
        }
        help_texts = {
            'name': 'Например, Смартфоны, Ноутбуки и т.д.',
        }

# КРИТЕРИЙ (Часть 3): File Uploads (особенности сохранения файлов в формах)
# Для работы с FileField и ImageField в ModelForm ничего особенного делать не нужно,
# Django ModelForm автоматически создаст нужный тип поля (ClearableFileInput).
# Важно, чтобы HTML-форма имела атрибут enctype="multipart/form-data",
# и чтобы во view при обработке POST-запроса файлы передавались в конструктор формы: form = MyForm(request.POST, request.FILES)
class ProductAdminForm(forms.ModelForm): # Форма для админки, если нужна кастомизация
    class Meta:
        model = Product
        fields = '__all__' # Или перечислить нужные поля

class ProductUserForm(forms.ModelForm): # Форма для пользовательского интерфейса
    # КРИТЕРИЙ (Часть 4): __icontains и __contains (пример использования в виджете, если бы это был поиск)
    # name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Поиск по названию (содержит)'}))
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'brand', 'tech_type', 'categories', 
            'instruction_manual', 'manufacturer_url', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'tech_type': forms.Select(attrs={'class': 'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'instruction_manual': forms.ClearableFileInput(attrs={'class': 'form-control'}), # КРИТЕРИЙ (Часть 3): models.FileField
            'manufacturer_url': forms.URLInput(attrs={'class': 'form-control'}), # КРИТЕРИЙ (Часть 4): models.URLField()
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }