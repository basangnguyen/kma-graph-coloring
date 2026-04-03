from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc

app = Flask(__name__)
app.secret_key = 'kma_secret_key'

# Hàm kết nối SQL Server - Đã được cập nhật Driver ổn định hơn
def get_db_connection():
    try:
        conn_str = (
            "Driver={SQL Server Native Client 11.0};" # Hoặc dùng {ODBC Driver 17 for SQL Server}
            "Server=LAPTOP-891ALRRU;"
            "Database=KMA_Learning;"
            "Trusted_Connection=yes;"
        )
        return pyodbc.connect(conn_str, timeout=5) # Giới hạn 5s để tránh treo web
    except Exception as e:
        print(f"Lỗi cấu hình kết nối: {e}")
        return None

@app.route('/')
def home():
    if 'user' in session:
        # Quan trọng: Phải truyền user vào render_template để hiển thị tên trên web
        return render_template('index.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn is None:
            return "Không thể kết nối đến cơ sở dữ liệu. Hãy kiểm tra SQL Server!"
            
        try:
            cursor = conn.cursor()
            # Kiểm tra tài khoản
            cursor.execute("SELECT username FROM Users WHERE username=? AND password=?", (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['user'] = user[0]
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
        if conn is None:
            return "Lỗi kết nối DB!"
            
        try:
            cursor = conn.cursor()
            # Thêm user mới
            cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            return "Tên đăng nhập đã tồn tại hoặc có lỗi xảy ra!"
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)