import os
import psycopg2
from groq import Groq
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_sieu_bao_mat')

# ---------------------------------------------------------------------------
# CẤU HÌNH AI (GROQ - LLAMA 3)
# ---------------------------------------------------------------------------
GROQ_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# ---------------------------------------------------------------------------
# HÀM KẾT NỐI DATABASE
# ---------------------------------------------------------------------------
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("Chưa tìm thấy DATABASE_URL!")
    return psycopg2.connect(db_url)

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
        print("Khởi tạo Database thành công!")
    except Exception as e:
        print(f"Lỗi DB: {e}")

init_db()

# ---------------------------------------------------------------------------
# ROUTE GIAO DIỆN
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
            cur.execute('INSERT INTO Users (username, password) VALUES (%s, %s)', (username, hashed_pw))
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
# ROUTE CHATBOT AI (GROQ)
# ---------------------------------------------------------------------------
@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({"answer": "Vui lòng đăng nhập!"}), 401

    if not client:
        return jsonify({"answer": "Lỗi: Chưa cấu hình GROQ_API_KEY trên Render!"}), 500

    data = request.json
    user_message = data.get('message', '')

    try:
        # Gọi API của Groq (dùng model Llama 3 cực xịn của Meta)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là trợ lý ảo thân thiện của trường Học viện Kỹ thuật Mật mã (KMA). Hãy trả lời ngắn gọn, tự nhiên bằng tiếng Việt."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.1-8b-instant", # Model nhẹ, siêu tốc độ
        )
        return jsonify({"answer": chat_completion.choices[0].message.content})
        
    except Exception as e:
        print(f"Lỗi AI: {e}")
        return jsonify({"answer": f"Lỗi: {str(e)}"}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
