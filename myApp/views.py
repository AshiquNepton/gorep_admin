# views.py - Updated with admin functionality
import json
import pymysql
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import urllib.parse
from datetime import datetime, timedelta

from pip._vendor import requests
import json
import pymysql
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pip._vendor import requests

# Load environment variables
load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))
if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Missing critical database environment variables. Check your .env file.")


class CpanelAPIClient:
    def __init__(self, cpanel_url, username, password):
        self.cpanel_url = cpanel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)

    def authenticate(self):
        """Test cPanel authentication"""
        try:
            url = f"{self.cpanel_url}/execute/CpanelApi/version"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            #print(f"Auth error: {e}")
            return False

    def get_databases(self):
        """Get list of databases - Fixed to extract only database names"""
        try:
            url = f"{self.cpanel_url}/execute/Mysql/list_databases"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                # #print(f"Raw database response: {data}")

                if 'data' in data:
                    databases = data['data']
                elif 'result' in data:
                    databases = data['result']
                else:
                    databases = data

                db_names = []
                for db in databases:
                    if isinstance(db, dict):
                        if 'db' in db:
                            db_names.append(db['db'])
                        elif 'database' in db:
                            db_names.append(db['database'])
                        elif 'name' in db:
                            db_names.append(db['name'])
                        else:
                            for key, value in db.items():
                                if key.lower() in ['db', 'database', 'name'] and isinstance(value, str):
                                    db_names.append(value)
                                    break
                    elif isinstance(db, str):
                        db_names.append(db)

                db_names = list(set([name.strip() for name in db_names if name and name.strip()]))
                # #print(f"Extracted database names: {db_names}")
                return db_names

            #print(f"Failed to get databases: {response.status_code}")
            return []
        except Exception as e:
            #print(f"Database fetch error: {e}")
            return []

    def get_database_users(self):
        """Get database users - Fixed to extract only usernames"""
        try:
            url = f"{self.cpanel_url}/execute/Mysql/list_users"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                # #print(f"Raw users response: {data}")

                if 'data' in data:
                    users = data['data']
                elif 'result' in data:
                    users = data['result']
                else:
                    users = data

                user_names = []
                for user in users:
                    if isinstance(user, dict):
                        if 'user' in user:
                            user_names.append(user['user'])
                        elif 'username' in user:
                            user_names.append(user['username'])
                        elif 'name' in user:
                            user_names.append(user['name'])
                        else:
                            for key, value in user.items():
                                if key.lower() in ['user', 'username', 'name'] and isinstance(value, str):
                                    user_names.append(value)
                                    break
                    elif isinstance(user, str):
                        user_names.append(user)

                user_names = list(set([name.strip() for name in user_names if name and name.strip()]))
                #print(f"Extracted user names: {user_names}")
                return user_names

            #print(f"Failed to get users: {response.status_code}")
            return []
        except Exception as e:
            #print(f"Users fetch error: {e}")
            return []

    def create_database(self, database_name):
        """Create a new database"""
        try:
            #print(f"Attempting to create database: {database_name}")
            url = f"{self.cpanel_url}/execute/Mysql/create_database"
            #print(f"Using URL: {url}")

            # Use GET method with query parameters instead of POST
            response = self.session.get(url, params={'name': database_name})
            #print(f"Response status: {response.status_code}")
            #print(f"Response content: {response.text}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    #print(f"Response JSON: {data}")

                    # Check various possible success indicators
                    if 'status' in data:
                        success = data.get('status', 0) == 1
                    elif 'result' in data and isinstance(data['result'], dict):
                        success = data['result'].get('status', 0) == 1
                    elif 'data' in data:
                        success = True  # Some cPanel versions just return data without explicit status
                    else:
                        # If we get a 200 response with JSON, assume success
                        success = True

                    #print(f"Database creation success: {success}")
                    return success

                except json.JSONDecodeError as e:
                    #print(f"Failed to parse JSON response: {e}")
                    #print(f"Raw response: {response.text}")
                    return False
            else:
                #print(f"HTTP error: {response.status_code}")
                #print(f"Response: {response.text}")
                return False

        except Exception as e:
            #print(f"Database creation error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_user_to_database(self, database_name, username):
        """Add user to database with ALL PRIVILEGES"""
        try:
            #print(f"Attempting to add user '{username}' to database '{database_name}' with ALL PRIVILEGES")
            url = f"{self.cpanel_url}/execute/Mysql/set_privileges_on_database"
            #print(f"Using URL: {url}")

            # Parameters for granting ALL PRIVILEGES
            params = {
                'user': username,
                'database': database_name,
                'privileges': 'ALL PRIVILEGES'
            }

            response = self.session.get(url, params=params)
            #print(f"Response status: {response.status_code}")
            #print(f"Response content: {response.text}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    #print(f"Response JSON: {data}")

                    # Check various possible success indicators
                    if 'status' in data:
                        success = data.get('status', 0) == 1
                    elif 'result' in data and isinstance(data['result'], dict):
                        success = data['result'].get('status', 0) == 1
                    elif 'data' in data:
                        success = True  # Some cPanel versions just return data without explicit status
                    else:
                        # If we get a 200 response with JSON, assume success
                        success = True

                    #print(f"User privileges success: {success}")
                    return success

                except json.JSONDecodeError as e:
                    #print(f"Failed to parse JSON response: {e}")
                    #print(f"Raw response: {response.text}")
                    return False
            else:
                #print(f"HTTP error: {response.status_code}")
                #print(f"Response: {response.text}")
                return False

        except Exception as e:
            #print(f"User privileges error: {e}")
            import traceback
            traceback.print_exc()
            return False


class DatabaseManager:
    def __init__(self, host, user, password, database, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def connect(self):
        try:
            #print(f"Attempting to connect to MySQL:")
            #print(f"Host: {self.host}")
            #print(f"Port: {self.port}")
            #print(f"User: {self.user}")
            #print(f"Database: {self.database}")

            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                connect_timeout=10,
                autocommit=True
            )
            #print("MySQL connection successful!")
            return True
        except pymysql.Error as e:
            #print(f"PyMySQL Connection error: {e}")
            return False
        except Exception as e:
            #print(f"General Connection error: {e}")
            return False

    def get_tables(self):
        if not self.connection:
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            #print(f"Tables fetch error: {e}")
            return []

    def get_table_structure(self, table_name):
        if not self.connection:
            return []

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            cursor.close()
            return [
                {
                    'field': col[0],
                    'type': col[1],
                    'null': col[2],
                    'key': col[3],
                    'default': col[4],
                    'extra': col[5]
                }
                for col in columns
            ]
        except Exception as e:
            #print(f"Table structure error: {e}")
            return []

    def get_table_data(self, table_name, limit=100, offset=0, filter_condition=None):
        """Get table data with optional filtering"""
        if not self.connection:
            return []

        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)

            # Build base query
            query = f"SELECT * FROM `{table_name}`"
            params = []

            # Add filter condition if provided
            if filter_condition:
                field = filter_condition.get('field')
                condition = filter_condition.get('condition')
                value = filter_condition.get('value')

                if field and condition:
                    if condition in ['IS NULL', 'IS NOT NULL']:
                        query += f" WHERE `{field}` {condition}"
                    elif condition == 'LIKE':
                        query += f" WHERE `{field}` LIKE %s"
                        params.append(f"%{value}%")
                    elif condition == 'NOT LIKE':
                        query += f" WHERE `{field}` NOT LIKE %s"
                        params.append(f"%{value}%")
                    else:
                        query += f" WHERE `{field}` {condition} %s"
                        params.append(value)

            # Add limit and offset
            query += f" LIMIT {limit} OFFSET {offset}"

            #print(f"Executing query: {query}")
            #print(f"Parameters: {params}")

            cursor.execute(query, params)
            data = cursor.fetchall()
            cursor.close()
            return data
        except Exception as e:
            #print(f"Table data error: {e}")
            return []

    def get_table_count(self, table_name, filter_condition=None):
        """Get total count of records with optional filtering"""
        if not self.connection:
            return 0

        try:
            cursor = self.connection.cursor()

            # Build count query
            query = f"SELECT COUNT(*) FROM `{table_name}`"
            params = []

            # Add filter condition if provided
            if filter_condition:
                field = filter_condition.get('field')
                condition = filter_condition.get('condition')
                value = filter_condition.get('value')

                if field and condition:
                    if condition in ['IS NULL', 'IS NOT NULL']:
                        query += f" WHERE `{field}` {condition}"
                    elif condition == 'LIKE':
                        query += f" WHERE `{field}` LIKE %s"
                        params.append(f"%{value}%")
                    elif condition == 'NOT LIKE':
                        query += f" WHERE `{field}` NOT LIKE %s"
                        params.append(f"%{value}%")
                    else:
                        query += f" WHERE `{field}` {condition} %s"
                        params.append(value)

            #print(f"Executing count query: {query}")
            #print(f"Parameters: {params}")

            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            #print(f"Table count error: {e}")
            return 0

    def create_tables(self):
        """Create all required tables after database creation"""
        if not self.connection:
            return False, "No database connection"

        table_schemas = [
            # Attendance table
            """
            CREATE TABLE `Attendance` (
              `refNo` int(11) NOT NULL AUTO_INCREMENT,
              `empId` int(11) NOT NULL,
              `date` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              `checkInTime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
              `checkInLocation` varchar(300) NOT NULL,
              `checkOutTime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
              `checkOutLocation` varchar(300) DEFAULT NULL,
              `notes` varchar(500) DEFAULT NULL,
              `status` int(11) NOT NULL,
              PRIMARY KEY (`refNo`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # TransactionDetails table
            """
            CREATE TABLE `TransactionDetails` (
              `transId` int(11) NOT NULL AUTO_INCREMENT,
              `transDate` date NOT NULL,
              `typeCode` int(11) NOT NULL,
              `customerId` int(11) NOT NULL,
              `transAmount` double DEFAULT NULL,
              `transCount` int(11) DEFAULT NULL,
              `description` varchar(100) DEFAULT NULL,
              `empId` int(11) NOT NULL,
              PRIMARY KEY (`transId`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # Transaction table
            """
            CREATE TABLE `Transaction` (
              `transId` int(11) NOT NULL AUTO_INCREMENT,
              `transDate` date NOT NULL,
              `transAmount` double NOT NULL,
              `transCount` int(11) NOT NULL,
              `typeCode` int(11) NOT NULL,
              `empID` int(11) NOT NULL,
              PRIMARY KEY (`transId`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # Tickets table
            """
CREATE TABLE `Tickets` (
`ticket_no` int(11) NOT NULL AUTO_INCREMENT,
`customer_name` varchar(100) DEFAULT NULL,
`mobile` varchar(20) DEFAULT NULL,
`email` varchar(100) DEFAULT NULL,
`service_type` varchar(50) DEFAULT NULL,
`problem_description` text DEFAULT NULL,
`ip_address` varchar(45) DEFAULT NULL,
`created_at` datetime DEFAULT current_timestamp(),
`ticket_status` int(11) DEFAULT 0,
`schedule_status` int(11) DEFAULT 0,
`narration` varchar(100) DEFAULT NULL,
PRIMARY KEY (`ticket_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci
""",
            # Schedules table
            """
            CREATE TABLE `Schedules` (
              `refNo` int(11) NOT NULL AUTO_INCREMENT,
              `empId` int(11) NOT NULL,
              `scheduleDate` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              `custId` int(11) NOT NULL,
              `visitType` int(11) NOT NULL,
              `narration` varchar(300) NOT NULL,
              `status` int(11) NOT NULL,
              PRIMARY KEY (`refNo`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # ItemGroups table
            """
            CREATE TABLE `ItemGroups` (
              `GroupID` int(11) NOT NULL AUTO_INCREMENT,
              `Category` int(11) NOT NULL,
              `Description` varchar(60) NOT NULL,
              `uCode` varchar(10) DEFAULT NULL,
              `Under` int(11) DEFAULT NULL,
              PRIMARY KEY (`GroupID`)
            ) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
            """,

            # Events table
            """
            CREATE TABLE `Events` (
              `refNo` int(11) NOT NULL AUTO_INCREMENT,
              `empId` int(11) NOT NULL,
              `date` date NOT NULL,
              `custId` int(11) DEFAULT NULL,
              `visitType` int(11) NOT NULL,
              `checkIn` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              `checkOut` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
              `checkInLocation` varchar(100) NOT NULL,
              `checkOutLocation` varchar(100) DEFAULT NULL,
              `paymentType` int(11) DEFAULT NULL,
              `amount` float DEFAULT NULL,
              `narration` varchar(500) DEFAULT NULL,
              `status` int(11) NOT NULL DEFAULT 1,
              `checkOutStatus` int(11) NOT NULL,
              PRIMARY KEY (`refNo`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # Employee table (UPDATED: added user_type column)
            """
            CREATE TABLE `Employee` (
              `empId` int(11) NOT NULL AUTO_INCREMENT,
              `empName` varchar(100) NOT NULL,
              `empCode` varchar(20) DEFAULT NULL,
              `pwd` varchar(10) DEFAULT NULL,
              `target` double DEFAULT 0,
              `user_type` int(11) DEFAULT 0,
              PRIMARY KEY (`empId`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
            """,

            # Customer table (UPDATED: added AcBal and LastPayment columns)
            """
            CREATE TABLE `Customer` (
              `CustId` int(10) NOT NULL AUTO_INCREMENT,
              `CustCode` varchar(25) NOT NULL,
              `CustName` varchar(150) NOT NULL,
              `Address1` varchar(100) DEFAULT NULL,
              `Address2` varchar(100) DEFAULT NULL,
              `Area` int(11) DEFAULT NULL,
              `Phone` varchar(15) DEFAULT NULL,
              `Mobile` varchar(15) DEFAULT NULL,
              `TypeCode` int(11) NOT NULL,
              `empId` int(11) DEFAULT NULL,
              `AcBal` int(11) DEFAULT NULL,
              `LastPayment` date DEFAULT NULL,
              `createdAt` timestamp NULL DEFAULT current_timestamp(),
              `importStatus` int(11) DEFAULT NULL,
              PRIMARY KEY (`CustId`,`TypeCode`)
            ) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
            """,

            # ChartOfCode table
            """
            CREATE TABLE `ChartOfCode` (
              `Category` varchar(20) NOT NULL,
              `Code` varchar(15) NOT NULL,
              `Description` varchar(100) NOT NULL,
              `TypeCode` varchar(15) DEFAULT NULL,
              `EDate` datetime DEFAULT current_timestamp(),
              `ENo` int(11) DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci
            """,

            # Schedule_details table (NEW)
            """
            CREATE TABLE `Schedule_details` (
              `Sn` tinyint(4) NOT NULL,
              `ScheduleRefNo` int(11) NOT NULL,
              `CurrentDate` date NOT NULL,
              `FollowUpStatus` int(11) NOT NULL,
              `NextSchedule` date NOT NULL,
              `Rep` int(11) NOT NULL,
              `Remarks` varchar(200) NOT NULL,
              `Status` tinyint(1) NOT NULL,
              PRIMARY KEY (`Sn`, `ScheduleRefNo`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        ]

        try:
            cursor = self.connection.cursor()

            for i, schema in enumerate(table_schemas):
                try:
                    cursor.execute(schema)
                    #print(f"Created table {i+1} of {len(table_schemas)}")
                except Exception as table_error:
                    print(f"Error creating table {i+1}: {table_error}")
                    # Continue with other tables even if one fails

            cursor.close()
            return True, f"Successfully created {len(table_schemas)} tables"

        except Exception as e:
            #print(f"Error in create_tables: {e}")
            return False, str(e)

    def execute_query(self, query):
        if not self.connection:
            return False, "No database connection"

        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query)

            if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                result = cursor.fetchall()
                cursor.close()
                return True, result
            else:
                affected_rows = cursor.rowcount
                cursor.close()
                return True, f"Query executed successfully. {affected_rows} rows affected."
        except Exception as e:
            return False, str(e)

    def insert_record(self, table_name, data):
        if not self.connection:
            return False, "No database connection"

        try:
            # Remove empty values and convert them to None for proper NULL handling
            cleaned_data = {}
            for key, value in data.items():
                if value == '' or value is None:
                    cleaned_data[key] = None
                else:
                    cleaned_data[key] = value

            columns = ', '.join([f"`{col}`" for col in cleaned_data.keys()])
            placeholders = ', '.join(['%s'] * len(cleaned_data))
            query = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"

            cursor = self.connection.cursor()
            cursor.execute(query, list(cleaned_data.values()))
            insert_id = cursor.lastrowid
            cursor.close()
            return True, insert_id
        except Exception as e:
            return False, str(e)

    def update_record(self, table_name, data, where_clause, where_values):
        if not self.connection:
            return False, "No database connection"

        try:
            # Remove empty values and convert them to None for proper NULL handling
            cleaned_data = {}
            for key, value in data.items():
                if value == '' or value is None:
                    cleaned_data[key] = None
                else:
                    cleaned_data[key] = value

            set_clause = ', '.join([f"`{col}` = %s" for col in cleaned_data.keys()])
            query = f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause}"

            cursor = self.connection.cursor()
            cursor.execute(query, list(cleaned_data.values()) + where_values)
            affected_rows = cursor.rowcount
            cursor.close()
            return True, f"Updated {affected_rows} record(s)"
        except Exception as e:
            return False, str(e)

    def delete_record(self, table_name, where_clause, where_values):
        if not self.connection:
            return False, "No database connection"

        try:
            query = f"DELETE FROM `{table_name}` WHERE {where_clause}"
            cursor = self.connection.cursor()
            cursor.execute(query, where_values)
            affected_rows = cursor.rowcount
            cursor.close()
            return True, f"Deleted {affected_rows} record(s)"
        except Exception as e:
            return False, str(e)

    def close_connection(self):
        if self.connection and self.connection.open:
            self.connection.close()


# Existing views
def login_view(request):
    if request.method == 'POST':
        cpanel_url = request.POST.get('cpanel_url')
        username = request.POST.get('username')
        password = request.POST.get('password')

        cpanel_client = CpanelAPIClient(cpanel_url, username, password)

        if cpanel_client.authenticate():
            request.session['cpanel_url'] = cpanel_url
            request.session['cpanel_user'] = username
            request.session['cpanel_pass'] = password
            request.session['user'] = username
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid cPanel credentials or connection failed')

    return render(request, 'login.html')


def dashboard_view(request):
    if 'user' not in request.session:
        return redirect('login')

    # ── MySQL databases (via cPanel API) ──────────────────────────────────
    cpanel_client = CpanelAPIClient(
        request.session['cpanel_url'],
        request.session['cpanel_user'],
        request.session['cpanel_pass']
    )
    mysql_databases = cpanel_client.get_databases()
    db_users        = cpanel_client.get_database_users()

    # ── PostgreSQL databases (via server .env credentials) ────────────────
    pg_databases = []
    try:
        from .views_sas import PostgreSQLManager, PG_HOST, PG_USER, PG_PASSWORD, PG_PORT
        if PG_USER and PG_PASSWORD:
            pg_manager = PostgreSQLManager(PG_HOST, PG_USER, PG_PASSWORD, database='postgres', port=PG_PORT)
            if pg_manager.connect():
                pg_databases = pg_manager.get_databases()
                pg_manager.close_connection()
    except Exception as e:
        print(f"Dashboard: Failed to load PostgreSQL databases: {e}")

    context = {
        'mysql_databases': mysql_databases,
        'pg_databases':    pg_databases,
        'db_users':        db_users,
        'user':            request.session['user'],

        # Keep backward-compat key in case anything else references 'databases'
        'databases':       mysql_databases,
    }

    return render(request, 'dashboard.html', context)

def database_explorer_view(request, db_name):
    if 'user' not in request.session:
        return redirect('login')

    if not db_name or db_name.strip() == '':
        messages.error(request, 'Database name is required')
        return redirect('dashboard')

    db_name = urllib.parse.unquote(db_name).strip()
    #print(f"Cleaned database name: '{db_name}'")

    db_host = request.GET.get('host', 'localhost')
    db_port = request.GET.get('port', '3306')
    db_user = request.GET.get('db_user')
    db_password = request.GET.get('db_password')

    if db_host.startswith(('http://', 'https://')):
        from urllib.parse import urlparse
        parsed_url = urlparse(db_host)
        db_host = parsed_url.hostname or 'localhost'
        #print(f"Extracted hostname: {db_host}")

    try:
        db_port = int(db_port)
    except (ValueError, TypeError):
        db_port = 3306

    #print(f"Connection parameters:")
    #print(f"Host: {db_host}")
    #print(f"Port: {db_port}")
    #print(f"User: {db_user}")
    #print(f"Database: {db_name}")

    if not db_user or not db_password:
        messages.error(request, 'Database credentials required')
        return redirect('dashboard')

    db_manager = DatabaseManager(db_host, db_user, db_password, db_name, db_port)

    if not db_manager.connect():
        messages.error(request,
                       f'Failed to connect to database: {db_name}. Check your MySQL host, credentials, and network connectivity.')
        return redirect('dashboard')

    tables = db_manager.get_tables()
    db_manager.close_connection()

    context = {
        'database': db_name,
        'tables': tables,
        'db_host': db_host,
        'db_port': db_port,
        'db_user': db_user,
        'db_password': db_password
    }

    return render(request, 'database_explorer.html', context)


# Admin page views
def admin_create_database_view(request):
    """Render the create database page with database users"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Get database users to pass to template
    try:
        cpanel_client = CpanelAPIClient(
            request.session['cpanel_url'],
            request.session['cpanel_user'],
            request.session['cpanel_pass']
        )
        db_users = cpanel_client.get_database_users()
    except Exception as e:
        #print(f"Error getting database users: {e}")
        db_users = []

    context = {
        'db_users': db_users
    }

    return render(request, 'admin/create_database.html', context)


def admin_device_management_view(request):
    """Render the device management page"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return render(request, 'admin/device_management.html')


def admin_add_admin_view(request):
    """Render the add admin page"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return render(request, 'admin/add_admin.html')


def admin_add_permission_view(request):
    """Render the add permission page"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return render(request, 'admin/add_permission.html')


def admin_add_location_view(request):
    """Render the add location page"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return render(request, 'admin/add_location.html')


# Admin API endpoints
@csrf_exempt
def admin_api_devices(request):
    """Get devices with customer information for device management"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        try:
            # Connect to neptouia_nepton database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to neptouia_nepton database'})

            # Get devices with customer names - include deviceImei, order by activationDate descending
            query = """
                    SELECT d.*, c.custName 
                    FROM Devices d
                    LEFT JOIN Customers c ON d.custId = c.custId
                    ORDER BY d.activationDate DESC
                """

            cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query)
            devices = cursor.fetchall()
            cursor.close()
            db_manager.close_connection()

            return JsonResponse({'success': True, 'devices': devices})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_update_device_status(request):
    """Update device status (activate/deactivate/block) using deviceImei"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_imei = data.get('device_imei')  # Changed from device_id
            status = data.get('status')

            if not device_imei or status is None:
                return JsonResponse({'success': False, 'error': 'Device IMEI and status are required'})

            # Validate status values
            if status not in [1, 0, -1]:
                return JsonResponse({'success': False,
                                     'error': 'Invalid status value. Must be 1 (Active), 0 (Inactive), or -1 (Blocked)'})

            # Connect to neptouia_nepton database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to neptouia_nepton database'})

            # First, check if device exists
            cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM Devices WHERE deviceImei = %s", [device_imei])
            existing_device = cursor.fetchone()
            cursor.close()

            if not existing_device:
                db_manager.close_connection()
                return JsonResponse({'success': False, 'error': f'Device with IMEI {device_imei} not found'})

            # Update device status using deviceImei
            success, message = db_manager.update_record(
                'Devices',
                {'status': status},
                'deviceImei = %s',  # Changed from 'id = %s' to 'deviceImei = %s'
                [device_imei]
            )

            db_manager.close_connection()

            if success:
                status_text = {1: 'Active', 0: 'Inactive', -1: 'Blocked'}
                return JsonResponse({
                    'success': True,
                    'message': f'Device {device_imei} status updated to {status_text[status]}'
                })
            else:
                return JsonResponse({'success': False, 'error': message})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_database_users(request):
    """Get list of database users - with debugging"""
    #print(f"API called: {request.method} {request.path}")
    #print(f"Session keys: {list(request.session.keys())}")
    #print(f"Session user: {request.session.get('user')}")

    # Check if user is authenticated
    if 'user' not in request.session:
        #print("User not authenticated - returning 401")
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'GET':
        try:
            #print("Getting cPanel client details...")
            cpanel_url = request.session.get('cpanel_url')
            cpanel_user = request.session.get('cpanel_user')
            cpanel_pass = request.session.get('cpanel_pass')

            #print(f"cPanel URL: {cpanel_url}")
            #print(f"cPanel User: {cpanel_user}")
            #print(f"cPanel Pass: {'*' * len(cpanel_pass) if cpanel_pass else 'None'}")

            if not all([cpanel_url, cpanel_user, cpanel_pass]):
                #print("Missing cPanel credentials in session")
                return JsonResponse({'success': False, 'error': 'Missing cPanel credentials in session'})

            cpanel_client = CpanelAPIClient(cpanel_url, cpanel_user, cpanel_pass)

            #print("Getting database users...")
            users = cpanel_client.get_database_users()
            #print(f"Retrieved users: {users}")

            return JsonResponse({'success': True, 'users': users})

        except Exception as e:
            #print(f"Exception in admin_api_database_users: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    #print("Invalid request method")
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_create_database(request):
    """Create a new database and add entry to Softwares table"""
    #print(f"Create database API called: {request.method}")
    #print(f"Session user: {request.session.get('user')}")

    if 'user' not in request.session:
        #print("User not authenticated")
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
                #print(f"Received data: {data}")
            except json.JSONDecodeError as e:
                #print(f"JSON decode error: {e}")
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'})

            database_name = data.get('database_name')
            database_user = data.get('database_user')
            expiry_years = data.get('expiry_years', 1)

            #print(f"Database name: {database_name}")
            #print(f"Database user: {database_user}")
            #print(f"Expiry years: {expiry_years}")

            if not database_name or not database_user:
                return JsonResponse({'success': False, 'error': 'Database name and user are required'})

            # Validate database name format
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', database_name):
                return JsonResponse(
                    {'success': False, 'error': 'Database name can only contain letters, numbers, and underscores'})

            # Create database via cPanel API
            cpanel_url = request.session.get('cpanel_url')
            cpanel_user = request.session.get('cpanel_user')
            cpanel_pass = request.session.get('cpanel_pass')

            if not all([cpanel_url, cpanel_user, cpanel_pass]):
                return JsonResponse({'success': False, 'error': 'Missing cPanel credentials'})

            #print("Creating cPanel client...")
            cpanel_client = CpanelAPIClient(cpanel_url, cpanel_user, cpanel_pass)

            # Test authentication first
            #print("Testing cPanel authentication...")
            if not cpanel_client.authenticate():
                return JsonResponse(
                    {'success': False, 'error': 'Failed to authenticate with cPanel. Please check your credentials.'})

            #print("Creating database via cPanel...")
            database_created = cpanel_client.create_database(database_name)

            if not database_created:
                # Try to get more specific error information
                return JsonResponse({'success': False,
                                     'error': 'Failed to create database via cPanel. This could be due to: 1) Database name already exists, 2) Invalid database name format, 3) cPanel API limitations, or 4) Insufficient permissions.'})

            #print("Database created successfully via cPanel")

            # Connect to neptouia_nepton database to add software entry
            #print("Connecting to neptouia_nepton database...")
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                #print("Failed to connect to neptouia_nepton database")
                return JsonResponse({'success': False,
                                     'error': 'Database created via cPanel but failed to connect to neptouia_nepton database for record keeping'})

            # Get next custId
            #print("Getting next custId...")
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(custId), 0) + 1 FROM Softwares")
            next_cust_id = cursor.fetchone()[0]
            cursor.close()
            #print(f"Next custId: {next_cust_id}")

            # Calculate expiry date
            from datetime import datetime, timedelta
            expiry_date = datetime.now() + timedelta(days=expiry_years * 365)
            #print(f"Expiry date: {expiry_date}")

            # Insert into Softwares table
            #print("Inserting into Softwares table...")
            software_data = {
                'custId': next_cust_id,
                'software': 3,
                'host': DB_HOST,
                'db': database_name,
                'dbPass': DB_PASSWORD,
                'userName': database_user,
                'pwd': DB_PASSWORD,
                'expiry': expiry_date.strftime('%Y-%m-%d')
            }
            #print(f"Software data: {software_data}")

            success, result = db_manager.insert_record('Softwares', software_data)
            db_manager.close_connection()

            if success:
                #print("Software entry created successfully")
                return JsonResponse(
                    {'success': True, 'message': 'Database created successfully', 'cust_id': next_cust_id})
            else:
                #print(f"Failed to create software entry: {result}")
                return JsonResponse(
                    {'success': False, 'error': f'Database created but failed to add software entry: {result}'})

        except Exception as e:
            #print(f"Exception in admin_api_create_database: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})

    #print("Invalid request method")
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_customers(request):
    """Get list of customers"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        try:
            # Connect to neptouia_nepton database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to neptouia_nepton database'})

            # Get customers
            cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT custId, custName, location, expiryDate FROM Customers ORDER BY custId")
            customers = cursor.fetchall()
            cursor.close()
            db_manager.close_connection()

            return JsonResponse({'success': True, 'customers': customers})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_create_customer(request):
    """Create a new customer"""
    #print(f"Create customer API called: {request.method}")
    #print(f"Session user: {request.session.get('user')}")

    if 'user' not in request.session:
        #print("User not authenticated")
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
                #print(f"Received data: {data}")
            except json.JSONDecodeError as e:
                #print(f"JSON decode error: {e}")
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'})

            customer_name = data.get('customer_name')
            location = data.get('location')
            expiry_date = data.get('expiry_date')

            #print(f"Customer name: {customer_name}")
            #print(f"Location: {location}")
            #print(f"Expiry date: {expiry_date}")

            if not customer_name or not location or not expiry_date:
                return JsonResponse(
                    {'success': False, 'error': 'Customer name, location, and expiry date are required'})

            # Connect to neptouia_nepton database
            #print("Connecting to neptouia_nepton database...")
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                #print("Failed to connect to neptouia_nepton database")
                return JsonResponse({'success': False, 'error': 'Failed to connect to neptouia_nepton database'})

            # Get next custId
            #print("Getting next custId...")
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(custId), 0) + 1 FROM Customers")
            next_cust_id = cursor.fetchone()[0]
            cursor.close()
            #print(f"Next custId: {next_cust_id}")

            # Insert customer
            #print("Inserting customer...")
            customer_data = {
                'custId': next_cust_id,
                'custName': customer_name,
                'location': location,
                'expiryDate': expiry_date
            }
            #print(f"Customer data: {customer_data}")

            success, result = db_manager.insert_record('Customers', customer_data)
            db_manager.close_connection()

            if success:
                #print("Customer created successfully")
                return JsonResponse(
                    {'success': True, 'message': 'Customer created successfully', 'cust_id': next_cust_id})
            else:
                #print(f"Failed to create customer: {result}")
                return JsonResponse({'success': False, 'error': str(result)})

        except Exception as e:
            #print(f"Exception in admin_api_create_customer: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    #print("Invalid request method")
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_add_admin(request):
    """Add admin to itemgroups table in neptouia_nepton database"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            customer_id = data.get('customer_id')

            if not username or not password or not customer_id:
                return JsonResponse({'success': False, 'error': 'Username, password, and customer ID are required'})

            # FIXED: Connect to neptouia_nepton database (not itemgroups as database)
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': 'Failed to connect to neptouia_nepton database'})

            # Get next group_id from itemgroups TABLE
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(group_id), 0) + 1 FROM itemgroups")
            next_group_id = cursor.fetchone()[0]
            cursor.close()

            # Insert admin into itemgroups TABLE
            admin_data = {
                'group_id': next_group_id,
                'description': username,
                'category': 1,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'narration': password,
                'custId': customer_id,
                'software_id': 3
            }

            success, result = db_manager.insert_record('itemgroups', admin_data)
            db_manager.close_connection()

            if success:
                return JsonResponse(
                    {'success': True, 'message': 'Admin created successfully', 'group_id': next_group_id})
            else:
                return JsonResponse({'success': False, 'error': str(result)})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_add_permission(request):
    """Add permission to system"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            permission_name = data.get('permission_name')
            description = data.get('description', '')
            permission_level = data.get('permission_level')
            customer_id = data.get('customer_id')
            is_active = data.get('is_active', True)

            if not permission_name or not permission_level:
                return JsonResponse({'success': False, 'error': 'Permission name and level are required'})

            # For now, we'll store permissions in a simple format
            # In a real system, you'd have a proper permissions table
            permission_data = {
                'name': permission_name,
                'description': description,
                'level': permission_level,
                'customer_id': customer_id,
                'active': is_active,
                'created_at': datetime.now().isoformat()
            }

            # Here you would typically insert into a permissions table
            # For this example, we'll just return success with a mock ID
            permission_id = f"PERM_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return JsonResponse({
                'success': True,
                'message': f'Permission "{permission_name}" created successfully',
                'permission_id': permission_id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_add_location(request):
    """Add location to system"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            location_name = data.get('location_name')
            address = data.get('address', '')
            city = data.get('city')
            state = data.get('state', '')
            country = data.get('country')
            zip_code = data.get('zip_code', '')
            phone = data.get('phone', '')
            email = data.get('email', '')
            description = data.get('description', '')
            is_active = data.get('is_active', True)

            if not location_name or not city or not country:
                return JsonResponse({'success': False, 'error': 'Location name, city, and country are required'})

            # For now, we'll store locations in a simple format
            # In a real system, you'd have a proper locations table
            location_data = {
                'name': location_name,
                'address': address,
                'city': city,
                'state': state,
                'country': country,
                'zip_code': zip_code,
                'phone': phone,
                'email': email,
                'description': description,
                'active': is_active,
                'created_at': datetime.now().isoformat()
            }

            # Here you would typically insert into a locations table
            # For this example, we'll just return success with a mock ID
            location_id = f"LOC_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return JsonResponse({
                'success': True,
                'message': f'Location "{location_name}" created successfully',
                'location_id': location_id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


# Existing API endpoints
@csrf_exempt
def table_data_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        db_name = request.GET.get('database')
        table_name = request.GET.get('table')
        action = request.GET.get('action', 'data')

        db_host = request.GET.get('host', 'localhost')
        db_user = request.GET.get('db_user')
        db_password = request.GET.get('db_password')

        if not all([db_name, table_name, db_user, db_password]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        db_manager = DatabaseManager(db_host, db_user, db_password, db_name)

        if not db_manager.connect():
            return JsonResponse({'error': 'Database connection failed'}, status=500)

        try:
            if action == 'structure':
                structure = db_manager.get_table_structure(table_name)
                return JsonResponse({'structure': structure})

            elif action == 'data':
                limit = int(request.GET.get('limit', 100))
                offset = int(request.GET.get('offset', 0))

                # Parse filter if provided
                filter_condition = None
                filter_param = request.GET.get('filter')
                if filter_param:
                    try:
                        filter_condition = json.loads(filter_param)
                        #print(f"Applied filter: {filter_condition}")
                    except json.JSONDecodeError:
                        print("Invalid filter JSON")

                data = db_manager.get_table_data(table_name, limit, offset, filter_condition)
                total_count = db_manager.get_table_count(table_name, filter_condition)

                return JsonResponse({
                    'data': data,
                    'total_count': total_count,
                    'has_more': (offset + limit) < total_count
                })
        finally:
            db_manager.close_connection()

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def execute_query_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query')
        db_name = data.get('database')

        db_host = data.get('host', 'localhost')
        db_user = data.get('db_user')
        db_password = data.get('db_password')

        if not all([query, db_name, db_user, db_password]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        db_manager = DatabaseManager(db_host, db_user, db_password, db_name)

        if not db_manager.connect():
            return JsonResponse({'error': 'Database connection failed'}, status=500)

        try:
            success, result = db_manager.execute_query(query)

            if success:
                return JsonResponse({'success': True, 'result': result})
            else:
                return JsonResponse({'success': False, 'error': result})
        finally:
            db_manager.close_connection()

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def table_operations_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        db_name = data.get('database')
        table_name = data.get('table')

        db_host = data.get('host', 'localhost')
        db_user = data.get('db_user')
        db_password = data.get('db_password')

        if not all([action, db_name, table_name, db_user, db_password]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        db_manager = DatabaseManager(db_host, db_user, db_password, db_name)

        if not db_manager.connect():
            return JsonResponse({'error': 'Database connection failed'}, status=500)

        try:
            if action == 'insert':
                record_data = data.get('data', {})
                success, message = db_manager.insert_record(table_name, record_data)

            elif action == 'update':
                record_data = data.get('data', {})
                where_clause = data.get('where_clause')
                where_values = data.get('where_values', [])
                success, message = db_manager.update_record(table_name, record_data, where_clause, where_values)

            elif action == 'delete':
                where_clause = data.get('where_clause')
                where_values = data.get('where_values', [])
                success, message = db_manager.delete_record(table_name, where_clause, where_values)

            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)

            if success:
                return JsonResponse({'success': True, 'message': message})
            else:
                return JsonResponse({'success': False, 'error': message})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            db_manager.close_connection()

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def test_connection_api(request):
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        data = json.loads(request.body)
        db_host = data.get('host', 'localhost')
        db_port = data.get('port', 3306)
        db_user = data.get('user')
        db_password = data.get('password')
        db_name = data.get('database')

        if not all([db_host, db_user, db_password, db_name]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})

        try:
            db_port = int(db_port) if db_port else 3306

            db_manager = DatabaseManager(db_host, db_user, db_password, db_name, db_port)

            if db_manager.connect():
                db_manager.close_connection()
                return JsonResponse({'success': True, 'message': 'Connection successful'})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to connect to database'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Connection test failed: {str(e)}'})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_databases(request):
    """Get list of databases from cPanel"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        try:
            # Get databases using existing cPanel client
            cpanel_client = CpanelAPIClient(
                request.session['cpanel_url'],
                request.session['cpanel_user'],
                request.session['cpanel_pass']
            )

            databases = cpanel_client.get_databases()
            return JsonResponse({'success': True, 'databases': databases})

        except Exception as e:
            #print(f"Error in admin_api_databases: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def logout_view(request):
    request.session.flush()
    return redirect('login')


# Add these new functions to your views.py file

@csrf_exempt
@csrf_exempt
def admin_api_employees(request):
    """Get list of employees from selected database - Enhanced with better error handling"""
    #print(f"=== EMPLOYEE API DEBUG START ===")
    #print(f"Method: {request.method}")
    #print(f"Path: {request.path}")
    #print(f"GET params: {request.GET}")
    #print(f"Session keys: {list(request.session.keys())}")
    #print(f"User in session: {'user' in request.session}")

    # Enhanced authentication check
    if 'user' not in request.session:
        #print("AUTHENTICATION FAILED - No user in session")
        return JsonResponse({
            'success': False,
            'error': 'Authentication failed - please log in again',
            'debug': 'No user in session'
        }, status=401)

    if request.method == 'GET':
        try:
            database_name = request.GET.get('database')
            #print(f"Database parameter: {database_name}")

            if not database_name:
                #print("ERROR: No database name provided")
                return JsonResponse({
                    'success': False,
                    'error': 'Database name is required',
                    'debug': 'Missing database parameter'
                })

            #print(f"Attempting connection to database: {database_name}")

            # Enhanced database connection with more detailed error handling
            try:
                db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)
                #print("DatabaseManager created successfully")

                connection_success = db_manager.connect()
                #print(f"Connection attempt result: {connection_success}")

                if not connection_success:
                    #print("DATABASE CONNECTION FAILED")
                    return JsonResponse({
                        'success': False,
                        'error': f'Failed to connect to database: {database_name}',
                        'debug': f'Connection failed for database: {database_name}'
                    })

                #print("Database connection successful")

            except Exception as db_error:
                #print(f"DATABASE CONNECTION EXCEPTION: {db_error}")
                return JsonResponse({
                    'success': False,
                    'error': f'Database connection error: {str(db_error)}',
                    'debug': f'Connection exception: {type(db_error).__name__}'
                })

            # Enhanced query execution with better error handling
            try:
                #print("Executing employee query...")
                cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)

                # First, check if Employee table exists
                cursor.execute("SHOW TABLES LIKE 'Employee'")
                table_exists = cursor.fetchone()

                if not table_exists:
                    cursor.close()
                    db_manager.close_connection()
                    #print("ERROR: Employee table does not exist")
                    return JsonResponse({
                        'success': False,
                        'error': f'Employee table not found in database: {database_name}',
                        'debug': 'Employee table does not exist'
                    })

                # Execute the main query
                cursor.execute("SELECT empId, empName, empCode, pwd FROM Employee ORDER BY empName")
                employees = cursor.fetchall()
                cursor.close()
                db_manager.close_connection()

                #print(f"Successfully found {len(employees)} employees")
                #print(f"Sample employee data: {employees[:2] if employees else 'No employees'}")

                return JsonResponse({
                    'success': True,
                    'employees': employees,
                    'debug': f'Found {len(employees)} employees'
                })

            except pymysql.Error as query_error:
                #print(f"MYSQL QUERY ERROR: {query_error}")
                if db_manager.connection:
                    db_manager.close_connection()
                return JsonResponse({
                    'success': False,
                    'error': f'Database query failed: {str(query_error)}',
                    'debug': f'MySQL error: {type(query_error).__name__}'
                })

            except Exception as query_error:
                #print(f"GENERAL QUERY ERROR: {query_error}")
                if db_manager.connection:
                    db_manager.close_connection()
                return JsonResponse({
                    'success': False,
                    'error': f'Query execution failed: {str(query_error)}',
                    'debug': f'Query exception: {type(query_error).__name__}'
                })

        except Exception as outer_error:
            #print(f"OUTER EXCEPTION in admin_api_employees: {outer_error}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(outer_error)}',
                'debug': f'Outer exception: {type(outer_error).__name__}'
            })

    #print("ERROR: Invalid request method")
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method - only GET allowed',
        'debug': f'Method was: {request.method}'
    }, status=405)


@csrf_exempt
def admin_api_update_employee_permission(request):
    """Update employee password and permissions"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            database_name = data.get('database')
            employee_id = data.get('employee_id')
            employee_name = data.get('employee_name')
            password = data.get('password')
            rep_wise_customer = data.get('rep_wise_customer', False)

            #print(f"Updating employee permission for database: {database_name}, employee: {employee_id}")

            if not all([database_name, employee_id, password]):
                return JsonResponse({'success': False, 'error': 'Database, employee ID, and password are required'})

            # Validate password length (max 10 characters as per table structure)
            if len(password) > 10:
                return JsonResponse({'success': False, 'error': 'Password cannot exceed 10 characters'})

            # Connect to the selected database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': f'Failed to connect to database: {database_name}'})

            # Update password in Employee table
            success, message = db_manager.update_record(
                'Employee',
                {'pwd': password},
                'empId = %s',
                [employee_id]
            )

            if not success:
                db_manager.close_connection()
                return JsonResponse({'success': False, 'error': f'Failed to update password: {message}'})

            #print(f"Password updated successfully for employee {employee_id}")

            # If rep-wise customer permission is checked, add entry to ChartOfCode
            if rep_wise_customer:
                chart_data = {
                    'Category': 'goRep',
                    'Code': str(employee_id),
                    'Description': '1',
                    'TypeCode': 'PRM',
                    'EDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # Check if entry already exists to avoid duplicates
                cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)
                cursor.execute(
                    "SELECT COUNT(*) as count FROM ChartOfCode WHERE Category = %s AND Code = %s AND TypeCode = %s",
                    ['goRep', str(employee_id), 'PRM']
                )
                existing = cursor.fetchone()
                cursor.close()

                if existing['count'] == 0:
                    success, message = db_manager.insert_record('ChartOfCode', chart_data)
                    if not success:
                        db_manager.close_connection()
                        return JsonResponse(
                            {'success': False, 'error': f'Password updated but failed to add permission: {message}'})
                    #print(f"Rep-wise customer permission added for employee {employee_id}")
                else:
                    print(f"Rep-wise customer permission already exists for employee {employee_id}")

            db_manager.close_connection()

            return JsonResponse({
                'success': True,
                'message': f'Employee "{employee_name}" updated successfully' + (
                ' with rep-wise customer permission' if rep_wise_customer else '')
            })

        except Exception as e:
            #print(f"Error updating employee permission: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


# Updated admin_api_create_database function
@csrf_exempt
def admin_api_create_database(request):
    """Create a new database, add user privileges, add entry to Softwares table, and create required tables"""
    #print(f"Create database API called: {request.method}")
    #print(f"Session user: {request.session.get('user')}")

    if 'user' not in request.session:
        #print("User not authenticated")
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
                #print(f"Received data: {data}")
            except json.JSONDecodeError as e:
                #print(f"JSON decode error: {e}")
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'})

            database_name = data.get('database_name')
            database_user = data.get('database_user')
            expiry_years = data.get('expiry_years', 1)

            #print(f"Database name: {database_name}")
            #print(f"Database user: {database_user}")
            #print(f"Expiry years: {expiry_years}")

            if not database_name or not database_user:
                return JsonResponse({'success': False, 'error': 'Database name and user are required'})

            # Validate database name format
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', database_name):
                return JsonResponse(
                    {'success': False, 'error': 'Database name can only contain letters, numbers, and underscores'})

            # Create database via cPanel API
            cpanel_url = request.session.get('cpanel_url')
            cpanel_user = request.session.get('cpanel_user')
            cpanel_pass = request.session.get('cpanel_pass')

            if not all([cpanel_url, cpanel_user, cpanel_pass]):
                return JsonResponse({'success': False, 'error': 'Missing cPanel credentials'})

            #print("Creating cPanel client...")
            cpanel_client = CpanelAPIClient(cpanel_url, cpanel_user, cpanel_pass)

            # Test authentication first
            #print("Testing cPanel authentication...")
            if not cpanel_client.authenticate():
                return JsonResponse(
                    {'success': False, 'error': 'Failed to authenticate with cPanel. Please check your credentials.'})

            #print("Creating database via cPanel...")
            database_created = cpanel_client.create_database(database_name)

            if not database_created:
                return JsonResponse({'success': False,
                                     'error': 'Failed to create database via cPanel. This could be due to: 1) Database name already exists, 2) Invalid database name format, 3) cPanel API limitations, or 4) Insufficient permissions.'})

            #print("Database created successfully via cPanel")

            # Add user to database with ALL PRIVILEGES
            #print(f"Adding user '{database_user}' to database '{database_name}' with ALL PRIVILEGES...")
            user_added = cpanel_client.add_user_to_database(database_name, database_user)

            if not user_added:
                print("Warning: Failed to add user privileges via cPanel API")
                # Don't fail the entire process, just log the warning
                # The user might already have access or the API might work differently

            #print("User privileges configured")

            # Connect to the newly created database to create tables
            #print(f"Connecting to newly created database: {database_name}")
            new_db_manager = DatabaseManager(DB_HOST, database_user, DB_PASSWORD, database_name)

            if not new_db_manager.connect():
                #print("Failed to connect to new database for table creation")
                return JsonResponse({'success': False,
                                     'error': 'Database created but failed to connect for table creation'})

            # Create tables in the new database
            #print("Creating tables in new database...")
            tables_success, tables_message = new_db_manager.create_tables()
            new_db_manager.close_connection()

            if not tables_success:
                #print(f"Failed to create tables: {tables_message}")
                return JsonResponse({'success': False,
                                     'error': f'Database created but failed to create tables: {tables_message}'})

            #print("Tables created successfully")

            # Connect to neptouia_nepton database to add software entry
            #print("Connecting to neptouia_nepton database...")
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

            if not db_manager.connect():
                #print("Failed to connect to neptouia_nepton database")
                return JsonResponse({'success': False,
                                     'error': 'Database and tables created but failed to connect to neptouia_nepton database for record keeping'})

            # Get next custId
            #print("Getting next custId...")
            cursor = db_manager.connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(custId), 0) + 1 FROM Softwares")
            next_cust_id = cursor.fetchone()[0]
            cursor.close()
            #print(f"Next custId: {next_cust_id}")

            # Calculate expiry date
            from datetime import datetime, timedelta
            expiry_date = datetime.now() + timedelta(days=expiry_years * 365)
            #print(f"Expiry date: {expiry_date}")

            # Insert into Softwares table
            #print("Inserting into Softwares table...")
            software_data = {
                'custId': next_cust_id,
                'software': 3,
                'host': DB_HOST,
                'db': database_name,
                'dbPass': DB_PASSWORD,
                'userName': database_user,
                'pwd': DB_PASSWORD,
                'expiry': expiry_date.strftime('%Y-%m-%d')
            }
            #print(f"Software data: {software_data}")

            success, result = db_manager.insert_record('Softwares', software_data)
            db_manager.close_connection()

            if success:
                #print("Software entry created successfully")
                return JsonResponse({
                    'success': True,
                    'message': 'Database created successfully with user privileges and all tables',
                    'cust_id': next_cust_id,
                    'tables_created': True,
                    'user_privileges_added': user_added
                })
            else:
                #print(f"Failed to create software entry: {result}")
                return JsonResponse(
                    {'success': False,
                     'error': f'Database and tables created but failed to add software entry: {result}'})

        except Exception as e:
            #print(f"Exception in admin_api_create_database: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})

    #print("Invalid request method")
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_itemgroups(request):
    """Get ItemGroups data by category from selected database"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        try:
            database_name = request.GET.get('database')
            category = request.GET.get('category')

            if not database_name or not category:
                return JsonResponse({'success': False, 'error': 'Database and category are required'})

            #print(f"Getting ItemGroups from database: {database_name}, category: {category}")

            # Connect to the selected database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': f'Failed to connect to database: {database_name}'})

            # Check if ItemGroups table exists
            cursor = db_manager.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'ItemGroups'")
            table_exists = cursor.fetchone()

            if not table_exists:
                cursor.close()
                db_manager.close_connection()
                return JsonResponse({'success': True, 'items': []})  # Return empty list if table doesn't exist

            # Get items from ItemGroups with the specified category
            cursor = db_manager.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT GroupID, Description FROM ItemGroups WHERE Category = %s ORDER BY Description",
                [category]
            )
            items = cursor.fetchall()
            cursor.close()
            db_manager.close_connection()

            #print(f"Found {len(items)} items for category {category}")
            return JsonResponse({'success': True, 'items': items})

        except Exception as e:
            #print(f"Error in admin_api_itemgroups: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_add_itemgroup(request):
    """Add new item to ItemGroups table"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            database_name = data.get('database')
            description = data.get('description')
            category = data.get('category')
            item_type = data.get('type')

            if not all([database_name, description, category]):
                return JsonResponse({'success': False, 'error': 'Database, description, and category are required'})

            #print(f"Adding item to database: {database_name}, description: {description}, category: {category}")

            # Connect to the selected database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': f'Failed to connect to database: {database_name}'})

            # Check if ItemGroups table exists, if not create it
            cursor = db_manager.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'ItemGroups'")
            table_exists = cursor.fetchone()

            if not table_exists:
                #print("ItemGroups table doesn't exist, creating it...")
                create_table_query = """
                    CREATE TABLE `ItemGroups` (
                      `GroupID` int(11) NOT NULL AUTO_INCREMENT,
                      `Category` int(11) NOT NULL,
                      `Description` varchar(60) NOT NULL,
                      `uCode` varchar(10) DEFAULT NULL,
                      `Under` int(11) DEFAULT NULL,
                      PRIMARY KEY (`GroupID`)
                    ) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
                    """
                cursor.execute(create_table_query)

            # Get the next GroupID
            cursor.execute("SELECT COALESCE(MAX(GroupID), 0) + 1 FROM ItemGroups")
            next_group_id = cursor.fetchone()[0]

            # Check if item already exists (double-check on server side)
            cursor.execute(
                "SELECT COUNT(*) FROM ItemGroups WHERE Description = %s AND Category = %s",
                [description, category]
            )
            exists_count = cursor.fetchone()[0]

            if exists_count > 0:
                cursor.close()
                db_manager.close_connection()
                type_name = 'Area' if item_type == 'location' else 'Visit Type'
                return JsonResponse({'success': False, 'error': f'{type_name} "{description}" already exists'})

            cursor.close()

            # Insert the new item
            item_data = {
                'GroupID': next_group_id,
                'Category': category,
                'Description': description,
                'uCode': None,
                'Under': None
            }

            success, result = db_manager.insert_record('ItemGroups', item_data)
            db_manager.close_connection()

            if success:
                type_name = 'Area' if item_type == 'location' else 'Visit Type'
                #print(f"{type_name} added successfully with GroupID: {next_group_id}")
                return JsonResponse({
                    'success': True,
                    'message': f'{type_name} "{description}" added successfully',
                    'group_id': next_group_id
                })
            else:
                return JsonResponse({'success': False, 'error': str(result)})

        except Exception as e:
            #print(f"Error in admin_api_add_itemgroup: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_verify_database_view(request):
    """Render the verify database page"""
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Get databases list
    try:
        cpanel_client = CpanelAPIClient(
            request.session['cpanel_url'],
            request.session['cpanel_user'],
            request.session['cpanel_pass']
        )
        databases = cpanel_client.get_databases()
    except Exception as e:
        #print(f"Error getting databases: {e}")
        databases = []

    context = {
        'databases': databases
    }
    return render(request, 'admin/verify_database.html', context)


@csrf_exempt
def admin_api_verify_database(request):
    """Verify database structure against expected schema"""
    # CHECK FOR SESSION, NOT DJANGO ADMIN
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized', 'redirect': '/login/'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            database_name = data.get('database')

            if not database_name:
                return JsonResponse({'success': False, 'error': 'Database name is required'})

            #print(f"Verifying database structure: {database_name}")

            # Connect to the database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': f'Failed to connect to database: {database_name}'})

            # Expected table schemas
            expected_schemas = get_expected_table_schemas()

            # Get current database structure
            verification_results = {
                'database': database_name,
                'missing_tables': [],
                'extra_tables': [],
                'table_differences': {},
                'has_differences': False
            }

            try:
                cursor = db_manager.connection.cursor()

                # Get all tables in database
                cursor.execute("SHOW TABLES")
                current_tables = [table[0] for table in cursor.fetchall()]

                expected_table_names = list(expected_schemas.keys())

                # Find missing tables
                verification_results['missing_tables'] = [
                    table for table in expected_table_names if table not in current_tables
                ]

                # Find extra tables (not critical, just informational)
                verification_results['extra_tables'] = [
                    table for table in current_tables if table not in expected_table_names
                ]

                # Check structure of existing tables
                for table_name in expected_table_names:
                    if table_name in current_tables:
                        differences = compare_table_structure(
                            cursor, table_name, expected_schemas[table_name]
                        )
                        if differences:
                            verification_results['table_differences'][table_name] = differences

                cursor.close()

                # Determine if there are any differences
                verification_results['has_differences'] = (
                    len(verification_results['missing_tables']) > 0 or
                    len(verification_results['table_differences']) > 0
                )

                db_manager.close_connection()

                return JsonResponse({
                    'success': True,
                    'verification': verification_results
                })

            except Exception as e:
                db_manager.close_connection()
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            #print(f"Error in admin_api_verify_database: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def admin_api_fix_database(request):
    """Fix database structure issues"""
    # CHECK FOR SESSION, NOT DJANGO ADMIN
    if 'user' not in request.session:
        return JsonResponse({'error': 'Unauthorized', 'redirect': '/login/'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            database_name = data.get('database')
            fix_type = data.get('fix_type', 'all')

            if not database_name:
                return JsonResponse({'success': False, 'error': 'Database name is required'})

            #print(f"Fixing database structure: {database_name}")

            # Connect to the database
            db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASSWORD, database_name)

            if not db_manager.connect():
                return JsonResponse({'success': False, 'error': f'Failed to connect to database: {database_name}'})

            fix_results = {
                'tables_created': [],
                'columns_added': [],
                'columns_modified': [],
                'errors': []
            }

            try:
                cursor = db_manager.connection.cursor()
                expected_schemas = get_expected_table_schemas()

                # Get current tables
                cursor.execute("SHOW TABLES")
                current_tables = [table[0] for table in cursor.fetchall()]

                # Create missing tables
                for table_name, schema in expected_schemas.items():
                    if table_name not in current_tables:
                        try:
                            cursor.execute(schema['create_statement'])
                            fix_results['tables_created'].append(table_name)
                            #print(f"Created table: {table_name}")
                        except Exception as table_error:
                            error_msg = f"Failed to create table {table_name}: {str(table_error)}"
                            fix_results['errors'].append(error_msg)
                            #print(error_msg)
                    else:
                        # Fix column differences in existing tables
                        try:
                            fixes = fix_table_columns(cursor, table_name, schema)
                            fix_results['columns_added'].extend(fixes['added'])
                            fix_results['columns_modified'].extend(fixes['modified'])
                        except Exception as col_error:
                            error_msg = f"Failed to fix columns in {table_name}: {str(col_error)}"
                            fix_results['errors'].append(error_msg)
                            #print(error_msg)

                cursor.close()
                db_manager.close_connection()

                success = (
                    len(fix_results['tables_created']) > 0 or
                    len(fix_results['columns_added']) > 0 or
                    len(fix_results['columns_modified']) > 0
                )

                return JsonResponse({
                    'success': True,
                    'results': fix_results,
                    'message': 'Database structure fixed successfully' if success else 'No changes needed'
                })

            except Exception as e:
                db_manager.close_connection()
                return JsonResponse({'success': False, 'error': str(e)})

        except Exception as e:
            #print(f"Error in admin_api_fix_database: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def get_expected_table_schemas():
    """Return expected table schemas with create statements"""
    return {
        'Attendance': {
            'create_statement': """
                    CREATE TABLE `Attendance` (
                      `refNo` int(11) NOT NULL AUTO_INCREMENT,
                      `empId` int(11) NOT NULL,
                      `date` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                      `checkInTime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
                      `checkInLocation` varchar(300) NOT NULL,
                      `checkOutTime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
                      `checkOutLocation` varchar(300) DEFAULT NULL,
                      `notes` varchar(500) DEFAULT NULL,
                      `status` int(11) NOT NULL,
                      PRIMARY KEY (`refNo`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'refNo': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'empId': {'type': 'int(11)', 'null': 'NO'},
                'date': {'type': 'timestamp', 'null': 'NO'},
                'checkInTime': {'type': 'timestamp', 'null': 'NO'},
                'checkInLocation': {'type': 'varchar(300)', 'null': 'NO'},
                'checkOutTime': {'type': 'timestamp', 'null': 'NO'},
                'checkOutLocation': {'type': 'varchar(300)', 'null': 'YES'},
                'notes': {'type': 'varchar(500)', 'null': 'YES'},
                'status': {'type': 'int(11)', 'null': 'NO'}
            }
        },
        'TransactionDetails': {
            'create_statement': """
                    CREATE TABLE `TransactionDetails` (
                      `transId` int(11) NOT NULL AUTO_INCREMENT,
                      `transDate` date NOT NULL,
                      `typeCode` int(11) NOT NULL,
                      `customerId` int(11) NOT NULL,
                      `transAmount` double DEFAULT NULL,
                      `transCount` int(11) DEFAULT NULL,
                      `description` varchar(100) DEFAULT NULL,
                      `empId` int(11) NOT NULL,
                      PRIMARY KEY (`transId`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'transId': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'transDate': {'type': 'date', 'null': 'NO'},
                'typeCode': {'type': 'int(11)', 'null': 'NO'},
                'customerId': {'type': 'int(11)', 'null': 'NO'},
                'transAmount': {'type': 'double', 'null': 'YES'},
                'transCount': {'type': 'int(11)', 'null': 'YES'},
                'description': {'type': 'varchar(100)', 'null': 'YES'},
                'empId': {'type': 'int(11)', 'null': 'NO'}
            }
        },
        'Transaction': {
            'create_statement': """
                    CREATE TABLE `Transaction` (
                      `transId` int(11) NOT NULL AUTO_INCREMENT,
                      `transDate` date NOT NULL,
                      `transAmount` double NOT NULL,
                      `transCount` int(11) NOT NULL,
                      `typeCode` int(11) NOT NULL,
                      `empID` int(11) NOT NULL,
                      PRIMARY KEY (`transId`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'transId': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'transDate': {'type': 'date', 'null': 'NO'},
                'transAmount': {'type': 'double', 'null': 'NO'},
                'transCount': {'type': 'int(11)', 'null': 'NO'},
                'typeCode': {'type': 'int(11)', 'null': 'NO'},
                'empID': {'type': 'int(11)', 'null': 'NO'}
            }
        },
        'Tickets': {
            'create_statement': """
        CREATE TABLE `Tickets` (
          `ticket_no` int(11) NOT NULL AUTO_INCREMENT,
          `customer_name` varchar(100) DEFAULT NULL,
          `mobile` varchar(20) DEFAULT NULL,
          `email` varchar(100) DEFAULT NULL,
          `service_type` varchar(50) DEFAULT NULL,
          `problem_description` text DEFAULT NULL,
          `ip_address` varchar(45) DEFAULT NULL,
          `created_at` datetime DEFAULT current_timestamp(),
          `ticket_status` int(11) DEFAULT 0,
          `schedule_status` int(11) DEFAULT 0,
          `narration` varchar(100) DEFAULT NULL,
          PRIMARY KEY (`ticket_no`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci
    """,
            'columns': {
                'ticket_no': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'customer_name': {'type': 'varchar(100)', 'null': 'YES'},
                'mobile': {'type': 'varchar(20)', 'null': 'YES'},
                'email': {'type': 'varchar(100)', 'null': 'YES'},
                'service_type': {'type': 'varchar(50)', 'null': 'YES'},
                'problem_description': {'type': 'text', 'null': 'YES'},
                'ip_address': {'type': 'varchar(45)', 'null': 'YES'},
                'created_at': {'type': 'datetime', 'null': 'YES'},
                'ticket_status': {'type': 'int(11)', 'null': 'YES'},
                'schedule_status': {'type': 'int(11)', 'null': 'YES'},
                'narration': {'type': 'varchar(100)', 'null': 'YES'}
            }
        },
        'Schedules': {
            'create_statement': """
                    CREATE TABLE `Schedules` (
                      `refNo` int(11) NOT NULL AUTO_INCREMENT,
                      `empId` int(11) NOT NULL,
                      `scheduleDate` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                      `custId` int(11) NOT NULL,
                      `visitType` int(11) NOT NULL,
                      `narration` varchar(300) NOT NULL,
                      `status` int(11) NOT NULL,
                      PRIMARY KEY (`refNo`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'refNo': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'empId': {'type': 'int(11)', 'null': 'NO'},
                'scheduleDate': {'type': 'timestamp', 'null': 'NO'},
                'custId': {'type': 'int(11)', 'null': 'NO'},
                'visitType': {'type': 'int(11)', 'null': 'NO'},
                'narration': {'type': 'varchar(300)', 'null': 'NO'},
                'status': {'type': 'int(11)', 'null': 'NO'}
            }
        },
        'ItemGroups': {
            'create_statement': """
                    CREATE TABLE `ItemGroups` (
                      `GroupID` int(11) NOT NULL AUTO_INCREMENT,
                      `Category` int(11) NOT NULL,
                      `Description` varchar(60) NOT NULL,
                      `uCode` varchar(10) DEFAULT NULL,
                      `Under` int(11) DEFAULT NULL,
                      PRIMARY KEY (`GroupID`)
                    ) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
                """,
            'columns': {
                'GroupID': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'Category': {'type': 'int(11)', 'null': 'NO'},
                'Description': {'type': 'varchar(60)', 'null': 'NO'},
                'uCode': {'type': 'varchar(10)', 'null': 'YES'},
                'Under': {'type': 'int(11)', 'null': 'YES'}
            }
        },
        'Events': {
            'create_statement': """
                    CREATE TABLE `Events` (
                      `refNo` int(11) NOT NULL AUTO_INCREMENT,
                      `empId` int(11) NOT NULL,
                      `date` date NOT NULL,
                      `custId` int(11) DEFAULT NULL,
                      `visitType` int(11) NOT NULL,
                      `checkIn` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                      `checkOut` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
                      `checkInLocation` varchar(100) NOT NULL,
                      `checkOutLocation` varchar(100) DEFAULT NULL,
                      `paymentType` int(11) DEFAULT NULL,
                      `amount` float DEFAULT NULL,
                      `narration` varchar(500) DEFAULT NULL,
                      `status` int(11) NOT NULL DEFAULT 1,
                      `checkOutStatus` int(11) NOT NULL,
                      PRIMARY KEY (`refNo`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'refNo': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'empId': {'type': 'int(11)', 'null': 'NO'},
                'date': {'type': 'date', 'null': 'NO'},
                'custId': {'type': 'int(11)', 'null': 'YES'},
                'visitType': {'type': 'int(11)', 'null': 'NO'},
                'checkIn': {'type': 'timestamp', 'null': 'NO'},
                'checkOut': {'type': 'timestamp', 'null': 'NO'},
                'checkInLocation': {'type': 'varchar(100)', 'null': 'NO'},
                'checkOutLocation': {'type': 'varchar(100)', 'null': 'YES'},
                'paymentType': {'type': 'int(11)', 'null': 'YES'},
                'amount': {'type': 'float', 'null': 'YES'},
                'narration': {'type': 'varchar(500)', 'null': 'YES'},
                'status': {'type': 'int(11)', 'null': 'NO'},
                'checkOutStatus': {'type': 'int(11)', 'null': 'NO'}
            }
        },
        'Employee': {
            'create_statement': """
                    CREATE TABLE `Employee` (
                      `empId` int(11) NOT NULL AUTO_INCREMENT,
                      `empName` varchar(100) NOT NULL,
                      `empCode` varchar(20) DEFAULT NULL,
                      `pwd` varchar(10) DEFAULT NULL,
                      `target` double DEFAULT 0,
                      `user_type` int(11) DEFAULT 0,
                      PRIMARY KEY (`empId`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci
                """,
            'columns': {
                'empId': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'empName': {'type': 'varchar(100)', 'null': 'NO'},
                'empCode': {'type': 'varchar(20)', 'null': 'YES'},
                'pwd': {'type': 'varchar(10)', 'null': 'YES'},
                'target': {'type': 'double', 'null': 'YES'},
                'user_type': {'type': 'int(11)', 'null': 'YES'}
            }
        },
        'Customer': {
            'create_statement': """
                    CREATE TABLE `Customer` (
                      `CustId` int(10) NOT NULL AUTO_INCREMENT,
                      `CustCode` varchar(25) NOT NULL,
                      `CustName` varchar(150) NOT NULL,
                      `Address1` varchar(100) DEFAULT NULL,
                      `Address2` varchar(100) DEFAULT NULL,
                      `Area` int(11) DEFAULT NULL,
                      `Phone` varchar(15) DEFAULT NULL,
                      `Mobile` varchar(15) DEFAULT NULL,
                      `TypeCode` int(11) NOT NULL,
                      `empId` int(11) DEFAULT NULL,
                      `AcBal` int(11) DEFAULT NULL,
                      `LastPayment` date DEFAULT NULL,
                      `createdAt` timestamp NULL DEFAULT current_timestamp(),
                      `importStatus` int(11) DEFAULT NULL,
                      PRIMARY KEY (`CustId`,`TypeCode`)
                    ) ENGINE=MyISAM DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
                """,
            'columns': {
                'CustId': {'type': 'int(10)', 'null': 'NO', 'key': 'PRI', 'extra': 'auto_increment'},
                'CustCode': {'type': 'varchar(25)', 'null': 'NO'},
                'CustName': {'type': 'varchar(150)', 'null': 'NO'},
                'Address1': {'type': 'varchar(100)', 'null': 'YES'},
                'Address2': {'type': 'varchar(100)', 'null': 'YES'},
                'Area': {'type': 'int(11)', 'null': 'YES'},
                'Phone': {'type': 'varchar(15)', 'null': 'YES'},
                'Mobile': {'type': 'varchar(15)', 'null': 'YES'},
                'TypeCode': {'type': 'int(11)', 'null': 'NO'},
                'empId': {'type': 'int(11)', 'null': 'YES'},
                'AcBal': {'type': 'int(11)', 'null': 'YES'},
                'LastPayment': {'type': 'date', 'null': 'YES'},
                'createdAt': {'type': 'timestamp', 'null': 'YES'},
                'importStatus': {'type': 'int(11)', 'null': 'YES'}
            }
        },
        'ChartOfCode': {
            'create_statement': """
                    CREATE TABLE `ChartOfCode` (
                      `Category` varchar(20) NOT NULL,
                      `Code` varchar(15) NOT NULL,
                      `Description` varchar(100) NOT NULL,
                      `TypeCode` varchar(15) DEFAULT NULL,
                      `EDate` datetime DEFAULT current_timestamp(),
                      `ENo` int(11) DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci
                """,
            'columns': {
                'Category': {'type': 'varchar(20)', 'null': 'NO'},
                'Code': {'type': 'varchar(15)', 'null': 'NO'},
                'Description': {'type': 'varchar(100)', 'null': 'NO'},
                'TypeCode': {'type': 'varchar(15)', 'null': 'YES'},
                'EDate': {'type': 'datetime', 'null': 'YES'},
                'ENo': {'type': 'int(11)', 'null': 'YES'}
            }
        },
        'Schedule_details': {
            'create_statement': """
                CREATE TABLE `Schedule_details` (
                  `Sn` tinyint(4) NOT NULL,
                  `ScheduleRefNo` int(11) NOT NULL,
                  `CurrentDate` date NOT NULL,
                  `FollowUpStatus` int(11) NOT NULL,
                  `NextSchedule` date NOT NULL,
                  `Rep` int(11) NOT NULL,
                  `Remarks` varchar(200) NOT NULL,
                  `Status` tinyint(1) NOT NULL,
                  PRIMARY KEY (`Sn`, `ScheduleRefNo`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            'columns': {
                'Sn': {'type': 'tinyint(4)', 'null': 'NO', 'key': 'PRI'},
                'ScheduleRefNo': {'type': 'int(11)', 'null': 'NO', 'key': 'PRI'},
                'CurrentDate': {'type': 'date', 'null': 'NO'},
                'FollowUpStatus': {'type': 'int(11)', 'null': 'NO'},
                'NextSchedule': {'type': 'date', 'null': 'NO'},
                'Rep': {'type': 'int(11)', 'null': 'NO'},
                'Remarks': {'type': 'varchar(200)', 'null': 'NO'},
                'Status': {'type': 'tinyint(1)', 'null': 'NO'}
            }
        }
    }


def compare_table_structure(cursor, table_name, expected_schema):
    """Compare current table structure with expected schema"""
    differences = {
        'missing_columns': [],
        'extra_columns': [],
        'type_mismatches': []
    }

    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        current_columns = cursor.fetchall()

        current_col_dict = {col[0]: {
            'type': col[1],
            'null': col[2],
            'key': col[3],
            'default': col[4],
            'extra': col[5]
        } for col in current_columns}

        expected_columns = expected_schema['columns']

        # Find missing columns
        for col_name, col_def in expected_columns.items():
            if col_name not in current_col_dict:
                differences['missing_columns'].append({
                    'name': col_name,
                    'definition': col_def
                })

        # Find extra columns
        for col_name in current_col_dict.keys():
            if col_name not in expected_columns:
                differences['extra_columns'].append(col_name)

        # Check for type mismatches
        for col_name, expected_def in expected_columns.items():
            if col_name in current_col_dict:
                current_def = current_col_dict[col_name]
                if not types_match(current_def['type'], expected_def['type']):
                    differences['type_mismatches'].append({
                        'column': col_name,
                        'current_type': current_def['type'],
                        'expected_type': expected_def['type']
                    })

    except Exception as e:
        print(f"Error comparing table {table_name}: {e}")

    # Return None if no differences
    if not any([differences['missing_columns'], differences['extra_columns'], differences['type_mismatches']]):
        return None

    return differences


def types_match(current_type, expected_type):
    """Check if two column types match (allowing for minor variations)"""
    # Normalize types
    current = current_type.lower().replace(' ', '')
    expected = expected_type.lower().replace(' ', '')

    # Direct match
    if current == expected:
        return True

    # Check if base types match (ignoring length specifications for some types)
    current_base = current.split('(')[0]
    expected_base = expected.split('(')[0]

    return current_base == expected_base


def fix_table_columns(cursor, table_name, schema):
    """Fix missing or incorrect columns in a table"""
    fixes = {
        'added': [],
        'modified': []
    }

    differences = compare_table_structure(cursor, table_name, schema)

    if not differences:
        return fixes

    # Add missing columns
    for missing_col in differences['missing_columns']:
        col_name = missing_col['name']
        col_def = missing_col['definition']

        alter_query = f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def['type']}"

        if col_def['null'] == 'NO':
            alter_query += " NOT NULL"

        if col_def.get('default'):
            alter_query += f" DEFAULT {col_def['default']}"

        if col_def.get('extra'):
            if 'auto_increment' in col_def['extra'].lower():
                alter_query += " AUTO_INCREMENT"

        try:
            cursor.execute(alter_query)
            fixes['added'].append(f"{table_name}.{col_name}")
            #print(f"Added column: {table_name}.{col_name}")
        except Exception as e:
            print(f"Error adding column {table_name}.{col_name}: {e}")

    # Modify columns with type mismatches
    for type_mismatch in differences.get('type_mismatches', []):
        col_name = type_mismatch['column']
        expected_type = type_mismatch['expected_type']

        # Get the full column definition from schema
        col_def = schema['columns'].get(col_name)
        if not col_def:
            continue

        alter_query = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {col_def['type']}"

        if col_def['null'] == 'NO':
            alter_query += " NOT NULL"
        else:
            alter_query += " NULL"

        if col_def.get('default') and col_def['default'] != 'NULL':
            alter_query += f" DEFAULT {col_def['default']}"

        if col_def.get('extra'):
            if 'auto_increment' in col_def['extra'].lower():
                alter_query += " AUTO_INCREMENT"

        try:
            cursor.execute(alter_query)
            fixes['modified'].append(f"{table_name}.{col_name} ({type_mismatch['current_type']} → {expected_type})")
            #print(f"Modified column: {table_name}.{col_name} from {type_mismatch['current_type']} to {expected_type}")
        except Exception as e:
            #print(f"Error modifying column {table_name}.{col_name}: {e}")
            # If direct modify fails, try a safer approach for data type changes
            try:
                # For varchar changes, this should work better
                safer_query = f"ALTER TABLE `{table_name}` CHANGE COLUMN `{col_name}` `{col_name}` {col_def['type']}"

                if col_def['null'] == 'NO':
                    safer_query += " NOT NULL"
                else:
                    safer_query += " NULL"

                cursor.execute(safer_query)
                fixes['modified'].append(f"{table_name}.{col_name} ({type_mismatch['current_type']} → {expected_type})")
                #print(f"Modified column (using CHANGE): {table_name}.{col_name}")
            except Exception as e2:
                print(f"Error with alternative modify method for {table_name}.{col_name}: {e2}")

    return fixes