from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kma_secret_key') # Ưu tiên lấy từ biến môi trường

# Đường dẫn DB tuyệt đối để tránh lỗi không tìm thấy file trên server
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context(): # Chạy trong context của Flask
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS Users 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         username TEXT UNIQUE, 
                         password TEXT)''')
        conn.commit()
        conn.close()

# Chỉ khởi tạo nếu file DB chưa tồn tại hoặc chạy lần đầu
if not os.path.exists(DB_PATH):
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
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()
        conn.close()
        
        if user:
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

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO Users (username, password) VALUES (?, ?)', 
                         (username, password))
            conn.commit()
            flash("Đăng ký thành công! Mời bạn đăng nhập.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Tên đăng nhập đã tồn tại!", "warning")
        except Exception as e:
            flash(f"Lỗi hệ thống: {str(e)}", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear() # Xóa sạch session cho an toàn
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Chạy local
    app.run(debug=True)
