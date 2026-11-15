from django.urls import path
from . import views
app_name = 'store'
urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/add/', views.product_create, name='product_add'),
    path('product/<int:pk>/likes', views.like_product, name='like_product'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('product/<int:pk>/edit/', views.product_update, name='product_update'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('search/', views.product_search, name='product_search'),
    path('notifications/', views.notification_list, name = 'notification_list'),
    path('register/', views.register_view, name='register'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('payment/checkout/<int:product_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
]