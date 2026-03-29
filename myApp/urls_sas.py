from django.urls import path
from . import views_sas

urlpatterns = [

    # ========== SAS (PostgreSQL) Database Explorer ==========
    path('pg-database/<str:db_name>/', views_sas.sas_database_explorer_view, name='pg_database_explorer'),

    # ========== SAS (PostgreSQL) Admin Views ==========
    path('manage/create-pg-sas-database/',  views_sas.sas_create_pg_sas_database_view, name='admin_create_pg_sas_database'),
    path('manage/delete-pg-sas-database/',  views_sas.sas_delete_pg_sas_database_view, name='admin_delete_pg_sas_database'),
    path('manage/add-pg-user/',             views_sas.sas_add_pg_user_view,             name='admin_add_pg_user'),
    path('manage/grant-pg-access/',         views_sas.sas_grant_pg_access_view,         name='admin_grant_pg_access'),

    # ========== SAS (PostgreSQL) Database Explorer API ==========
    path('api/pg/table-data/',      views_sas.sas_table_data_api,    name='pg_table_data_api'),
    path('api/pg/execute-query/',   views_sas.sas_execute_query_api, name='pg_execute_query_api'),

    # ========== SAS (PostgreSQL) Admin API Endpoints ==========
    path('manage/api/pg/databases/',            views_sas.sas_api_databases,          name='admin_api_pg_databases'),
    path('manage/api/pg/test-connection/',       views_sas.sas_api_test_connection,    name='admin_api_pg_test_connection'),
    path('manage/api/pg/create-database/',       views_sas.sas_api_create_database,    name='admin_api_create_pg_database'),
    path('manage/api/pg/create-sas-database/',   views_sas.sas_api_create_sas_database, name='admin_api_create_pg_sas_database'),
    path('manage/api/pg/delete-sas-database/',   views_sas.sas_api_delete_sas_database, name='admin_api_delete_pg_sas_database'),
    path('manage/api/pg/add-user/',              views_sas.sas_api_add_user,           name='admin_api_add_pg_user'),
    path('manage/api/pg/grant-access/',          views_sas.sas_api_grant_access,       name='admin_api_grant_pg_access'),

path('manage/api/pg/create-sas-customer/', views_sas.sas_api_create_sas_customer, name='admin_api_create_pg_sas_customer'),
path('debug-pg/', views_sas.sas_debug_pg_connection, name='debug_pg'),

]