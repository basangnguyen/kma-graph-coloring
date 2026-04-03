from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'kma_secret_key' # Thay đổi tùy ý

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Khởi tạo DB nếu chưa có
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS Users 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     username TEXT UNIQUE, 
                     password TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
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
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO Users (username, password) VALUES (?, ?)', 
                         (username, password))
            conn.commit()
            flash("Đăng ký thành công! Mời bạn đăng nhập.", "success")
            return redirect(url_for('login'))
        except:
            flash("Tên đăng nhập đã tồn tại!", "warning")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
