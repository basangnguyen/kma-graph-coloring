import os
import psycopg2
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Lấy SECRET_KEY từ Render, nếu chạy local thì dùng mặc định
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_sieu_bao_mat')

# ---------------------------------------------------------------------------
# HÀM KẾT NỐI DATABASE (POSTGRESQL)
# ---------------------------------------------------------------------------
def get_db_connection():
    # Render sẽ tự động cấp biến DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("Chưa tìm thấy DATABASE_URL trong biến môi trường!")
    
    conn = psycopg2.connect(db_url)
    return conn

# Tự động tạo bảng nếu chưa có (Chỉ chạy 1 lần khi app khởi động)
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

# Gọi hàm khởi tạo
init_db()

# ---------------------------------------------------------------------------
# CÁC ROUTE XỬ LÝ
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
        # Dùng RealDictCursor để trả về dữ liệu dạng Dictionary (giống sqlite3.Row)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # BƯỚC 1: Chỉ tìm user theo username
        cur.execute('SELECT * FROM Users WHERE username = %s', (username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        # BƯỚC 2: Kiểm tra mật khẩu bằng hàm check_password_hash
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

        # BƯỚC 3: Băm mật khẩu (Hashing) trước khi lưu
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Lưu mật khẩu đã mã hóa (hashed_pw) thay vì mật khẩu gốc
            cur.execute('INSERT INTO Users (username, password) VALUES (%s, %s)', 
                         (username, hashed_pw))
            conn.commit()
            flash("Đăng ký thành công! Mời bạn đăng nhập.", "success")
            return redirect(url_for('login'))
        
        # Bắt lỗi trùng username của PostgreSQL
        except IntegrityError:
            conn.rollback() # Cần rollback nếu có lỗi để tránh kẹt database
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
    session.clear() # Xóa sạch session cho an toàn
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
