import mimetypes
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ApplicationStatusForm,
    AdminUserCreationForm,
    DiagnosisForm,
    MainServiceForm,
    MedicineForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    PaymentSubmissionForm,
    PortalContactDetailsForm,
    ServiceForm,
    RegistrationRequestForm,
    UserLoginForm,
)
from .models import (
    Diagnosis,
    MainService,
    Medicine,
    PortalContactDetails,
    PasswordResetOTP,
    RegistrationRequest,
    Service,
    ServiceApplication,
)

User = get_user_model()
logger = logging.getLogger(__name__)

def home(request):
    reference_number = request.GET.get("ref", "").strip()[:24]
    registration_request = None
    application = None

    if reference_number:
        reference_number_upper = reference_number.upper()
        registration_request = RegistrationRequest.objects.filter(
            reference_number__iexact=reference_number
        ).first()

        if not registration_request:
            receipt_suffix = reference_number_upper
            if receipt_suffix.startswith("CSP-"):
                receipt_suffix = receipt_suffix[4:]

            if receipt_suffix.isdigit():
                application = ServiceApplication.objects.select_related("service").filter(
                    pk=int(receipt_suffix)
                ).first()

    contact_details = PortalContactDetails.objects.filter(pk=1).first()
    return render(request, "home.html", {
        "reference_number": reference_number,
        "registration_request": registration_request,
        "application": application,
        "tracking_performed": bool(reference_number),
        "contact_details": contact_details,
    })

@login_required
def dashboard(request):
    services = (
        Service.objects.filter(main_service__is_active=True, is_active=True)
        .select_related("main_service")
    )
    applications = request.user.service_applications.select_related("service").all()
    return render(request, "dashboard.html", {
        "services": services,
        "applications": applications,
    })


def medicine_list(request, id):

    diagnosis = Diagnosis.objects.get(id=id)

    medicines = Medicine.objects.filter(diagnosis=diagnosis)

    return render(request, 'medicine_list.html', {
        'diagnosis': diagnosis,
        'medicines': medicines
    })



def logout_view(request):

    logout(request)

    return redirect('/home/')



@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def admin_dashboard(request):
    main_services = MainService.objects.prefetch_related("services").all()
    return render(request, "admin_dashboard.html", {
        "main_services": main_services,
        "main_service_count": MainService.objects.count(),
        "service_count": Service.objects.count(),
        "active_service_count": Service.objects.filter(is_active=True).count(),
        "application_count": ServiceApplication.objects.count(),
        "unpaid_application_count": ServiceApplication.objects.filter(
            payment_status="unpaid"
        ).count(),
    })

def add_diagnosis(request):

    if request.method == 'POST':

        name = request.POST.get('name')

        if name:
            Diagnosis.objects.create(name=name)
            return redirect('/admin-dashboard/')

    return render(request, 'add_diagnosis.html')





def delete_diagnosis(request, id):

    diagnosis = get_object_or_404(Diagnosis, id=id)

    diagnosis.delete()

    return redirect('/admin-dashboard/')


def add_medicine(request):

    diagnosis = Diagnosis.objects.all()

    if request.method == 'POST':

        diagnosis_id = request.POST.get('diagnosis')

        diagnosis_obj = Diagnosis.objects.get(id=diagnosis_id)

        Medicine.objects.create(
            diagnosis=diagnosis_obj,
            name=request.POST.get('name'),
            dosage=request.POST.get('dosage')
        )

        return redirect('/admin-dashboard/')

    return render(request, 'add_medicine.html', {
        'diagnosis': diagnosis
    })


def edit_medicine(request, id):

    medicine = get_object_or_404(Medicine, id=id)

    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            return redirect('/admin-dashboard/')
    else:
        form = MedicineForm(instance=medicine)

    return render(request, 'edit_medicine.html', {
        'form': form,
        'medicine': medicine
    })


# views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login


def user_login(request):
    form = UserLoginForm(
        request,
        data=request.POST if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if user.is_superuser:
            return redirect("admin_dashboard")
        return redirect("dashboard")
    return render(request, "login.html", {"form": form})


def request_password_reset(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        request.session.pop("password_reset_user_id", None)
        request.session.pop("password_reset_email_error", None)

        if user:
            now = timezone.now()
            recent_requests = PasswordResetOTP.objects.filter(
                user=user,
                created_at__gte=now - timedelta(hours=1),
            ).count()
            if recent_requests < 3:
                PasswordResetOTP.objects.filter(
                    user=user,
                    used_at__isnull=True,
                ).update(used_at=now)
                code = f"{secrets.randbelow(1_000_000):06d}"
                otp_record = PasswordResetOTP.objects.create(
                    user=user,
                    code_hash=make_password(code),
                    expires_at=now + timedelta(minutes=10),
                )
                request.session["password_reset_user_id"] = user.pk
                if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
                    logger.error(
                        "Password reset email backend is console-only for user %s",
                        user.pk,
                    )
                    sent = False
                else:
                    try:
                        sent = send_mail(
                            subject="Your password reset code",
                            message=(
                                f"Your SEVA ONE password reset code is: {code}\n\n"
                                "This code expires in 10 minutes and can only be used once. "
                                "If you did not request this, ignore this email."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        ) == 1
                    except Exception:
                        logger.exception(
                            "Failed to send password reset email for user %s",
                            user.pk,
                        )
                        sent = False
                if not sent:
                    logger.error("Password reset email was not sent for user %s", user.pk)
                    otp_record.used_at = timezone.now()
                    otp_record.save(update_fields=["used_at"])
                    request.session["password_reset_email_error"] = True

        return redirect("verify_password_reset")
    return render(request, "password_reset_request.html", {"form": form})


def verify_password_reset(request):
    user_id = request.session.get("password_reset_user_id")
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if request.method == "POST" and not user:
        email = request.POST.get("email", "").strip()
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()

    form = PasswordResetConfirmForm(
        request.POST if request.method == "POST" else None,
        user=user,
    )

    if request.method == "POST":
        if not user:
            if form.is_valid():
                form.add_error(None, "The code is invalid or expired. Request a new code and try again.")
        elif form.is_valid():
            now = timezone.now()
            with transaction.atomic():
                otp_record = PasswordResetOTP.objects.select_for_update().filter(
                    user=user,
                    used_at__isnull=True,
                    expires_at__gt=now,
                ).order_by("-created_at").first()
                if not otp_record or otp_record.attempts >= 5:
                    form.add_error(None, "The code is invalid or expired. Request a new code and try again.")
                elif not check_password(form.cleaned_data["otp"], otp_record.code_hash):
                    otp_record.attempts += 1
                    if otp_record.attempts >= 5:
                        otp_record.used_at = now
                    otp_record.save(update_fields=["attempts", "used_at"])
                    form.add_error("otp", "The code is invalid or expired. Request a new code and try again.")
                else:
                    user.set_password(form.cleaned_data["new_password1"])
                    user.save(update_fields=["password"])
                    PasswordResetOTP.objects.filter(
                        user=user,
                        used_at__isnull=True,
                    ).update(used_at=now)
                    request.session.pop("password_reset_user_id", None)
                    request.session.pop("password_reset_email_error", None)
                    return redirect("password_reset_complete")

    return render(
        request,
        "password_reset_verify.html",
        {
            "form": form,
            "reset_user": user,
            "delivery_error": request.session.get("password_reset_email_error", False),
        },
    )


def password_reset_complete(request):
    return render(request, "password_reset_complete.html")


def register(request):
    form = RegistrationRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        registration_request = form.save()
        return redirect(
            f"{reverse('home')}?ref={registration_request.reference_number}"
        )
    return render(request, "register.html", {"form": form})


def contact(request):
    contact_details = PortalContactDetails.objects.filter(pk=1).first()
    return render(request, "contact.html", {"contact_details": contact_details})


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def manage_contact_details(request):
    contact_details, _ = PortalContactDetails.objects.get_or_create(pk=1)
    form = PortalContactDetailsForm(
        request.POST if request.method == "POST" else None,
        instance=contact_details,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Portal contact details updated.")
        return redirect("manage_contact_details")
    return render(request, "manage_contact_details.html", {"form": form})


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def manage_users(request):
    users = User.objects.filter(is_superuser=False).order_by("username")
    registration_requests = RegistrationRequest.objects.select_related(
        "reviewed_by"
    ).all()
    return render(request, "manage_users.html", {
        "users": users,
        "registration_requests": registration_requests,
        "pending_request_count": RegistrationRequest.objects.filter(
            status="pending"
        ).count(),
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def create_requested_user(request, request_id):
    registration_request = get_object_or_404(
        RegistrationRequest,
        pk=request_id,
        status="pending",
    )
    name_parts = registration_request.full_name.split(maxsplit=1)
    initial = {
        "first_name": name_parts[0],
        "last_name": name_parts[1] if len(name_parts) > 1 else "",
        "email": registration_request.email,
    }
    form = AdminUserCreationForm(
        request.POST if request.method == "POST" else None,
        initial=initial if request.method == "GET" else None,
    )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        registration_request.status = "approved"
        registration_request.reviewed_at = timezone.now()
        registration_request.reviewed_by = request.user
        registration_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])

        credentials_sent = False
        console_backend = settings.EMAIL_BACKEND.endswith("console.EmailBackend")
        if not console_backend:
            try:
                credentials_sent = send_mail(
                    subject="Your SEVA ONE login details",
                    message=(
                        f"Hello {registration_request.full_name},\n\n"
                        "Your account request has been approved. Use these details to sign in:\n\n"
                        f"Username: {user.username}\n"
                        f"Temporary password: {form.cleaned_data['password1']}\n\n"
                        f"Sign in: {request.build_absolute_uri(reverse('login'))}\n\n"
                        "Please keep these credentials private."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[registration_request.email],
                    fail_silently=False,
                ) == 1
            except Exception:
                credentials_sent = False

        if credentials_sent:
            registration_request.credentials_sent_at = timezone.now()
            registration_request.save(update_fields=["credentials_sent_at"])
            messages.success(request, f"Account {user.username} created and credentials emailed.")
        elif console_backend:
            messages.warning(
                request,
                f"Account {user.username} created, but email delivery is not configured. Configure SMTP and share these credentials securely.",
            )
        else:
            messages.error(
                request,
                f"Account {user.username} was created, but the credential email could not be delivered. Share the credentials securely or configure SMTP.",
            )
        return redirect("manage_users")
    return render(request, "admin_create_user.html", {
        "form": form,
        "registration_request": registration_request,
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
@require_POST
def reject_registration_request(request, request_id):
    registration_request = get_object_or_404(
        RegistrationRequest,
        pk=request_id,
        status="pending",
    )
    registration_request.status = "rejected"
    registration_request.reviewed_at = timezone.now()
    registration_request.reviewed_by = request.user
    registration_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    messages.success(request, "Registration request rejected.")
    return redirect("manage_users")


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
@require_POST
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    username = user.username
    user.delete()
    messages.success(request, f"User {username} deleted.")
    return redirect("manage_users")


# Edit Medicine


# Delete Medicine

def delete_medicine(request, id):

    medicine = get_object_or_404(
        Medicine,
        id=id
    )

    medicine.delete()

    return redirect('/admin-dashboard/')


def edit_diagnosis(request, id):

    diagnosis = get_object_or_404(Diagnosis, id=id)

    if request.method == 'POST':
        form = DiagnosisForm(request.POST, instance=diagnosis)
        if form.is_valid():
            form.save()
            return redirect('/admin-dashboard/')
    else:
        form = DiagnosisForm(instance=diagnosis)

    return render(request, 'edit_diagnosis.html', {
        'form': form,
        'diagnosis': diagnosis
    })


# Citizen service catalog and admin management
def service_catalog(request):
    main_services = (
        MainService.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch("services", queryset=Service.objects.filter(is_active=True))
        )
    )
    return render(request, "service_catalog.html", {"main_services": main_services})


@login_required
@require_POST
def apply_for_service(request, service_id):
    service = get_object_or_404(
        Service.objects.select_related("main_service"),
        pk=service_id,
        is_active=True,
        main_service__is_active=True,
    )
    application = ServiceApplication.objects.create(
        user=request.user,
        service=service,
        service_name=service.name,
        amount=service.amount,
        payment_status="unpaid" if service.amount > 0 else "waived",
        applicant_name=request.user.get_full_name() or request.user.get_username(),
        applicant_email=request.user.email or "",
    )
    return redirect("payment_page", application_id=application.pk)


@login_required
def payment_page(request, application_id):
    application = get_object_or_404(
        ServiceApplication.objects.select_related("service"),
        pk=application_id,
    )
    if not request.user.is_superuser and application.user_id != request.user.id:
        raise Http404
    if not application.service:
        messages.error(request, "The service application form is no longer available.")
        return redirect("dashboard")

    if request.method == "POST":
        if application.payment_status in {"paid", "waived"}:
            return redirect(application.service.google_form_url)
        if application.amount <= 0:
            return redirect(application.service.google_form_url)
        form = PaymentSubmissionForm(
            request.POST,
            request.FILES,
            instance=application,
        )
        if form.is_valid():
            application = form.save(commit=False)
            application.payment_status = "verification_pending"
            application.save()
            return redirect(application.service.google_form_url)
    else:
        form = PaymentSubmissionForm(instance=application)

    return render(request, "payment_page.html", {
        "application": application,
        "form": form,
    })


def service_payment_qr(request, service_id):
    service = get_object_or_404(
        Service.objects.filter(
            is_active=True,
            main_service__is_active=True,
        ),
        pk=service_id,
    )
    if not service.payment_qr_image:
        raise Http404
    content_type = mimetypes.guess_type(service.payment_qr_image.name)[0]
    return FileResponse(
        service.payment_qr_image.open("rb"),
        content_type=content_type or "application/octet-stream",
    )


@login_required
def application_receipt(request, application_id):
    application = get_object_or_404(
        ServiceApplication.objects.select_related("service", "user"),
        pk=application_id,
    )
    if not request.user.is_superuser and application.user_id != request.user.id:
        raise Http404
    return render(request, "application_receipt.html", {"application": application})


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def manage_services(request):
    main_services = MainService.objects.prefetch_related("services").all()
    return render(request, "manage_services.html", {"main_services": main_services})


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def manage_applications(request):
    applications = ServiceApplication.objects.select_related("user", "service").all()
    payment_status = request.GET.get("payment_status", "")
    work_status = request.GET.get("work_status", "")
    service_id = request.GET.get("service", "")

    payment_values = dict(ServiceApplication.PAYMENT_STATUS_CHOICES)
    work_values = dict(ServiceApplication.WORK_STATUS_CHOICES)
    if payment_status in payment_values:
        applications = applications.filter(payment_status=payment_status)
    if work_status in work_values:
        applications = applications.filter(work_status=work_status)
    if service_id.isdigit():
        applications = applications.filter(service_id=service_id)

    return render(request, "manage_applications.html", {
        "applications": applications,
        "services": Service.objects.order_by("name"),
        "payment_statuses": ServiceApplication.PAYMENT_STATUS_CHOICES,
        "work_statuses": ServiceApplication.WORK_STATUS_CHOICES,
        "selected_payment_status": payment_status,
        "selected_work_status": work_status,
        "selected_service": service_id,
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
@require_POST
def update_application_status(request, application_id):
    application = get_object_or_404(ServiceApplication, pk=application_id)
    form = ApplicationStatusForm(request.POST, instance=application)
    if form.is_valid():
        form.save()
        messages.success(request, "Application statuses updated.")
    else:
        messages.error(request, "Could not update application statuses.")
    return redirect("manage_applications")


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def add_main_service(request):
    form = MainServiceForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Main service added.")
        return redirect("manage_services")
    return render(request, "service_form.html", {
        "form": form,
        "title": "Add Main Service",
        "help_text": "Create a category such as Aadhaar Services or PAN Services.",
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def add_service(request):
    initial = {"main_service": request.GET.get("main_service")}
    form = ServiceForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        initial=initial if request.method == "GET" else None,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sub-service and application form link added.")
        return redirect("manage_services")
    return render(request, "service_form.html", {
        "form": form,
        "title": "Add Sub-service",
        "submit_label": "Add sub-service",
        "help_text": "Add a service under a main category and paste its Google Form URL.",
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
def edit_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    form = ServiceForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=service,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sub-service updated.")
        return redirect("manage_services")
    return render(request, "service_form.html", {
        "form": form,
        "title": "Edit Sub-service",
        "submit_label": "Save changes",
        "help_text": "Update the category, service details, status, or Google Form link.",
    })


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
@require_POST
def delete_service(request, service_id):
    get_object_or_404(Service, pk=service_id).delete()
    messages.success(request, "Sub-service deleted.")
    return redirect("manage_services")


@user_passes_test(lambda user: user.is_superuser, login_url="/login/")
@require_POST
def delete_main_service(request, service_id):
    get_object_or_404(MainService, pk=service_id).delete()
    messages.success(request, "Main service and its sub-services deleted.")
    return redirect("manage_services")
