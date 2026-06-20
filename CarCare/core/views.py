import datetime
import random
import string
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q
from django.urls import reverse

# --- CRITICAL NEW IMPORTS FOR EMAIL ---
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages as django_messages # Renamed to prevent dictionary conflict

from .forms import SignUpForm, ServiceRequestForm, VehicleForm, ChatForm
from .models import ServiceRequest, User, Vehicle, ServicePart, ChatMessage
from .utils import render_to_pdf 

# --- HOME & AUTHENTICATION ---

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # --- 1. TECHNICIAN REGISTRATION ---
            if user.role == 'technician':
                user.is_approved = False
                user.save()
                
                # Build exact clickable links for the Admin email
                approve_url = request.build_absolute_uri(reverse('approve_technician', args=[user.id]))
                reject_url = request.build_absolute_uri(reverse('reject_technician', args=[user.id]))
                
                # Send Email to Admin (You)
                try:
                    subject = f"ACTION REQUIRED: New Technician Registration - {user.username}"
                    body = (
                        f"Hello Admin,\n\n"
                        f"A new Technician/Service Center has registered and is waiting for your approval.\n\n"
                        f"--- DETAILS ---\n"
                        f"Name: {user.first_name} {user.last_name}\n"
                        f"Username: {user.username}\n"
                        f"District: {getattr(user, 'district', 'N/A')}\n"
                        f"Phone: {getattr(user, 'phone', 'N/A')}\n\n"
                        f"--- ACTIONS ---\n"
                        f"✅ Click here to APPROVE:\n{approve_url}\n\n"
                        f"❌ Click here to REJECT:\n{reject_url}\n\n"
                        f"Note: You must be logged in as an Admin on your browser for the links to work."
                    )
                    
                    # Sends the email to the DEFAULT_FROM_EMAIL (ashimcs23@gmail.com)
                    send_mail(
                        subject, 
                        body, 
                        settings.DEFAULT_FROM_EMAIL, 
                        [settings.DEFAULT_FROM_EMAIL], 
                        fail_silently=False
                    )
                    print(f"Admin Approval Email sent for {user.username}!")
                except Exception as e:
                    print(f"Admin Email Failed: {e}")

                return render(request, 'registration_pending.html')
            
            # --- 2. CUSTOMER REGISTRATION ---
            else:
                # Customers are auto-approved
                user.is_approved = True
                user.save()
                
                # Send a Welcome Email to the Customer
                if user.email:
                    try:
                        send_mail(
                            "Welcome to CarCare!",
                            f"Hello {user.username},\n\nYour account has been created successfully. You can now book services directly from your dashboard.",
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email],
                            fail_silently=True
                        )
                    except Exception as e:
                        print(f"Welcome Email Failed: {e}")

                login(request, user)
                return redirect('dashboard')
    else:
        form = SignUpForm()
        
    return render(request, 'register.html', {'form': form})
# --- DASHBOARDS ---

@login_required
def dashboard(request):
    user = request.user
    
    # 1. ADMIN
    if user.is_superuser or getattr(user, 'role', '') == 'admin':
        return redirect('admin_dashboard') 
    
    # 2. CUSTOMER
    elif getattr(user, 'role', '') == 'customer':
        requests = ServiceRequest.objects.filter(vehicle__owner=user).order_by('-created_at')
        vehicles = Vehicle.objects.filter(owner=user)
        available_technicians = User.objects.filter(role='technician', district=user.district, is_approved=True)
        
        context = {
            'requests': requests, 
            'vehicles': vehicles, 
            'technicians': available_technicians
        }
        return render(request, 'dashboard_customer.html', context)

    # 3. TECHNICIAN
    elif getattr(user, 'role', '') == 'technician':
        if not getattr(user, 'is_approved', False):
            return render(request, 'registration_pending.html')

        active_jobs = ServiceRequest.objects.filter(
            technician=user, 
            status__in=['in_progress', 'payment_pending']
        ).order_by('-created_at')

        new_requests = ServiceRequest.objects.filter(
            status='pending'
        ).filter(
            Q(technician=user) |  # Assigned to me specifically
            Q(technician__isnull=True) # OR Unassigned (Open Pool)
        ).order_by('-created_at')
        
        completed_jobs = ServiceRequest.objects.filter(
            technician=user, 
            status='completed'
        ).order_by('-created_at')
        
        # Combine lists for display
        all_jobs = list(active_jobs) + list(new_requests) + list(completed_jobs)

        context = {
            'requests': all_jobs, 
            'completed_count': completed_jobs.count(),
            'user': user,
            'active_job': active_jobs.first() if active_jobs else None
        }
        return render(request, 'dashboard_tech.html', context)

    return render(request, 'home.html')

@staff_member_required
def admin_dashboard(request):
    total_users = User.objects.filter(role='customer').count()
    total_techs = User.objects.filter(role='technician', is_approved=True).count()
    pending_techs = User.objects.filter(role='technician', is_approved=False)

    all_reqs = ServiceRequest.objects.all()
    active_requests = all_reqs.filter(status='in_progress').count()
    completed_count = all_reqs.filter(status='completed').count()
    
    revenue_data = all_reqs.filter(status='completed').aggregate(Sum('total_cost'))
    total_revenue = revenue_data['total_cost__sum'] or 0

    recent_requests = all_reqs.select_related('customer', 'technician').order_by('-created_at')[:10]
    all_users = User.objects.all().order_by('-date_joined')[:20]

    context = {
        'total_users': total_users,
        'total_techs': total_techs,
        'pending_techs': pending_techs,
        'active_requests': active_requests,
        'completed_count': completed_count,
        'total_revenue': total_revenue,
        'recent_requests': recent_requests,
        'all_users': all_users,
    }
    return render(request, 'dashboard_admin.html', context)

# --- SERVICE MANAGEMENT ---

@login_required
def book_service(request):
    user_home_district = request.user.district if request.user.district else "Ernakulam"
    selected_district = request.GET.get('district', user_home_district).strip().title()

    available_technicians = User.objects.filter(
        role='technician', 
        is_approved=True, 
        is_available=True,
        district__iexact=selected_district
    )

    if request.method == 'POST':
        form = ServiceRequestForm(request.user, request.POST)
        if form.is_valid():
            serv = form.save(commit=False)
            serv.customer = request.user
            serv.status = 'pending'
            
            # Technician Assignment
            tech_id = request.POST.get('technician_id')
            if tech_id and tech_id.strip():
                try:
                    assigned_tech = User.objects.get(id=int(tech_id))
                    serv.technician = assigned_tech
                    django_messages.success(request, f"Request sent to {assigned_tech.username}!")
                except (ValueError, User.DoesNotExist):
                    django_messages.info(request, "Technician unavailable, broadcasting to nearby.")
            else:
                django_messages.info(request, "Broadcasting request to nearby technicians.")

            # Location
            final_loc = request.POST.get('location')
            if final_loc:
                serv.location = final_loc

            serv.save()

            # ==========================================
            # EMAIL 1: BOOKING CONFIRMATION TO CUSTOMER
            # ==========================================
            print("\n--- DEBUG EMAIL START ---")
            print(f"Customer's saved email address is: '{request.user.email}'")

            if request.user.email:
                try:
                    print("Attempting to send email now...")
                    subject = f"CarCare Booking Pending - #{serv.id}"
                    body = f"Hello {request.user.username},\n\nYour request for '{serv.get_service_type_display()}' has been logged and is currently Pending.\nWe are looking for a technician in your area.\n\nThank you for using CarCare!"
                    
                    # Notice: fail_silently is False so we can catch exact errors
                    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=False)
                    print("Email successfully processed by Django!")
                    
                except Exception as e:
                    print(f"EMAIL CRASHED! The error is: {e}")
            else:
                print("EMAIL SKIPPED: The user logged in right now does NOT have an email address in the database!")
                
            print("--- DEBUG EMAIL END ---\n")
            # ==========================================

            return redirect('dashboard')
    else:
        form = ServiceRequestForm(request.user)
    
    kerala_districts = [
        'Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 
        'Kollam', 'Kottayam', 'Kozhikode', 'Malappuram', 'Palakkad', 
        'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad'
    ]

    return render(request, 'book_service.html', {
        'form': form, 
        'technicians': available_technicians,
        'selected_district': selected_district,
        'kerala_districts': kerala_districts
    })

@login_required
@require_POST
def update_status(request, request_id):
    job = get_object_or_404(ServiceRequest, id=request_id)
    action = request.POST.get('status')
    
    send_alert = False
    subject = ""
    body = ""

    # --- 1. HANDLE ACCEPTING A JOB ---
    if action == 'in_progress':
        if job.technician is None:
            job.technician = request.user
        elif job.technician != request.user:
            django_messages.error(request, "This job has already been taken by another technician.")
            return redirect('dashboard')
            
        job.status = 'in_progress'
        django_messages.success(request, "Job Accepted! Head to the location.")
        
        # EMAIL PREP: Tech Accepted
        send_alert = True
        subject = f"Technician En Route - Request #{job.id}"
        body = f"Hello {job.customer.username},\n\nGood news! Technician {job.technician.username} has accepted your request and is on their way.\nContact them at: {job.technician.phone}"

    # --- 2. HANDLE REJECTING A JOB (FIXED) ---
    elif action == 'rejected':
        # Change the status entirely so it permanently disappears from your feed
        job.status = 'rejected'
        job.technician = None
        django_messages.warning(request, "Job rejected. It has been permanently removed from your feed.")
        
        # EMAIL PREP: Tell the customer to rebook
        send_alert = True
        subject = f"Booking Update - Request #{job.id}"
        body = f"Hello {job.customer.username},\n\nUnfortunately, your service request was rejected by the technician. Please log in to your dashboard to re-book or broadcast to other nearby technicians."

    # --- 3. HANDLE COMPLETING A JOB ---
    elif action == 'completed':
        if job.technician != request.user:
            django_messages.error(request, "You are not authorized to manage this job.")
            return redirect('dashboard')
            
        job.status = 'completed'
        django_messages.success(request, "Great job! Service marked as completed.")
        
        # EMAIL PREP: Job Done
        send_alert = True
        subject = f"Service Completed - Request #{job.id}"
        body = f"Hello {job.customer.username},\n\nYour service has been marked as Completed by {job.technician.username}. Thank you for using CarCare!"

    job.save()

    # ==========================================
    # SEND THE EMAILS
    # ==========================================
    if send_alert and job.customer.email:
        try:
            # We are keeping fail_silently=False so you can see any terminal errors
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [job.customer.email], fail_silently=False)
        except Exception as e:
            print(f"Email failed: {e}")

    return redirect('dashboard')

@login_required
def track_service(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    steps = ['Pending', 'Approved', 'In Progress', 'Completed']
    
    current_step_index = -1
    if service_request.status in steps:
        current_step_index = steps.index(service_request.status)
        
    context = {
        'service': service_request,
        'steps': steps,
        'current_step_index': current_step_index
    }
    return render(request, 'track_service.html', context)

@login_required
def service_chat(request, request_id):
    service = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.user != getattr(service.vehicle, 'owner', service.customer) and request.user != service.technician:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ChatForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.service_request = service
            msg.sender = request.user
            msg.save()
            return redirect('service_chat', request_id=request_id)
    else:
        form = ChatForm()

    messages_list = ChatMessage.objects.filter(service_request=service).order_by('created_at')

    context = {
        'service': service,
        'messages': messages_list,
        'form': form
    }
    return render(request, 'service_chat.html', context)

# --- VEHICLE MANAGEMENT ---

@login_required
def add_vehicle(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user 
            vehicle.save()
            django_messages.success(request, "Vehicle added successfully!")
            return redirect('dashboard')
    else:
        form = VehicleForm()
    return render(request, 'add_vehicle.html', {'form': form})

# --- ADMIN ACTIONS ---

@staff_member_required
def approve_technician(request, tech_id):
    tech = get_object_or_404(User, id=tech_id, role='technician')
    tech.is_approved = True
    tech.save()
    
    # Optional: Send an email to the technician telling them they are approved!
    if tech.email:
        try:
            send_mail(
                "CarCare Application Approved!",
                f"Hello {tech.username},\n\nGood news! Your technician account has been approved by the admin. You can now log in and start accepting jobs.",
                settings.DEFAULT_FROM_EMAIL,
                [tech.email],
                fail_silently=True
            )
        except Exception:
            pass
            
    django_messages.success(request, f"Technician {tech.username} has been APPROVED.")
    return redirect('admin:index') # Redirects you back to the admin panel

@staff_member_required
def reject_technician(request, tech_id):
    tech = get_object_or_404(User, id=tech_id, role='technician')
    
    # Optional: Send a rejection email before deleting
    if tech.email:
        try:
            send_mail(
                "CarCare Application Update",
                f"Hello {tech.username},\n\nUnfortunately, your application to join CarCare as a technician has been declined at this time.",
                settings.DEFAULT_FROM_EMAIL,
                [tech.email],
                fail_silently=True
            )
        except Exception:
            pass
            
    tech.delete() # Deletes the rejected user from the database
    django_messages.warning(request, f"Technician {tech.username} has been REJECTED and removed.")
    return redirect('admin:index')

@staff_member_required
def delete_user(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    user_to_delete.delete()
    django_messages.success(request, f"User {user_to_delete.username} has been deleted.")
    return redirect('admin_dashboard')

@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    user_to_delete = get_object_or_404(User, id=user_id)
    user_to_delete.delete()
    return redirect('admin_dashboard')

# --- BILLING & PAYMENT ---

@login_required
def generate_invoice(request, request_id):
    job = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        labor = float(request.POST.get('labor_cost', 0))
        job.labor_cost = labor
        
        part_names = request.POST.getlist('part_name[]')
        part_costs = request.POST.getlist('part_cost[]')
        
        total_parts = 0
        job.parts.all().delete()
        
        for name, cost in zip(part_names, part_costs):
            if name and cost:
                c = float(cost)
                ServicePart.objects.create(service=job, part_name=name, cost=c)
                total_parts += c
        
        job.parts_cost = total_parts
        job.total_cost = labor + total_parts
        job.status = 'payment_pending'
        job.save()
        
        return redirect('dashboard')  

    return render(request, 'core/generate_invoice.html', {'job': job})

@login_required
def payment_gateway(request, request_id):
    job = get_object_or_404(ServiceRequest, id=request_id)
    
    # Safe check in case vehicle doesn't have an owner attr directly
    customer = getattr(job.vehicle, 'owner', getattr(job, 'customer', None))
    if request.user != customer:
        return redirect('dashboard')
        
    return render(request, 'payment_gateway.html', {'job': job})

@login_required
def process_payment(request, request_id):
    job = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        method = request.POST.get('payment_method')
        
        job.payment_method = method
        job.payment_status = 'paid'
        job.status = 'completed'
        job.save()
        
        if method in ['online', 'card', 'upi']:
            return redirect('payment_success', request_id=job.id)
            
        django_messages.success(request, f"Payment of ₹{job.total_cost} successful via {method.upper()}!")
        return redirect('dashboard')
        
    return redirect('dashboard')

@login_required
def payment_success(request, request_id):
    job = get_object_or_404(ServiceRequest, id=request_id)
    
    rand_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    transaction_id = f"TXN-{job.id}-{rand_suffix}"
    
    context = {
        'job': job,
        'transaction_id': transaction_id,
        'date': timezone.now()
    }
    return render(request, 'payment_success.html', context)

# --- PDF GENERATION ---

def download_invoice(request, request_id):
    service = get_object_or_404(ServiceRequest, id=request_id)
    vehicle = service.vehicle
    customer = getattr(vehicle, 'owner', getattr(vehicle, 'user', getattr(service, 'customer', None)))

    data = {
        'service': service,
        'date': datetime.datetime.now(),
        'customer': customer, 
        'tech': service.technician,
    }
    return render_to_pdf('core/invoice_pdf.html', data)

@login_required
def download_full_report(request):
    services = ServiceRequest.objects.filter(vehicle__owner=request.user).order_by('-created_at')
    total_spent = sum(s.total_cost for s in services if s.total_cost)
    total_services = services.count()
    
    context = {
        'user': request.user,
        'services': services,
        'total_spent': total_spent,
        'total_services': total_services,
        'date': datetime.datetime.now(),
    }
    return render_to_pdf('core/full_report_pdf.html', context)

@login_required
def rebook_service(request, request_id):
    old_job = get_object_or_404(ServiceRequest, id=request_id, customer=request.user)
    
    new_job = ServiceRequest.objects.create(
        customer=request.user,
        vehicle=old_job.vehicle,
        service_type=old_job.service_type,
        description=old_job.description, 
        location=old_job.location,
        status='pending',
        technician=old_job.technician 
    )
    
    django_messages.success(request, f"Service Re-Booked! Request sent to {old_job.technician.username}.")
    return redirect('dashboard')