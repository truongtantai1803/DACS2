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
    password = db.Column(db.String(60), nullable=False)
    # Quan hệ
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Quan hệ
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
def load_flashcards():
    # Đường dẫn tới file json: thư mục hiện tại / data / vocabulary.json
    file_path = os.path.join(app.root_path, 'data', 'vocabulary.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file vocabulary.json trong thư mục data.")
        return []
    except json.JSONDecodeError:
        print("Lỗi: File vocabulary.json bị lỗi cú pháp.")
        return []

# Biến toàn cục chứa danh sách từ vựng (được load khi khởi động)
FLASHCARDS_DB = load_flashcards()

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
        
        user = User.query.filter_by(username=username).first()
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
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error = 'Mật khẩu nhập lại không khớp!'
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                error = 'Tên tài khoản đã tồn tại!'
            else:
                new_user = User(username=username, password=password)
                db.session.add(new_user)
                db.session.commit()
                # Đăng ký thành công -> Tự động đăng nhập
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
    # Dữ liệu giả lập cho trang Chủ đề
    categories = [
        {
            'name': 'Daily English Conversation',
            'icon': 'fa-comments',
            'videos': [
                {'title': '100 Common English Phrases', 'desc': 'Các mẫu câu giao tiếp thông dụng nhất.', 'thumbnail': 'https://img.youtube.com/vi/aFnU_H13J8s/maxresdefault.jpg', 'duration': '15:30', 'level': 'Dễ'}
            ]
        }
    ]
    return render_template('topics.html', page_name='topics', categories=categories)

@app.route('/vocabulary')
def vocabulary():
    if 'user' not in session: return redirect(url_for('login'))
    
    # Reload lại dữ liệu từ file JSON mỗi lần vào trang (để cập nhật nếu bạn sửa file json)
    global FLASHCARDS_DB
    FLASHCARDS_DB = load_flashcards()
    
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
    FLASHCARDS_DB = load_flashcards()

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
    FLASHCARDS_DB = load_flashcards()
    
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
    # Dữ liệu giả lập cho trang thống kê
    stats_data = {
        'total_cards': len(FLASHCARDS_DB),
        'reviews': 12,
        'due': 5,
        'accuracy': 85,
        'learning': 10,
        'reviewing': 5,
        'mastered': 20,
        'total_vocab': len(FLASHCARDS_DB)
    }
    return render_template('stats.html', page_name='stats', stats=stats_data)

@app.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('profile.html', page_name='profile')

@app.route('/leaderboard')
def leaderboard():
    if 'user' not in session: return redirect(url_for('login'))
    leaderboard_data = [
        {'rank': 1, 'username': 'Sarah_Polyglot', 'xp': 2850, 'avatar_color': 'f44336'},
        {'rank': 2, 'username': 'Mike_English', 'xp': 2720, 'avatar_color': '2196f3'},
        {'rank': 3, 'username': 'Jessica_AI', 'xp': 2680, 'avatar_color': '9c27b0'}
    ]
    current_user_rank = {'rank': 15, 'username': session['user'], 'xp': 1200, 'avatar_color': '58cc02'}
    return render_template('leaderboard.html', page_name='leaderboard', leaderboard=leaderboard_data, my_rank=current_user_rank)

# --- KHỞI ĐỘNG ---
if __name__ == '__main__':
    with app.app_context():
        # Tạo bảng nếu chưa có
        db.create_all()
        print(">>> Database đã sẵn sàng!")
    app.run(debug=True)