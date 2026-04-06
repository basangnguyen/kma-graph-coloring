import os
import psycopg2
from google import genai  # <-- THƯ VIỆN MỚI NHẤT CỦA GOOGLE
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Lấy SECRET_KEY từ Render
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_sieu_bao_mat')

# ---------------------------------------------------------------------------
# CẤU HÌNH GEMINI AI (CHUẨN MỚI NHẤT)
# ---------------------------------------------------------------------------
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_KEY:
    # Khởi tạo Client theo chuẩn mới của thư viện google-genai
    gemini_client = genai.Client(api_key=GEMINI_KEY)
else:
    gemini_client = None
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
    if 'user' not in session:
        return jsonify({"answer": "Vui lòng đăng nhập!"}), 401

    if not gemini_client:
        return jsonify({"answer": "Lỗi: Hệ thống chưa được cấp API Key!"}), 500

    data = request.json
    user_message = data.get('message', '')

    try:
        full_prompt = f"Bạn là trợ lý ảo thân thiện của trường KMA. Trả lời: {user_message}"
        
        # Cú pháp gọi AI hoàn toàn mới
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=full_prompt
        )
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
