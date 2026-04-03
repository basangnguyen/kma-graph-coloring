from flask import Flask, render_template, request, redirect, url_for, session, flash # Thêm flash

# ... (các phần init_db và get_db_connection giữ nguyên) ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM Users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user'] = user['username']
            return redirect(url_for('home'))
        
        # Nếu sai tài khoản, thông báo lỗi ngay tại trang login
        flash("Sai tài khoản hoặc mật khẩu!", "danger")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            # Gửi thông báo thành công và chuyển hướng về trang đăng nhập
            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Tên đăng nhập đã tồn tại!", "warning")
            return redirect(url_for('register'))
            
    return render_template('register.html')
