from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import uuid
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
CORS(app)

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'securevote'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS elections (
                    id VARCHAR(36) PRIMARY KEY,
                    title VARCHAR(100) NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    party VARCHAR(50) NOT NULL,
                    election_id VARCHAR(36) NOT NULL,
                    votes INT DEFAULT 0,
                    FOREIGN KEY (election_id) REFERENCES elections(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    voter_id VARCHAR(50) UNIQUE NOT NULL,
                    has_voted BOOLEAN DEFAULT FALSE,
                    election_id VARCHAR(36),
                    FOREIGN KEY (election_id) REFERENCES elections(id)
                )
            """)
            
            conn.commit()
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

# Initialize database on startup
init_db()

@app.route('/api/elections', methods=['POST'])
def create_election():
    data = request.get_json()
    election_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Insert election
        cursor.execute(
            "INSERT INTO elections (id, title, start_date, end_date) VALUES (%s, %s, %s, %s)",
            (election_id, data['title'], data['start_date'], data['end_date'])
        )
        
        # Insert candidates
        for candidate in data['candidates']:
            cursor.execute(
                "INSERT INTO candidates (name, party, election_id) VALUES (%s, %s, %s)",
                (candidate['name'], candidate['party'], election_id)
            )
        
        conn.commit()
        return jsonify({'success': True, 'election_id': election_id})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/elections/active', methods=['GET'])
def get_active_elections():
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT * FROM elections 
            WHERE start_date <= %s AND end_date >= %s
        """, (now, now))
        
        elections = cursor.fetchall()
        
        for election in elections:
            cursor.execute(
                "SELECT id, name, party FROM candidates WHERE election_id = %s",
                (election['id'],)
            )
            election['candidates'] = cursor.fetchall()
        
        return jsonify(elections)
    except Error as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/vote', methods=['POST'])
def submit_vote():
    data = request.get_json()
    # Add your voting logic here
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)