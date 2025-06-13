# st/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Демонстрационные URL для различных функций ORM и Django
    path('products-demo-extended/', views.product_list_view_extended, name='products_demo_extended_list'),
    path('products-optimized/', views.optimized_product_list_view, name='products_optimized_list'),
    
    # CRUD для модели TechType
    path('techtypes/', views.TechTypeListView.as_view(), name='tech_type_list'),
    path('techtype/add/', views.TechTypeCreateView.as_view(), name='tech_type_create'),
    path('techtype/<int:pk>/', views.TechTypeDetailView.as_view(), name='tech_type_detail'),
    path('techtype/<int:pk>/update/', views.TechTypeUpdateView.as_view(), name='tech_type_update'),
    path('techtype/<int:pk>/delete/', views.TechTypeDeleteView.as_view(), name='tech_type_delete'),

    # CRUD для модели Product (пользовательский интерфейс)
    path('products/', views.ProductListViewUser.as_view(), name='product_user_list'), # Изменил URL для большей ясности
    path('product/add/', views.ProductCreateUserView.as_view(), name='product_user_create'), # Изменил URL
    # Этот URL будет использоваться методом get_absolute_url() модели Product
    path('product/<int:pk>/', views.ProductDetailViewUser.as_view(), name='product_detail_view'), # ИЗМЕНЕНО ИМЯ НА 'product_detail_view'
    path('product/<int:pk>/update/', views.ProductUpdateUserView.as_view(), name='product_user_update'), # Изменил URL
    path('product/<int:pk>/delete/', views.ProductDeleteUserView.as_view(), name='product_user_delete'), # Изменил URL

    # Генерация PDF для заказа из админки
    path('admin/order/<int:order_id>/pdf/', views.admin_order_pdf, name='admin_order_pdf'),
    
    # Пример редиректа для старых URL продуктов
    path('old-product/<str:old_id>/', views.old_product_redirect_view, name='old_product_redirect'),
]