import os
import psycopg2
import google.generativeai as genai  # Thư viện Gemini
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Lấy SECRET_KEY từ Render
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_sieu_bao_mat')

# ---------------------------------------------------------------------------
# CẤU HÌNH GEMINI AI
# ---------------------------------------------------------------------------
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # Cấu hình model (dùng bản 1.5-flash cho nhanh và miễn phí)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    print("CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY trong biến môi trường!")

# ---------------------------------------------------------------------------
# HÀM KẾT NỐI DATABASE (POSTGRESQL)
# ---------------------------------------------------------------------------
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("Chưa tìm thấy DATABASE_URL trong biến môi trường!")
    
    conn = psycopg2.connect(db_url)
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id SERIAL PRIMARY KEY, 
                username VARCHAR(50) UNIQUE NOT NULL, 
                password VARCHAR(255) NOT NULL
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Đã kiểm tra/khởi tạo Database thành công!")
    except Exception as e:
        print(f"Lỗi khởi tạo DB: {e}")

# Khởi tạo bảng khi app chạy
init_db()

# ---------------------------------------------------------------------------
# CÁC ROUTE XỬ LÝ GIAO DIỆN
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM Users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect(url_for('home'))
        
        flash("Sai tài khoản hoặc mật khẩu!", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Vui lòng nhập đầy đủ thông tin!", "warning")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO Users (username, password) VALUES (%s, %s)', 
                         (username, hashed_pw))
            conn.commit()
            flash("Đăng ký thành công! Mời bạn đăng nhập.", "success")
            return redirect(url_for('login'))
        except IntegrityError:
            conn.rollback()
            flash("Tên đăng nhập đã tồn tại!", "warning")
        except Exception as e:
            conn.rollback()
            flash(f"Lỗi hệ thống: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
            
    return render_template('register.html')

# ---------------------------------------------------------------------------
# ROUTE XỬ LÝ CHATBOT (GEMINI AI)
# ---------------------------------------------------------------------------

@app.route('/chat', methods=['POST'])
def chat():
    # Chỉ cho phép người dùng đã đăng nhập sử dụng Chatbot
    if 'user' not in session:
        return jsonify({"answer": "Vui lòng đăng nhập để trò chuyện với trợ lý!"}), 401

    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"answer": "Bạn chưa nhập câu hỏi mà!"}), 400

    try:
        # Prompt định hướng cho AI
        full_prompt = f"Bạn là trợ lý ảo thân thiện của trường KMA. Hãy trả lời câu hỏi sau một cách lịch sự và ngắn gọn bằng tiếng Việt: {user_message}"
        
        # Gọi Gemini API
        response = model.generate_content(full_prompt)
        
        return jsonify({"answer": response.text})
    except Exception as e:
        print(f"Lỗi Gemini: {e}")
       return jsonify({"answer": f"Lỗi hệ thống: {str(e)}"}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
