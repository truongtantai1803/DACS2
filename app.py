from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'mat_khau_bi_mat_cua_app'  # Bắt buộc phải có để dùng session

# 1. Trang mặc định: Tự động chuyển hướng về trang đăng nhập
@app.route('/')
def root():
    if 'user' in session: # Nếu đã đăng nhập thì vào thẳng trang chủ
        return redirect(url_for('home'))
    return redirect(url_for('login'))

# 2. Xử lý Đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Lấy thông tin người dùng nhập vào
        username = request.form['username']
        password = request.form['password']

        # KIỂM TRA TÀI KHOẢN (Hardcode để test)
        if username == 'admin' and password == '123':
            session['user'] = username  # Lưu trạng thái đăng nhập
            return redirect(url_for('home')) # Chuyển sang trang chủ
        else:
            error = 'Sai tài khoản hoặc mật khẩu! (Thử: admin / 123)'

    return render_template('login.html', error=error)

# 3. Trang Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user', None) # Xóa trạng thái đăng nhập
    return redirect(url_for('login'))

# --- CÁC TRANG CÓ MENU ---

@app.route('/home')
def home():
    if 'user' not in session: return redirect(url_for('login')) # Chặn nếu chưa đăng nhập
    return render_template('home.html', page_name='home')

@app.route('/topics')
def topics():
    if 'user' not in session: return redirect(url_for('login'))
    
    # Cấu trúc dữ liệu mới: Danh sách các NHÓM CHỦ ĐỀ
    categories = [
        {
            'name': 'Daily English Conversation',
            'icon': 'fa-comments',
            'videos': [
                {
                    'title': '100 Common English Phrases',
                    'desc': 'Các mẫu câu giao tiếp thông dụng nhất hàng ngày.',
                    'thumbnail': 'https://img.youtube.com/vi/aFnU_H13J8s/maxresdefault.jpg',
                    'duration': '15:30',
                    'level': 'Dễ'
                },
                {
                    'title': 'At the Coffee Shop',
                    'desc': 'Cách gọi đồ uống và thanh toán tại quán cà phê.',
                    'thumbnail': 'https://img.youtube.com/vi/caW3jU9Xq5I/maxresdefault.jpg',
                    'duration': '08:45',
                    'level': 'Dễ'
                },
                {
                    'title': 'Talking about Weather',
                    'desc': 'Chủ đề thời tiết - Cách bắt chuyện tự nhiên nhất.',
                    'thumbnail': 'https://img.youtube.com/vi/D0n0p2-fN6Y/maxresdefault.jpg',
                    'duration': '06:20',
                    'level': 'Trung bình'
                }
            ]
        },
        {
            'name': 'US-UK Songs',
            'icon': 'fa-music',
            'videos': [
                {
                    'title': 'Perfect - Ed Sheeran',
                    'desc': 'Học từ vựng lãng mạn qua bài hát Perfect.',
                    'thumbnail': 'https://img.youtube.com/vi/2Vv-BfVoq4g/maxresdefault.jpg',
                    'duration': '04:23',
                    'level': 'Trung bình'
                },
                {
                    'title': 'Someone Like You - Adele',
                    'desc': 'Luyện phát âm giọng Anh-Anh chuẩn cùng Adele.',
                    'thumbnail': 'https://img.youtube.com/vi/hLQl3WQQoQ0/maxresdefault.jpg',
                    'duration': '04:45',
                    'level': 'Khó'
                },
                {
                    'title': 'A Thousand Years',
                    'desc': 'Bài hát đám cưới kinh điển - Christina Perri.',
                    'thumbnail': 'https://img.youtube.com/vi/rtOvBOTyX00/maxresdefault.jpg',
                    'duration': '04:50',
                    'level': 'Dễ'
                }
            ]
        }
    ]
    
    return render_template('topics.html', page_name='topics', categories=categories)

@app.route('/review')
def review():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('base.html', page_name='review', content="Giao diện Ôn tập")

@app.route('/vocabulary')
def vocabulary():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('base.html', page_name='vocabulary', content="Giao diện Từ vựng")

@app.route('/community')
def community():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('base.html', page_name='community', content="Giao diện Cộng đồng")

@app.route('/leaderboard')
def leaderboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('base.html', page_name='leaderboard', content="Giao diện Bảng xếp hạng")

if __name__ == '__main__':
    app.run(debug=True)