import mysql.connector
import psycopg2
import sqlite3

class DatabaseManager:
    def __init__(self):
        self.supported_dbs = ['mysql', 'postgresql', 'sqlite']
    
    def connect_database(self, db_type, host, user, password, database=None):
        """Connect to database based on type"""
        try:
            if db_type.lower() == 'mysql':
                conn = mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database if database else None  # Connect without database if not provided
                )
            elif db_type.lower() == 'postgresql':
                conn = psycopg2.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database if database else 'postgres'  # Default to 'postgres' for listing databases
                )
            elif db_type.lower() == 'sqlite':
                if not database:
                    raise ValueError("SQLite requires a database file path")
                conn = sqlite3.connect(database)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            # Get list of databases if no specific database is provided
            databases = []
            if not database and db_type.lower() != 'sqlite':
                databases = self.get_databases(conn, db_type)
            elif db_type.lower() == 'sqlite':
                databases = [database] # SQLite uses the file path as the database name
            return conn, databases
        except Exception as e:
            raise Exception(f"Database connection failed: {str(e)}")
    
    def get_databases(self, conn, db_type):
        """Get list of databases"""
        cursor = conn.cursor()
        try:
            if db_type.lower() == 'mysql':
                cursor.execute("SHOW DATABASES")
                databases = [db[0] for db in cursor.fetchall()]
                # Filter out system databases
                system_dbs = ['information_schema', 'performance_schema', 'mysql', 'sys']
                databases = [db for db in databases if db not in system_dbs]
            elif db_type.lower() == 'postgresql':
                cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
                databases = [db[0] for db in cursor.fetchall()]
                # Filter out system databases
                system_dbs = ['postgres', 'template0', 'template1']
                databases = [db for db in databases if db not in system_dbs]
            elif db_type.lower() == 'sqlite':
                databases = ['main']  # SQLite typically has one database
            
            return databases
        finally:
            cursor.close()
    
    def get_tables(self, conn, db_type, database=None):
        """Get list of tables in database"""
        cursor = conn.cursor()
        try:
            if db_type.lower() == 'mysql':
                if database:
                    cursor.execute(f"USE {database}")
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
            elif db_type.lower() == 'postgresql':
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = [table[0] for table in cursor.fetchall()]
            elif db_type.lower() == 'sqlite':
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [table[0] for table in cursor.fetchall()]
            
            return tables
        finally:
            cursor.close()
    
    def get_table_schema(self, conn, db_type, table_name, database=None):
        """Get table schema information"""
        cursor = conn.cursor()
        try:
            if db_type.lower() == 'mysql':
                if database:
                    cursor.execute(f"USE {database}")
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                schema = []
                for col in columns:
                    schema.append({
                        'column': col[0],
                        'type': col[1],
                        'null': col[2],
                        'key': col[3],
                        'default': col[4],
                        'extra': col[5]
                    })
            elif db_type.lower() == 'postgresql':
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                """)
                columns = cursor.fetchall()
                schema = []
                for col in columns:
                    schema.append({
                        'column': col[0],
                        'type': col[1],
                        'null': col[2],
                        'key': '',
                        'default': col[3],
                        'extra': ''
                    })
            elif db_type.lower() == 'sqlite':
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                schema = []
                for col in columns:
                    schema.append({
                        'column': col[1],
                        'type': col[2],
                        'null': 'NO' if col[3] else 'YES',
                        'key': 'PRI' if col[5] else '',
                        'default': col[4],
                        'extra': ''
                    })
            
            return schema
        finally:
            cursor.close()
    
    def get_foreign_keys(self, conn, db_type, table_name, database=None):
        """Get foreign key relationships"""
        cursor = conn.cursor()
        try:
            foreign_keys = []
            if db_type.lower() == 'mysql':
                if database:
                    cursor.execute(f"USE {database}")
                cursor.execute(f"""
                    SELECT 
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_NAME = '{table_name}'
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """)
                fks = cursor.fetchall()
                for fk in fks:
                    foreign_keys.append({
                        'column': fk[0],
                        'referenced_table': fk[1],
                        'referenced_column': fk[2]
                    })
            elif db_type.lower() == 'postgresql':
                cursor.execute(f"""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name = '{table_name}'
                """)
                fks = cursor.fetchall()
                for fk in fks:
                    foreign_keys.append({
                        'column': fk[0],
                        'referenced_table': fk[1],
                        'referenced_column': fk[2]
                    })
            elif db_type.lower() == 'sqlite':
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = cursor.fetchall()
                for fk in fks:
                    foreign_keys.append({
                        'column': fk[3],
                        'referenced_table': fk[2],
                        'referenced_column': fk[4]
                    })
            
            return foreign_keys
        finally:
            cursor.close()
    
    def get_table_statistics(self, conn, db_type, table_name, database=None):
        """Get table statistics"""
        cursor = conn.cursor()
        try:
            stats = {}
            
            # Get row count
            if db_type.lower() in ['mysql', 'postgresql']:
                if database and db_type.lower() == 'mysql':
                    cursor.execute(f"USE {database}")
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                stats['row_count'] = cursor.fetchone()[0]
            elif db_type.lower() == 'sqlite':
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                stats['row_count'] = cursor.fetchone()[0]
            
            # Get column count
            schema = self.get_table_schema(conn, db_type, table_name, database)
            stats['column_count'] = len(schema)
            
            # Get table size (approximate)
            if db_type.lower() == 'mysql':
                cursor.execute(f"""
                    SELECT 
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'size_mb'
                    FROM information_schema.TABLES
                    WHERE table_name = '{table_name}'
                """)
                result = cursor.fetchone()
                stats['size_mb'] = result[0] if result else 0
            else:
                stats['size_mb'] = 'N/A'
            
            # Estimate last update (this is database-specific and may not be available)
            stats['last_update'] = 'N/A'
            stats['usage_frequency'] = 'N/A'  # This would require monitoring over time
            
            return stats
        finally:
            cursor.close()
