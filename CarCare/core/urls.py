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
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('book-service/', views.book_service, name='book_service'),
    path('update-status/<int:request_id>/', views.update_status, name='update_status'),
    path('track-service/<int:request_id>/', views.track_service, name='track_service'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/delete-user/<int:pk>/', views.delete_user, name='admin_delete_user'),
    path('approve-tech/<int:user_id>/', views.approve_technician, name='approve_technician'),
    path('reject-tech/<int:user_id>/', views.reject_technician, name='reject_technician'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle')
    
]
