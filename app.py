from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.secret_key = 'mat_khau_bi_mat_cua_app'  # Thay bằng chuỗi bí mật của bạn

# Cấu hình Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS (CÁC BẢNG CƠ SỞ DỮ LIỆU) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)      # Mới: Email
    fullname = db.Column(db.String(100), nullable=False)                # Mới: Tên hiển thị
    password = db.Column(db.String(60), nullable=False)
    # Quan hệ
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True) # Có thể null nếu chỉ chia sẻ mà không viết gì thêm
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Mới: Logic Chia sẻ (Self-referencing)
    # original_post_id trỏ về bài gốc. Nếu bài gốc bị xóa, các bài share cũng bị xóa (cascade)
    original_post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    shares = db.relationship('Post', 
                             backref=db.backref('original', remote_side=[id]), 
                             cascade="all, delete-orphan") 

    # Quan hệ khác
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")

    def is_liked_by(self, user_id):
        return Like.query.filter_by(user_id=user_id, post_id=self.id).first() is not None

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

# Bảng lưu tiến độ học tập (Vị trí thẻ hiện tại)
class StudyProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    set_id = db.Column(db.Integer, nullable=False) # ID của bộ thẻ
    current_index = db.Column(db.Integer, default=0, nullable=False) # Vị trí thẻ đang học

# Bảng lưu lịch ôn tập SRS
class FlashcardReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_id = db.Column(db.Integer, nullable=False) # ID của thẻ từ vựng
    next_review = db.Column(db.DateTime, nullable=False) # Thời gian ôn tập tiếp theo

# --- HÀM LOAD DỮ LIỆU TỪ JSON ---
def load_json_data(filename):
    # Đường dẫn tới file json trong thư mục data
    file_path = os.path.join(app.root_path, 'data', filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {filename} trong thư mục data.")
        return []
    except json.JSONDecodeError:
        print(f"Lỗi: File {filename} bị lỗi cú pháp.")
        return []

# Biến toàn cục chứa danh sách từ vựng (được load khi khởi động)
FLASHCARDS_DB = load_json_data('vocabulary.json')
VIDEOS_DB = load_json_data('videos.json')

# --- ROUTES ---

@app.route('/')
def root():
    if 'user' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

# 1. ĐĂNG NHẬP
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Tìm user trong DB
        user = User.query.filter_by(username=username).first()
        
        # Kiểm tra mật khẩu (đơn giản, chưa mã hóa)
        if user and user.password == password:
            session['user'] = user.username
            return redirect(url_for('home'))
        else:
            error = 'Sai tên tài khoản hoặc mật khẩu!'
            
    return render_template('login.html', error=error)

# 2. ĐĂNG KÝ
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']           # Mới
        fullname = request.form['fullname']     # Mới
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error = 'Mật khẩu nhập lại không khớp!'
        else:
            # Kiểm tra trùng username hoặc email
            user_exists = User.query.filter((User.username==username) | (User.email==email)).first()
            if user_exists:
                error = 'Tên tài khoản hoặc Email đã tồn tại!'
            else:
                new_user = User(username=username, email=email, fullname=fullname, password=password)
                db.session.add(new_user)
                db.session.commit()
                session['user'] = username
                return redirect(url_for('home'))

    return render_template('register.html', error=error)
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('home.html', page_name='home')

@app.route('/topics')
def topics():
    if 'user' not in session: return redirect(url_for('login'))
    
    # [CẬP NHẬT] Load dữ liệu Video từ JSON
    global VIDEOS_DB
    VIDEOS_DB = load_json_data('videos.json')
    
    return render_template('topics.html', page_name='topics', categories=VIDEOS_DB)

@app.route('/vocabulary')
def vocabulary():
    if 'user' not in session: return redirect(url_for('login'))
    
    # Reload lại dữ liệu từ file JSON mỗi lần vào trang
    global FLASHCARDS_DB
    FLASHCARDS_DB = load_json_data('vocabulary.json')
    
    vocab_sections = [
        {
            'title': 'Tiếng Anh Thông dụng',
            'icon': 'fa-globe-americas',
            'color': 'success',
            'sets': [
                {'id': 1, 'name': '1000 từ tiếng Anh thông dụng', 'count': len(FLASHCARDS_DB), 'desc': 'Nền tảng giao tiếp hàng ngày.', 'img': 'https://img.freepik.com/free-vector/english-book-illustration_1284-3976.jpg'}
            ]
        }
    ]
    return render_template('vocabulary.html', page_name='vocabulary', sections=vocab_sections)

# ROUTE HỌC TỪ (Lấy tiến độ từ DB)
@app.route('/study/<int:set_id>')
def study(set_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    if not user: return redirect(url_for('login'))

    # Lấy tiến độ học tập của user cho bộ thẻ này
    progress = StudyProgress.query.filter_by(user_id=user.id, set_id=set_id).first()
    
    start_index = 0
    if progress:
        start_index = progress.current_index

    # Reload data
    global FLASHCARDS_DB
    FLASHCARDS_DB = load_json_data('vocabulary.json')

    # Kiểm tra index hợp lệ
    if start_index >= len(FLASHCARDS_DB):
        start_index = 0

    set_name = "1000 từ tiếng Anh thông dụng" if set_id == 1 else f"Bộ thẻ số {set_id}"
    cards = FLASHCARDS_DB if set_id == 1 else []
    
    set_info = {'name': set_name, 'total': len(cards)}
    
    return render_template('study.html', page_name='vocabulary', cards=cards, set_info=set_info, start_index=start_index, current_set_id=set_id)

# API: CẬP NHẬT VỊ TRÍ THẺ ĐANG HỌC
@app.route('/update_study_index', methods=['POST'])
def update_study_index():
    if 'user' not in session: return jsonify({'status': 'error'}), 401
    
    data = request.json
    set_id = data.get('set_id')
    new_index = data.get('new_index')
    
    user = User.query.filter_by(username=session['user']).first()
    if user:
        progress = StudyProgress.query.filter_by(user_id=user.id, set_id=set_id).first()
        if progress:
            progress.current_index = new_index
        else:
            new_progress = StudyProgress(user_id=user.id, set_id=set_id, current_index=new_index)
            db.session.add(new_progress)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

# API: RESET TIẾN ĐỘ VỀ 0 (KHI HỌC XONG)
@app.route('/reset_study_index', methods=['POST'])
def reset_study_index():
    if 'user' not in session: return jsonify({'status': 'error'}), 401
    
    data = request.json
    set_id = data.get('set_id')
    
    user = User.query.filter_by(username=session['user']).first()
    if user:
        progress = StudyProgress.query.filter_by(user_id=user.id, set_id=set_id).first()
        if progress:
            progress.current_index = 0
            db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

# API: LƯU ĐÁNH GIÁ SRS
@app.route('/save_progress', methods=['POST'])
def save_progress():
    if 'user' not in session: return jsonify({'status': 'error'}), 401
    
    data = request.json
    card_id = data.get('card_id')
    rating = data.get('rating')
    
    user = User.query.filter_by(username=session['user']).first()
    if not user: return jsonify({'status': 'error'}), 401

    # Logic tính thời gian ôn tập
    now = datetime.now()
    if rating == 'hoc-lai':
        next_review = now + timedelta(minutes=10)
    elif rating == 'kho':
        next_review = now + timedelta(days=1)
    elif rating == 'tot':
        next_review = now + timedelta(days=3)
    elif rating == 'de':
        next_review = now + timedelta(days=5)
    else:
        next_review = now

    # Lưu vào DB FlashcardReview
    entry = FlashcardReview.query.filter_by(user_id=user.id, card_id=card_id).first()
    if entry:
        entry.next_review = next_review
    else:
        new_entry = FlashcardReview(user_id=user.id, card_id=card_id, next_review=next_review)
        db.session.add(new_entry)
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'next_review': next_review.isoformat()})

# ROUTE: ÔN TẬP
@app.route('/review')
def review():
    if 'user' not in session: return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    if not user: return redirect(url_for('login'))
    
    # Reload data
    global FLASHCARDS_DB
    FLASHCARDS_DB = load_json_data('vocabulary.json')
    
    review_cards = []
    now = datetime.now()
    
    # Lấy các thẻ cần ôn tập từ DB
    due_reviews = FlashcardReview.query.filter_by(user_id=user.id).filter(FlashcardReview.next_review <= now).all()
    
    for rev in due_reviews:
        # Tìm thông tin chi tiết của thẻ trong JSON dựa vào ID
        card = next((item for item in FLASHCARDS_DB if item["id"] == rev.card_id), None)
        if card:
            review_cards.append(card)
    
    return render_template('review.html', page_name='review', cards=review_cards)

# [QUAN TRỌNG] Dictation: Đọc từ file JSON
@app.route('/dictation/<video_id>')
def dictation(video_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    # Reload data
    global VIDEOS_DB
    VIDEOS_DB = load_json_data('videos.json')
    
    # Tìm video trong danh sách
    video_data = None
    for category in VIDEOS_DB:
        for video in category['videos']:
            if video['id'] == video_id:
                video_data = video
                break
        if video_data: break
    
    # Nếu không tìm thấy, trả về video mặc định hoặc báo lỗi
    if not video_data:
        # Fallback (Phòng trường hợp file JSON lỗi hoặc video cũ)
        video_data = {
            'id': video_id,
            'title': 'Video Not Found',
            'segments': []
        }
    
    return render_template('dictation.html', video=video_data)

# CÁC ROUTE KHÁC (COMMUNITY, STATS, PROFILE...)

@app.route('/community')
def community():
    if 'user' not in session: return redirect(url_for('login'))
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        session.pop('user', None)
        return redirect(url_for('login'))
    return render_template('community.html', page_name='community', posts=posts, current_user=current_user)

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user' not in session: return redirect(url_for('login'))
    content = request.form.get('content')
    if content:
        user = User.query.filter_by(username=session['user']).first()
        if user:
            new_post = Post(content=content, author=user)
            db.session.add(new_post)
            db.session.commit()
    return redirect(url_for('community'))

@app.route('/like/<int:post_id>')
def like_post(post_id):
    if 'user' not in session: return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    if not user: return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        new_like = Like(user_id=user.id, post_id=post.id)
        db.session.add(new_like)
    db.session.commit()
    return redirect(url_for('community'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session: return redirect(url_for('login'))
    content = request.form.get('content')
    if content:
        user = User.query.filter_by(username=session['user']).first()
        if user:
            new_comment = Comment(content=content, user_id=user.id, post_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
    return redirect(url_for('community'))

@app.route('/stats')
def stats():
    if 'user' not in session: return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    if not user: return redirect(url_for('login'))
    
    # Tính toán số liệu thật từ DB
    total_vocab = len(FLASHCARDS_DB)
    # Số từ đã học (có trong bảng Review)
    learned_count = FlashcardReview.query.filter_by(user_id=user.id).count()
    # Số từ cần ôn tập (Next review <= Now)
    now = datetime.now()
    due_count = FlashcardReview.query.filter_by(user_id=user.id).filter(FlashcardReview.next_review <= now).count()
    
    # Giả lập các số liệu khác cho đẹp
    stats_data = {
        'total_cards': total_vocab,
        'reviews': learned_count * 2,
        'due': due_count,
        'accuracy': 85,
        'learning': due_count,
        'reviewing': 5,
        'mastered': max(0, learned_count - due_count), # Đã học trừ đi số cần ôn
        'total_vocab': total_vocab
    }
    return render_template('stats.html', page_name='stats', stats=stats_data)

@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    if 'user' not in session: return redirect(url_for('login'))
    
    # Nếu không truyền username, mặc định là user đang đăng nhập
    target_username = username if username else session['user']
    target_user = User.query.filter_by(username=target_username).first_or_404()
    
    # Lấy danh sách bài viết của người này (sắp xếp mới nhất)
    user_posts = Post.query.filter_by(user_id=target_user.id).order_by(Post.date_posted.desc()).all()
    
    return render_template('profile.html', page_name='profile', user=target_user, posts=user_posts)

# Route Xóa bài viết
@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    current_user = User.query.filter_by(username=session['user']).first()
    
    # Chỉ chủ bài viết mới được xóa
    if post.author.id == current_user.id:
        db.session.delete(post) # Cascade sẽ tự động xóa các bài share liên quan
        db.session.commit()
    
    # Quay lại trang trước đó (Community hoặc Profile)
    return redirect(request.referrer or url_for('community'))

# Route Chia sẻ bài viết
@app.route('/share_post/<int:original_id>')
def share_post(original_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    current_user = User.query.filter_by(username=session['user']).first()
    original_post = Post.query.get_or_404(original_id)
    
    # Nếu bài này vốn là bài share, ta share bài gốc của nó (tránh share chồng share)
    real_original_id = original_post.original_post_id if original_post.original_post_id else original_post.id
    
    # Tạo bài viết mới trỏ về bài gốc
    new_share = Post(content="", user_id=current_user.id, original_post_id=real_original_id)
    
    db.session.add(new_share)
    db.session.commit()
    
    return redirect(url_for('profile')) # Share xong chuyển về trang cá nhân để thấy bài

@app.route('/leaderboard')
def leaderboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # 1. Tính điểm XP cho TẤT CẢ User
    all_users = User.query.all()
    leaderboard_data = []
    
    for u in all_users:
        # Đếm số thẻ user này đã học (có trong bảng Review)
        words_learned = FlashcardReview.query.filter_by(user_id=u.id).count()
        xp = words_learned * 10 
        
        # Chọn màu avatar ngẫu nhiên dựa trên ID
        colors = ['f44336', 'e91e63', '9c27b0', '673ab7', '3f51b5', '2196f3', '03a9f4', '00bcd4', '009688', '4caf50', '8bc34a', 'cddc39', 'ffeb3b', 'ffc107', 'ff9800', 'ff5722']
        avatar_color = colors[u.id % len(colors)]
        
        leaderboard_data.append({
            'username': u.username,
            'xp': xp,
            'avatar_color': avatar_color,
            'words_learned': words_learned
        })
    
    # 2. Sắp xếp theo XP giảm dần
    leaderboard_data.sort(key=lambda x: x['xp'], reverse=True)
    
    # 3. Gán thứ hạng (Rank)
    for i, data in enumerate(leaderboard_data):
        data['rank'] = i + 1
        
    # 4. Tìm thứ hạng của User hiện tại
    current_user_rank = next((item for item in leaderboard_data if item['username'] == session['user']), None)
    
    # Chỉ lấy Top 10 để hiển thị
    top_10 = leaderboard_data[:10]
    
    return render_template('leaderboard.html', page_name='leaderboard', leaderboard=top_10, my_rank=current_user_rank)

# --- KHỞI ĐỘNG ---
if __name__ == '__main__':
    with app.app_context():
        # Tạo bảng nếu chưa có
        db.create_all()
        print(">>> Database đã sẵn sàng!")
    app.run(debug=True)