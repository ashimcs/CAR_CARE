
# Create your models here.
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    IS_CUSTOMER = 'customer'
    IS_TECHNICIAN = 'technician'
    IS_ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (IS_CUSTOMER, 'Car Owner'),
        (IS_TECHNICIAN, 'Technician'),
        (IS_ADMIN, 'Admin'),
    ]

    DISTRICT_CHOICES = [
        ('Alappuzha', 'Alappuzha'),
        ('Ernakulam', 'Ernakulam'),
        ('Idukki', 'Idukki'),
        ('Kannur', 'Kannur'),
        ('Kasaragod', 'Kasaragod'),
        ('Kollam', 'Kollam'),
        ('Kottayam', 'Kottayam'),
        ('Kozhikode', 'Kozhikode'),
        ('Malappuram', 'Malappuram'),
        ('Palakkad', 'Palakkad'),
        ('Pathanamthitta', 'Pathanamthitta'),
        ('Thiruvananthapuram', 'Thiruvananthapuram'),
        ('Thrissur', 'Thrissur'),
        ('Wayanad', 'Wayanad'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=IS_CUSTOMER)
    phone = models.CharField(max_length=15, null=True)
    district = models.CharField(max_length=50, choices=DISTRICT_CHOICES, default='Thiruvananthapuram')
    address = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    garage_name = models.CharField(max_length=100, blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    is_approved = models.BooleanField(default=False) # For technicians

    def __str__(self):
        return self.username

class Vehicle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50) # e.g., Toyota
    model = models.CharField(max_length=50) # e.g., Innova
    reg_number = models.CharField(max_length=20, unique=True)
    year = models.IntegerField()

    def __str__(self):
        return f"{self.make} {self.model} ({self.reg_number})"

class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SERVICE_TYPES = [
        ('emergency', 'Emergency SOS'),
        ('fuel', 'Fuel Delivery'),          # <--- Add this
        ('jump_start', 'Jump Start'),       # <--- Add this
        ('towing', 'Towing'),               # <--- Add this
        ('lockout', 'Lockout'),             # <--- Add this
        ('repair', 'Mechanical Repair'),
        ('general', 'General Service'),
        ('cleaning', 'Car Wash'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    description = models.TextField()
    location = models.CharField(max_length=100, help_text="GPS Coordinates or Address")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_cost_approved = models.BooleanField(default=False)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    PAYMENT_STATUS = [('pending', 'Pending'), ('paid', 'Paid')]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, blank=True, null=True) # 'cash' or 'upi'

    def __str__(self):
        return f"{self.service_type} - {self.customer.username}"
    
class ServicePart(models.Model):
    service = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='parts')
    part_name = models.CharField(max_length=100) # e.g., "Brake Pads"
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.part_name} - {self.cost}"
    
class ChatMessage(models.Model):
    # Link to the specific job
    service_request = models.ForeignKey('ServiceRequest', on_delete=models.CASCADE, related_name='messages')
    
    # Who sent the message (Customer or Technician)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Content
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} at {self.created_at}"