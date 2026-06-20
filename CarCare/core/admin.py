
# Register your models here.
from django.contrib import admin
from .models import User, Vehicle, ServiceRequest

admin.site.register(User)
admin.site.register(Vehicle)
admin.site.register(ServiceRequest)