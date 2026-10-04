from django.urls import path
from . import views 
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),

    

    #path('login/', TemplateView.as_view(template_name='template/login.html'), name='login'),
    #path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('forgot-password/', views.request_password_reset, name='request_password_reset'),
    path('forgot-password/verify/', views.verify_password_reset, name='verify_password_reset'),
    path('forgot-password/complete/', views.password_reset_complete, name='password_reset_complete'),

    #path('dashboard/', views.dashboard, name='dashboard'),



    path('dashboard/', views.dashboard, name='dashboard'),

    path(
        'medicines/<int:id>/',
        views.medicine_list,
        name='medicine_list'
    ),

    path('logout/', views.logout_view, name='logout'),


    path('admin_dashboard/', views.admin_dashboard),

path('add-diagnosis/', views.add_diagnosis),



path(
    'delete-diagnosis/<int:id>/',
    views.delete_diagnosis
),

path('add-medicine/', views.add_medicine),

path(
    'edit-medicine/<int:id>/',
    views.edit_medicine
),

path(
    'delete-medicine/<int:id>/',
    views.delete_medicine
),





    # Diagnosis CRUD

    path(
        'add-diagnosis/',
        views.add_diagnosis,
        name='add_diagnosis'
    ),


    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('edit-diagnosis/<int:id>/', views.edit_diagnosis, name='edit_diagnosis'),

    path('register/', views.register, name='register'),
    path('contact/', views.contact, name='contact'),
    path('manage-contact/', views.manage_contact_details, name='manage_contact_details'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('manage-users/requests/<int:request_id>/create-user/', views.create_requested_user, name='create_requested_user'),
    path('manage-users/requests/<int:request_id>/reject/', views.reject_registration_request, name='reject_registration_request'),
    path('manage-users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    path('services/', views.service_catalog, name='service_catalog'),
    path('services/<int:service_id>/apply/', views.apply_for_service, name='apply_for_service'),
    path('services/<int:service_id>/payment-qr/', views.service_payment_qr, name='service_payment_qr'),
    path('applications/<int:application_id>/payment/', views.payment_page, name='payment_page'),
    path('applications/<int:application_id>/receipt/', views.application_receipt, name='application_receipt'),
    path('manage-services/', views.manage_services, name='manage_services'),
    path('manage-applications/', views.manage_applications, name='manage_applications'),
    path('manage-applications/<int:application_id>/update/', views.update_application_status, name='update_application_status'),
    path('manage-services/main/add/', views.add_main_service, name='add_main_service'),
    path('manage-services/sub/add/', views.add_service, name='add_service'),
    path('manage-services/sub/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('manage-services/main/<int:service_id>/delete/', views.delete_main_service, name='delete_main_service'),
    path('manage-services/sub/<int:service_id>/delete/', views.delete_service, name='delete_service'),


]
