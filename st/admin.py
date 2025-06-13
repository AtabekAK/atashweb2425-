# st/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.humanize.templatetags.humanize import intcomma

import csv
from decimal import Decimal

from .models import (
    User, TechType, Category, Product, ProductSpecification, Color, Size,
    ProductVariant, Review, Favorite, Order, OrderItem, Promo, PromoProduct
)
from .forms import ProductAdminForm

# --- Инлайны ---
class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    verbose_name_plural = "Характеристики товара"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    verbose_name_plural = "Варианты товара (SKU, цена, остатки)"
    fields = ('sku', 'color', 'size', 'price', 'stock_quantity', 'image', 'admin_image_preview')
    readonly_fields = ('admin_image_preview',)
    raw_id_fields = ('color', 'size')

    @admin.display(description="Превью")
    def admin_image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "Нет изображения"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1 
    fields = ('variant', 'quantity', 'price_at_time', 'display_item_total_price')
    readonly_fields = ('price_at_time', 'display_item_total_price')
    raw_id_fields = ('variant',)

    @admin.display(description="Сумма позиции")
    def display_item_total_price(self, obj):
        if obj.pk and obj.price_at_time is not None and obj.quantity is not None:
            from django.contrib.humanize.templatetags.humanize import intcomma
            total = obj.quantity * obj.price_at_time
            return f"{intcomma(total)} руб."
        elif not obj.pk and obj.variant and obj.quantity is not None and hasattr(obj.variant, 'price'):
            from django.contrib.humanize.templatetags.humanize import intcomma
            total = obj.quantity * obj.variant.price
            return f"{intcomma(total)} руб. (предв.)"
        return "0.00 руб."

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('variant', 'variant__product', 'variant__color', 'variant__size')

class PromoProductInline(admin.TabularInline):
    model = PromoProduct
    extra = 1
    verbose_name = "Товар в акции"
    verbose_name_plural = "Товары, участвующие в акции"
    raw_id_fields = ('product',)

# --- Регистрация моделей и настройка админки ---

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # ... (код UserAdmin без изменений) ...
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined_formatted')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email', 'address', 'phone')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    @admin.display(description="Дата регистрации", ordering='date_joined')
    def date_joined_formatted(self, obj):
        if obj.date_joined:
            return timezone.localtime(obj.date_joined).strftime("%d.%m.%Y %H:%M")
        return "-"

@admin.register(TechType)
class TechTypeAdmin(admin.ModelAdmin):
    # ... (код TechTypeAdmin без изменений) ...
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # ... (код CategoryAdmin без изменений) ...
    list_display = ('name', 'parent', 'product_count')
    list_filter = ('parent',)
    search_fields = ('name', 'description')
    raw_id_fields = ('parent',)

    @admin.display(description="Кол-во товаров")
    def product_count(self, obj):
        return obj.products.count()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # ... (код ProductAdmin без изменений) ...
    form = ProductAdminForm
    list_display = (
        'name', 'tech_type', 'brand', 'is_active', 
        'created_at_formatted', 'display_categories', 'variants_count',
        'get_full_name_with_brand_admin',
        'average_rating_display'
    )
    list_filter = ('tech_type', 'is_active', 'brand', 'created_at', 'categories')
    search_fields = ('name', 'description', 'brand', 'tech_type__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'average_rating_display') 
    inlines = [ProductSpecificationInline, ProductVariantInline]
    filter_horizontal = ('categories',)
    actions = ['mark_as_inactive', 'mark_as_active', 'export_selected_products_as_csv']

    fieldsets = (
        (None, {'fields': ('name', 'brand', 'is_active')}),
        ('Описание и тип', {'fields': ('description', 'tech_type', 'categories')}),
        ('Файлы и ссылки', {'fields': ('instruction_manual', 'manufacturer_url')}),
        ('Даты', {'fields': ('created_at',)}),
    )

    @admin.display(description="Дата создания", ordering='created_at')
    def created_at_formatted(self, obj):
        if obj.created_at:
            return timezone.localtime(obj.created_at).strftime("%d.%m.%Y %H:%M")
        return "-"

    @admin.display(description="Категории")
    def display_categories(self, obj):
        return ", ".join([cat.name for cat in obj.categories.all()[:3]]) + ("..." if obj.categories.count() > 3 else "")

    @admin.display(description="Кол-во вариантов")
    def variants_count(self, obj):
        return obj.variants.count()

    @admin.display(description="Полное название", ordering='name')
    def get_full_name_with_brand_admin(self, obj):
        return obj.get_full_name_with_brand()

    @admin.display(description="Средний рейтинг")
    def average_rating_display(self, obj):
        avg_rating = obj.get_average_rating()
        return f"{avg_rating:.2f}" if avg_rating is not None else "Нет оценок"
    
    @admin.action(description="Сделать неактивными")
    def mark_as_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} товаров были помечены как неактивные.")

    @admin.action(description="Сделать активными")
    def mark_as_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} товаров были помечены как активные.")

    @admin.action(description="Экспортировать выбранные товары в CSV")
    def export_selected_products_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.verbose_name if field.verbose_name else field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{meta.verbose_name_plural}.csv"'
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field.name) for field in meta.fields])
        return response

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categories', 'variants', 'reviews').select_related('tech_type')

@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    # ... (код ProductSpecificationAdmin без изменений) ...
    list_display = ('product_link', 'name', 'value')
    list_filter = ('product__tech_type', 'name')
    search_fields = ('product__name', 'name', 'value')
    raw_id_fields = ('product',)

    @admin.display(description="Товар", ordering='product__name')
    def product_link(self, obj):
        if obj.product:
            link = reverse("admin:st_product_change", args=[obj.product.id])
            return mark_safe(f'<a href="{link}">{obj.product.name}</a>')
        return "N/A"

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    # ... (код ColorAdmin без изменений) ...
    list_display = ('name', 'hex_code', 'color_preview')
    search_fields = ('name', 'hex_code')

    @admin.display(description="Предпросмотр")
    def color_preview(self, obj):
        if obj.hex_code:
            return format_html(
                '<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc;"></div>',
                obj.hex_code
            )
        return "N/A"

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    # ... (код SizeAdmin без изменений) ...
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    # ... (код ProductVariantAdmin без изменений) ...
    list_display = ('sku', 'product_link', 'color', 'size', 'price', 'stock_quantity', 'admin_image_preview_list')
    list_filter = ('product__tech_type', 'product__brand', 'color', 'size')
    search_fields = ('sku', 'product__name', 'color__name', 'size__name')
    raw_id_fields = ('product', 'color', 'size')
    readonly_fields = ('admin_image_preview_form',)
    list_select_related = ('product', 'color', 'size')

    fieldsets = (
        (None, {'fields': ('product', 'sku')}),
        ('Характеристики', {'fields': ('color', 'size')}),
        ('Цена и остатки', {'fields': ('price', 'stock_quantity')}),
        ('Изображение', {'fields': ('image', 'admin_image_preview_form')}),
    )

    @admin.display(description="Изображение")
    def admin_image_preview_list(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "Нет изображения"
    
    @admin.display(description="Превью изображения")
    def admin_image_preview_form(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.image.url)
        return "Изображение не загружено"

    @admin.display(description="Товар", ordering='product__name')
    def product_link(self, obj):
        if obj.product:
            link = reverse("admin:st_product_change", args=[obj.product.id])
            return mark_safe(f'<a href="{link}">{obj.product.name}</a>')
        return "N/A"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # ... (код ReviewAdmin без изменений) ...
    list_display = ('product_link', 'user_link', 'rating', 'is_moderated', 'created_at_formatted')
    list_filter = ('is_moderated', 'rating', 'created_at', 'product__tech_type')
    search_fields = ('user__username', 'product__name', 'comment')
    date_hierarchy = 'created_at'
    actions = ['mark_as_moderated', 'mark_as_not_moderated']
    raw_id_fields = ('user', 'product')

    @admin.display(description="Дата создания", ordering='created_at')
    def created_at_formatted(self, obj):
        if obj.created_at:
            return timezone.localtime(obj.created_at).strftime("%d.%m.%Y %H:%M")
        return "-"

    @admin.display(description="Товар", ordering='product__name')
    def product_link(self, obj):
        link = reverse("admin:st_product_change", args=[obj.product.id])
        return mark_safe(f'<a href="{link}">{obj.product.name}</a>')

    @admin.display(description="Пользователь", ordering='user__username')
    def user_link(self, obj):
        link = reverse("admin:st_user_change", args=[obj.user.id])
        return mark_safe(f'<a href="{link}">{obj.user.username}</a>')

    @admin.action(description="Отметить как промодерированные")
    def mark_as_moderated(self, request, queryset):
        queryset.update(is_moderated=True)

    @admin.action(description="Отметить как НЕ промодерированные")
    def mark_as_not_moderated(self, request, queryset):
        queryset.update(is_moderated=False)

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    # ... (код FavoriteAdmin без изменений) ...
    list_display = ('user_link', 'product_link')
    search_fields = ('user__username', 'product__name')
    raw_id_fields = ('user', 'product')

    @admin.display(description="Товар", ordering='product__name')
    def product_link(self, obj):
        link = reverse("admin:st_product_change", args=[obj.product.id])
        return mark_safe(f'<a href="{link}">{obj.product.name}</a>')

    @admin.display(description="Пользователь", ordering='user__username')
    def user_link(self, obj):
        link = reverse("admin:st_user_change", args=[obj.user.id])
        return mark_safe(f'<a href="{link}">{obj.user.username}</a>')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_info', 'order_date_formatted', 'status', 
                    'payment_method', 'total_price_formatted', 'updated_at_formatted',
                    'order_pdf_link')
    list_filter = ('status', 'order_date', 'payment_method', 'user__username')
    search_fields = ('id', 'user__username', 'user__email', 'guest_email', 'guest_phone', 'guest_name', 'shipping_address', 'tracking_number')
    date_hierarchy = 'order_date'
    base_readonly_fields = ('calculated_total_price', 'order_date', 'updated_at', 'total_price') 
    inlines = [OrderItemInline]
    raw_id_fields = ('user',)
    
    def get_fieldsets(self, request, obj=None):
        base_main_info_fields = ['order_date', 'updated_at', 'status', 'payment_method', 'tracking_number']
        base_cost_fields = ['shipping_address', 'total_price', 'calculated_total_price']
        if obj: 
            main_info_fields = ['id'] + base_main_info_fields 
        else: 
            main_info_fields = base_main_info_fields 
        fieldsets = (
            ("Основная информация", {'fields': tuple(main_info_fields)}),
            ("Клиент", {'fields': ('user', 'guest_name', 'guest_email', 'guest_phone')}),
            ("Доставка и стоимость", {'fields': tuple(base_cost_fields)}),
        )
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        current_readonly = list(self.base_readonly_fields)
        if obj: 
            current_readonly.append('id') 
            if obj.user:
                current_readonly.extend(['guest_name', 'guest_email', 'guest_phone'])
            else:
                 current_readonly.append('user')
        return tuple(set(current_readonly))

    @admin.display(description="Клиент", ordering='user__username')
    def user_info(self, obj):
        if obj.user:
            link = reverse("admin:st_user_change", args=[obj.user.id])
            return mark_safe(f'<a href="{link}">{obj.user.username}</a>')
        return f"Гость: {obj.guest_name or 'N/A'} ({obj.guest_email or obj.guest_phone or 'N/A'})"

    @admin.display(description="Дата заказа", ordering='order_date')
    def order_date_formatted(self, obj):
        if obj.order_date:
            return timezone.localtime(obj.order_date).strftime("%d.%m.%Y %H:%M")
        return "-"

    @admin.display(description="Дата обновления", ordering='updated_at')
    def updated_at_formatted(self, obj):
        if obj.updated_at:
            return timezone.localtime(obj.updated_at).strftime("%d.%m.%Y %H:%M")
        return "-"

    @admin.display(description="Итоговая стоимость", ordering='total_price')
    def total_price_formatted(self, obj):
        from django.contrib.humanize.templatetags.humanize import intcomma
        if obj.pk:
            obj.refresh_from_db(fields=['total_price'])
        return f"{intcomma(obj.total_price)} руб."

    @admin.display(description="Расчетная стоимость (инлайн)")
    def calculated_total_price(self, obj):
        if not obj.pk: return "0.00 руб."
        items_qs = obj.items.all() if hasattr(obj, 'items') and obj.pk else []
        current_total = sum(item.item_total_price for item in items_qs)
        from django.contrib.humanize.templatetags.humanize import intcomma
        return f"{intcomma(current_total)} руб."
    
    @admin.display(description="Счет (PDF)")
    def order_pdf_link(self, obj):
        url = reverse('admin_order_pdf', args=[obj.id])
        return mark_safe(f'<a href="{url}" target="_blank">PDF</a>')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items__variant__product', 'user')

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False) 
        order_instance = form.instance 

        for instance in instances:
            if isinstance(instance, OrderItem) and instance.variant:
                if not instance.pk or not instance.price_at_time: 
                    instance.price_at_time = instance.variant.price
            
            if not instance.order_id and order_instance.pk:
                instance.order = order_instance
            instance.save() 
        formset.save_m2m()
        
        if order_instance.pk: 
            if hasattr(order_instance, 'update_total_price'):
                order_instance.update_total_price()
            else:
                # Запасной вариант, если метода update_total_price нет
                current_total = sum(item.item_total_price for item in order_instance.items.all())
                if order_instance.total_price != current_total:
                    order_instance.total_price = current_total
                    order_instance.save(update_fields=['total_price'])

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'variant_link', 'quantity', 'price_at_time', 'item_total_price_display')
    list_filter = ('variant__product__tech_type', 'order__status')
    search_fields = ('order__id', 'variant__sku', 'variant__product__name')
    raw_id_fields = ('order', 'variant')
    readonly_fields = ('price_at_time', 'item_total_price_display')
    fields = ('order', 'variant', 'quantity', 'price_at_time', 'item_total_price_display') # Добавил 'price_at_time' и 'item_total_price_display' сюда

    # Переопределяем save_model для установки price_at_time при прямом добавлении OrderItem
    def save_model(self, request, obj, form, change):
        # obj - это экземпляр OrderItem, который будет сохранен
        # form - это форма, связанная с этим объектом
        if obj.variant and (not obj.price_at_time or not change): # Если выбран вариант и цена не установлена или это новый объект
            obj.price_at_time = obj.variant.price
        super().save_model(request, obj, form, change)
        # После сохранения OrderItem, также нужно обновить total_price связанного заказа
        if obj.order: # Убедимся, что заказ существует
            if hasattr(obj.order, 'update_total_price'):
                obj.order.update_total_price()
            else:
                # Запасной вариант, если метода update_total_price нет
                current_total = sum(item.item_total_price for item in obj.order.items.all())
                if obj.order.total_price != current_total:
                    obj.order.total_price = current_total
                    obj.order.save(update_fields=['total_price'])

    @admin.display(description="Заказ", ordering='order__id')
    def order_link(self, obj):
        if obj.order:
            link = reverse("admin:st_order_change", args=[obj.order.id])
            return mark_safe(f'<a href="{link}">Заказ №{obj.order.id}</a>')
        return "N/A"

    @admin.display(description="Вариант товара", ordering='variant__sku')
    def variant_link(self, obj):
        if obj.variant:
            link = reverse("admin:st_productvariant_change", args=[obj.variant.id])
            return mark_safe(f'<a href="{link}">{obj.variant}</a>')
        return "N/A"
    
    @admin.display(description="Сумма позиции", ordering='price_at_time')
    def item_total_price_display(self, obj):
        from django.contrib.humanize.templatetags.humanize import intcomma
        total = obj.item_total_price 
        return f"{intcomma(total)} руб." if total is not None else "0.00 руб."

@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    # ... (код PromoAdmin без изменений) ...
    list_display = ('title', 'discount_percent', 'start_date', 'end_date', 'is_active', 'is_currently_active_admin')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'
    inlines = [PromoProductInline]

    @admin.display(boolean=True, description="Действует сейчас?")
    def is_currently_active_admin(self, obj):
        return obj.is_currently_active()

@admin.register(PromoProduct)
class PromoProductAdmin(admin.ModelAdmin):
    # ... (код PromoProductAdmin без изменений) ...
    list_display = ('promo_link', 'product_link')
    search_fields = ('promo__title', 'product__name')
    raw_id_fields = ('promo', 'product')

    @admin.display(description="Промоакция", ordering='promo__title')
    def promo_link(self, obj):
        link = reverse("admin:st_promo_change", args=[obj.promo.id])
        return mark_safe(f'<a href="{link}">{obj.promo.title}</a>')

    @admin.display(description="Товар", ordering='product__name')
    def product_link(self, obj):
        link = reverse("admin:st_product_change", args=[obj.product.id])
        return mark_safe(f'<a href="{link}">{obj.product.name}</a>')