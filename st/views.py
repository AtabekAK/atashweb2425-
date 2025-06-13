# st/views.py
from django.shortcuts import render, get_object_or_404, redirect # КРИТЕРИЙ (Часть 3): return redirect
from django.http import HttpResponse, Http404 # КРИТЕРИЙ (Часть 4): The Http404 exception
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Product, Category, Review, Order, ProductVariant, TechType, User # Добавил User
from .forms import TechTypeForm, ProductUserForm # Добавил ProductUserForm
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Min, Max, F, Q, ExpressionWrapper, DecimalField # КРИТЕРИЙ (Часть 4): F expressions (использовано в aggregate)
from django.contrib.admin.views.decorators import staff_member_required # Для PDF
from django.conf import settings # Для PDF
from django.template.loader import render_to_string # Для PDF
import weasyprint # Для PDF
import os # Для PDF (если CSS из файла)

# --- Демонстрационные Views для Части 2 и 4 ---

def product_list_view_extended(request):
    # КРИТЕРИЙ (Часть 4): __icontains и __contains
    search_query_name = request.GET.get('name_contains', '') # Для __contains (регистрозависимый)
    search_query_desc = request.GET.get('desc_icontains', '') # Для __icontains (регистронезависимый)

    products = Product.active_products.all()

    if search_query_name:
        # products = products.filter(name__contains=search_query_name)
        # ИЛИ используем Q для более сложных запросов (пример)
        products = products.filter(Q(name__contains=search_query_name) | Q(brand__contains=search_query_name))
    
    if search_query_desc:
        products = products.filter(description__icontains=search_query_desc)

    # КРИТЕРИЙ (Часть 4): values(), values_list()
    # values() - возвращает QuerySet словарей
    product_names_and_brands = Product.active_products.filter(brand__isnull=False).values('name', 'brand')[:5] 
    # [{'name': 'Товар1', 'brand': 'БрендА'}, ...]

    # values_list() - возвращает QuerySet кортежей
    product_ids = Product.active_products.values_list('id', flat=True).order_by('-created_at')[:5]
    # [5, 4, 3, 2, 1] (если flat=True, иначе [(5,), (4,), ...])

    # КРИТЕРИЙ (Часть 4): count(), exists()
    total_active_products = Product.active_products.count()
    has_apple_products = Product.active_products.filter(brand="Apple").exists()


    # КРИТЕРИЙ (Часть 4): update(), delete() (демонстрация работы ORM, не как view)
    # Эти операции обычно выполняются в ответ на POST-запрос или в management commands.
    # Пример (не запускать напрямую во view без POST и прав):
    # Product.objects.filter(brand="OldBrand").update(brand="NewBrand") # Массовое обновление
    # Product.objects.filter(is_active=False, stock_quantity=0).delete() # Массовое удаление
    
    # Пример F expressions (сложение значения поля с числом)
    # ProductVariant.objects.update(price=F('price') * Decimal('1.1')) # Увеличить все цены на 10%

    context = {
        'products': products,
        'product_names_and_brands': product_names_and_brands,
        'product_ids': product_ids,
        'total_active_products': total_active_products,
        'has_apple_products': has_apple_products,
        'page_title': "Расширенный список товаров (демо)",
        'search_query_name': search_query_name,
        'search_query_desc': search_query_desc,
    }
    # return render(request, 'st/product_list_extended.html', context)
    return HttpResponse(f"<html><body><h1>Расширенный список товаров (демо)</h1>"
                        f"<p>Результаты ORM-запросов см. в отладчике/консоли или реализуйте шаблон.</p>"
                        f"<p>Всего активных товаров: {total_active_products}</p>"
                        f"<p>Есть товары Apple: {has_apple_products}</p>"
                        f"</body></html>")


def optimized_product_list_view(request):
    products = Product.objects.all() \
        .select_related('tech_type') \
        .prefetch_related(
            'categories', 
            'variants__color', 
            'variants__size',
            'reviews' # Добавим отзывы для примера
        )
    
    context = {
        'products': products,
        'page_title': "Оптимизированный список товаров"
    }
    # return render(request, 'st/optimized_product_list.html', context)
    return HttpResponse(f"<html><body><h1>Оптимизированный список товаров</h1><p>Загружено {products.count()} товаров с оптимизацией (select_related, prefetch_related).</p></body></html>")


# --- CRUD для TechType (Часть 2) ---
class TechTypeListView(ListView):
    model = TechType
    template_name = 'st/techtype_list.html'
    context_object_name = 'object_list'
    extra_context = {'page_title': 'Список типов техники'}

class TechTypeDetailView(DetailView):
    model = TechType
    template_name = 'st/techtype_detail.html'
    context_object_name = 'object'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Тип техники: {self.object.name}'
        context['breadcrumb_active'] = self.object.name
        return context

class TechTypeCreateView(CreateView):
    model = TechType
    form_class = TechTypeForm
    template_name = 'st/techtype_form.html'
    # КРИТЕРИЙ (Часть 3): return redirect (success_url ведет к редиректу)
    success_url = reverse_lazy('tech_type_list') 
    extra_context = {'page_title': 'Добавить тип техники', 'breadcrumb_active': 'Добавление'}

class TechTypeUpdateView(UpdateView):
    model = TechType
    form_class = TechTypeForm
    template_name = 'st/techtype_form.html'
    success_url = reverse_lazy('tech_type_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Редактировать: {self.object.name}'
        context['breadcrumb_active'] = 'Редактирование'
        return context

class TechTypeDeleteView(DeleteView):
    model = TechType
    template_name = 'st/techtype_confirm_delete.html'
    success_url = reverse_lazy('tech_type_list')
    context_object_name = 'object'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Удалить: {self.object.name}'
        context['breadcrumb_active'] = 'Удаление'
        return context

# --- CRUD для Product (Часть 3 - FileField, URLField) ---
# Мы будем использовать эти views для демонстрации загрузки файлов и URLField
class ProductListViewUser(ListView):
    model = Product
    template_name = 'st/product_user_list.html' # Создайте этот шаблон
    context_object_name = 'products'
    queryset = Product.active_products.all().select_related('tech_type').prefetch_related('categories')
    paginate_by = 10 # Пример пагинации

class ProductDetailViewUser(DetailView):
    model = Product
    template_name = 'st/product_user_detail.html' # Создайте этот шаблон
    context_object_name = 'product'

    def get_object(self, queryset=None):
        # КРИТЕРИЙ (Часть 4): The Http404 exception
        # Если объект не найден по pk, get_object_or_404 вызовет Http404
        obj = get_object_or_404(Product, pk=self.kwargs.get('pk'), is_active=True)
        return obj
        # Если бы мы хотели кастомную обработку:
        # try:
        #     obj = Product.objects.get(pk=self.kwargs.get('pk'), is_active=True)
        # except Product.DoesNotExist:
        #     raise Http404("Такой товар не найден или неактивен.")
        # return obj


class ProductCreateUserView(CreateView):
    model = Product
    form_class = ProductUserForm
    template_name = 'st/product_user_form.html' # Создайте этот шаблон
    
    def get_success_url(self):
        # КРИТЕРИЙ (Часть 3): return redirect (success_url через метод)
        return reverse('product_user_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # КРИТЕРИЙ (Часть 3): File Uploads (особенности сохранения файлов в формах)
        # ModelForm автоматически обработает request.FILES, если форма настроена правильно
        # и HTML-тег <form> имеет enctype="multipart/form-data"
        # Дополнительная логика может быть здесь, если нужна (например, связать с текущим пользователем)
        # form.instance.author = self.request.user (если бы было поле author)
        return super().form_valid(form)

class ProductUpdateUserView(UpdateView):
    model = Product
    form_class = ProductUserForm
    template_name = 'st/product_user_form.html'
    
    def get_success_url(self):
        return reverse('product_user_detail', kwargs={'pk': self.object.pk})

    def get_queryset(self):
        # Для безопасности, позволяем редактировать только свои объекты (если бы было поле user)
        # queryset = super().get_queryset()
        # return queryset.filter(author=self.request.user)
        return super().get_queryset() # Пока без ограничения по пользователю

class ProductDeleteUserView(DeleteView):
    model = Product
    template_name = 'st/product_user_confirm_delete.html' # Создайте этот шаблон
    success_url = reverse_lazy('product_user_list')


# --- Генерация PDF для заказа (Часть 3) ---
# КРИТЕРИЙ (Часть 3): Генерация pdf документа в админке
@staff_member_required # Только для персонала (администраторов)
def admin_order_pdf(request, order_id):
    try:
        order = Order.objects.select_related('user').prefetch_related(
            'items__variant__product', 
            'items__variant__color', 
            'items__variant__size'
        ).get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Заказ не найден") # КРИТЕРИЙ (Часть 4): The Http404 exception
        
    html = render_to_string('st/order/pdf.html', {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="order_{order.id}.pdf"'
    
    # Путь к CSS файлу. Мы можем попробовать найти его в статике приложения.
    # css_path = os.path.join(settings.STATIC_ROOT, 'st/css/pdf.css') # Для collectstatic
    # Если STATIC_ROOT не используется/не настроен для разработки, Weasyprint может не найти CSS по этому пути.
    # Альтернатива для разработки - передать абсолютный путь или встроить стили в HTML.
    # В pdf.html уже есть встроенные стили, если css_path не будет передан.
    
    # Попытка найти CSS в статических файлах приложения (работает без collectstatic в DEBUG)
    css_file_path_in_app = os.path.join(settings.BASE_DIR, 'st', 'static', 'st', 'css', 'pdf.css')
    stylesheets = []
    if os.path.exists(css_file_path_in_app):
        stylesheets.append(weasyprint.CSS(css_file_path_in_app))
    
    weasyprint.HTML(string=html).write_pdf(response, stylesheets=stylesheets)
    return response

# Пример redirect для несуществующего объекта (не в CRUD)
def old_product_redirect_view(request, old_id):
    # Предположим, это старый URL, и мы хотим редиректить на новый
    try:
        # Логика поиска нового продукта по старому ID (здесь упрощенно)
        new_product_pk = int(old_id) + 1000 # Просто пример
        product = Product.objects.get(pk=new_product_pk)
        # КРИТЕРИЙ (Часть 3): return redirect
        return redirect(product.get_absolute_url(), permanent=True) # 301 редирект
    except (Product.DoesNotExist, ValueError):
        # КРИТЕРИЙ (Часть 3): return redirect (на главную, если не найдено)
        # КРИТЕРИЙ (Часть 4): The Http404 exception (альтернативно можно было бы вызвать Http404)
        # raise Http404("Продукт для редиректа не найден")
        return redirect(reverse('tech_type_list')) # Редирект на список типов, например