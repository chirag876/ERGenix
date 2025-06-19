"""
ERGenix - Automatic ER Diagram Generator
A complete solution for generating ER diagrams and table statistics from databases
"""

import base64
import io
import os
import threading
import time
from datetime import datetime, timedelta

import matplotlib
import matplotlib.pyplot as plt
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from database.erdb import DatabaseManager
from services.erservice import ERDiagramGenerator

matplotlib.use('Agg')  # Set non-GUI backend
from threading import Lock

matplotlib_lock = Lock()

app = Flask(__name__)
CORS(app)

# Global storage for database connections (will be cleared every 5 minutes)
active_connections = {}
connection_timestamps = {}


# Initialize database manager
db_manager = DatabaseManager()
er_generator = ERDiagramGenerator()
def cleanup_connections():
    """Clean up connections older than 5 minutes"""
    current_time = datetime.now()
    to_remove = []
    
    for conn_id, timestamp in list(connection_timestamps.items()):
        if current_time - timestamp > timedelta(minutes=5):
            to_remove.append(conn_id)
    
    for conn_id in to_remove:
        if conn_id in active_connections:
            try:
                active_connections[conn_id].close()
            except:
                pass
            del active_connections[conn_id]
        if conn_id in connection_timestamps:
            del connection_timestamps[conn_id]

# Schedule cleanup every minute
def schedule_cleanup():
    cleanup_connections()
    threading.Timer(60.0, schedule_cleanup).start()

# Start cleanup scheduler
schedule_cleanup()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect_database():
    try:
        data = request.json
        db_type = data.get('db_type', 'mysql')
        host = data.get('host')
        user = data.get('user')
        password = data.get('password')
        
        if not all([db_type, host, user, password]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # For SQLite, use host as the database file path
        database = host if db_type.lower() == 'sqlite' else None
        
        # Create connection and get databases
        conn, databases = db_manager.connect_database(db_type, host, user, password, database)
        
        # Generate connection ID
        conn_id = f"{user}_{host}_{int(time.time())}"
        
        # Store connection
        active_connections[conn_id] = conn
        connection_timestamps[conn_id] = datetime.now()
        
        # Get databases
        databases = db_manager.get_databases(conn, db_type)
        
        return jsonify({
            'success': True,
            'connection_id': conn_id,
            'databases': databases,
            'db_type': db_type
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_tables', methods=['POST'])
def get_tables():
    try:
        data = request.json
        conn_id = data.get('connection_id')
        database = data.get('database')
        db_type = data.get('db_type')
        
        if conn_id not in active_connections:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        conn = active_connections[conn_id]
        tables = db_manager.get_tables(conn, db_type, database)
        
        return jsonify({
            'success': True,
            'tables': tables
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate_er_diagram', methods=['POST'])
def generate_er_diagram():
    try:
        data = request.json
        conn_id = data.get('connection_id')
        database = data.get('database')
        db_type = data.get('db_type')
        selected_tables = data.get('tables', [])
        
        if conn_id not in active_connections:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        conn = active_connections[conn_id]
        
        # Get table schemas and relationships
        tables_data = {}
        relationships = []
        
        for table_name in selected_tables:
            schema = db_manager.get_table_schema(conn, db_type, table_name, database)
            foreign_keys = db_manager.get_foreign_keys(conn, db_type, table_name, database)
            
            tables_data[table_name] = {
                'schema': schema,
                'foreign_keys': foreign_keys
            }
            
            # Add relationships
            for fk in foreign_keys:
                if fk['referenced_table'] in selected_tables:
                    relationships.append({
                        'from_table': table_name,
                        'to_table': fk['referenced_table'],
                        'from_column': fk['column'],
                        'to_column': fk['referenced_column']
                    })
        
        # Generate ER diagram
        with matplotlib_lock:
            fig = er_generator.generate_diagram(tables_data, relationships)
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            img_buffer.close()
            
        return jsonify({
            'success': True,
            'diagram': img_base64,
            'tables_data': tables_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_statistics', methods=['POST'])
def get_statistics():
    try:
        data = request.json
        conn_id = data.get('connection_id')
        database = data.get('database')
        db_type = data.get('db_type')
        selected_tables = data.get('tables', [])
        
        if conn_id not in active_connections:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        conn = active_connections[conn_id]
        
        # Get statistics for each table
        statistics = {}
        for table_name in selected_tables:
            stats = db_manager.get_table_statistics(conn, db_type, table_name, database)
            statistics[table_name] = stats
        with matplotlib_lock:
        # Generate statistics visualization
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # Row count chart
            tables = list(statistics.keys())
            row_counts = [statistics[table]['row_count'] for table in tables]
            ax1.bar(tables, row_counts, color='skyblue')
            ax1.set_title('Row Count by Table')
            ax1.set_xlabel('Tables')
            ax1.set_ylabel('Row Count')
            plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
            
            # Column count chart
            col_counts = [statistics[table]['column_count'] for table in tables]
            ax2.bar(tables, col_counts, color='lightgreen')
            ax2.set_title('Column Count by Table')
            ax2.set_xlabel('Tables')
            ax2.set_ylabel('Column Count')
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
            
            # Size chart (if available)
            sizes = []
            size_tables = []
            for table in tables:
                size = statistics[table]['size_mb']
                if size != 'N/A' and size is not None:
                    sizes.append(float(size))
                    size_tables.append(table)
            
            if sizes:
                ax3.bar(size_tables, sizes, color='orange')
                ax3.set_title('Table Size (MB)')
                ax3.set_xlabel('Tables')
                ax3.set_ylabel('Size (MB)')
                plt.setp(ax3.get_xticklabels(), rotation=45, ha='right')
            else:
                ax3.text(0.5, 0.5, 'Size data not available', ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('Table Size (MB)')
            
            # Summary pie chart
            total_rows = sum(row_counts)
            if total_rows > 0:
                ax4.pie(row_counts, labels=tables, autopct='%1.1f%%', startangle=90)
                ax4.set_title('Data Distribution by Table')
            else:
                ax4.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax4.transAxes)
                ax4.set_title('Data Distribution by Table')
            
            plt.tight_layout()
            
            # Convert to base64
            stats_buffer = io.BytesIO()
            fig.savefig(stats_buffer, format='png', dpi=300, bbox_inches='tight')
            stats_buffer.seek(0)
            stats_base64 = base64.b64encode(stats_buffer.getvalue()).decode()
            plt.close(fig)
            stats_buffer.close()
            
        return jsonify({
            'success': True,
            'statistics': statistics,
            'stats_chart': stats_base64
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<format_type>/<content_type>')
def download_file(format_type, content_type):
    try:
        # This would need to be implemented with session storage
        # For now, return a placeholder response
        return jsonify({'success': False, 'error': 'Download feature needs session implementation'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Create templates directory structure
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # HTML template will be created separately
    app.run(debug=True, host='0.0.0.0', port=5000)