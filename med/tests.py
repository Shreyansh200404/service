import re
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .models import (
    MainService,
    PasswordResetOTP,
    PortalContactDetails,
    RegistrationRequest,
    Service,
    ServiceApplication,
)


User = get_user_model()


class LoginTests(TestCase):
    def test_login_works_without_captcha(self):
        user = User.objects.create_user(
            username="plain-login-user",
            password="Secure-Password-123!",
        )

        response = self.client.post(
            reverse("login"),
            {"username": user.username, "password": "Secure-Password-123!"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class ServiceApplicationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="applicant",
            password="test-password",
            email="applicant@example.com",
            first_name="Taylor",
            last_name="Citizen",
        )
        self.other_user = User.objects.create_user(
            username="other-applicant",
            password="test-password",
        )
        self.admin = User.objects.create_superuser(
            username="portal-admin",
            password="test-password",
            email="admin@example.com",
        )
        self.main_service = MainService.objects.create(name="Identity Services")
        self.service = Service.objects.create(
            main_service=self.main_service,
            name="Aadhaar Update",
            description="Update identity details",
            google_form_url="https://forms.google.com/example",
            amount=Decimal("25.50"),
        )

    def test_apply_records_user_and_service_before_redirecting(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("apply_for_service", args=[self.service.pk])
        )

        application = ServiceApplication.objects.get()
        self.assertRedirects(
            response,
            reverse("payment_page", args=[application.pk]),
        )
        self.assertEqual(application.user, self.user)
        self.assertEqual(application.service, self.service)
        self.assertEqual(application.applicant_name, "Taylor Citizen")
        self.assertEqual(application.amount, Decimal("25.50"))
        self.assertEqual(application.payment_status, "unpaid")
        self.assertEqual(application.work_status, "submitted")

        payment_url = reverse("payment_page", args=[application.pk])
        self.assertContains(self.client.get(payment_url), "PhonePe")
        response = self.client.post(
            payment_url,
            {"transaction_ref": "PHONEPE123456"},
        )
        self.assertRedirects(
            response,
            self.service.google_form_url,
            fetch_redirect_response=False,
        )
        application.refresh_from_db()
        self.assertEqual(application.payment_status, "verification_pending")
        self.assertEqual(application.transaction_ref, "PHONEPE123456")

        self.service.amount = Decimal("40.00")
        self.service.save()
        application.refresh_from_db()
        self.assertEqual(application.amount, Decimal("25.50"))

    def test_free_service_application_is_waived(self):
        self.service.amount = Decimal("0.00")
        self.service.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("apply_for_service", args=[self.service.pk])
        )
        application = ServiceApplication.objects.get()
        self.assertRedirects(
            response,
            reverse("payment_page", args=[application.pk]),
        )
        self.assertEqual(application.amount, Decimal("0.00"))
        self.assertEqual(application.payment_status, "waived")

        payment_url = reverse("payment_page", args=[application.pk])
        self.assertContains(self.client.get(payment_url), "No payment is due")
        response = self.client.post(payment_url)
        self.assertRedirects(
            response,
            self.service.google_form_url,
            fetch_redirect_response=False,
        )

    def test_apply_requires_sign_in(self):
        response = self.client.post(
            reverse("apply_for_service", args=[self.service.pk])
        )
        self.assertEqual(ServiceApplication.objects.count(), 0)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_users_only_see_their_own_applications(self):
        own_application = ServiceApplication.objects.create(
            user=self.user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Taylor Citizen",
        )
        ServiceApplication.objects.create(
            user=self.other_user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Other Applicant",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_application.service_name)
        self.assertNotContains(response, "Other Applicant")

    def test_receipt_is_private_to_applicant_and_admin(self):
        application = ServiceApplication.objects.create(
            user=self.other_user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Other Applicant",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("application_receipt", args=[application.pk])
        )
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("application_receipt", args=[application.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, application.receipt_number)

    def test_home_page_tracks_application_by_receipt_number_without_login(self):
        application = ServiceApplication.objects.create(
            user=self.user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Taylor Citizen",
            payment_status="verification_pending",
            work_status="in_progress",
        )

        response = self.client.get(
            reverse("home"),
            {"ref": application.receipt_number},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, application.receipt_number)
        self.assertContains(response, "Application for")
        self.assertContains(response, self.service.name)

    def test_superuser_can_update_application_statuses(self):
        application = ServiceApplication.objects.create(
            user=self.user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Taylor Citizen",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("update_application_status", args=[application.pk]),
            {"payment_status": "paid", "work_status": "completed"},
        )

        application.refresh_from_db()
        self.assertRedirects(response, reverse("manage_applications"))
        self.assertEqual(application.payment_status, "paid")
        self.assertEqual(application.work_status, "completed")

    def test_regular_user_cannot_manage_application_statuses(self):
        application = ServiceApplication.objects.create(
            user=self.user,
            service=self.service,
            service_name=self.service.name,
            applicant_name="Taylor Citizen",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("update_application_status", args=[application.pk]),
            {"payment_status": "paid", "work_status": "completed"},
        )

        application.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(application.payment_status, "unpaid")
        self.assertEqual(application.work_status, "submitted")


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="account-admin",
            password="test-password",
        )
        self.user = User.objects.create_user(
            username="existing-user",
            password="test-password",
        )

    def test_public_registration_only_creates_a_request(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "New Applicant",
                "email": "new-applicant@example.com",
                "phone_number": "+91 98765 43210",
                "reason": "I need portal access.",
            },
        )

        registration_request = RegistrationRequest.objects.get()
        self.assertRedirects(
            response,
            f"{reverse('home')}?ref={registration_request.reference_number}",
        )
        self.assertEqual(registration_request.phone_number, "+91 98765 43210")
        self.assertFalse(User.objects.filter(email="new-applicant@example.com").exists())

        status_response = self.client.get(
            reverse("home"),
            {"ref": registration_request.reference_number},
        )
        self.assertContains(status_response, registration_request.reference_number)
        self.assertContains(status_response, "Pending review")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_creates_requested_account_and_assigns_password(self):
        registration_request = RegistrationRequest.objects.create(
            full_name="New Applicant",
            email="new-applicant@example.com",
            phone_number="+91 98765 43210",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("create_requested_user", args=[registration_request.pk]),
            {
                "username": "new-applicant",
                "first_name": "New",
                "last_name": "Applicant",
                "email": "new-applicant@example.com",
                "password1": "Unique-Temp-Password-948!",
                "password2": "Unique-Temp-Password-948!",
            },
        )

        created_user = User.objects.get(username="new-applicant")
        registration_request.refresh_from_db()
        self.assertRedirects(response, reverse("manage_users"))
        self.assertTrue(created_user.check_password("Unique-Temp-Password-948!"))
        self.assertEqual(registration_request.status, "approved")
        self.assertEqual(registration_request.reviewed_by, self.admin)
        self.assertIsNotNone(registration_request.credentials_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Unique-Temp-Password-948!", mail.outbox[0].body)

        status_response = self.client.get(
            reverse("home"),
            {"ref": registration_request.reference_number},
        )
        self.assertContains(status_response, "credentials were sent")

    def test_regular_user_cannot_open_user_management(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("manage_users"))

        self.assertEqual(response.status_code, 302)

    def test_admin_can_delete_regular_user_but_not_superuser(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("delete_user", args=[self.user.pk]))

        self.assertRedirects(response, reverse("manage_users"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        protected_response = self.client.post(
            reverse("delete_user", args=[self.admin.pk])
        )
        self.assertEqual(protected_response.status_code, 404)

    def test_contact_page_shows_configured_contact_channels(self):
        PortalContactDetails.objects.create(
            pk=1,
            phone_number="+91 98765 43210",
            email="help@example.com",
            whatsapp_number="+91 98765 43210",
            instagram_id="@citizen_services",
        )

        response = self.client.get(reverse("contact"))

        self.assertContains(response, "+91 98765 43210")
        self.assertContains(response, "mailto:help@example.com")
        self.assertContains(response, "https://wa.me/919876543210")
        self.assertContains(response, "https://www.instagram.com/citizen_services/")


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset-user",
            email="reset-user@example.com",
            password="Old-Password-123!",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_otp_changes_password(self):
        response = self.client.post(
            reverse("request_password_reset"),
            {"email": self.user.email},
        )
        self.assertRedirects(response, reverse("verify_password_reset"))
        self.assertEqual(len(mail.outbox), 1)
        form_response = self.client.get(reverse("verify_password_reset"))
        self.assertContains(form_response, 'name="otp"')
        self.assertContains(form_response, 'name="new_password1"')
        self.assertContains(form_response, 'name="new_password2"')
        code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
        otp_record = PasswordResetOTP.objects.get(user=self.user)
        self.assertNotEqual(otp_record.code_hash, code)

        response = self.client.post(
            reverse("verify_password_reset"),
            {
                "otp": code,
                "new_password1": "New-Password-456!",
                "new_password2": "New-Password-456!",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-Password-456!"))
        otp_record.refresh_from_db()
        self.assertIsNotNone(otp_record.used_at)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_works_when_reset_session_is_missing(self):
        self.client.post(
            reverse("request_password_reset"),
            {"email": self.user.email},
        )
        code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)

        session = self.client.session
        session.pop("password_reset_user_id", None)
        session.save()

        form_response = self.client.get(reverse("verify_password_reset"))
        self.assertContains(form_response, 'name="email"')
        self.assertContains(form_response, 'name="otp"')

        response = self.client.post(
            reverse("verify_password_reset"),
            {
                "email": self.user.email,
                "otp": code,
                "new_password1": "New-Password-456!",
                "new_password2": "New-Password-456!",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-Password-456!"))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
    )
    @patch("med.views.send_mail", side_effect=OSError("SMTP unavailable"))
    def test_email_delivery_failure_is_shown_and_code_is_invalidated(self, send_mail_mock):
        response = self.client.post(
            reverse("request_password_reset"),
            {"email": self.user.email},
            follow=True,
        )

        self.assertContains(response, "The reset email could not be sent")
        self.assertEqual(send_mail_mock.call_count, 1)
        otp_record = PasswordResetOTP.objects.get(user=self.user)
        self.assertIsNotNone(otp_record.used_at)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    @patch("med.views.send_mail")
    def test_console_backend_does_not_report_otp_as_sent(self, send_mail_mock):
        response = self.client.post(
            reverse("request_password_reset"),
            {"email": self.user.email},
            follow=True,
        )

        self.assertContains(response, "The reset email could not be sent")
        send_mail_mock.assert_not_called()
        otp_record = PasswordResetOTP.objects.get(user=self.user)
        self.assertIsNotNone(otp_record.used_at)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_reset_requests_are_limited_to_three_per_hour(self):
        for _ in range(3):
            self.client.post(
                reverse("request_password_reset"),
                {"email": self.user.email},
            )

        self.assertEqual(PasswordResetOTP.objects.filter(user=self.user).count(), 3)
        self.client.post(
            reverse("request_password_reset"),
            {"email": self.user.email},
        )
        self.assertEqual(PasswordResetOTP.objects.filter(user=self.user).count(), 3)
        self.assertEqual(len(mail.outbox), 3)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_unknown_email_gets_same_generic_response_without_mail(self):
        response = self.client.post(
            reverse("request_password_reset"),
            {"email": "not-registered@example.com"},
        )

        self.assertRedirects(response, reverse("verify_password_reset"))
        self.assertEqual(len(mail.outbox), 0)
        verify_response = self.client.get(reverse("verify_password_reset"))
        self.assertContains(verify_response, "If the email belongs to an active account")
        self.assertContains(verify_response, 'name="email"')
        self.assertContains(verify_response, 'name="otp"')

    def test_five_incorrect_codes_disable_the_otp(self):
        now = timezone.now()
        otp_record = PasswordResetOTP.objects.create(
            user=self.user,
            code_hash=make_password("481516"),
            expires_at=now + timedelta(minutes=10),
        )
        session = self.client.session
        session["password_reset_user_id"] = self.user.pk
        session.save()

        for _ in range(5):
            self.client.post(
                reverse("verify_password_reset"),
                {
                    "otp": "000000",
                    "new_password1": "New-Password-456!",
                    "new_password2": "New-Password-456!",
                },
            )

        otp_record.refresh_from_db()
        self.assertEqual(otp_record.attempts, 5)
        self.assertIsNotNone(otp_record.used_at)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-Password-123!"))
