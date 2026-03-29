# views_sas.py - SAS (PostgreSQL) Views and API Endpoints [FIXED VERSION]
# Changes marked with [FIX] comments

import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import urllib.parse
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# SAS - POSTGRESQL CREDENTIALS (from .env)
# ============================================================================
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')
PG_PORT = int(os.getenv('PG_PORT', 5432))
PG_DB = os.getenv('PG_DB', 'postgres')  # main PG registry DB (neptouia_erp)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))


# ============================================================================
# POSTGRESQL MANAGER CLASS
# ============================================================================

class PostgreSQLManager:
    def __init__(self, host, user, password, database=None, port=5432):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database or 'postgres',
                port=self.port,
                connect_timeout=10
            )
            self.connection.autocommit = True
            return True
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Connection error: {e}")
            return False

    def get_databases(self):
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT datname FROM pg_database
                WHERE datistemplate = false
                AND datname NOT IN ('postgres', 'template0', 'template1')
                ORDER BY datname
            """)
            databases = [db[0] for db in cursor.fetchall()]
            cursor.close()
            return databases
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error fetching databases: {e}")
            return []

    def get_tables(self):
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            tables = [t[0] for t in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error fetching tables: {e}")
            return []

    def get_table_structure(self, table_name):
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, [table_name])
            columns = cursor.fetchall()
            cursor.close()
            return [
                {
                    'field': col[0],
                    'type': f"{col[1]}{f'({col[4]})' if col[4] else ''}",
                    'null': col[2],
                    'default': col[3],
                    'key': '',
                    'extra': ''
                }
                for col in columns
            ]
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error fetching table structure: {e}")
            return []

    def get_table_data(self, table_name, limit=100, offset=0, filter_condition=None):
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            query = f'SELECT * FROM "{table_name}"'
            params = []
            if filter_condition:
                field = filter_condition.get('field')
                condition = filter_condition.get('condition')
                value = filter_condition.get('value')
                if field and condition:
                    if condition in ['IS NULL', 'IS NOT NULL']:
                        query += f' WHERE "{field}" {condition}'
                    elif condition in ['LIKE', 'ILIKE']:
                        query += f' WHERE "{field}" {condition} %s'
                        params.append(f"%{value}%")
                    elif condition == 'NOT LIKE':
                        query += f' WHERE "{field}" NOT LIKE %s'
                        params.append(f"%{value}%")
                    else:
                        query += f' WHERE "{field}" {condition} %s'
                        params.append(value)
            query += f" LIMIT {limit} OFFSET {offset}"
            cursor.execute(query, params)
            data = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in data]
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error fetching table data: {e}")
            return []

    def get_table_count(self, table_name, filter_condition=None):
        if not self.connection:
            return 0
        try:
            cursor = self.connection.cursor()
            query = f'SELECT COUNT(*) FROM "{table_name}"'
            params = []
            if filter_condition:
                field = filter_condition.get('field')
                condition = filter_condition.get('condition')
                value = filter_condition.get('value')
                if field and condition:
                    if condition in ['IS NULL', 'IS NOT NULL']:
                        query += f' WHERE "{field}" {condition}'
                    elif condition in ['LIKE', 'ILIKE']:
                        query += f' WHERE "{field}" {condition} %s'
                        params.append(f"%{value}%")
                    else:
                        query += f' WHERE "{field}" {condition} %s'
                        params.append(value)
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error counting records: {e}")
            return 0

    def execute_query(self, query):
        if not self.connection:
            return False, "No database connection"
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            if query.strip().upper().startswith(('SELECT', 'SHOW', 'EXPLAIN')):
                result = cursor.fetchall()
                cursor.close()
                return True, [dict(row) for row in result]
            else:
                affected = cursor.rowcount
                cursor.close()
                return True, f"Query executed successfully. {affected} rows affected."
        except Exception as e:
            return False, str(e)

    def close_connection(self):
        if self.connection and not self.connection.closed:
            self.connection.close()


# ============================================================================
# TABLE SCHEMAS
# ============================================================================

def get_common_schemas():
    """Common tables created for ALL business types."""
    return {
        'organization': {
            'create_statement': """
                CREATE TABLE IF NOT EXISTS "Organization" (
                    "CompanyId"          INTEGER PRIMARY KEY,
                    "CompanyName"        VARCHAR(300) NOT NULL,
                    "ArabicName"         VARCHAR(300),
                    "Subtitle"           VARCHAR(300),
                    "Address1"           VARCHAR(300),
                    "Address2"           VARCHAR(300),
                    "Address3"           VARCHAR(300),
                    "Phone"              VARCHAR(300),
                    "Mobile"             VARCHAR(300),
                    "Url"                VARCHAR(300),
                    "Email"              VARCHAR(254),
                    "TinNo"              VARCHAR(300),
                    "CrNo"               VARCHAR(300),
                    "LicenseNo"          VARCHAR(300),
                    "BuildingNo"         VARCHAR(300),
                    "StreetName"         VARCHAR(300),
                    "Zone"               VARCHAR(300),
                    "Area"               VARCHAR(300),
                    "City"               VARCHAR(300),
                    "State"              VARCHAR(300),
                    "District"           VARCHAR(300),
                    "PoBox"              VARCHAR(300),
                    "PlotIdentification" VARCHAR(300),
                    "AccountNumber"      VARCHAR(300),
                    "AccountName"        VARCHAR(300),
                    "Branch"             VARCHAR(300),
                    "Ifsc"               VARCHAR(300),
                    "PayerId"            VARCHAR(300),
                    "PayerBank"          VARCHAR(300),
                    "PayerIban"          VARCHAR(300),
                    "PeriodFrom"         DATE NOT NULL,
                    "PeriodTo"           DATE NOT NULL,
                    "DefaultDb"          SMALLINT,
                    "BusinessType"       SMALLINT NOT NULL,
                    "CreatedAt"          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        },
        'report_details': {
            'create_statement': """
                CREATE TABLE IF NOT EXISTS "ReportDetails" (
                    "SlNo"        INTEGER NOT NULL PRIMARY KEY,
                    "ReportName"  VARCHAR(50),
                    "MRName"      VARCHAR(50),
                    "Section"     VARCHAR(50),
                    "FName"       VARCHAR(150),
                    "UFName"      VARCHAR(50),
                    "Width"       NUMERIC(19,4),
                    "Index"       NUMERIC(19,4),
                    "Alignment"   NUMERIC(19,4),
                    "Show"        SMALLINT,
                    "Heder"       SMALLINT,
                    "Break"       SMALLINT,
                    "UIndex"      NUMERIC(19,4),
                    "UWidth"      NUMERIC(19,4),
                    "MReport"     SMALLINT,
                    "DField"      SMALLINT,
                    "Font"        SMALLINT,
                    "FieldType"   SMALLINT,
                    "FormatText"  VARCHAR(50),
                    "FontName"    CHAR(45),
                    "SYS_ITEM"    SMALLINT,
                    "Color"       CHAR(20)
                )
            """
        },
        'filter_details': {
            'create_statement': """
                CREATE TABLE IF NOT EXISTS "FilterDetails" (
                    "ReportName"  VARCHAR(20),
                    "FieldName"   VARCHAR(20),
                    "DisplayName" VARCHAR(20),
                    "FieldType"   SMALLINT,
                    "FilterSql"   VARCHAR(150),
                    "ColWidth"    VARCHAR(15),
                    "IDField"     VARCHAR(20),
                    "Default"     SMALLINT,
                    "Operator"    INTEGER
                )
            """
        },
        'item_groups': {
            'create_statement': """
                CREATE TABLE IF NOT EXISTS "ItemGroups" (
                    "GroupID"     INTEGER UNIQUE,
                    "Category"    INTEGER NOT NULL,
                    "Description" VARCHAR(50) NOT NULL,
                    "UCode"       VARCHAR(10),
                    "Under"       INTEGER,
                    "NREC"        SMALLINT,
                    PRIMARY KEY ("Category", "Description")
                )
            """
        },
        'form_design': {
            'create_statement': """
            CREATE TABLE IF NOT EXISTS "FormDesign" (
                "ForamName" VARCHAR(20) NOT NULL,
                "TypeCode" INTEGER NOT NULL,
                "ControlName" VARCHAR(20) NOT NULL,
                "Left" INTEGER,
                "Top" INTEGER,
                "Width" INTEGER,
                "Height" INTEGER,
                "Container" VARCHAR(20),
                "TabIndex" INTEGER,
                "TabStop" SMALLINT,
                "Visible" SMALLINT,
                "Caption" VARCHAR(25),
                "Value" INTEGER,
                "Design" SMALLINT,
                "Enabled" SMALLINT,
                "ArabicCaption" CHAR(30),
                "Font" CHAR(30),
                "FontSize" INTEGER,
                PRIMARY KEY ("ForamName", "TypeCode", "ControlName")
            )
        """
        },

    }


def get_business_schemas(business_type):
    """Return tables specific to the chosen business type."""
    schemas = {
        # ── LAUNDRY ──────────────────────────────────────────────────────────
        'laundry': {
            'clothes': {
                'create_statement': """
                    CREATE TABLE IF NOT EXISTS clothes (
                        item_id        SERIAL PRIMARY KEY,
                        item_code      VARCHAR(30) NOT NULL,
                        item_name      VARCHAR(150) NOT NULL,
                        category       VARCHAR(60),
                        wash_price     DOUBLE PRECISION DEFAULT 0,
                        iron_price     DOUBLE PRECISION DEFAULT 0,
                        dryclean_price DOUBLE PRECISION DEFAULT 0,
                        unit           VARCHAR(10),
                        is_active      BOOLEAN DEFAULT TRUE,
                        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
        },
        # ── RESTAURANT ───────────────────────────────────────────────────────
        'restaurant': {
            'waiter': {
                'create_statement': """
                    CREATE TABLE IF NOT EXISTS waiter (
                        waiter_id   SERIAL PRIMARY KEY,
                        waiter_code VARCHAR(20),
                        waiter_name VARCHAR(100) NOT NULL,
                        mobile      VARCHAR(20),
                        table_no    VARCHAR(20),
                        shift       VARCHAR(20),
                        is_active   BOOLEAN DEFAULT TRUE,
                        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
        },
        # ── HRMS ─────────────────────────────────────────────────────────────
        'hrms': {
            'employee': {
                'create_statement': """
                    CREATE TABLE IF NOT EXISTS employee (
                        emp_id       SERIAL PRIMARY KEY,
                        emp_name     VARCHAR(100) NOT NULL,
                        emp_code     VARCHAR(20),
                        pwd          VARCHAR(10),
                        department   VARCHAR(60),
                        designation  VARCHAR(60),
                        joining_date DATE,
                        salary       DOUBLE PRECISION DEFAULT 0,
                        target       DOUBLE PRECISION DEFAULT 0,
                        user_type    INTEGER DEFAULT 0,
                        is_active    BOOLEAN DEFAULT TRUE,
                        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            },
        },
    }
    return schemas.get(business_type, {})


# ============================================================================
# HELPER — ensure tables exist in the registry PG database
# ============================================================================

def _ensure_softwares_table(cursor):
    """Create the Softwares registry table in neptouia_erp if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS softwares (
            custid SERIAL PRIMARY KEY,
            software INTEGER NOT NULL,
            host VARCHAR(200),
            db VARCHAR(200),
            dbpass VARCHAR(200),
            username VARCHAR(200),
            pwd VARCHAR(200),
            expiry DATE,
            createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ============================================================================
# SAS - ADMIN VIEWS (Page Renders)
# ============================================================================

def sas_create_pg_sas_database_view(request):
    if 'user' not in request.session:
        return redirect('login')
    context = {'pg_host': PG_HOST, 'pg_port': PG_PORT, 'pg_user': PG_USER}
    return render(request, 'admin/create_pg_sas_database.html', context)


def sas_add_pg_user_view(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    context = {'pg_host': PG_HOST, 'pg_port': PG_PORT, 'pg_user': PG_USER}
    return render(request, 'admin/add_pg_user.html', context)


def sas_grant_pg_access_view(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    context = {'pg_host': PG_HOST, 'pg_port': PG_PORT, 'pg_user': PG_USER}
    return render(request, 'admin/grant_pg_access.html', context)


def sas_database_explorer_view(request, db_name):
    if 'user' not in request.session:
        return redirect('login')

    if not db_name or db_name.strip() == '':
        messages.error(request, 'Database name is required')
        return redirect('dashboard')

    db_name = urllib.parse.unquote(db_name).strip()
    pg_manager = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, db_name, PG_PORT)

    if not pg_manager.connect():
        messages.error(request, f'Failed to connect to PostgreSQL database: {db_name}')
        return redirect('dashboard')

    tables = pg_manager.get_tables()
    pg_manager.close_connection()

    context = {
        'database': db_name,
        'tables': tables,
        'db_host': PG_HOST,
        'db_port': PG_PORT,
        'db_user': PG_USER,
        'db_password': PG_PASSWORD,
    }
    return render(request, 'pg_database_explorer.html', context)


# ============================================================================
# SAS - DATABASE EXPLORER API ENDPOINTS
# ============================================================================

@csrf_exempt
def sas_table_data_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        db_name = request.GET.get('database')
        table_name = request.GET.get('table')
        action = request.GET.get('action', 'data')

        if not all([db_name, table_name]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        pg_manager = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, db_name, PG_PORT)
        if not pg_manager.connect():
            return JsonResponse({'error': 'Database connection failed'}, status=500)

        try:
            if action == 'structure':
                structure = pg_manager.get_table_structure(table_name)
                return JsonResponse({'structure': structure})
            elif action == 'data':
                limit = int(request.GET.get('limit', 100))
                offset = int(request.GET.get('offset', 0))
                filter_condition = None
                fp = request.GET.get('filter')
                if fp:
                    try:
                        filter_condition = json.loads(fp)
                    except json.JSONDecodeError:
                        pass
                data = pg_manager.get_table_data(table_name, limit, offset, filter_condition)
                total_count = pg_manager.get_table_count(table_name, filter_condition)
                return JsonResponse({'data': data, 'total_count': total_count,
                                     'has_more': (offset + limit) < total_count})
        finally:
            pg_manager.close_connection()

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def sas_execute_query_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query')
        db_name = data.get('database')

        if not all([query, db_name]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        pg_manager = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, db_name, PG_PORT)
        if not pg_manager.connect():
            return JsonResponse({'error': 'Database connection failed'}, status=500)

        try:
            success, result = pg_manager.execute_query(query)
            if success:
                return JsonResponse({'success': True, 'result': result})
            else:
                return JsonResponse({'success': False, 'error': result})
        finally:
            pg_manager.close_connection()

    return JsonResponse({'error': 'Invalid request'}, status=400)


# ============================================================================
# SAS - ADMIN API ENDPOINTS
# ============================================================================

@csrf_exempt
def sas_api_databases(request):
    """
    GET /manage/api/pg/databases/
    Returns list of PostgreSQL databases for the dashboard.
    Uses server-side credentials from .env — no client credentials needed.
    """
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        try:
            if not PG_USER or not PG_PASSWORD:
                return JsonResponse({
                    'success': False,
                    'error': 'PG_USER / PG_PASSWORD not set in .env',
                    'databases': []
                })

            pg_manager = PostgreSQLManager(
                PG_HOST, PG_USER, PG_PASSWORD, database='postgres', port=PG_PORT
            )
            if not pg_manager.connect():
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to connect to PostgreSQL. Check PG_HOST, PG_USER, PG_PASSWORD in .env',
                    'databases': []
                })

            databases = pg_manager.get_databases()
            pg_manager.close_connection()

            print(f"# SAS - POSTGRESQL: Found {len(databases)} databases")
            return JsonResponse({'success': True, 'databases': databases})

        except Exception as e:
            print(f"# SAS - POSTGRESQL: Error in sas_api_databases: {e}")
            return JsonResponse({'success': False, 'error': str(e), 'databases': []})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_test_connection(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            host = data.get('host')
            port = data.get('port', 5432)
            username = data.get('username')
            password = data.get('password')

            if not all([host, username, password]):
                return JsonResponse({'success': False,
                                     'error': 'Host, username, and password are required'})

            pg_manager = PostgreSQLManager(host, username, password, port=port)
            if not pg_manager.connect():
                return JsonResponse({'success': False,
                                     'error': 'Connection failed. Check host, port, credentials, and pg_hba.conf'})

            databases = pg_manager.get_databases()
            version = None
            try:
                cursor = pg_manager.connection.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                cursor.close()
            except Exception:
                pass

            pg_manager.close_connection()
            return JsonResponse({'success': True, 'message': 'Connected successfully',
                                 'databases': databases, 'version': version})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Connection error: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_create_database(request):
    """Create a plain PostgreSQL database (no SAS tables)."""
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            host = data.get('host', PG_HOST)
            port = data.get('port', PG_PORT)
            username = data.get('username', PG_USER)
            password = data.get('password', PG_PASSWORD)
            database_name = data.get('database_name')
            owner = data.get('owner')
            encoding = data.get('encoding', 'UTF8')

            if not database_name:
                return JsonResponse({'success': False, 'error': 'Database name is required'})
            if not re.match(r'^[a-zA-Z0-9_]+$', database_name):
                return JsonResponse({'success': False,
                                     'error': 'Database name can only contain letters, numbers, and underscores'})

            pg_manager = PostgreSQLManager(host, username, password, port=port)
            if not pg_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to PostgreSQL'})

            try:
                cursor = pg_manager.connection.cursor()
                query = f'CREATE DATABASE "{database_name}"'
                if owner:
                    query += f' OWNER "{owner}"'
                query += f" ENCODING '{encoding}'"
                cursor.execute(query)
                cursor.close()
                pg_manager.close_connection()
                return JsonResponse({'success': True,
                                     'message': f'Database "{database_name}" created successfully'})
            except Exception as e:
                pg_manager.close_connection()
                if 'already exists' in str(e).lower():
                    return JsonResponse({'success': False,
                                         'error': f'Database "{database_name}" already exists'})
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_create_sas_database(request):
    """
    Full SAS database creation:
      1. Create PostgreSQL database
      2. Create user
      3. Grant privileges
      4. Create common tables (all types)
      5. Create business-specific tables (laundry / restaurant / hrms)
      6. Save software entry to PostgreSQL registry DB (PG_DB = neptouia_erp):
            laundry    → software = 1
            restaurant → software = 2
            hrms       → software = 3

    [FIX] Multiple corrections applied to handle foreign key constraints properly
    """
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            host = data.get('host', PG_HOST)
            port = data.get('port', PG_PORT)
            admin_username = data.get('admin_username', PG_USER)
            admin_password = data.get('admin_password', PG_PASSWORD)
            database_name = data.get('database_name')
            database_user = data.get('database_user')
            user_password = data.get('user_password')
            expiry_years = data.get('expiry_years', 1)
            business_type = data.get('business_type', '').lower().strip()

            if not all([database_name, database_user, user_password]):
                return JsonResponse({'success': False,
                                     'error': 'Database name, user, and password are required'})

            if not re.match(r'^[a-zA-Z0-9_]+$', database_name):
                return JsonResponse({'success': False,
                                     'error': 'Database name can only contain letters, numbers, and underscores'})

            if business_type not in ('laundry', 'restaurant', 'hrms'):
                return JsonResponse({'success': False,
                                     'error': 'business_type must be one of: laundry, restaurant, hrms'})

            print(f"# SAS - POSTGRESQL: Creating {business_type} database: {database_name}")

            pg_manager = PostgreSQLManager(
                host, admin_username, admin_password, database='postgres', port=port
            )
            if not pg_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to PostgreSQL'})

            # [FIX] Map business_type to software_id early
            software_id_map = {'laundry': 1, 'restaurant': 2, 'hrms': 3}
            software_id = software_id_map[business_type]

            results = {
                'database_created': False,
                'user_created': False,
                'privileges_granted': False,
                'tables_created': [],
                'common_tables_created': 0,
                'biz_tables_created': 0,
                'software_entry_created': False,
                'errors': [],
                'software_id': software_id  # [FIX] Return software_id for step 2
            }

            try:
                cursor = pg_manager.connection.cursor()

                # ── Step 1: Create database ───────────────────────────────
                try:
                    cursor.execute(f"CREATE DATABASE \"{database_name}\" ENCODING 'UTF8'")
                    results['database_created'] = True
                    print(f"# SAS - POSTGRESQL: Database created: {database_name}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        return JsonResponse({'success': False,
                                             'error': f'Database "{database_name}" already exists'})
                    return JsonResponse({'success': False,
                                         'error': f'Failed to create database: {str(e)}'})

                # ── Step 2: Create user ───────────────────────────────────
                try:
                    cursor.execute(
                        f"CREATE USER \"{database_user}\" WITH PASSWORD '{user_password}'"
                    )
                    results['user_created'] = True
                    print(f"# SAS - POSTGRESQL: User created: {database_user}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        results['user_created'] = True
                        print(f"# SAS - POSTGRESQL: User {database_user} already exists, continuing")
                    else:
                        results['errors'].append(f'Failed to create user: {str(e)}')

                cursor.close()
                pg_manager.close_connection()

                # ── Connect to new database for steps 3–5 ────────────────
                new_db = PostgreSQLManager(
                    host, admin_username, admin_password, database_name, port
                )
                if not new_db.connect():
                    results['errors'].append('Failed to connect to new database for setup')
                    return JsonResponse({
                        'success': False,
                        'error': 'Database created but failed to connect for setup',
                        'results': results
                    })

                cursor = new_db.connection.cursor()

                # ── Step 3: Grant privileges ──────────────────────────────
                try:
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON DATABASE "{database_name}" TO "{database_user}"'
                    )
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{database_user}"'
                    )
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{database_user}"'
                    )
                    cursor.execute(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        f'GRANT ALL ON TABLES TO "{database_user}"'
                    )
                    cursor.execute(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        f'GRANT ALL ON SEQUENCES TO "{database_user}"'
                    )
                    results['privileges_granted'] = True
                    print(f"# SAS - POSTGRESQL: Privileges granted to {database_user}")
                except Exception as e:
                    results['errors'].append(f'Failed to grant privileges: {str(e)}')

                # ── Step 4: Create COMMON tables ──────────────────────────
                for table_key, schema in get_common_schemas().items():
                    try:
                        cursor.execute(schema['create_statement'])
                        results['tables_created'].append(table_key)
                        results['common_tables_created'] += 1
                        print(f"# SAS - POSTGRESQL: Created common table: {table_key}")
                    except Exception as e:
                        msg = f"Failed to create common table {table_key}: {str(e)}"
                        print(f"# SAS - POSTGRESQL: {msg}")
                        results['errors'].append(msg)

                # ── Step 5: Create BUSINESS-SPECIFIC tables ───────────────
                for table_key, schema in get_business_schemas(business_type).items():
                    try:
                        cursor.execute(schema['create_statement'])
                        results['tables_created'].append(table_key)
                        results['biz_tables_created'] += 1
                        print(f"# SAS - POSTGRESQL: Created {business_type} table: {table_key}")
                    except Exception as e:
                        msg = f"Failed to create {business_type} table {table_key}: {str(e)}"
                        print(f"# SAS - POSTGRESQL: {msg}")
                        results['errors'].append(msg)

                cursor.close()
                new_db.close_connection()

                # ── Step 6: Save software entry to neptouia_erp (PG_DB) ───
                # [FIX] Changed column name from expirydate to expiry (matches schema)
                try:
                    expiry_date = datetime.now() + timedelta(days=expiry_years * 365)

                    registry_db = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, PG_DB, PG_PORT)

                    if not registry_db.connect():
                        results['errors'].append(f'Failed to connect to PG registry database: {PG_DB}')
                    else:
                        rc = registry_db.connection.cursor()

                        # Get next custid from existing softwares table
                        rc.execute('SELECT COALESCE(MAX(custid), 0) + 1 FROM softwares')
                        next_cust_id = rc.fetchone()[0]

                        # [FIX] Changed column name: expirydate → expiry
                        rc.execute(
                            """INSERT INTO softwares
                               (custid, software, host, db, dbpass, username, pwd, expiry)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                next_cust_id,
                                software_id,
                                host,
                                database_name,
                                user_password,
                                database_user,
                                user_password,
                                expiry_date.strftime('%Y-%m-%d'),
                            )
                        )
                        rc.close()
                        registry_db.close_connection()

                        results['software_entry_created'] = True
                        results['cust_id'] = next_cust_id
                        print(f"# SAS: softwares entry saved to {PG_DB}, software={software_id}, custid={next_cust_id}")

                except Exception as e:
                    results['errors'].append(f'Failed to add software entry: {str(e)}')
                    print(f"# SAS: Error adding software entry: {e}")

                # ── Final response ────────────────────────────────────────
                if results['database_created'] and results['user_created']:
                    total = len(results['tables_created'])
                    msg = (
                        f'PostgreSQL {business_type.upper()} database "{database_name}" '
                        f'created with {total} tables '
                        f'({results["common_tables_created"]} common + '
                        f'{results["biz_tables_created"]} business-specific)'
                    )
                    if results.get('cust_id'):
                        msg += f' — Customer ID: {results["cust_id"]}'
                    return JsonResponse({'success': True, 'message': msg, 'results': results})
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Database creation partially completed with errors',
                        'results': results
                    })

            except Exception as e:
                import traceback;
                traceback.print_exc()
                return JsonResponse({'success': False, 'error': str(e), 'results': results})

        except Exception as e:
            import traceback;
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_add_user(request):
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            host = data.get('host', PG_HOST)
            port = data.get('port', PG_PORT)
            admin_username = data.get('admin_username', PG_USER)
            admin_password = data.get('admin_password', PG_PASSWORD)
            username = data.get('username')
            password = data.get('password')
            createdb = data.get('createdb', False)
            createrole = data.get('createrole', False)

            if not all([username, password]):
                return JsonResponse({'success': False, 'error': 'Username and password are required'})

            pg_manager = PostgreSQLManager(host, admin_username, admin_password, port=port)
            if not pg_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to PostgreSQL'})

            try:
                cursor = pg_manager.connection.cursor()
                q = f"CREATE USER \"{username}\" WITH PASSWORD '{password}'"
                if createdb:   q += " CREATEDB"
                if createrole: q += " CREATEROLE"
                cursor.execute(q)
                cursor.close()
                pg_manager.close_connection()
                return JsonResponse({'success': True,
                                     'message': f'User "{username}" created successfully'})
            except Exception as e:
                pg_manager.close_connection()
                if 'already exists' in str(e).lower():
                    return JsonResponse({'success': False,
                                         'error': f'User "{username}" already exists'})
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_grant_access(request):
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            host = data.get('host', PG_HOST)
            port = data.get('port', PG_PORT)
            admin_username = data.get('admin_username', PG_USER)
            admin_password = data.get('admin_password', PG_PASSWORD)
            database = data.get('database')
            username = data.get('username')
            privileges = data.get('privileges', [])

            if not all([database, username, privileges]):
                return JsonResponse({'success': False,
                                     'error': 'Database, username, and privileges are required'})

            pg_manager = PostgreSQLManager(host, admin_username, admin_password, database, port)
            if not pg_manager.connect():
                return JsonResponse({'success': False,
                                     'error': f'Failed to connect to database "{database}"'})

            try:
                cursor = pg_manager.connection.cursor()
                if 'ALL' in privileges:
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON DATABASE "{database}" TO "{username}"'
                    )
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{username}"'
                    )
                    cursor.execute(
                        f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{username}"'
                    )
                    cursor.execute(
                        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        f'GRANT ALL ON TABLES TO "{username}"'
                    )
                else:
                    priv_str = ', '.join(privileges)
                    cursor.execute(
                        f'GRANT {priv_str} ON DATABASE "{database}" TO "{username}"'
                    )
                    cursor.execute(
                        f'GRANT {priv_str} ON ALL TABLES IN SCHEMA public TO "{username}"'
                    )
                cursor.close()
                pg_manager.close_connection()
                return JsonResponse({'success': True,
                                     'message': f'Access granted to "{username}" on "{database}"'})
            except Exception as e:
                pg_manager.close_connection()
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


def sas_delete_pg_sas_database_view(request):
    if 'user' not in request.session:
        return redirect('login')
    context = {'pg_host': PG_HOST, 'pg_port': PG_PORT, 'pg_user': PG_USER}
    return render(request, 'admin/delete_pg_sas_database.html', context)


@csrf_exempt
def sas_api_delete_sas_database(request):
    """
    Delete a SAS PostgreSQL database:
      1. Terminate active connections and drop the database
      2. Drop the user (optional)
      3. Remove the Softwares entry from neptouia_erp (PG_DB)

    [FIX] Changed table name from quoted "Softwares" to lowercase softwares
    """
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            database_name = data.get('database_name')
            drop_user = data.get('drop_user', False)
            database_user = data.get('database_user', '')

            if not database_name:
                return JsonResponse({'success': False, 'error': 'Database name is required'})

            results = {
                'database_dropped': False,
                'user_dropped': False,
                'software_entry_removed': False,
                'errors': []
            }

            # ── Step 1: Drop the database ─────────────────────────────────
            pg_manager = PostgreSQLManager(
                PG_HOST, PG_USER, PG_PASSWORD, database='postgres', port=PG_PORT
            )
            if not pg_manager.connect():
                return JsonResponse({'success': False,
                                     'error': 'Failed to connect to PostgreSQL'})

            try:
                cursor = pg_manager.connection.cursor()

                # Terminate active connections first
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """, [database_name])

                cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
                results['database_dropped'] = True
                print(f"# SAS - POSTGRESQL: Dropped database: {database_name}")

                # ── Step 2: Optionally drop the user ──────────────────────
                if drop_user and database_user:
                    try:
                        cursor.execute(f'DROP USER IF EXISTS "{database_user}"')
                        results['user_dropped'] = True
                        print(f"# SAS - POSTGRESQL: Dropped user: {database_user}")
                    except Exception as e:
                        results['errors'].append(f'Failed to drop user: {str(e)}')

                cursor.close()
            except Exception as e:
                pg_manager.close_connection()
                return JsonResponse({'success': False,
                                     'error': f'Failed to drop database: {str(e)}'})

            pg_manager.close_connection()

            # ── Step 3: Remove Softwares entry from neptouia_erp (PG_DB) ──
            # [FIX] Changed from quoted "Softwares" to lowercase softwares
            try:
                registry_db = PostgreSQLManager(
                    PG_HOST, PG_USER, PG_PASSWORD, PG_DB, PG_PORT
                )
                if not registry_db.connect():
                    results['errors'].append(
                        f'Failed to connect to PG registry database: {PG_DB}'
                    )
                else:
                    rc = registry_db.connection.cursor()
                    rc.execute(
                        'DELETE FROM softwares WHERE db = %s',  # [FIX] Unquoted lowercase
                        [database_name]
                    )
                    deleted_rows = rc.rowcount
                    rc.close()
                    registry_db.close_connection()
                    results['software_entry_removed'] = True
                    print(
                        f"# SAS - POSTGRESQL: Removed {deleted_rows} Softwares entry "
                        f"from {PG_DB} for: {database_name}"
                    )
            except Exception as e:
                results['errors'].append(f'Failed to remove software entry: {str(e)}')
                print(f"# SAS - POSTGRESQL: Error removing software entry: {e}")

            return JsonResponse({
                'success': True,
                'message': f'Database "{database_name}" deleted successfully',
                'results': results
            })

        except Exception as e:
            import traceback;
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def sas_api_create_sas_customer(request):
    """
    Create SAS customer in neptouia_erp (PostgreSQL PG_DB)
    Uses existing tables: customers, itemgroups, softwares

    [FIX] The softwares entry MUST exist before itemgroups insertion
    due to foreign key constraint itemgroups_software_custid_fk
    """
    if 'user' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name', '').strip()
            location = data.get('location', '').strip()
            expiry_date = data.get('expiry_date', '')
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            cust_id = data.get('cust_id')  # from step 1 (softwares)
            software_id = data.get('software_id')  # 1/2/3

            if not all([customer_name, location, expiry_date, username, password]):
                return JsonResponse({'success': False,
                                     'error': 'Customer name, location, expiry, username and password are required'})

            # [FIX] Validate that cust_id was passed and software entry exists
            if not cust_id or not software_id:
                return JsonResponse({'success': False,
                                     'error': 'Missing customer ID or software ID from database creation. Please recreate the database.'})

            registry_db = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, PG_DB, PG_PORT)
            if not registry_db.connect():
                return JsonResponse({'success': False,
                                     'error': f'Failed to connect to PG registry database: {PG_DB}'})

            rc = registry_db.connection.cursor()

            try:
                # [FIX] Verify softwares entry exists BEFORE proceeding
                rc.execute('SELECT custid FROM softwares WHERE custid = %s', [cust_id])
                software_exists = rc.fetchone()
                if not software_exists:
                    return JsonResponse({'success': False,
                                         'error': f'Software entry (custid={cust_id}) not found. Please recreate the database.'})

                # ── Insert into customers ──────────────────────────────
                rc.execute(
                    """INSERT INTO customers
                       (custid, custname, location, expirydate)
                       VALUES (%s, %s, %s, %s)""",
                    (cust_id, customer_name, location, expiry_date)
                )

                print(f"# SAS: customers row inserted, custid={cust_id}")

                # ── Insert into itemgroups ────────────────────────────
                # [FIX] Now softwares entry definitely exists, so foreign key is satisfied
                rc.execute('SELECT COALESCE(MAX(group_id), 0) + 1 FROM itemgroups')
                next_group_id = rc.fetchone()[0]

                print(f"# DEBUG: About to insert itemgroups")
                print(f"# DEBUG: cust_id={cust_id}, software_id={software_id}")
                print(f"# DEBUG: username={username}, password={password}")

                rc.execute(
                    """INSERT INTO itemgroups
                       (group_id, description, category, date, narration, custid, software_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        next_group_id,  # INTEGER
                        username,  # VARCHAR - login username
                        1,  # INTEGER - category
                        datetime.now().strftime('%Y-%m-%d'),  # DATE
                        password,  # VARCHAR - narration (password)
                        cust_id,  # INTEGER - must exist in softwares
                        software_id  # INTEGER
                    )
                )

                print(f"# SAS: itemgroups row inserted, group_id={next_group_id}")

                rc.close()
                registry_db.close_connection()

                return JsonResponse({
                    'success': True,
                    'message': f'Customer "{customer_name}" created successfully',
                    'cust_id': cust_id,
                    'group_id': next_group_id,
                })

            except Exception as e:
                rc.close()
                registry_db.close_connection()
                import traceback;
                traceback.print_exc()
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            import traceback;file
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


def sas_debug_pg_connection(request):
    from django.http import HttpResponse
    lines = []
    lines.append(f"PG_HOST={PG_HOST}")
    lines.append(f"PG_PORT={PG_PORT}")
    lines.append(f"PG_USER={PG_USER}")
    lines.append(f"PG_DB={PG_DB}")
    lines.append(f"PG_PASSWORD={'SET' if PG_PASSWORD else 'NOT SET'}")
    lines.append("---")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DB,
            port=PG_PORT,
            connect_timeout=5
        )
        conn.close()
        lines.append(f"SUCCESS: Connected to {PG_DB}")
    except Exception as e:
        lines.append(f"FAILED: {e}")
    return HttpResponse("<br>".join(lines))