import os
import psycopg2
import datetime
import numpy as np
from groq import Groq
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_sieu_bao_mat')

# ---------------------------------------------------------------------------
# CẤU HÌNH AI & RAG (TÍNH NĂNG 3: RETRIEVAL-AUGMENTED GENERATION)
# ---------------------------------------------------------------------------
GROQ_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# Đây là Cơ sở dữ liệu tri thức giả lập (Bạn có thể thêm hàng trăm câu vào đây)
kma_knowledge_base = [
    "Học viện Kỹ thuật Mật mã (KMA) có trụ sở chính tại 141 Chiến Thắng, Tân Triều, Thanh Trì, Hà Nội.",
    "Điểm chuẩn ngành An toàn thông tin năm 2023 của KMA là 25.6 điểm.",
    "Trường có cơ sở phía Nam tại 17A Cộng Hòa, Phường 4, Quận Tân Bình, TP.HCM.",
    "Học phí hệ đóng học phí của KMA dự kiến năm học 2024-2025 là khoảng 400.000 VNĐ/tín chỉ.",
    "KMA đào tạo 3 ngành chính: An toàn thông tin, Công nghệ thông tin (chuyên ngành Kỹ thuật phần mềm nhúng và di động), và Kỹ thuật điện tử viễn thông.",
    "Mã trường của Học viện Kỹ thuật Mật mã là KMA."
]

# Khởi tạo công cụ tìm kiếm siêu nhẹ (TF-IDF Vectorizer)
vectorizer = TfidfVectorizer()
kb_vectors = vectorizer.fit_transform(kma_knowledge_base)

def retrieve_kma_info(query, top_k=2):
    """Hàm tìm kiếm thông tin liên quan nhất từ thư viện kiến thức nội bộ"""
    query_vec = vectorizer.transform([query])
    sims = cosine_similarity(query_vec, kb_vectors)[0]
    
    top_indices = sims.argsort()[-top_k:][::-1]
    results = []
    for idx in top_indices:
        if sims[idx] > 0.05: # Ngưỡng tương đồng tối thiểu
            results.append(kma_knowledge_base[idx])
    
    return "\n".join(results)

# ---------------------------------------------------------------------------
# DATABASE & ROUTE GIAO DIỆN (Giữ nguyên như cũ)
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
    except Exception as e:
        print(f"Lỗi DB: {e}")

init_db()

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# ROUTE CHATBOT AI ĐÃ NÂNG CẤP
# ---------------------------------------------------------------------------
@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({"answer": "Vui lòng đăng nhập!"}), 401

    if not client:
        return jsonify({"answer": "Lỗi: Chưa cấu hình GROQ_API_KEY!"}), 500

    data = request.json
    user_message = data.get('message', '')
    # TÍNH NĂNG 1: TRÍ NHỚ - Nhận lịch sử chat từ giao diện
    chat_history = data.get('history', []) 

    try:
        # TÍNH NĂNG 3 (Tiếp): Rút trích dữ liệu liên quan từ câu hỏi
        retrieved_context = retrieve_kma_info(user_message)
        
        # TÍNH NĂNG 4: BƠM DỮ LIỆU ĐỘNG (Thời gian thực)
        current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        # Khởi tạo System Prompt với RAG
        system_prompt = f"""Bạn là LinLin, trợ lý ảo cực kỳ thân thiện, thông minh và năng động của Học viện Kỹ thuật Mật mã (KMA).
Hôm nay là: {current_time}

Dưới đây là cơ sở dữ liệu nội bộ MỚI NHẤT của trường. Hãy LUÔN ƯU TIÊN dùng thông tin này để trả lời câu hỏi:
---
{retrieved_context if retrieved_context else "Không có thông tin nội bộ đặc biệt nào được tìm thấy cho câu hỏi này."}
---

Quy tắc:
1. Xưng hô là 'LinLin' và gọi người dùng là 'bạn'.
2. Nếu câu hỏi nằm trong cơ sở dữ liệu nội bộ, hãy trả lời chính xác theo đó.
3. Nếu không có dữ liệu nội bộ, hãy dùng kiến thức chung nhưng thể hiện sự khiêm tốn.
4. Trả lời ngắn gọn, tự nhiên, hiện đại, có emoji."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Thêm lịch sử trò chuyện (giữ 8 tin nhắn gần nhất để AI hiểu ngữ cảnh)
        messages.extend(chat_history[-8:])
        
        # Thêm câu hỏi hiện tại
        messages.append({"role": "user", "content": user_message})

        # TÍNH NĂNG 2: MODEL XỊN HƠN (Llama 3.1 70B)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-70b-versatile",
            temperature=0.7, # Độ sáng tạo vừa phải
        )
        return jsonify({"answer": chat_completion.choices[0].message.content})
        
    except Exception as e:
        print(f"Lỗi AI: {e}")
        return jsonify({"answer": f"Lỗi: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
