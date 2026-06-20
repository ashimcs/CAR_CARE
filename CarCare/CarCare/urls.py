"""
URL configuration for CarCare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    # --- 1. Custom Admin Actions ---
    # IMPORTANT: This must come BEFORE 'admin/' to prevent the 404 error
    # We also renamed it to 'custom_delete_user' to match your HTML
    path('admin/delete-user/<int:pk>/', views.delete_user, name='custom_delete_user'),

    # --- 2. Default Admin ---
    path('admin/', admin.site.urls),

    # --- 3. Auth & Core ---
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # --- 4. User Dashboard ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('book-service/', views.book_service, name='book_service'),
    path('update-status/<int:request_id>/', views.update_status, name='update_status'),
    path('track-service/<int:request_id>/', views.track_service, name='track_service'),

    # --- 5. Admin Dashboard ---
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve-tech/<int:tech_id>/', views.approve_technician, name='approve_technician'),
    path('reject-tech/<int:tech_id>/', views.reject_technician, name='reject_technician'),

    path('invoice/<int:request_id>/', views.download_invoice, name='download_invoice'),
    path('report/full-history/', views.download_full_report, name='download_full_report'),
    path('generate-invoice/<int:request_id>/', views.generate_invoice, name='generate_invoice'),
    path('pay/<int:request_id>/', views.process_payment, name='process_payment'),
    path('chat/<int:request_id>/', views.service_chat, name='service_chat'),
    path('payment-gateway/<int:request_id>/', views.payment_gateway, name='payment_gateway'),
    path('process-payment/<int:request_id>/', views.process_payment, name='process_payment'),
    path('payment-success/<int:request_id>/', views.payment_success, name='payment_success'),
    path('rebook/<int:request_id>/', views.rebook_service, name='rebook_service'),
]