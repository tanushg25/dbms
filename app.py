from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
#ertghj
app = Flask(__name__)
CORS(app)  # Allow frontend to call backend

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root@1725",
    database="exam_system"
)
cursor = db.cursor(dictionary=True)

# Fetch questions
@app.route("/add-question", methods=["POST"])
def add_question():
    try:
        data = request.get_json()

        # For now, we'll associate all questions with ExamID = 1
        # exam_id = 1


        question_text = data["question"]
        option1 = data["option1"]
        option2 = data["option2"]
        option3 = data["option3"]
        option4 = data["option4"]
        correct_answer_index = data["answer"]
        duration = data["duration"]  # Not used in DB yet
        marks = data["marks"]  # Added marks field

        # Map the number to actual answer text
        correct_answer = [option1, option2, option3, option4][int(correct_answer_index) - 1]

        cursor.execute("""
    INSERT INTO question 
    (ExamID, QuestionText, Option1, Option2, Option3, Option4, CorrectAnswer, Marks) 
    VALUES (NULL, %s, %s, %s, %s, %s, %s, %s)
""", (question_text, option1, option2, option3, option4, correct_answer, marks))

        db.commit()
        return jsonify({"success": True, "message": "Question added successfully."})

    except Exception as e:
        print("❌ Error adding question:", e)
        return jsonify({"success": False, "message": str(e)}), 500


# Submit answers
@app.route("/submit", methods=["POST"])
def submit_answers():
    data = request.get_json()
    student = data['student_name']
    answers = str(data['answers'])

    query = "INSERT INTO responses (student_name, answers) VALUES (%s, %s)"
    cursor.execute(query, (student, answers))
    db.commit()
    return jsonify({"success": True})

# Added logout endpoint
@app.route("/logout", methods=["POST"])
def logout():
    try:
        # Perform any necessary session cleanup or logout logic here
        print("User logged out successfully.")
        return jsonify({"success": True, "message": "Logged out successfully."})
    except Exception as e:
        print("❌ Error during logout:", e)
        return jsonify({"success": False, "message": "An error occurred during logout."}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")

        print("🔍 Checking:", username, password, role)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s AND role=%s",
            (username, password, role)
        )
        user = cursor.fetchone()

        if user:
            print("✅ User found:", user)
            return jsonify({"success": True, "role": role, "user_id": user.get("id")})
        else:
            print("❌ User not found.")
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({"success": False, "message": "An error occurred while processing the request."}), 500

@app.route("/questions", methods=["GET"])
def get_questions():
    try:
        cursor.execute("""
            SELECT QuestionID, QuestionText, Option1, Option2, Option3, Option4, CorrectAnswer
            FROM question
        """)
        rows = cursor.fetchall()

        questions = []
        for row in rows:
            options = f"A) {row['Option1']}, B) {row['Option2']}, C) {row['Option3']}, D) {row['Option4']}"
            correct = f"{row['CorrectAnswer']}"
            questions.append({
                "id": row["QuestionID"], 
                "question": row["QuestionText"],
                "options": options,
                "correctAnswer": correct
            })

        return jsonify(questions)
    except Exception as e:
        print("❌ Error fetching questions:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/launch_test", methods=["POST"])
def launch_test():
    try:
        data = request.get_json()
        test_name = data.get("test_name")
        question_ids = data.get("question_ids")

        if not test_name:
            return jsonify({"success": False, "message": "Test name is required."}), 400

        if not question_ids or not all(str(q_id).isdigit() for q_id in question_ids):
            return jsonify({"success": False, "message": "Question IDs must be a list of integers."}), 400

        # 1. Insert test into available_tests
        cursor.execute("INSERT INTO available_tests (test_name, launch_date) VALUES (%s, NOW())", (test_name,))
        db.commit()

        # 2. Fetch the newly created test ID
        cursor.execute("SELECT id FROM available_tests WHERE test_name = %s ORDER BY id DESC LIMIT 1", (test_name,))
        test_id_row = cursor.fetchone()

        if not test_id_row:
            return jsonify({"success": False, "message": "Failed to fetch new test ID."}), 500

        new_test_id = test_id_row['id']

        # 3. Update ExamID for selected questions
        format_strings = ','.join(['%s'] * len(question_ids))
        sql = f"UPDATE question SET ExamID = %s WHERE QuestionID IN ({format_strings})"
        cursor.execute(sql, tuple([new_test_id] + [int(q) for q in question_ids]))
        db.commit()

        return jsonify({"success": True, "message": "Test launched and questions assigned successfully."})

    except Exception as e:
        print("❌ Error launching test:", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/available_tests", methods=["GET"])
def get_available_tests():
    try:
        cursor.execute("SELECT test_name, launch_date FROM available_tests")
        rows = cursor.fetchall()

        tests = [{"test_name": row["test_name"], "launch_date": row["launch_date"]} for row in rows]
        return jsonify(tests)
    except Exception as e:
        print("❌ Error fetching available tests:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/test_questions", methods=["GET"])
def get_test_questions():
    try:
        test_name = request.args.get("test_name")

        if not test_name:
            return jsonify({"error": "Test name is required."}), 400

        cursor.execute("""
            SELECT QuestionText, Option1, Option2, Option3, Option4, CorrectAnswer
            FROM question
            WHERE ExamID = (SELECT id FROM available_tests WHERE test_name = %s)
        """, (test_name,))
        rows = cursor.fetchall()

        questions = []
        for row in rows:
            options = [
                {"label": "A", "text": row["Option1"]},
                {"label": "B", "text": row["Option2"]},
                {"label": "C", "text": row["Option3"]},
                {"label": "D", "text": row["Option4"]}
            ]
            questions.append({
                "question": row["QuestionText"],
                "options": options
            })

        return jsonify(questions)
    except Exception as e:
        print("❌ Error fetching test questions:", e)
        return jsonify({"error": str(e)}), 500

# Updated scoring logic to ensure 1 mark for correct answers and 0 for incorrect answers
@app.route("/submit_test", methods=["POST"])
def submit_test():
    try:
        data = request.get_json()
        test_name = data.get("test_name")
        answers = data.get("answers")

        if not test_name or not answers:
            return jsonify({"success": False, "message": "Test name and answers are required."}), 400

        # Fetch full options + correct answers
        cursor.execute("""
            SELECT QuestionText, Option1, Option2, Option3, Option4, CorrectAnswer
            FROM question
            WHERE ExamID = (SELECT id FROM available_tests WHERE test_name = %s)
        """, (test_name,))
        rows = cursor.fetchall()

        score = 0
        total_questions = len(rows)

        # Map answer numbers to actual text
        for index, row in enumerate(rows):
            q_text = row['QuestionText']
            correct = row['CorrectAnswer'].strip().lower()
            options = [row['Option1'], row['Option2'], row['Option3'], row['Option4']]

            submitted = answers.get(f"question{index}")
            if submitted:
                submitted_answer = submitted.strip().lower()
                if submitted_answer == correct:
                    score += 1

        result = {
            "test_name": test_name,
            "score": score,
            "total_questions": total_questions,
            "percentage": (score / total_questions) * 100 if total_questions > 0 else 0
        }

        # Save result to database (optional)
        cursor.execute("""
            INSERT INTO results (test_name, score, total_questions, percentage, submission_date)
            VALUES (%s, %s, %s, %s, NOW())
        """, (test_name, score, total_questions, result["percentage"]))
        db.commit()

        return jsonify({"success": True, "result": result})
    except Exception as e:
        print("❌ Error submitting test:", e)
        return jsonify({"success": False, "message": "An error occurred while submitting the test."}), 500

@app.route("/results", methods=["GET"])
def get_results():
    try:
        cursor.execute("""
            SELECT test_name, score, total_questions, percentage, submission_date
            FROM results
        """)
        rows = cursor.fetchall()

        results = [
            {
                "test_name": row["test_name"],
                "score": row["score"],
                "total_questions": row["total_questions"],
                "percentage": row["percentage"],
                "submission_date": row["submission_date"]
            }
            for row in rows
        ]

        return jsonify(results)
    except Exception as e:
        print("❌ Error fetching results:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/test_details", methods=["GET"])
def get_test_details():
    try:
        test_name = request.args.get("test_name")

        if not test_name:
            return jsonify({"error": "Test name is required."}), 400

        # Get the exam ID for the test
        cursor.execute("SELECT id FROM available_tests WHERE test_name = %s", (test_name,))
        exam_row = cursor.fetchone()
        if not exam_row:
            return jsonify({"error": "Test not found."}), 404

        exam_id = exam_row["id"]

        # Fetch questions and correct answers
        cursor.execute("""
            SELECT QuestionID, QuestionText, Option1, Option2, Option3, Option4, CorrectAnswer
            FROM question
            WHERE ExamID = %s
        """, (exam_id,))
        questions = cursor.fetchall()

        if not questions:
            return jsonify({"error": "No questions found for this test."}), 404

        # Get student answers from `responses` table
        cursor.execute("SELECT answers FROM responses WHERE test_name = %s", (test_name,))
        answer_row = cursor.fetchone()
        if not answer_row:
            return jsonify({"error": "No answers found for this test."}), 404

        user_answers = eval(answer_row["answers"])  # Convert string to dict

        result = []
        for index, q in enumerate(questions):
            correct = q["CorrectAnswer"]
            your_answer_index = user_answers.get(f"question{index + 1}", "Not Answered")
            your_answer = "Not Answered"
            if your_answer_index.isdigit() and 1 <= int(your_answer_index) <= 4:
                your_answer = [q["Option1"], q["Option2"], q["Option3"], q["Option4"]][int(your_answer_index) - 1]

            result.append({
                "question": q["QuestionText"],
                "your_answer": your_answer,
                "correct_answer": correct
            })

        return jsonify(result)
    except Exception as e:
        print("❌ Error fetching test details:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/student_dashboard_data", methods=["GET"])
def student_dashboard_data():
    try:
        # Get number of tests taken
        cursor.execute("SELECT COUNT(*) AS total_tests FROM results")
        total_tests = cursor.fetchone()["total_tests"]

        # Get average score
        cursor.execute("SELECT AVG(percentage) AS avg_score FROM results")
        avg_score_row = cursor.fetchone()
        avg_score = round(avg_score_row["avg_score"] or 0, 2)

        # Get upcoming tests
        cursor.execute("SELECT COUNT(*) AS upcoming_tests FROM available_tests WHERE launch_date > NOW()")
        upcoming_tests = cursor.fetchone()["upcoming_tests"]

        # Recent 5 test results
        cursor.execute("SELECT test_name, percentage, submission_date FROM results ORDER BY submission_date DESC LIMIT 5")
        recent_scores = cursor.fetchall()

        # Upcoming exams list
        cursor.execute("SELECT test_name, launch_date, description FROM available_tests WHERE launch_date > NOW() ORDER BY launch_date ASC LIMIT 5")
        upcoming_exams = cursor.fetchall()

        dashboard_data = {
            "testsTaken": total_tests,
            "averageScore": avg_score,
            "upcomingTests": upcoming_tests,
            "recentScores": [
                {
                    "test_name": row["test_name"],
                    "score": row["percentage"],
                    "date": row["submission_date"].strftime("%Y-%m-%d %H:%M")
                } for row in recent_scores
            ],
            "upcomingExams": [
                {
                    "name": row["test_name"],
                    "date": row["launch_date"].strftime("%Y-%m-%d %H:%M"),
                    "description": row["description"]
                } for row in upcoming_exams
            ],
        }

        return jsonify(dashboard_data)

    except Exception as e:
        print("❌ Error loading dashboard data:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/delete_question", methods=["POST"])  # ✅ Keep POST, not DELETE
def delete_question():
    try:
        data = request.get_json()
        question_ids = data.get("question_ids")

        if not question_ids or not isinstance(question_ids, list):
            return jsonify({"success": False, "message": "A list of question IDs is required."}), 400

        format_strings = ','.join(['%s'] * len(question_ids))
        query = f"DELETE FROM question WHERE QuestionID IN ({format_strings})"

        cursor.execute(query, tuple(question_ids))
        db.commit()

        return jsonify({"success": True, "message": "Selected questions deleted successfully."})
    except Exception as e:
        print("❌ Error deleting questions:", e)
        return jsonify({"success": False, "message": f"An error occurred: {e}"}), 500

# ✅ This stays at the bottom
if __name__ == "__main__":
    app.run(debug=True)
