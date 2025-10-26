# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Regular views
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('database/<str:db_name>/', views.database_explorer_view, name='database_explorer'),

    # Admin page views
    path('manage/create-database/', views.admin_create_database_view, name='admin_create_database'),
    path('manage/device-management/', views.admin_device_management_view, name='admin_device_management'),
    path('manage/add-admin/', views.admin_add_admin_view, name='admin_add_admin'),
    path('manage/add-permission/', views.admin_add_permission_view, name='admin_add_permission'),
    path('manage/add-location/', views.admin_add_location_view, name='admin_add_location'),

    # Regular API endpoints
    path('api/table-data/', views.table_data_api, name='table_data_api'),
    path('api/execute-query/', views.execute_query_api, name='execute_query_api'),
    path('api/table-operations/', views.table_operations_api, name='table_operations_api'),
    path('api/test-connection/', views.test_connection_api, name='test_connection_api'),

    # Management API endpoints (matching what the templates expect)
    path('api/manage/devices/', views.admin_api_devices, name='api_manage_devices'),
    path('api/manage/update-device-status/', views.admin_api_update_device_status,
         name='api_manage_update_device_status'),
    path('api/manage/customers/', views.admin_api_customers, name='api_manage_customers'),
    path('api/manage/create-customer/', views.admin_api_create_customer, name='api_manage_create_customer'),
    path('api/manage/add-admin/', views.admin_api_add_admin, name='api_manage_add_admin'),
    path('api/manage/add-permission/', views.admin_api_add_permission, name='api_manage_add_permission'),
    path('api/manage/add-location/', views.admin_api_add_location, name='api_manage_add_location'),
    path('api/manage/database-users/', views.admin_api_database_users, name='api_manage_database_users'),
    path('api/manage/create-database/', views.admin_api_create_database, name='api_manage_create_database'),

    # Admin API endpoints (keeping existing ones for backward compatibility)
    path('admin/api/devices/', views.admin_api_devices, name='admin_api_devices'),
    path('admin/api/update-device-status/', views.admin_api_update_device_status,
         name='admin_api_update_device_status'),
    path('admin/api/database-users/', views.admin_api_database_users, name='admin_api_database_users'),
    path('admin/api/create-database/', views.admin_api_create_database, name='admin_api_create_database'),
    path('admin/api/customers/', views.admin_api_customers, name='admin_api_customers'),
    path('admin/api/create-customer/', views.admin_api_create_customer, name='admin_api_create_customer'),
    path('admin/api/add-admin/', views.admin_api_add_admin, name='admin_api_add_admin'),
    path('admin/api/add-permission/', views.admin_api_add_permission, name='admin_api_add_permission'),
    path('admin/api/add-location/', views.admin_api_add_location, name='admin_api_add_location'),

    # path('admin/api/employees/', views.admin_api_employees, name='admin_api_employees'),
    # path('admin/api/update-employee-permission/', views.admin_api_update_employee_permission,
    #      name='admin_api_update_employee_permission'),

    # FIXED: Employee management endpoints
    path('api/manage/employees/', views.admin_api_employees, name='api_manage_employees'),
    path('api/manage/update-employee-permission/', views.admin_api_update_employee_permission,
         name='api_manage_update_employee_permission'),

    path('api/manage/databases/', views.admin_api_databases, name='api_manage_databases'),
    path('api/manage/itemgroups/', views.admin_api_itemgroups, name='api_manage_itemgroups'),
    path('api/manage/add-itemgroup/', views.admin_api_add_itemgroup, name='api_manage_add_itemgroup'),

# Add this line with your other admin page views
path('manage/verify-database/', views.admin_verify_database_view, name='admin_verify_database'),
path('api/manage/verify-database/', views.admin_api_verify_database, name='api_manage_verify_database'),
path('api/manage/fix-database/', views.admin_api_fix_database, name='api_manage_fix_database'),

]
