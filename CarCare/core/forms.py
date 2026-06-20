from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ServiceRequest, Vehicle
from .models import ChatMessage

class SignUpForm(UserCreationForm):
    KERALA_DISTRICTS = [
        ('', 'Select your District...'), # Default empty option
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
    district = forms.ChoiceField(choices=KERALA_DISTRICTS, widget=forms.Select(attrs={'class': 'form-control'}))
    phone = forms.CharField(required=True)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)


    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'phone', 'district', 'role', 'garage_name', 'license_number')

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['vehicle', 'service_type', 'description', 'location']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'location': forms.TextInput(attrs={'placeholder': 'Enter address or Click SOS for GPS'}),
        }

    def __init__(self, user, *args, **kwargs):
        super(ServiceRequestForm, self).__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=user)

from django import forms
from .models import Vehicle

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        # Include fields you want the user to fill
        fields = ['make', 'model', 'year', 'reg_number'] 
        # Exclude 'owner' because we set that automatically in the view

class ChatForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['message', 'image']
        widgets = {
            'message': forms.TextInput(attrs={
                'class': 'chat-input', 
                'placeholder': 'Type a message...',
                'autocomplete': 'off'
            }),
        }