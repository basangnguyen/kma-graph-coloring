from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
# Sử dụng Secret Key từ Environment Variable trên Render, hoặc mặc định nếu chạy local
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key_default')

# --- CẤU HÌNH DATABASE SQLITE ---
def get_db_connection():
    # SQLite sẽ tạo một file database.db ngay trong thư mục project
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Hàm khởi tạo database (Tạo bảng Users nếu chưa có)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tạo bảng Users phù hợp với logic của bạn
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    # Thêm thử một tài khoản mẫu để bạn đăng nhập ngay
    try:
        cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", ('admin', '123456'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Tài khoản đã tồn tại thì bỏ qua
    conn.close()

# Chạy khởi tạo DB khi ứng dụng bắt đầu
init_db()

@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Truy vấn kiểm tra tài khoản
            cursor.execute("SELECT username FROM Users WHERE username=? AND password=?", (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['user'] = user['username']
                return redirect(url_for('home'))
            return "Sai tài khoản hoặc mật khẩu! <a href='/login'>Thử lại</a>"
        except Exception as e:
            return f"Lỗi truy vấn: {e}"
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Thêm user mới vào SQLite
            cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Tên đăng nhập đã tồn tại! <a href='/register'>Thử lại</a>"
        except Exception as e:
            return f"Lỗi đăng ký: {e}"
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Render yêu cầu app chạy trên port được cấp phát hoặc 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
