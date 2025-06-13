# st/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.utils import timezone # КРИТЕРИЙ: Использование from django.utils import timezone
from django.urls import reverse # КРИТЕРИЙ: reverse (для get_absolute_url)
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, DecimalField, Q 
from decimal import Decimal # ИСПРАВЛЕНИЕ: Добавлен импорт Decimal
import os # Для работы с путями файлов

# --- Собственный модельный менеджер ---
# КРИТЕРИЙ: Использование собственного модельного менеджера
class ActiveProductManager(models.Manager):
    def get_queryset(self):
        # Этот менеджер будет возвращать только активные товары
        return super().get_queryset().filter(is_active=True)

class RecentProductManager(models.Manager):
    def get_queryset(self):
        # Этот менеджер будет возвращать товары, созданные за последние 7 дней
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        return super().get_queryset().filter(created_at__gte=one_week_ago)


# --- Пользователи ---
class User(AbstractUser):
    address = models.CharField(max_length=255, verbose_name="Адрес", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True, null=True)
    # date_joined - поле, которое уже есть в AbstractUser, хранит дату создания пользователя.
    # КРИТЕРИЙ: Использование from django.utils import timezone (+логика работы с датой).
    # Пример 1: date_joined хранит дату регистрации пользователя (UTC по умолчанию, если USE_TZ=True).
    # Это системная дата, фиксирующая момент создания записи в БД.
    # Кейс: Можно использовать для аналитики (сколько новых пользователей за период) или для предоставления "новичковых" бонусов.

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        # КРИТЕРИЙ: class Meta: ordering
        ordering = ['username'] # Сортировка пользователей по имени пользователя по умолчанию

    def __str__(self):
        return self.username

# --- Каталог товаров ---
class TechType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название типа техники")

    class Meta:
        verbose_name = "Тип техники"
        verbose_name_plural = "Типы техники"
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        # КРИТЕРИЙ: related_name в модели
        # related_name='subcategories' позволяет обращаться от родительской категории к её дочерним категориям.
        # Пример использования: parent_category.subcategories.all() вернет QuerySet всех дочерних категорий.
        related_name='subcategories',
        verbose_name="Родительская категория"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent} -> {self.name}"
        return self.name

def product_instruction_path(instance, filename):
    # КРИТЕРИЙ (Часть 3): File Uploads (особенности сохранения файлов)
    # Файл будет загружен в MEDIA_ROOT/product_instructions/product_<id>/<filename>
    # Это помогает организовать файлы и избежать конфликтов имен.
    return f'product_instructions/product_{instance.pk}/{filename}'

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название товара")
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    brand = models.CharField(max_length=100, verbose_name="Бренд", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    # КРИТЕРИЙ: Использование from django.utils import timezone (+логика работы с датой).
    # Пример 2: created_at хранит дату и время создания записи о товаре.
    # Это дата, когда товар был добавлен в базу данных магазина (сохраняется в UTC).
    # Кейс: Сортировка товаров по новизне, отображение метки "Новинка" для товаров, добавленных недавно.
    created_at = models.DateTimeField(
        default=timezone.now, # КРИТЕРИЙ: Использование timezone.now для значения по умолчанию
        verbose_name="Дата создания",
        editable=False # Чтобы нельзя было изменить через админку, т.к. это дата создания
    )
    tech_type = models.ForeignKey(
        TechType,
        on_delete=models.PROTECT,
        verbose_name="Тип техники"
    )
    categories = models.ManyToManyField(
        Category,
        # КРИТЕРИЙ: related_name в модели
        # related_name='products' позволяет обращаться от объекта Category к товарам этой категории.
        # Пример: category_obj.products.all() вернет все товары, принадлежащие данной категории.
        related_name='products',
        verbose_name="Категории",
        blank=True
    )
    # КРИТЕРИЙ (Часть 3): models.FileField
    instruction_manual = models.FileField(
        upload_to=product_instruction_path, # Используем функцию для определения пути
        blank=True,
        null=True,
        verbose_name="Инструкция (PDF/DOC)"
    )
    # КРИТЕРИЙ (Часть 4): models.URLField()
    manufacturer_url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Сайт производителя",
        help_text="Например, https://www.apple.com"
    )

    # КРИТЕРИЙ: Использование собственного модельного менеджера
    objects = models.Manager() 
    active_products = ActiveProductManager()
    recent_products = RecentProductManager()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        # КРИТЕРИЙ: class Meta: ordering
        ordering = ['-created_at', 'name'] # Сначала новые, потом по имени

    def __str__(self):
        return self.name

    # КРИТЕРИЙ: get_absolute_url, reverse
    def get_absolute_url(self):
        # 'product_detail_view' - это имя URL-паттерна, которое мы определим в urls.py для ProductDetailViewUser.
        return reverse('product_detail_view', kwargs={'pk': self.pk})

    # КРИТЕРИЙ (Часть 3): Создание собственного функционального метода в модели
    def get_full_name_with_brand(self):
        """Возвращает полное название товара, включая бренд, если он есть."""
        if self.brand:
            return f"{self.brand} {self.name}"
        return self.name
    get_full_name_with_brand.short_description = "Полное название (с брендом)"

    def get_average_rating(self):
        """Возвращает средний рейтинг товара или None, если отзывов нет."""
        avg_data = self.reviews.aggregate(avg_rating=Avg('rating'))
        return avg_data['avg_rating'] if avg_data['avg_rating'] is not None else None
    get_average_rating.short_description = "Средний рейтинг"


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='specifications',
        verbose_name="Товар"
    )
    name = models.CharField(max_length=100, verbose_name="Название характеристики")
    value = models.CharField(max_length=255, verbose_name="Значение характеристики")

    class Meta:
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товара"
        unique_together = ('product', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.product.name}: {self.name} - {self.value}"

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название цвета")
    hex_code = models.CharField(max_length=7, unique=True, verbose_name="HEX-код", help_text="Например, #FFFFFF")

    class Meta:
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"
        ordering = ['name']

    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Размер/Объем")

    class Meta:
        verbose_name = "Размер/Объем"
        verbose_name_plural = "Размеры/Объемы"
        ordering = ['name']

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name="Товар"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Цвет"
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Размер/Объем"
    )
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="Количество на складе")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    sku = models.CharField(max_length=100, unique=True, verbose_name="Артикул (SKU)", help_text="Уникальный идентификатор варианта")
    image = models.ImageField(
        upload_to='product_variants/',
        blank=True,
        null=True,
        verbose_name="Изображение варианта"
    )

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товара"
        unique_together = ('product', 'color', 'size')
        ordering = ['product__name', 'price']

    def __str__(self):
        parts = [str(self.product.name)]
        if self.color:
            parts.append(f"Цвет: {self.color.name}")
        if self.size:
            parts.append(f"Размер: {self.size.name}")
        return ", ".join(parts) + f" (Артикул: {self.sku})"

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="Товар")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Рейтинг"
    )
    comment = models.TextField(verbose_name="Комментарий")
    created_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name="Дата создания")
    is_moderated = models.BooleanField(default=False, verbose_name="Промодерирован")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв от {self.user.username} на {self.product.name} (Рейтинг: {self.rating})"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by', verbose_name="Товар")

    class Meta:
        verbose_name = "Избранный товар"
        verbose_name_plural = "Избранные товары"
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} добавил в избранное {self.product.name}"

class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'В обработке'),
        (STATUS_PROCESSING, 'Собирается'),
        (STATUS_SHIPPED, 'Отправлен'),
        (STATUS_DELIVERED, 'Доставлен'),
        (STATUS_CANCELLED, 'Отменен'),
    ]

    PAYMENT_CARD_ONLINE = 'card_online'
    PAYMENT_CASH_PICKUP = 'cash_pickup'
    PAYMENT_COURIER_CASH = 'courier_cash'
    PAYMENT_COURIER_CARD = 'courier_card'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CARD_ONLINE, 'Картой онлайн'),
        (PAYMENT_CASH_PICKUP, 'Наличными при самовывозе'),
        (PAYMENT_COURIER_CASH, 'Курьеру наличными'),
        (PAYMENT_COURIER_CARD, 'Курьеру картой'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь")
    order_date = models.DateTimeField(default=timezone.now, verbose_name="Дата заказа", editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Статус заказа")
    # ИЗМЕНЕНИЕ: Добавляем default и делаем editable=False для total_price
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Итоговая стоимость",
        default=Decimal('0.00'), # Устанавливаем значение по умолчанию
        editable=False # Делаем нередактируемым в админке, т.к. будет вычисляться
    )
    shipping_address = models.TextField(verbose_name="Адрес доставки")
    payment_method = models.CharField(
        max_length=50, 
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_CARD_ONLINE, 
        verbose_name="Метод оплаты"
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Номер отслеживания")
    guest_email = models.EmailField(verbose_name="Email гостя", blank=True, null=True)
    guest_phone = models.CharField(max_length=20, verbose_name="Телефон гостя", blank=True, null=True)
    guest_name = models.CharField(max_length=150, verbose_name="Имя гостя", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата последнего обновления")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-order_date']

    def __str__(self):
        user_info = str(self.user.username) if self.user else f"Гость ({self.guest_email or 'N/A'})"
        return f"Заказ №{self.id} от {user_info} ({self.order_date.strftime('%d.%m.%Y %H:%M')})"

    def get_customer_full_name(self):
        if self.user:
            return self.user.get_full_name() if self.user.get_full_name() else self.user.username
        elif self.guest_name:
            return self.guest_name
        return "Клиент не указан"
    get_customer_full_name.short_description = "ФИО клиента"

    def get_order_items_for_pdf(self):
        items_data = []
        for item in self.items.all().select_related('variant__product', 'variant__color', 'variant__size'):
            cost = item.quantity * item.price_at_time
            variant_description_parts = []
            if item.variant.color:
                variant_description_parts.append(item.variant.color.name)
            if item.variant.size:
                variant_description_parts.append(item.variant.size.name)
            variant_info = ", ".join(variant_description_parts)
            
            items_data.append({
                'product_name': item.variant.product.name,
                'variant_info': f" ({variant_info})" if variant_info else "",
                'price': item.price_at_time,
                'quantity': item.quantity,
                'cost': cost
            })
        return items_data

    # Метод для обновления total_price (будет вызываться сигналом или из save_formset)
    def update_total_price(self):
        """Вычисляет и обновляет общую стоимость заказа на основе его позиций."""
        if not self.pk: # Если заказ еще не сохранен (нет pk), то и items быть не может.
            self.total_price = Decimal('0.00')
            # Не вызываем save() здесь, т.к. объект еще не сохранен первично.
            # default=Decimal('0.00') в поле total_price позаботится об этом при первом save().
            return

        # Используем aggregate для подсчета суммы на стороне БД - эффективнее
        # Убеждаемся, что items существуют, прежде чем пытаться агрегировать
        aggregation = self.items.aggregate(
            calculated_total=Sum(F('quantity') * F('price_at_time'), output_field=DecimalField())
        )
        new_total_price = aggregation['calculated_total'] or Decimal('0.00')
        
        # Обновляем поле и сохраняем только если значение изменилось,
        # и только это поле, чтобы избежать рекурсии с сигналами/save()
        if self.total_price != new_total_price:
            self.total_price = new_total_price
            # Важно: используем super().save() или save(update_fields=...)
            # чтобы избежать бесконечной рекурсии, если этот метод вызывается из переопределенного save()
            # или если есть сигнал post_save на Order, который тоже вызывает этот метод.
            # В данном случае, если этот метод вызывается сигналом от OrderItem, то просто self.save()
            # вызовет еще один сигнал post_save для Order, что нежелательно.
            # Поэтому используем update_fields.
            super(Order, self).save(update_fields=['total_price'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Заказ")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, verbose_name="Вариант товара")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    # price_at_time должно быть обязательным, его значение устанавливается при создании OrderItem
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент покупки")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ['order']

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} ({self.variant.sku}) в заказе №{self.order.id}"

    @property
    def item_total_price(self):
        if self.quantity is not None and self.price_at_time is not None:
            try:
                return self.quantity * self.price_at_time
            except TypeError: 
                return Decimal('0.00')
        return Decimal('0.00')
    item_total_price.fget.short_description = "Сумма по позиции"

# --- Сигналы для автоматического обновления Order.total_price ---
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=OrderItem)
def order_item_changed_receiver(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после сохранения или удаления OrderItem.
    Он пересчитывает и обновляет total_price связанного Order.
    """
    # instance - это объект OrderItem, который был сохранен или удален
    # instance.order - это связанный заказ
    if instance.order: # Убедимся, что есть связанный заказ
        instance.order.update_total_price()


class Promo(models.Model):
    title = models.CharField(max_length=150, verbose_name="Название акции")
    description = models.TextField(verbose_name="Описание акции", blank=True, null=True)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100.00)],
        verbose_name="Процент скидки"
    )
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    products = models.ManyToManyField(
        Product,
        through='PromoProduct',
        related_name='promotions',
        verbose_name="Товары в акции",
        blank=True
    )

    class Meta:
        verbose_name = "Промоакция"
        verbose_name_plural = "Промоакции"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} ({self.discount_percent}%)"

    def is_currently_active(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date
    is_currently_active.boolean = True
    is_currently_active.short_description = "Действует сейчас?"


class PromoProduct(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE, verbose_name="Промоакция")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")

    class Meta:
        verbose_name = "Товар в промоакции"
        verbose_name_plural = "Товары в промоакциях"
        unique_together = ('promo', 'product')

    def __str__(self):
        return f"Товар '{self.product.name}' в акции '{self.promo.title}'"