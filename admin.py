from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
import mysql.connector as mysql_connector  # <-- Import mysql.connector properly

app = Flask(__name__)
CORS(app)

# flask_mysqldb Configuration (for `ss_db`)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'jayant@2006'
app.config['MYSQL_DB'] = 'ss_db'

mysql = MySQL(app)

# Create connections for other databases using mysql_connector
db_announcement = mysql_connector.connect(
    host="localhost",
    user="root",
    password="jayant@2006",
    database="ann_db"
)

db_user_management = mysql_connector.connect(
    host="localhost",
    user="root",
    password="jayant@2006",
    database="user_management1"
)

db_exam_monitoring = mysql_connector.connect(
    host="localhost",
    user="root",
    password="jayant@2006",
    database="exam_monitoring"
)


# --- Utility Functions ---

def update_setting(setting_name, new_status, success_message):
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE settings_status SET status = %s WHERE setting_name = %s", (new_status, setting_name))
        mysql.connection.commit()
        if cur.rowcount == 0:
            return jsonify({"message": f"Setting '{setting_name}' not found."}), 404
        return jsonify({"message": success_message}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

def execute_query(connection, query, params=None, fetch=False, dictionary=False):
    try:
        cursor = connection.cursor(dictionary=dictionary)
        cursor.execute(query, params if params else ())
        if fetch:
            result = cursor.fetchall()
            return result
        connection.commit()
        return None
    except mysql.connector.Error as err:
        return {"error": str(err)}
    finally:
        cursor.close()

# --- Announcements Routes ---

@app.route('/announcements', methods=['GET'])
def get_announcements():
    result = execute_query(
        db_announcement,
        "SELECT id, title, message, created_at FROM announcements ORDER BY created_at DESC",
        fetch=True
    )
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    return jsonify(result)

@app.route('/announcements', methods=['POST'])
def create_announcement():
    data = request.json
    title = data.get('title')
    message = data.get('message')

    if not title or not message:
        return jsonify({"error": "Title and Message are required"}), 400

    execute_query(
        db_announcement,
        "INSERT INTO announcements (title, message) VALUES (%s, %s)",
        (title, message)
    )
    return jsonify({"message": "Announcement posted successfully"}), 201

@app.route('/announcements/<int:id>', methods=['DELETE'])
def delete_announcement(id):
    execute_query(
        db_announcement,
        "DELETE FROM announcements WHERE id = %s",
        (id,)
    )
    return jsonify({"message": "Announcement deleted successfully"}), 200

# --- User Management Routes ---

@app.route('/addUser', methods=['POST'])
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')

    if not username or not email or not role:
        return "All fields are required.", 400

    execute_query(
        db_user_management,
        'INSERT INTO users (username, email, role) VALUES (%s, %s, %s)',
        (username, email, role)
    )
    return 'User added successfully', 200

# --- Exam Monitoring Routes ---

@app.route('/active-exams', methods=['GET'])
def get_active_exams():
    result = execute_query(
        db_exam_monitoring,
        "SELECT * FROM active_exams WHERE status = 'Ongoing'",
        fetch=True,
        dictionary=True
    )
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    return jsonify(result)

@app.route('/cancel-exam', methods=['POST'])
def cancel_exam():
    exam_name = request.json.get('exam_name')

    if not exam_name:
        return jsonify({"error": "Exam name is required."}), 400

    execute_query(
        db_exam_monitoring,
        "UPDATE active_exams SET status = 'Completed' WHERE exam_name = %s",
        (exam_name,)
    )
    return jsonify({"message": f"Exam {exam_name} has been canceled."}), 200

@app.route('/completed-exams', methods=['GET'])
def get_completed_exams():
    result = execute_query(
        db_exam_monitoring,
        "SELECT * FROM completed_exams",
        fetch=True,
        dictionary=True
    )
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500
    return jsonify(result)

@app.route('/view-exam', methods=['GET'])
def view_exam():
    exam_name = request.args.get('exam_name')

    if not exam_name:
        return jsonify({"error": "Exam name parameter is required."}), 400

    result = execute_query(
        db_exam_monitoring,
        "SELECT * FROM active_exams WHERE exam_name = %s",
        (exam_name,),
        fetch=True,
        dictionary=True
    )
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

    if not result:
        return jsonify({"message": "Exam not found."}), 404

    return jsonify(result[0])

# --- Settings Status Routes (Maintenance, Backup, Restore) ---

@app.route('/api/enable-maintenance', methods=['POST'])
def enable_maintenance():
    return update_setting('maintenance_mode', 'active', 'Maintenance mode activated!')

@app.route('/api/initiate-backup', methods=['POST'])
def initiate_backup():
    return update_setting('backup', 'started', 'Backup initiated!')

@app.route('/api/restore-system', methods=['POST'])
def restore_system():
    return update_setting('restore', 'restored', 'System restored!')

# --- Run the App ---

if __name__ == '__main__':
    app.run(debug=True)
