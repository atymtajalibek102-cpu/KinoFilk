from flask import Flask, render_template, request, redirect, session, url_for, jsonify, Response, stream_with_context, abort, flash
from flask_caching import Cache
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import urljoin, urlparse, quote
import sqlite3, os, re, requests, math, secrets, time, random, string, logging, traceback
import urllib.request, urllib.parse, json
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

# ── Логирование ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('kinoflik.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger('kinoflik')

# ── Rate Limiting ────────────────────────────────────────────────
_login_attempts: dict = defaultdict(list)
MAX_ATTEMPTS  = 10
BLOCK_SECONDS = 300

def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < BLOCK_SECONDS]
    return len(_login_attempts[ip]) >= MAX_ATTEMPTS

def _record_attempt(ip: str):
    _login_attempts[ip].append(time.time())
# ================================================================
# EMAIL УВЕДОМЛЕНИЯ
# ================================================================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST     = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER     = os.environ.get('SMTP_USER', '')      # ваш gmail
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')  # пароль приложения
SMTP_FROM     = os.environ.get('SMTP_FROM', 'KinoFlik <noreply@kinoflik.kz>')

def send_email(to: str, subject: str, html: str) -> bool:
    """Отправляет HTML-письмо. Возвращает True при успехе."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP не настроен — письмо не отправлено")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = SMTP_FROM
        msg['To']      = to
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email error to {to}: {e}")
        return False

def _email_welcome(name: str, email: str, uid: int):
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#111;color:#fff;border-radius:12px;padding:32px">
      <h1 style="color:#800000;margin-top:0">🎬 Добро пожаловать в KinoFlik!</h1>
      <p>Привет, <b>{name}</b>!</p>
      <p>Твой аккаунт успешно создан.</p>
      <table style="background:#1a1a1a;border-radius:8px;padding:16px;width:100%">
        <tr><td style="color:#888">ID</td><td><b>{uid}</b></td></tr>
        <tr><td style="color:#888">Email</td><td>{email}</td></tr>
      </table>
      <p style="margin-top:24px">
        <a href="http://localhost:7777" style="background:#800000;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">Перейти на сайт</a>
      </p>
      <p style="color:#555;font-size:12px;margin-top:24px">Если вы не регистрировались — просто проигнорируйте это письмо.</p>
    </div>"""
    send_email(email, "Добро пожаловать в KinoFlik! 🎬", html)

def _email_password_reset(name: str, email: str, token: str):
    link = f"http://localhost:7777/reset-password/{token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#111;color:#fff;border-radius:12px;padding:32px">
      <h1 style="color:#800000;margin-top:0">🔑 Сброс пароля</h1>
      <p>Привет, <b>{name}</b>!</p>
      <p>Получен запрос на сброс пароля. Ссылка действительна <b>30 минут</b>.</p>
      <p style="margin:24px 0">
        <a href="{link}" style="background:#800000;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">Сбросить пароль</a>
      </p>
      <p style="color:#555;font-size:12px">Если вы не запрашивали сброс — проигнорируйте письмо. Пароль останется прежним.</p>
    </div>"""
    send_email(email, "Сброс пароля KinoFlik 🔑", html)

def _email_new_friend(user_name: str, user_email: str, friend_name: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#111;color:#fff;border-radius:12px;padding:32px">
      <h1 style="color:#800000;margin-top:0">👥 Новый друг!</h1>
      <p>Привет, <b>{user_name}</b>!</p>
      <p><b>{friend_name}</b> добавил(а) тебя в друзья на KinoFlik.</p>
      <p style="margin:24px 0">
        <a href="http://localhost:7777/profile" style="background:#800000;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">Посмотреть профиль</a>
      </p>
    </div>"""
    send_email(user_email, f"{friend_name} добавил(а) тебя в друзья 👥", html)


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kinoflik-dev-secret-2025')
app.config["SESSION_PERMANENT"]          = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["ALLOWED_EXTENSIONS"]         = {"png", "jpg", "jpeg", "webp", "gif"}
app.config["VIDEO_EXTENSIONS"]           = {"mp4", "mkv", "avi", "mov", "webm", "m3u8"}
app.config["MAX_CONTENT_LENGTH"]         = 4 * 1024 * 1024 * 1024
app.config['CACHE_TYPE']                 = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT']      = 300
cache = Cache(app)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "database.db")
os.makedirs(os.path.join(basedir, "static", "posters"), exist_ok=True)
os.makedirs(os.path.join(basedir, "static", "videos"),  exist_ok=True)
app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "static", "posters")


# ================================================================
# TEMPLATE FILTERS
# ================================================================

@app.template_filter('enumerate')
def do_enumerate(iterable, start=0):
    return enumerate(iterable, start=start)

@app.template_filter('duration')
def format_duration(minutes):
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return minutes or '-'
    h, rem = divmod(m, 60)
    return (f'{h}ч {rem}м' if rem else f'{h}ч') if h else f'{m} мин'

@app.template_filter('is_new')
def is_new_movie(year):
    return int(year or 0) >= datetime.now().year - 1


# ================================================================
# DB
# ================================================================

def get_db():
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ================================================================
# 8-ЗНАЧНЫЙ ID ПОЛЬЗОВАТЕЛЯ
# ================================================================

def gen_user_id():
    """Генерирует уникальный 8-значный числовой ID пользователя"""
    conn = get_db()
    for _ in range(200):
        uid = random.randint(10_000_000, 99_999_999)
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone():
            conn.close()
            return uid
    conn.close()
    return random.randint(10_000_000, 99_999_999)


# ================================================================
# ADMIN HELPERS
# ================================================================

def _load_admin_ids():
    ids = set()
    for part in os.environ.get('ADMIN_IDS', '').split(','):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids

ADMIN_IDS = _load_admin_ids()

def is_admin():
    uid = session.get('user_id')
    if not uid:
        return False
    if uid in ADMIN_IDS:
        return True
    conn = get_db()
    user = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return bool(user and user['role'] == 'admin')

@app.context_processor
def inject_globals():
    return dict(is_admin=is_admin(), current_user_id=session.get('user_id'))


# ================================================================
# HELPERS
# ================================================================

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def save_poster(file):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None

def save_video(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in app.config["VIDEO_EXTENSIONS"]:
        return None
    filename = secure_filename(file.filename)
    dest     = os.path.join(basedir, "static", "videos", filename)
    if os.path.exists(dest):
        import uuid
        filename = uuid.uuid4().hex[:8] + "_" + filename
        dest     = os.path.join(basedir, "static", "videos", filename)
    file.save(dest)
    return "/static/videos/" + filename

def generate_friend_code():
    conn = get_db()
    while True:
        code = "KINO-" + "".join(random.choices(string.digits + "ABCDEFGHJKLMNPQRSTUVWXYZ", k=4))
        if not conn.execute("SELECT 1 FROM users WHERE friend_code=?", (code,)).fetchone():
            conn.close()
            return code

ANIME_KEYWORDS = {'аниме','anime','хентай','hentai'}
ADULT_KEYWORDS = {'porn','порно','xxx','эротика','эротик','adult','sex ','18+','hentai','хентай'}

def is_indian_cinema(lang):
    return False  # language blocking removed — all languages allowed

def is_blocked_content(lang, genre_str='', title='', age_rating='', genre_ids=None):
    """Block only adult/anime content. Language is NOT a filter criterion."""
    g = (genre_str or '').lower()
    t = (title or '').lower()
    a = (age_rating or '').lower()
    if any(k in g or k in t for k in ADULT_KEYWORDS):
        return True
    if '18' in a:
        return True
    if any(k in g for k in ANIME_KEYWORDS):
        return True
    return False

def filter_safe_content(movies):
    """Remove anime and 18+ content. Languages are never blocked."""
    blocked_genres  = {'аниме', 'anime', 'хентай', 'hentai'}
    blocked_ratings = {'18+', '18'}
    result = []
    for m in movies:
        ar = str(m.get('age_rating') or '').strip()
        if ar in blocked_ratings:
            continue
        genre_low = str(m.get('genre') or '').lower()
        if any(bg in genre_low for bg in blocked_genres):
            continue
        if is_blocked_content('', m.get('genre', ''), m.get('title', ''), ar):
            continue
        result.append(m)
    return result

def clean_none(obj):
    """Recursively replace None values with empty string/zero for safe JSON serialization."""
    if isinstance(obj, dict):
        return {k: clean_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_none(i) for i in obj]
    return obj if obj is not None else ''

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def _set_session(user: dict, remember=True):
    session.permanent     = remember
    session['user_id']    = user['id']
    session['user_name']  = user['name']
    session['user']       = user['name']
    session['user_role']  = user.get('role') or 'user'
    session['avatar_url'] = user.get('profile_pic')


# ================================================================
# INIT DB  — users.id без AUTOINCREMENT (вставляем сами 8-значный)
# ================================================================

def init_db():
    conn = sqlite3.connect(db_path)
    c    = conn.cursor()

    # --- ПОЛЬЗОВАТЕЛИ (id без AUTOINCREMENT — вставляем сами) ---
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_banned INTEGER DEFAULT 0,
        card_mask TEXT DEFAULT NULL,
        friend_code TEXT,
        profile_pic TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        original_title TEXT,
        description TEXT,
        rating REAL DEFAULT 0,
        poster TEXT,
        year INTEGER,
        duration TEXT,
        genre TEXT,
        age_rating TEXT DEFAULT "16+",
        video_url TEXT,
        trailer_url TEXT,
        original_language TEXT DEFAULT 'en',
        tmdb_id INTEGER UNIQUE,
        countries TEXT,
        budget INTEGER,
        box_office INTEGER,
        slogan TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        original_title TEXT,
        description TEXT,
        rating REAL DEFAULT 0,
        poster TEXT,
        year INTEGER,
        seasons INTEGER DEFAULT 1,
        genre TEXT,
        status TEXT DEFAULT "ongoing",
        trailer_url TEXT,
        original_language TEXT DEFAULT 'en',
        tmdb_id INTEGER UNIQUE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER NOT NULL,
        season INTEGER DEFAULT 1,
        ep_num INTEGER,
        title TEXT,
        video_url TEXT,
        FOREIGN KEY (series_id) REFERENCES series(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS trailers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        trailer_url TEXT,
        poster TEXT,
        trailer_type TEXT DEFAULT "movie",
        created_at TEXT DEFAULT (date('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        UNIQUE(user_id, movie_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 10),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, movie_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS movie_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        image TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tv_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        logo_color TEXT,
        stream_url TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        item_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        duration_days INTEGER NOT NULL,
        description TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        start_date TEXT DEFAULT (date('now')),
        end_date TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS watch_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        progress INTEGER DEFAULT 0,
        watched_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, movie_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS watch_later (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, movie_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS friends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, friend_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS comment_likes (
        user_id INTEGER NOT NULL,
        comment_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, comment_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS follows (
        follower_id INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (follower_id, following_id)
    )''')

    # --- ЛИЧНЫЕ СООБЩЕНИЯ ---
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        group_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- ГРУППОВЫЕ ЧАТЫ (НОВОЕ) ---
    c.execute('''CREATE TABLE IF NOT EXISTS chat_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        avatar TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_group_members (
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member',
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (group_id, user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES chat_groups(id),
        FOREIGN KEY (sender_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_en TEXT,
        photo TEXT,
        birth_date TEXT,
        birth_place TEXT,
        biography TEXT,
        profession TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS movie_persons (
        movie_id INTEGER NOT NULL,
        person_id INTEGER NOT NULL,
        role TEXT,
        character_name TEXT,
        PRIMARY KEY (movie_id, person_id, role)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        is_public INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS collection_items (
        collection_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (collection_id, movie_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT DEFAULT 'neutral',
        likes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS compilations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        cover_image TEXT,
        is_featured INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- СБРОС ПАРОЛЯ ---
    c.execute('''CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- ИСТОРИЯ ПОИСКА ---
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute("INSERT OR IGNORE INTO plans (id,name,price,duration_days,description) VALUES (1,'Premium Месяц',555,30,'Доступ ко всем фильмам в 4K, без рекламы')")
    c.execute("INSERT OR IGNORE INTO plans (id,name,price,duration_days,description) VALUES (2,'Premium Год',5000,365,'Выгода 20%. Все преимущества Premium на целый год')")

    # Безопасное добавление колонок
    for table, col, definition in [
        ('users',    'profile_pic',        'TEXT'),
        ('users',    'friend_code',        'TEXT'),
        ('movies',   'original_language',  "TEXT DEFAULT 'en'"),
        ('movies',   'tmdb_id',            'INTEGER'),
        ('movies',   'countries',          'TEXT'),
        ('movies',   'budget',             'INTEGER'),
        ('movies',   'box_office',         'INTEGER'),
        ('movies',   'slogan',             'TEXT'),
        ('series',   'original_language',  "TEXT DEFAULT 'en'"),
        ('series',   'tmdb_id',            'INTEGER'),
        ('messages', 'group_id',           'INTEGER'),
    ]:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass

    # friend_code тем у кого нет
    for u in conn.execute("SELECT id FROM users WHERE friend_code IS NULL").fetchall():
        while True:
            code = "KINO-" + "".join(random.choices(string.digits + "ABCDEFGHJKLMNPQRSTUVWXYZ", k=4))
            if not conn.execute("SELECT 1 FROM users WHERE friend_code=?", (code,)).fetchone():
                conn.execute("UPDATE users SET friend_code=? WHERE id=?", (code, u["id"]))
                break

    c.execute("CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_series_rating ON series(rating DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON watch_history(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_group_messages ON group_messages(group_id)")

    conn.commit()
    conn.close()


# ================================================================
# BEFORE REQUEST
# ================================================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options']        = 'SAMEORIGIN'
    response.headers['X-XSS-Protection']       = '1; mode=block'
    response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    return response

@app.before_request
def block_banned_content():
    if request.endpoint in ['movie_page', 'watch_movie', 'watch_series', 'series_detail']:
        cont_id = request.view_args.get('id') if request.view_args else None
        if cont_id:
            conn  = get_db()
            table = 'movies' if 'movie' in (request.endpoint or '') else 'series'
            try:
                item = conn.execute(f"SELECT * FROM {table} WHERE id=?", (cont_id,)).fetchone()
            except Exception:
                item = None
            finally:
                conn.close()
            if item:
                d     = dict(item)
                genre = (d.get('genre') or '').lower()
                age   = str(d.get('age_rating', '')).lower()
                if any(b in genre for b in ['аниме','anime','эротика','порно']) or '18+' in age:
                    abort(403)


# ================================================================
# TMDB
# ================================================================

def get_tmdb_trailer(tmdb_id, is_series=False):
    try:
        endpoint = f"https://api.themoviedb.org/3/{'tv' if is_series else 'movie'}/{tmdb_id}/videos"
        r = requests.get(endpoint, params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru'}, timeout=5)
        for v in r.json().get('results', []):
            if v['site'] == 'YouTube' and v['type'] == 'Trailer':
                return f"https://www.youtube.com/embed/{v['key']}"
    except Exception:
        pass
    return None

def get_tmdb_info(title, is_series=False):
    try:
        url = f'https://api.themoviedb.org/3/search/multi?api_key=15d2ea6d0dc1d476efbca3eba2b9bbfb&language=ru-RU&query={urllib.parse.quote(title)}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            for item in data.get('results', []):
                if is_series and item.get('media_type') == 'tv':
                    return item['id'], 'tv'
                elif not is_series and item.get('media_type') == 'movie':
                    return item['id'], 'movie'
            if data.get('results'):
                return data['results'][0]['id'], data['results'][0].get('media_type', 'movie')
    except Exception:
        pass
    return None, None


# ================================================================
# OAUTH
# ================================================================

try:
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    oauth.register('google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'})
    oauth.register('vk',
        client_id=os.environ.get('VK_CLIENT_ID', ''),
        client_secret=os.environ.get('VK_CLIENT_SECRET', ''),
        access_token_url='https://oauth.vk.com/access_token',
        authorize_url='https://oauth.vk.com/authorize',
        api_base_url='https://api.vk.com/method/',
        client_kwargs={'scope': 'email', 'v': '5.131'})
except ImportError:
    oauth = None

def _oauth_get_or_create(email, name, profile_pic=None):
    if not email:
        return None
    conn = get_db()
    row  = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row:
        user = dict(row)
        if profile_pic and not user.get('profile_pic'):
            conn.execute("UPDATE users SET profile_pic=? WHERE id=?", (profile_pic, user['id']))
            conn.commit()
            user['profile_pic'] = profile_pic
    else:
        uid  = gen_user_id()
        code = generate_friend_code()
        pw   = generate_password_hash(secrets.token_hex(16))
        conn.execute(
            "INSERT INTO users (id,name,email,password,profile_pic,friend_code,role) VALUES (?,?,?,?,?,?,?)",
            (uid, name, email, pw, profile_pic, code, 'user'))
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    conn.close()
    return user

@app.route('/login/google')
def google_login():
    if not oauth: flash("Google OAuth не настроен.", "error"); return redirect('/login')
    return oauth.google.authorize_redirect(url_for('google_authorize', _external=True))

@app.route('/login/google/callback')
def google_authorize():
    try:
        token = oauth.google.authorize_access_token()
        info  = token.get('userinfo') or oauth.google.userinfo()
        user  = _oauth_get_or_create(info.get('email'), info.get('name') or 'User', info.get('picture'))
        if not user or user.get('is_banned'):
            flash("Ошибка авторизации.", "error"); return redirect('/login')
        _set_session(user); return redirect('/')
    except Exception as e:
        flash(f"Ошибка Google: {e}", "error"); return redirect('/login')

@app.route('/login/vk')
def vk_login():
    if not oauth: flash("VK OAuth не настроен.", "error"); return redirect('/login')
    return oauth.vk.authorize_redirect(url_for('vk_authorize', _external=True))

@app.route('/login/vk/callback')
def vk_authorize():
    try:
        token   = oauth.vk.authorize_access_token()
        resp    = oauth.vk.get('users.get', params={'user_ids': token.get('user_id'), 'fields': 'photo_100,first_name,last_name', 'access_token': token.get('access_token')})
        vu      = resp.json()['response'][0]
        name    = f"{vu.get('first_name','')} {vu.get('last_name','')}".strip()
        user    = _oauth_get_or_create(token.get('email'), name, vu.get('photo_100'))
        if not user or user.get('is_banned'):
            flash("Ошибка авторизации.", "error"); return redirect('/login')
        _set_session(user); return redirect('/')
    except Exception as e:
        flash(f"Ошибка VK: {e}", "error"); return redirect('/login')


# ================================================================
# АВТОРИЗАЦИЯ
# ================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect('/')
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        def err(msg):
            return render_template("login.html", error=msg, active_tab='login', prefill_email=email)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
        if _is_rate_limited(ip):
            logger.warning(f"Brute-force blocked: {ip}")
            return err("Слишком много попыток. Подождите 5 минут.")
        if not email or not password:
            return err("Введите email и пароль")
        conn = get_db()
        row  = conn.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
        conn.close()
        user = dict(row) if row else None
        if not user or not check_password_hash(user["password"], password):
            _record_attempt(ip)
            logger.info(f"Failed login: {email} from {ip}")
            return err("Неверный email или пароль")
        if user.get("is_banned"): return err("Аккаунт заблокирован")
        logger.info(f"Login: user_id={user['id']} from {ip}")
        _set_session(user, remember)
        return redirect("/")
    return render_template("login.html", active_tab='login')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        def err(msg):
            return render_template("login.html", error=msg, active_tab='register', prefill_name=name, prefill_email=email)
        email = email.lower()
        if not name or not email or not password: return err("Заполните все поля")
        if len(name) < 2:       return err("Имя минимум 2 символа")
        if len(name) > 50:      return err("Имя максимум 50 символов")
        if len(password) < 6:   return err("Пароль минимум 6 символов")
        if len(password) > 128: return err("Пароль слишком длинный")
        if "@" not in email or "." not in email.split("@")[-1]:
            return err("Некорректный email")
        conn = get_db()
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            conn.close(); return err("Email уже зарегистрирован")
        uid  = gen_user_id()   # ← 8-значный ID
        code = generate_friend_code()
        conn.execute(
            "INSERT INTO users (id,name,email,password,friend_code,role) VALUES (?,?,?,?,?,?)",
            (uid, name, email, generate_password_hash(password), code, 'user'))
        conn.commit(); conn.close()
        # Отправляем приветственное письмо в фоне (не блокируем ответ)
        import threading
        threading.Thread(target=_email_welcome, args=(name, email, uid), daemon=True).start()
        return render_template("login.html", success=f"Аккаунт создан! Ваш ID: {uid}. Войдите.",
                               active_tab='login', prefill_email=email)
    return render_template("login.html", active_tab='register')

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================================================================
# СБРОС ПАРОЛЯ ПО EMAIL
# ================================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        if not email:
            return render_template('login.html', error='Введите email', active_tab='forgot')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user:
            user = dict(user)
            token = secrets.token_urlsafe(32)
            expires = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute("DELETE FROM password_resets WHERE user_id=?", (user['id'],))
            conn.execute("INSERT INTO password_resets (user_id,token,expires_at) VALUES (?,?,?)",
                         (user['id'], token, expires))
            conn.commit()
            import threading
            threading.Thread(target=_email_password_reset, args=(user['name'], email, token), daemon=True).start()
            logger.info(f"Password reset requested for user_id={user['id']}")
        conn.close()
        # Всегда показываем одинаковый ответ (не раскрываем существование email)
        return render_template('login.html', active_tab='forgot',
                               success='Если email зарегистрирован — письмо отправлено.')
    return render_template('login.html', active_tab='forgot')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db()
    row  = conn.execute(
        "SELECT pr.*, u.name, u.email FROM password_resets pr JOIN users u ON pr.user_id=u.id WHERE pr.token=? AND pr.used=0",
        (token,)).fetchone()

    if not row:
        conn.close()
        return render_template('login.html', error='Ссылка недействительна или уже использована.', active_tab='login')

    if datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S') < datetime.now():
        conn.close()
        return render_template('login.html', error='Ссылка истекла. Запросите новую.', active_tab='forgot')

    if request.method == 'POST':
        new_pw  = request.form.get('password', '')
        new_pw2 = request.form.get('password2', '')
        if len(new_pw) < 6:
            return render_template('reset_password.html', token=token, error='Минимум 6 символов')
        if new_pw != new_pw2:
            return render_template('reset_password.html', token=token, error='Пароли не совпадают')
        conn.execute("UPDATE users SET password=? WHERE id=?",
                     (generate_password_hash(new_pw), row['user_id']))
        conn.execute("UPDATE password_resets SET used=1 WHERE token=?", (token,))
        conn.commit(); conn.close()
        logger.info(f"Password reset completed for user_id={row['user_id']}")
        return render_template('login.html', success='Пароль изменён! Войдите.', active_tab='login')

    conn.close()
    return render_template('reset_password.html', token=token, error=None)


# ================================================================
# ГЛАВНАЯ
# ================================================================

@app.route("/")
def index():
    page     = request.args.get('page', 1, type=int)
    per_page = 12
    conn     = get_db()
    total    = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    total_pages = math.ceil(total / per_page) if total else 1
    _safe_movies_sql = """
        age_rating NOT IN ('18+', '18')
        AND genre NOT LIKE '%аниме%'
        AND genre NOT LIKE '%anime%'
        AND genre NOT LIKE '%хентай%'
        AND genre NOT LIKE '%hentai%'
        AND poster IS NOT NULL AND poster != ''
    """
    _safe_series_sql = """
        genre NOT LIKE '%аниме%'
        AND genre NOT LIKE '%anime%'
        AND genre NOT LIKE '%хентай%'
        AND genre NOT LIKE '%hentai%'
        AND poster IS NOT NULL AND poster != ''
    """
    movies = filter_safe_content([dict(m) for m in conn.execute(
        f"SELECT * FROM movies WHERE rating > 6 AND {_safe_movies_sql} ORDER BY RANDOM() LIMIT 80"
    ).fetchall()])[:per_page]
    series = filter_safe_content([dict(s) for s in conn.execute(
        f"SELECT * FROM series WHERE {_safe_series_sql} ORDER BY id DESC LIMIT 12"
    ).fetchall()])
    top_movies = filter_safe_content([dict(m) for m in conn.execute(
        f"SELECT * FROM movies WHERE rating >= 8 AND {_safe_movies_sql} ORDER BY rating DESC LIMIT 30"
    ).fetchall()])[:6]
    continue_movies = []
    if session.get('user_id'):
        continue_movies = filter_safe_content([dict(r) for r in conn.execute("""
            SELECT m.*, wh.progress, wh.watched_at FROM movies m
            JOIN watch_history wh ON m.id=wh.movie_id
            WHERE wh.user_id=? AND m.poster IS NOT NULL AND m.poster != ''
            ORDER BY wh.watched_at DESC LIMIT 20
        """, (session['user_id'],)).fetchall()])[:12]
    genres = []
    for row in conn.execute("SELECT DISTINCT genre FROM movies WHERE genre IS NOT NULL").fetchall():
        for g in (row['genre'] or '').split(','):
            g = g.strip()
            if g and g not in genres: genres.append(g)
    conn.close()
    # hero_data для слайдера на главной
    hero_data = [
        {
            'id':          m['id'],
            'tmdb_id':     m.get('tmdb_id') or '',
            'title':       m.get('title') or '',
            'description': (m.get('description') or '')[:200],
            'poster_url':  ('/static/posters/' + m['poster']) if (m.get('poster') and not m['poster'].startswith('http')) else (m.get('poster') or ''),
            'year':        str(m.get('year') or ''),
            'rating':      str(m.get('rating') or ''),
            'genre':       (m.get('genre') or '').split(',')[0].strip(),
        }
        for m in top_movies
    ]
    return render_template("index.html", movies=movies, series=series, top_movies=top_movies,
                           continue_movies=continue_movies, genres=genres[:12],
                           page=page, total_pages=total_pages, hero_data=hero_data)


# ================================================================
# AJAX
# ================================================================

@app.route('/ajax/load')
def ajax_load():
    page     = request.args.get('page', 1, type=int)
    per_page = 12
    offset   = (page - 1) * per_page
    conn     = get_db()
    rows     = conn.execute(
        """SELECT id,title,poster,rating,year,genre,duration,age_rating,original_language FROM movies
           WHERE age_rating NOT IN ('18+','18')
             AND genre NOT LIKE '%аниме%' AND genre NOT LIKE '%anime%'
           ORDER BY id DESC LIMIT ? OFFSET ?""",
        (per_page * 3, offset)).fetchall()
    movies   = filter_safe_content([dict(m) for m in rows])[:per_page]
    conn.close()
    return jsonify(movies)

@app.route('/ajax/search')
def ajax_search_new():
    q = request.args.get('q', '').strip()
    if len(q) < 2: return jsonify([])
    conn   = get_db()
    movies = filter_safe_content([dict(m) for m in conn.execute(
        """SELECT id,title,original_title,poster,rating,year,genre,age_rating,original_language FROM movies
           WHERE (title LIKE ? OR original_title LIKE ?)
             AND age_rating NOT IN ('18+','18')
             AND genre NOT LIKE '%аниме%' AND genre NOT LIKE '%anime%'
           LIMIT 16""",
        (f'%{q}%', f'%{q}%')).fetchall()])[:8]
    series = filter_safe_content([dict(s) for s in conn.execute(
        """SELECT id,title,poster,rating,year,genre,age_rating,'series' as content_type FROM series
           WHERE (title LIKE ? OR original_title LIKE ?)
             AND age_rating NOT IN ('18+','18')
             AND genre NOT LIKE '%аниме%' AND genre NOT LIKE '%anime%'
           ORDER BY rating DESC LIMIT 4""",
        (f'%{q}%', f'%{q}%')).fetchall()])
    for m in movies: m.setdefault('content_type', 'movie')
    conn.close()
    return jsonify(movies + series)

@app.route('/ajax/favorite', methods=['POST'])
def ajax_favorite_new():
    if not session.get('user_id'): return jsonify({'status': 'error'}), 401
    data     = request.get_json(silent=True) or {}
    movie_id = data.get('movie_id')
    uid      = session['user_id']
    conn     = get_db()
    if conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (uid, movie_id)).fetchone():
        conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (uid, movie_id))
        conn.commit(); conn.close(); return jsonify({'status': 'removed'})
    conn.execute("INSERT OR IGNORE INTO favorites (user_id,movie_id) VALUES (?,?)", (uid, movie_id))
    conn.commit(); conn.close()
    return jsonify({'status': 'added'})

@app.route('/ajax/watch_later', methods=['POST'])
def ajax_watch_later_new():
    if not session.get('user_id'): return jsonify({'status': 'error'}), 401
    data     = request.get_json(silent=True) or {}
    movie_id = data.get('movie_id')
    uid      = session['user_id']
    conn     = get_db()
    if conn.execute("SELECT 1 FROM watch_later WHERE user_id=? AND movie_id=?", (uid, movie_id)).fetchone():
        conn.execute("DELETE FROM watch_later WHERE user_id=? AND movie_id=?", (uid, movie_id))
        conn.commit(); conn.close(); return jsonify({'status': 'removed'})
    conn.execute("INSERT OR IGNORE INTO watch_later (user_id,movie_id) VALUES (?,?)", (uid, movie_id))
    conn.commit(); conn.close()
    return jsonify({'status': 'added'})


# ================================================================
# ПОИСК / КАТАЛОГ
# ================================================================

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q: return redirect(url_for('movie_list'))
    conn = get_db()
    if session.get('user_id') and len(q) >= 2:
        last = conn.execute("SELECT query FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 1", (session['user_id'],)).fetchone()
        if not last or last['query'] != q:
            conn.execute("INSERT INTO search_history (user_id,query) VALUES (?,?)", (session['user_id'], q))
            conn.execute("DELETE FROM search_history WHERE user_id=? AND id NOT IN (SELECT id FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 20)", (session['user_id'], session['user_id']))
            conn.commit()
    movies = [dict(m) for m in conn.execute(
        "SELECT * FROM movies WHERE title LIKE ? OR original_title LIKE ? OR description LIKE ? ORDER BY rating DESC LIMIT 100",
        (f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()]
    series = [dict(s) for s in conn.execute(
        "SELECT * FROM series WHERE title LIKE ? OR original_title LIKE ? ORDER BY rating DESC LIMIT 50",
        (f'%{q}%', f'%{q}%')).fetchall()]
    conn.close()
    return render_template('search.html', movies=movies, series=series, query=q)

@app.route('/api/search/history')
@login_required
def search_history_api():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT query FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 10", (session['user_id'],)).fetchall()
    conn.close()
    return jsonify([r['query'] for r in rows])

@app.route('/api/search/history/clear', methods=['POST'])
@login_required
def clear_search_history():
    conn = get_db()
    conn.execute("DELETE FROM search_history WHERE user_id=?", (session['user_id'],))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/movie')
def movie_list():
    genre = request.args.get('genre', '')
    sort  = request.args.get('sort', 'new')
    order = {'new':'id DESC','rating':'rating DESC','year':'year DESC','title':'title ASC'}.get(sort, 'id DESC')
    conn  = get_db()
    base_where = """age_rating NOT IN ('18+','18')
        AND genre NOT LIKE '%аниме%' AND genre NOT LIKE '%anime%'
        AND genre NOT LIKE '%хентай%' AND genre NOT LIKE '%hentai%'
        AND age_rating NOT IN ('18+','18')"""
    if genre:
        rows = conn.execute(
            f"SELECT * FROM movies WHERE genre LIKE ? AND {base_where} ORDER BY {order}",
            (f'%{genre}%',)).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM movies WHERE {base_where} ORDER BY {order}").fetchall()
    conn.close()
    result = filter_safe_content([dict(m) for m in rows])
    return render_template('movie.html', movies=result, genre=genre, sort=sort)

@app.route("/radio")
@login_required
def radio_page():
    return render_template("radio.html")


# ================================================================
# ФИЛЬМЫ
# ================================================================

@app.route('/movie/<int:id>')
def movie_page(id):
    conn  = get_db()
    movie = conn.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
    if not movie: conn.close(); abort(404)
    movie = dict(movie)
    if not movie.get('tmdb_id') and movie.get('title'):
        tid, _ = get_tmdb_info(movie['title'])
        if tid: movie['tmdb_id'] = tid
    if movie.get('tmdb_id') and not movie.get('trailer_url'):
        t = get_tmdb_trailer(movie['tmdb_id'])
        if t: movie['trailer_url'] = t
    similar = conn.execute(
        "SELECT * FROM movies WHERE id!=? AND genre LIKE ? ORDER BY rating DESC LIMIT 8",
        (id, f'%{movie.get("genre","")}%')).fetchall()
    if not similar:
        similar = conn.execute("SELECT * FROM movies WHERE id!=? ORDER BY rating DESC LIMIT 8", (id,)).fetchall()
    images = conn.execute("SELECT * FROM movie_images WHERE movie_id=?", (id,)).fetchall()
    conn.close()
    return render_template('movie_detail.html', movie=movie,
                           similar_movies=[dict(m) for m in similar],
                           images=[dict(i) for i in images],
                           trailer_url=movie.get('trailer_url'))

@app.route('/watch/<int:id>')
def watch_movie(id):
    conn  = get_db()
    movie = conn.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
    conn.close()
    if not movie: return render_template('404.html'), 404
    tmdb_id, _ = get_tmdb_info(movie['title'])
    poster = ''
    if movie['poster']:
        poster = movie['poster'] if str(movie['poster']).startswith('http') else f"/static/posters/{movie['poster']}"
    movie = clean_none(dict(movie))
    return render_template('watch.html', title=movie.get('title') or '',
                           tmdb_id=tmdb_id or 0, is_series=False, season=1, episode=1,
                           movie_id=movie['id'], poster=poster, video_url=movie.get('video_url', ''))


@app.route('/watch/series/<int:id>/<int:ep_id>')
def watch_series(id, ep_id):
    conn   = get_db()
    ep_row = conn.execute("SELECT * FROM episodes WHERE id=?", (ep_id,)).fetchone()
    serial = conn.execute("SELECT title FROM series WHERE id=?", (id,)).fetchone()
    conn.close()
    if not ep_row: return render_template('404.html'), 404
    ep = clean_none(dict(ep_row))
    series_title = (serial['title'] if serial else None) or ep.get('title') or 'Сериал'
    tmdb_id, _   = get_tmdb_info(series_title, is_series=True)
    season  = ep.get('season')  or 1
    ep_num  = ep.get('ep_num')  or 1
    return render_template('watch.html',
                           title=f"{series_title} — Сезон {season}, Серия {ep_num}",
                           tmdb_id=tmdb_id or 0, is_series=True,
                           season=season, episode=ep_num, movie_id=0,
                           poster='', video_url=ep.get('video_url', ''))



# ================================================================
# ПРЯМЫЕ РОУТЫ ПО TMDB ID (для главной страницы)
# ================================================================

@app.route('/watch/tmdb/<int:tmdb_id>')
def watch_tmdb(tmdb_id):
    """Смотреть фильм напрямую по TMDB ID"""
    conn  = get_db()
    movie = conn.execute("SELECT title,poster FROM movies WHERE tmdb_id=?", (tmdb_id,)).fetchone()
    conn.close()
    title  = movie['title'] if movie else 'Фильм'
    poster = ''
    if movie and movie['poster']:
        poster = movie['poster'] if movie['poster'].startswith('http') else f"/static/posters/{movie['poster']}"
    return render_template('watch.html', title=title, tmdb_id=tmdb_id, is_series=False,
                           season=1, episode=1, movie_id=0, poster=poster,
                           video_url=movie.get('video_url', '') if movie else '')


@app.route('/watch/tv/<int:tmdb_id>')
def watch_tv(tmdb_id):
    """Смотреть сериал напрямую по TMDB ID"""
    season  = request.args.get('season', 1, type=int)
    episode = request.args.get('ep', 1, type=int)
    conn    = get_db()
    serial  = conn.execute("SELECT title,poster FROM series WHERE tmdb_id=?", (tmdb_id,)).fetchone()
    conn.close()
    title  = serial['title'] if serial else 'Сериал'
    poster = ''
    if serial and serial['poster']:
        poster = serial['poster'] if serial['poster'].startswith('http') else f"/static/posters/{serial['poster']}"
    return render_template('watch.html',
                           title=f"{title} — Сезон {season}, Серия {episode}",
                           tmdb_id=tmdb_id, is_series=True,
                           season=season, episode=episode, movie_id=0, poster=poster, video_url='')


@app.route('/movie/tmdb/<int:tmdb_id>')
def movie_tmdb(tmdb_id):
    """Страница фильма по TMDB ID"""
    conn  = get_db()
    movie = conn.execute("SELECT * FROM movies WHERE tmdb_id=?", (tmdb_id,)).fetchone()
    if movie:
        conn.close(); return redirect(f'/movie/{movie["id"]}')
    conn.close()
    try:
        r = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru-RU'}, timeout=6)
        d = r.json()
        movie = {
            'id': 0, 'tmdb_id': tmdb_id,
            'title': d.get('title') or d.get('original_title', ''),
            'original_title': d.get('original_title', ''),
            'description': d.get('overview', ''),
            'rating': round(d.get('vote_average', 0), 1),
            'poster': f"https://image.tmdb.org/t/p/w500{d['poster_path']}" if d.get('poster_path') else None,
            'year': (d.get('release_date') or '')[:4],
            'genre': ', '.join(g['name'] for g in d.get('genres', [])[:3]),
            'duration': d.get('runtime'), 'age_rating': '16+', 'video_url': None,
            'trailer_url': get_tmdb_trailer(tmdb_id),
            'countries': ', '.join(c['name'] for c in d.get('production_countries', [])[:2]),
            'slogan': d.get('tagline', ''),
        }
    except Exception:
        abort(404)
    return render_template('movie_detail.html', movie=movie, similar_movies=[], images=[], trailer_url=movie.get('trailer_url'))

@app.route('/series/tmdb/<int:tmdb_id>')
def series_tmdb(tmdb_id):
    """Страница сериала по TMDB ID"""
    conn   = get_db()
    serial = conn.execute("SELECT * FROM series WHERE tmdb_id=?", (tmdb_id,)).fetchone()
    if serial:
        conn.close(); return redirect(f'/series/{serial["id"]}')
    conn.close()
    try:
        r = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}",
            params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru-RU'}, timeout=6)
        d = r.json()
        serial = {
            'id': 0, 'tmdb_id': tmdb_id,
            'title': d.get('name') or d.get('original_name', ''),
            'original_title': d.get('original_name', ''),
            'description': d.get('overview', ''),
            'rating': round(d.get('vote_average', 0), 1),
            'poster': f"https://image.tmdb.org/t/p/w500{d['poster_path']}" if d.get('poster_path') else None,
            'year': (d.get('first_air_date') or '')[:4],
            'genre': ', '.join(g['name'] for g in d.get('genres', [])[:3]),
            'seasons': d.get('number_of_seasons', 1),
            'status': d.get('status', ''), 'age_rating': '16+',
            'trailer_url': get_tmdb_trailer(tmdb_id, is_series=True),
        }
        seasons_data = {}
        for s in range(1, min(serial['seasons'] + 1, 6)):
            try:
                sr  = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{s}",
                    params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru-RU'}, timeout=5)
                eps = sr.json().get('episodes', [])
                seasons_data[s] = [{'id': e['id'], 'ep_num': e['episode_number'],
                    'title': e.get('name', f'Серия {e["episode_number"]}'), 'season': s} for e in eps]
            except Exception:
                pass
    except Exception:
        abort(404)
    return render_template('series_detail.html', serial=serial, episodes=[],
                           seasons_data=seasons_data, recommended=[], trailer_url=serial.get('trailer_url'))


# ================================================================
# СЕРИАЛЫ
# ================================================================

@app.route('/series')
def series_list():
    genre  = request.args.get('genre', '')
    sort   = request.args.get('sort', 'rating')
    q      = request.args.get('q', '').strip()
    order  = {'rating':'rating DESC','new':'id DESC','year':'year DESC','title':'title ASC'}.get(sort, 'rating DESC')
    conn   = get_db()

    # Строим запрос
    conditions = []
    params     = []
    if genre:
        conditions.append("genre LIKE ?"); params.append(f'%{genre}%')
    if q:
        conditions.append("(title LIKE ? OR original_title LIKE ? OR description LIKE ?)")
        params += [f'%{q}%', f'%{q}%', f'%{q}%']

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows  = conn.execute(f"SELECT * FROM series {where} ORDER BY {order}", params).fetchall()

    # Жанры для фильтра
    genres = []
    for row in conn.execute("SELECT DISTINCT genre FROM series WHERE genre IS NOT NULL").fetchall():
        for g in (row['genre'] or '').split(','):
            g = g.strip()
            if g and g not in genres: genres.append(g)

    # Сохраняем поиск в историю
    if q and session.get('user_id'):
        last = conn.execute("SELECT query FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 1", (session['user_id'],)).fetchone()
        if not last or last['query'] != q:
            conn.execute("INSERT INTO search_history (user_id,query) VALUES (?,?)", (session['user_id'], q))
            conn.commit()

    conn.close()
    return render_template('series.html', series=[dict(s) for s in rows],
                           genre=genre, sort=sort, query=q, genres=genres[:15])

@app.route('/series/<int:id>')
def series_detail(id):
    conn   = get_db()
    serial = conn.execute("SELECT * FROM series WHERE id=?", (id,)).fetchone()
    if not serial:
        conn.close()
        return render_template('series_detail.html',
            serial={'id':id,'title':'Загружается...','description':'','poster':None,'rating':8.5,'year':2024,'genre':'Сериал'},
            episodes=[], seasons_data={}, recommended=[], trailer_url=None)
    serial = dict(serial)
    if not serial.get('tmdb_id'):
        tid, _ = get_tmdb_info(serial['title'], is_series=True)
        if tid: serial['tmdb_id'] = tid
    if serial.get('tmdb_id') and not serial.get('trailer_url'):
        t = get_tmdb_trailer(serial['tmdb_id'], is_series=True)
        if t: serial['trailer_url'] = t
    episodes    = conn.execute("SELECT * FROM episodes WHERE series_id=? ORDER BY season,ep_num", (id,)).fetchall()
    recommended = conn.execute("SELECT * FROM series WHERE id!=? AND genre LIKE ? ORDER BY rating DESC LIMIT 8",
                               (id, f'%{serial.get("genre","")}%')).fetchall()
    if not recommended:
        recommended = conn.execute("SELECT * FROM series WHERE id!=? ORDER BY rating DESC LIMIT 8", (id,)).fetchall()
    conn.close()
    seasons_data = {}
    for ep in episodes:
        ep = dict(ep)
        seasons_data.setdefault(ep['season'], []).append(ep)
    return render_template('series_detail.html', serial=serial,
                           episodes=[dict(e) for e in episodes], seasons_data=seasons_data,
                           recommended=[dict(r) for r in recommended], trailer_url=serial.get('trailer_url'))


# ================================================================
# ТВ  — без лагов: используем прямой URL из js/tv.js
# чтобы не лагало, прокси используем ТОЛЬКО для ts-сегментов,
# а m3u8-манифест отдаём без перезаписи если уже полный URL
# ================================================================

@app.route('/tv')
def tv():
    return render_template('tv.html')


# ================================================================
# СПОРТ (ESPN API)
# ================================================================

_sport_cache = {'data': None, 'ts': 0}
CACHE_TTL    = 120

def fetch_espn_sport(sport, league):
    url = f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard'
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'}, timeout=8)
        if r.status_code == 200: return r.json()
    except Exception:
        pass
    return None

def parse_espn_events(data, sport_name, sport_key, icon):
    events = []
    if not data or 'events' not in data: return events
    for ev in data.get('events', [])[:12]:
        try:
            comp   = ev.get('competitions', [{}])[0]
            comps  = comp.get('competitors', [])
            status = ev.get('status', {})
            state  = status.get('type', {}).get('state', 'pre')
            home   = next((c for c in comps if c.get('homeAway') == 'home'), {})
            away   = next((c for c in comps if c.get('homeAway') == 'away'), {})
            try:
                dt         = datetime.fromisoformat(ev.get('date','').replace('Z','+00:00'))
                local_time = dt.strftime('%H:%M')
                local_date = dt.strftime('%d.%m')
            except Exception:
                local_time = '--:--'; local_date = ''
            events.append({
                'id':         ev.get('id',''),
                'name':       ev.get('name', home.get('team',{}).get('shortDisplayName','?') + ' vs ' + away.get('team',{}).get('shortDisplayName','?')),
                'home':       home.get('team',{}).get('shortDisplayName','?'),
                'away':       away.get('team',{}).get('shortDisplayName','?'),
                'home_logo':  home.get('team',{}).get('logo',''),
                'away_logo':  away.get('team',{}).get('logo',''),
                'score':      f"{home.get('score','')} : {away.get('score','')}" if home.get('score') else '',
                'state':      state,
                'time':       local_time,
                'date':       local_date,
                'detail':     status.get('type',{}).get('shortDetail',''),
                'sport':      sport_key,
                'sport_name': sport_name,
                'icon':       icon,
                'venue':      comp.get('venue',{}).get('fullName',''),
                'broadcast':  ', '.join([b.get('names',[''])[0] for b in comp.get('broadcasts',[])[:2]]),
            })
        except Exception:
            continue
    return events

def get_all_sport_events():
    now = time.time()
    if _sport_cache['data'] and (now - _sport_cache['ts']) < CACHE_TTL:
        return _sport_cache['data']
    leagues = [
        ('soccer',     'uefa.champions_league',   'Лига чемпионов', 'football',   '⚽'),
        ('soccer',     'uefa.europa_league',       'Лига Европы',    'football',   '⚽'),
        ('soccer',     'eng.1',                    'АПЛ',            'football',   '⚽'),
        ('soccer',     'esp.1',                    'Ла Лига',        'football',   '⚽'),
        ('soccer',     'ger.1',                    'Бундеслига',     'football',   '⚽'),
        ('soccer',     'ita.1',                    'Серия А',        'football',   '⚽'),
        ('soccer',     'kaz.1',                    'КПЛ Казахстан',  'football',   '⚽'),
        ('basketball', 'nba',                      'НБА',            'basketball', '🏀'),
        ('basketball', 'mens-college-basketball',  'NCAA',           'basketball', '🏀'),
        ('hockey',     'nhl',                      'НХЛ',            'hockey',     '🏒'),
        ('tennis',     'atp',                      'ATP',            'tennis',     '🎾'),
        ('mma',        'ufc',                      'UFC',            'mma',        '🥊'),
        ('baseball',   'mlb',                      'MLB',            'other',      '⚾'),
        ('football',   'nfl',                      'NFL',            'other',      '🏈'),
    ]
    all_events = []
    for args in leagues:
        data = fetch_espn_sport(args[0], args[1])
        all_events.extend(parse_espn_events(data, args[2], args[3], args[4]))
    _sport_cache['data'] = all_events
    _sport_cache['ts']   = now
    return all_events

@app.route('/sport')
def sport():
    return render_template('sport.html', is_admin=is_admin(), current_user_id=session.get('user_id'))

@app.route('/api/sport/events')
def api_sport_events():
    try:
        events = get_all_sport_events()
        return jsonify({'ok': True, 'events': events, 'count': len(events)})
    except Exception as e:
        return jsonify({'ok': False, 'events': [], 'error': str(e)})


# ================================================================
# ПОДПИСКИ
# ================================================================

@app.route('/subscriptions')
def subscriptions():
    conn  = get_db()
    plans = [dict(p) for p in conn.execute("SELECT * FROM plans ORDER BY price").fetchall()]
    current_sub = None
    if 'user_id' in session:
        row = conn.execute("""SELECT p.name,us.end_date FROM user_subscriptions us
            JOIN plans p ON us.plan_id=p.id WHERE us.user_id=? AND us.is_active=1
            AND us.end_date>=date('now') ORDER BY us.id DESC LIMIT 1""", (session['user_id'],)).fetchone()
        if row: current_sub = dict(row)
    conn.close()
    return render_template('subscriptions.html', plans=plans, current_sub=current_sub)

@app.route('/subscribe', methods=['POST'])
@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходима авторизация'})
    data    = request.get_json()
    plan_id = data.get('plan_id') if data else request.form.get('plan_id')
    conn    = get_db()
    plan    = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not plan: conn.close(); return jsonify({'success': False, 'message': 'План не найден'})
    plan = dict(plan)
    conn.execute("UPDATE user_subscriptions SET is_active=0 WHERE user_id=?", (session['user_id'],))
    conn.execute("INSERT INTO user_subscriptions (user_id,plan_id,start_date,end_date,is_active) VALUES (?,?,date('now'),date('now',?),1)",
                 (session['user_id'], plan_id, f'+{plan["duration_days"]} days'))
    if data and data.get('save_card') and data.get('card_mask'):
        conn.execute("UPDATE users SET card_mask=? WHERE id=?", (data['card_mask'], session['user_id']))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': f'Подписка "{plan["name"]}" оформлена!'})

@app.route('/card/remove', methods=['POST'])
@login_required
def remove_card():
    conn = get_db()
    conn.execute("UPDATE users SET card_mask=NULL WHERE id=?", (session['user_id'],))
    conn.commit(); conn.close()
    return jsonify({'success': True})


# ================================================================
# КОММЕНТАРИИ
# ================================================================

@app.route('/comments/<int:movie_id>')
def get_comments(movie_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT c.id,c.content,c.likes,c.created_at,c.parent_id,u.name as author,u.friend_code,
               (SELECT COUNT(*) FROM comment_likes cl WHERE cl.comment_id=c.id) as like_count,
               CASE WHEN ?>0 THEN (SELECT COUNT(*) FROM comment_likes cl2 WHERE cl2.comment_id=c.id AND cl2.user_id=?) ELSE 0 END as user_liked
        FROM comments c JOIN users u ON c.user_id=u.id WHERE c.movie_id=? ORDER BY c.created_at DESC
    """, (session.get('user_id',0), session.get('user_id',0), movie_id)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/comments/add', methods=['POST'])
@login_required
def add_comment():
    data    = request.get_json()
    content = (data.get('content') or '').strip()
    if not content: return jsonify({'success': False, 'message': 'Пустой комментарий'})
    if len(content) > 1000: return jsonify({'success': False, 'message': 'Максимум 1000 символов'})
    conn   = get_db()
    cursor = conn.execute("INSERT INTO comments (user_id,movie_id,content,parent_id) VALUES (?,?,?,?)",
                          (session['user_id'], data.get('movie_id'), content, data.get('parent_id')))
    cid = cursor.lastrowid
    row = conn.execute("""SELECT c.id,c.content,c.created_at,c.parent_id,u.name as author,u.friend_code,0 as like_count,0 as user_liked
        FROM comments c JOIN users u ON c.user_id=u.id WHERE c.id=?""", (cid,)).fetchone()
    conn.commit(); conn.close()
    return jsonify({'success': True, 'comment': dict(row)})

@app.route('/comments/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    conn = get_db()
    row  = conn.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,)).fetchone()
    if not row: conn.close(); return jsonify({'success': False, 'message': 'Не найден'})
    if row['user_id'] != session['user_id'] and not is_admin():
        conn.close(); return jsonify({'success': False, 'message': 'Нет прав'})
    conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/comments/like/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    conn = get_db()
    if conn.execute("SELECT 1 FROM comment_likes WHERE user_id=? AND comment_id=?", (session['user_id'], comment_id)).fetchone():
        conn.execute("DELETE FROM comment_likes WHERE user_id=? AND comment_id=?", (session['user_id'], comment_id))
        liked = False
    else:
        conn.execute("INSERT INTO comment_likes (user_id,comment_id) VALUES (?,?)", (session['user_id'], comment_id))
        liked = True
    count = conn.execute("SELECT COUNT(*) FROM comment_likes WHERE comment_id=?", (comment_id,)).fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({'success': True, 'liked': liked, 'count': count})


# ================================================================
# РЕЙТИНГИ
# ================================================================

@app.route('/rate', methods=['POST'])
@login_required
def rate_movie():
    data     = request.get_json()
    movie_id = data.get('movie_id')
    try:
        rating = int(data.get('rating')); assert 1 <= rating <= 10
    except:
        return jsonify({'success': False, 'message': 'Оценка от 1 до 10'})
    conn = get_db()
    conn.execute("""INSERT INTO ratings (user_id,movie_id,rating,updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id,movie_id) DO UPDATE SET rating=excluded.rating,updated_at=CURRENT_TIMESTAMP""",
                 (session['user_id'], movie_id, rating))
    avg = conn.execute("SELECT ROUND(AVG(rating),1) FROM ratings WHERE movie_id=?", (movie_id,)).fetchone()[0]
    conn.execute("UPDATE movies SET rating=? WHERE id=?", (avg, movie_id))
    conn.commit()
    ur = conn.execute("SELECT rating FROM ratings WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone()
    conn.close()
    return jsonify({'success': True, 'avg': avg, 'user_rating': ur['rating'] if ur else None})

@app.route('/rate/<int:movie_id>', methods=['GET', 'POST'])
def rating_handler(movie_id):
    conn = get_db()
    if request.method == 'GET':
        avg  = conn.execute("SELECT ROUND(AVG(rating),1),COUNT(*) FROM ratings WHERE movie_id=?", (movie_id,)).fetchone()
        ur   = None
        if session.get('user_id'):
            row = conn.execute("SELECT rating FROM ratings WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone()
            ur  = row['rating'] if row else None
        conn.close()
        return jsonify({'avg': avg[0], 'count': avg[1], 'user_rating': ur})
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходима авторизация'})
    data   = request.get_json() or {}
    rating = data.get('rating')
    if conn.execute("SELECT 1 FROM ratings WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone():
        conn.execute("UPDATE ratings SET rating=? WHERE user_id=? AND movie_id=?", (rating, session['user_id'], movie_id))
    else:
        conn.execute("INSERT INTO ratings (user_id,movie_id,rating) VALUES (?,?,?)", (session['user_id'], movie_id, rating))
    avg = conn.execute("SELECT AVG(rating) FROM ratings WHERE movie_id=?", (movie_id,)).fetchone()[0]
    conn.execute("UPDATE movies SET rating=? WHERE id=?", (round(avg,1), movie_id))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'new_rating': round(avg,1)})


# ================================================================
# ФОЛЛОВЕРЫ
# ================================================================

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'Нельзя подписаться на себя'})
    conn = get_db()
    if conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND following_id=?", (session['user_id'], user_id)).fetchone():
        conn.execute("DELETE FROM follows WHERE follower_id=? AND following_id=?", (session['user_id'], user_id))
        following = False
    else:
        conn.execute("INSERT INTO follows (follower_id,following_id) VALUES (?,?)", (session['user_id'], user_id))
        following = True
    count = conn.execute("SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,)).fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({'success': True, 'following': following, 'followers': count})

@app.route('/followers/<int:user_id>')
def get_followers(user_id):
    conn      = get_db()
    followers = [dict(r) for r in conn.execute("SELECT u.id,u.name,u.friend_code FROM follows f JOIN users u ON f.follower_id=u.id WHERE f.following_id=?", (user_id,)).fetchall()]
    following = [dict(r) for r in conn.execute("SELECT u.id,u.name,u.friend_code FROM follows f JOIN users u ON f.following_id=u.id WHERE f.follower_id=?", (user_id,)).fetchall()]
    is_fol    = bool(session.get('user_id') and conn.execute("SELECT 1 FROM follows WHERE follower_id=? AND following_id=?", (session['user_id'], user_id)).fetchone())
    conn.close()
    return jsonify({'followers': followers, 'following': following, 'is_following': is_fol})


# ================================================================
# API
# ================================================================

@app.route('/api/analytics', methods=['POST'])
def save_analytics():
    if 'user_id' not in session: return jsonify({'success': False}), 401
    data    = request.get_json(silent=True) or {}
    action  = data.get('action')
    item_id = data.get('movie_id')
    if not action: return jsonify({'success': False}), 400
    conn = get_db()
    conn.execute("INSERT INTO analytics (user_id,action,item_id) VALUES (?,?,?)",
                 (session['user_id'], action, str(item_id)))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2: return jsonify([])
    conn   = get_db()
    movies = [dict(r) for r in conn.execute("SELECT id,title,poster,year,rating,'movie' as type FROM movies WHERE title LIKE ? ORDER BY rating DESC LIMIT 5", (f'%{q}%',)).fetchall()]
    series = [dict(r) for r in conn.execute("SELECT id,title,poster,year,rating,'series' as type FROM series WHERE title LIKE ? ORDER BY rating DESC LIMIT 5", (f'%{q}%',)).fetchall()]
    conn.close()
    return jsonify(movies + series)

@app.route('/set_lang', methods=['POST'])
def set_lang():
    lang = (request.get_json() or {}).get('lang', 'ru')
    session['lang'] = lang if lang in ('ru','en','kz') else 'ru'
    return jsonify({'success': True, 'lang': session['lang']})

@app.route('/api/movies')
def api_movies():
    conn = get_db()
    rows = conn.execute("SELECT id,title,year,rating,poster FROM movies ORDER BY rating DESC LIMIT 20").fetchall()
    conn.close()
    return jsonify([dict(m) for m in rows])

@app.route('/api/tmdb/<path:endpoint>')
def tmdb_proxy(endpoint):
    """Прокси для TMDB API — карточки на главной"""
    TMDB_KEY = '15d2ea6d0dc1d476efbca3eba2b9bbfb'
    TMDB_BASE = 'https://api.themoviedb.org/3'
    try:
        params = dict(request.args)
        params['api_key'] = TMDB_KEY
        params.setdefault('language', 'ru-RU')
        r = requests.get(f'{TMDB_BASE}/{endpoint}', params=params, timeout=8)
        data = r.json()
        if 'results' in data:
            filtered = []
            for item in data['results']:
                if not item.get('poster_path'):
                    continue
                if item.get('adult') == True:
                    continue
                if item.get('vote_average', 0) < 4:
                    continue
                # Блокируем аниме (японская анимация жанр 16)
                if item.get('original_language') == 'ja' and 16 in (item.get('genre_ids') or []):
                    continue
                filtered.append(item)
            data['results'] = filtered
        return jsonify(data)
    except Exception as e:
        logger.error(f'TMDB proxy error: {e}')
        return jsonify({'results': [], 'error': str(e)})

@app.route('/api/recommendations')
def api_recommendations():
    movie_id = request.args.get('id', 0, type=int)
    conn     = get_db()
    current  = conn.execute("SELECT genre FROM movies WHERE id=?", (movie_id,)).fetchone()
    if not current: conn.close(); return jsonify({'recommendations': []})
    rows = conn.execute("SELECT id,title,poster,rating FROM movies WHERE id!=? AND genre LIKE ? ORDER BY RANDOM() LIMIT 10",
                        (movie_id, f'%{current["genre"]}%')).fetchall()
    conn.close()
    return jsonify({'recommendations': [dict(m) for m in rows]})

@app.route('/api/series/<int:series_id>')
def api_series_episodes(series_id):
    conn = get_db()
    rows = conn.execute("SELECT id,season,ep_num,title FROM episodes WHERE series_id=? ORDER BY season,ep_num", (series_id,)).fetchall()
    conn.close()
    return jsonify({'episodes': [dict(e) for e in rows]})

@app.route('/api/save-progress', methods=['POST'])
@app.route('/api/save_progress', methods=['POST'])
@login_required
def save_progress():
    data     = request.get_json(silent=True) or {}
    movie_id = data.get('movie_id')
    progress = data.get('progress', 0)
    if not movie_id: return jsonify({'success': False}), 400
    conn = get_db()
    conn.execute("""INSERT INTO watch_history (user_id,movie_id,progress,watched_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id,movie_id) DO UPDATE SET progress=excluded.progress,watched_at=CURRENT_TIMESTAMP""",
                 (session['user_id'], movie_id, progress))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/favorite/toggle', methods=['POST'])
@login_required
def api_favorite_toggle():
    data     = request.get_json(silent=True) or {}
    movie_id = data.get('movie_id')
    if not movie_id: return jsonify({'success': False}), 400
    conn = get_db()
    if conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone():
        conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id))
        status = 'removed'
    else:
        conn.execute("INSERT OR IGNORE INTO favorites (user_id,movie_id) VALUES (?,?)", (session['user_id'], movie_id))
        status = 'added'
    conn.commit(); conn.close()
    return jsonify({'success': True, 'status': status})

@app.route('/api/channels')
def api_channels():
    conn     = get_db()
    channels = conn.execute("SELECT * FROM tv_channels WHERE is_active=1 ORDER BY name").fetchall()
    conn.close()
    seen, result = set(), []
    for row in channels:
        ch = dict(row)
        if ch['name'] not in seen:
            seen.add(ch['name'])
            result.append(ch)
    return jsonify(result)


# ================================================================
# ПРОФИЛЬ
# ================================================================

@app.route("/upload_avatar", methods=["POST"])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if not file or not file.filename:
        return jsonify({"success": False, "message": "Файл не выбран"})
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
        return jsonify({"success": False, "message": "Только PNG, JPG, WEBP, GIF"})
    file.seek(0, 2); size = file.tell(); file.seek(0)
    if size > 2 * 1024 * 1024:
        return jsonify({"success": False, "message": "Файл больше 2MB"})
    upload_path = os.path.join(basedir, "static", "uploads", "avatars")
    os.makedirs(upload_path, exist_ok=True)
    ext      = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"avatar_{session['user_id']}.{ext}"
    file.save(os.path.join(upload_path, filename))
    url = f"/static/uploads/avatars/{filename}"
    conn = get_db()
    conn.execute("UPDATE users SET profile_pic=? WHERE id=?", (url, session['user_id']))
    conn.commit(); conn.close()
    session['avatar_url'] = url
    session.modified      = True
    return jsonify({"success": True, "url": url})

@app.route('/favorites')
@login_required
def favorites_page():
    conn = get_db()
    rows = conn.execute("SELECT m.* FROM movies m JOIN favorites f ON m.id=f.movie_id WHERE f.user_id=? ORDER BY f.id DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('favorites.html', favorites=[dict(r) for r in rows])

@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    uid  = session['user_id']
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() or {})
    favorites     = [dict(r) for r in conn.execute("SELECT m.* FROM movies m JOIN favorites f ON m.id=f.movie_id WHERE f.user_id=? ORDER BY f.id DESC", (uid,)).fetchall()]
    watch_history = [dict(r) for r in conn.execute("SELECT m.*,wh.progress,wh.watched_at FROM movies m JOIN watch_history wh ON m.id=wh.movie_id WHERE wh.user_id=? ORDER BY wh.watched_at DESC LIMIT 50", (uid,)).fetchall()]
    watch_later   = [dict(r) for r in conn.execute("SELECT m.* FROM movies m JOIN watch_later wl ON m.id=wl.movie_id WHERE wl.user_id=? ORDER BY wl.id DESC", (uid,)).fetchall()]
    friends       = [dict(r) for r in conn.execute("SELECT u.id,u.name,u.email,u.profile_pic FROM users u JOIN friends fr ON u.id=fr.friend_id WHERE fr.user_id=?", (uid,)).fetchall()]
    sub_row       = conn.execute("SELECT p.name,us.end_date FROM user_subscriptions us JOIN plans p ON us.plan_id=p.id WHERE us.user_id=? AND us.is_active=1 AND us.end_date>=date('now') ORDER BY us.id DESC LIMIT 1", (uid,)).fetchone()
    current_sub   = dict(sub_row) if sub_row else None
    conn.close()
    return render_template('profile.html', user=user, favorites=favorites,
                           watch_history=watch_history, watch_later=watch_later,
                           friends=friends, current_sub=current_sub)

@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    conn = get_db()
    user = conn.execute("SELECT id,name,email FROM users WHERE id=?", (user_id,)).fetchone()
    if not user: conn.close(); return "Не найден", 404
    favorites = [dict(r) for r in conn.execute("SELECT m.id,m.title,m.poster,m.rating,m.year FROM movies m JOIN favorites f ON m.id=f.movie_id WHERE f.user_id=? ORDER BY f.id DESC LIMIT 12", (user_id,)).fetchall()]
    conn.close()
    return render_template('profile.html', user=dict(user), favorites=favorites,
                           watch_history=[], watch_later=[], friends=[], current_sub=None, is_public=True)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username', '').strip()
    email    = request.form.get('email', '').strip()
    new_pw   = request.form.get('new_password', '')
    conn     = get_db()
    if new_pw:
        conn.execute("UPDATE users SET name=?,email=?,password=? WHERE id=?",
                     (username, email, generate_password_hash(new_pw), session['user_id']))
    else:
        conn.execute("UPDATE users SET name=?,email=? WHERE id=?", (username, email, session['user_id']))
    conn.commit(); conn.close()
    session['user_name'] = username
    session['user']      = username
    return redirect('/profile')


# ================================================================
# ДРУЗЬЯ
# ================================================================

@app.route('/friends/add', methods=['POST'])
@login_required
def add_friend():
    data    = request.get_json()
    query   = (data.get('username') or data.get('friend_code') or data.get('user_id_str') or '').strip()
    if not query: return jsonify({'success': False, 'message': 'Введите ID или никнейм'})
    conn   = get_db()
    # Числовой 8-значный ID
    if query.isdigit():
        friend = conn.execute("SELECT id,name,email,friend_code FROM users WHERE id=?", (int(query),)).fetchone()
    else:
        friend = conn.execute("SELECT id,name,email,friend_code FROM users WHERE name=?", (query,)).fetchone()
    if not friend: conn.close(); return jsonify({'success': False, 'message': f'Пользователь «{query}» не найден'})
    friend = dict(friend)
    if friend['id'] == session['user_id']: conn.close(); return jsonify({'success': False, 'message': 'Нельзя добавить себя'})
    if conn.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=?", (session['user_id'], friend['id'])).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Уже в списке'})
    conn.execute("INSERT INTO friends (user_id,friend_id) VALUES (?,?)", (session['user_id'], friend['id']))
    conn.commit()
    # Уведомляем друга по email в фоне
    friend_row = conn.execute("SELECT name,email FROM users WHERE id=?", (friend['id'],)).fetchone()
    me_name    = session.get('user_name', 'Кто-то')
    conn.close()
    if friend_row and friend_row['email']:
        import threading
        threading.Thread(target=_email_new_friend,
            args=(friend_row['name'], friend_row['email'], me_name), daemon=True).start()
    return jsonify({'success': True, 'message': f'{friend["name"]} добавлен!', 'friend': friend})

@app.route('/friends/remove', methods=['POST'])
@login_required
def remove_friend():
    friend_id = (request.get_json() or {}).get('friend_id')
    conn = get_db()
    conn.execute("DELETE FROM friends WHERE user_id=? AND friend_id=?", (session['user_id'], friend_id))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/watch_later/<int:movie_id>', methods=['POST', 'DELETE'])
@login_required
def watch_later_toggle(movie_id):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM watch_later WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id))
        conn.commit(); conn.close(); return jsonify({'success': True})
    if conn.execute("SELECT 1 FROM watch_later WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone():
        conn.execute("DELETE FROM watch_later WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)); msg = 'Убрано'
    else:
        conn.execute("INSERT OR IGNORE INTO watch_later (user_id,movie_id) VALUES (?,?)", (session['user_id'], movie_id)); msg = 'Добавлено'
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': msg})

@app.route('/watch_history/add', methods=['POST'])
@login_required
def add_watch_history():
    data = request.get_json()
    conn = get_db()
    conn.execute("""INSERT INTO watch_history (user_id,movie_id,progress,watched_at) VALUES (?,?,?,datetime('now'))
        ON CONFLICT(user_id,movie_id) DO UPDATE SET progress=excluded.progress,watched_at=excluded.watched_at""",
                 (session['user_id'], data.get('movie_id'), data.get('progress', 0)))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/toggle_favorite/<int:movie_id>', methods=['POST'])
def toggle_favorite(movie_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходима авторизация'})
    conn = get_db()
    if conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)).fetchone():
        conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (session['user_id'], movie_id)); msg = 'Удалено из избранного'
    else:
        conn.execute("INSERT INTO favorites (user_id,movie_id) VALUES (?,?)", (session['user_id'], movie_id)); msg = 'Добавлено в избранное'
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': msg})


# ================================================================
# ВЫДАТЬ СЕБЕ АДМИНКУ
# ================================================================

@app.route('/make-me-admin', methods=['GET', 'POST'])
def make_me_admin():
    SECRET = os.environ.get('ADMIN_SECRET', 'kinoflik-admin-2025')
    if request.method == 'POST':
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Сначала войди на сайт'})
        data = request.get_json() or {}
        if data.get('secret') != SECRET:
            return jsonify({'success': False, 'message': 'Неверный секрет'})
        conn = get_db()
        conn.execute("UPDATE users SET role='admin' WHERE id=?", (session['user_id'],))
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone())
        conn.close()
        _set_session(user)
        return jsonify({'success': True, 'message': f'Готово! {user["name"]} (ID: {user["id"]}) теперь администратор'})
    uid  = session.get('user_id')
    name = session.get('user_name', 'не авторизован')
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Выдать себе админку</title>
<style>body{{font-family:sans-serif;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.box{{background:#1a1a1a;border:1px solid #333;border-radius:16px;padding:40px;max-width:420px;width:100%;text-align:center}}
h2{{color:#800000}}p{{color:#aaa;margin-bottom:20px}}
input{{width:100%;padding:12px;background:#222;border:1px solid #444;border-radius:8px;color:#fff;font-size:15px;box-sizing:border-box;margin-bottom:16px}}
button{{width:100%;padding:14px;background:#800000;border:none;border-radius:8px;color:#fff;font-size:16px;font-weight:700;cursor:pointer}}
button:hover{{background:#b30000}}.warn{{color:#f59e0b;font-size:13px;margin-top:16px}}</style></head>
<body><div class="box"><h2>🛡 Выдать права администратора</h2>
<p>Пользователь: <b>{name}</b> (ID: {uid or '—'})</p>
{"<p style='color:#800000'>⚠️ <a href='/login' style='color:#800000'>Войди на сайт</a> сначала</p>" if not uid else ""}
<input type="password" id="sec" placeholder="Секретное слово (по умолчанию: kinoflik-admin-2025)">
<button onclick="go()">Сделать меня администратором</button>
<div class="warn">⚠️ После получения прав удали роут /make-me-admin из app.py</div></div>
<script>function go(){{fetch('/make-me-admin',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{secret:document.getElementById('sec').value}})}})
.then(r=>r.json()).then(d=>{{alert(d.message);if(d.success)location.href='/admin';}});}}</script></body></html>"""


# ================================================================
# АДМИН
# ================================================================

@app.route("/admin")
def admin():
    if not is_admin(): return redirect('/login')
    conn = get_db()
    movies     = conn.execute("SELECT * FROM movies ORDER BY id DESC").fetchall()
    all_series = conn.execute("SELECT * FROM series ORDER BY id DESC").fetchall()
    trailers   = conn.execute("SELECT * FROM trailers ORDER BY id DESC").fetchall()
    users      = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    channels   = conn.execute("SELECT * FROM tv_channels ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin.html', movies=movies, series=all_series, trailers=trailers,
                           users=users, channels=channels, user_count=len(users))

@app.route("/add_movie", methods=["POST"])
def add_movie():
    if not is_admin(): return redirect('/login')
    conn = get_db()
    conn.execute("""INSERT INTO movies (title,original_title,description,rating,poster,year,duration,genre,age_rating,video_url,trailer_url)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        request.form.get("title","").strip(), request.form.get("original_title",""),
        request.form.get("description",""), request.form.get("rating") or 0,
        save_poster(request.files.get("poster")), request.form.get("year") or 2024,
        request.form.get("duration",""), ", ".join(request.form.getlist("genre")),
        request.form.get("age_rating","16+"),
        save_video(request.files.get("video_file")) or request.form.get("video_url",""),
        request.form.get("trailer_url","")))
    conn.commit(); conn.close()
    return redirect(url_for("admin") + "?success=1")

@app.route("/add_series", methods=["POST"])
def add_series():
    if not is_admin(): return redirect('/login')
    conn   = get_db()
    cursor = conn.execute("""INSERT INTO series (title,original_title,description,rating,poster,year,seasons,genre,status,trailer_url)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", (
        request.form.get("title","").strip(), request.form.get("original_title",""),
        request.form.get("description",""), request.form.get("rating") or 0,
        save_poster(request.files.get("poster")), request.form.get("year") or 2024,
        request.form.get("seasons") or 1, ", ".join(request.form.getlist("genre")),
        request.form.get("status","ongoing"), request.form.get("trailer_url","")))
    series_id = cursor.lastrowid
    for i, num in enumerate(request.form.getlist("ep_num[]") or request.form.getlist("ep_num")):
        titles  = request.form.getlist("ep_title[]") or request.form.getlist("ep_title")
        urls    = request.form.getlist("ep_url[]") or request.form.getlist("ep_url")
        seasons = request.form.getlist("ep_season[]") or request.form.getlist("ep_season")
        conn.execute("INSERT INTO episodes (series_id,season,ep_num,title,video_url) VALUES (?,?,?,?,?)",
                     (series_id, seasons[i] if i < len(seasons) else 1, num,
                      titles[i] if i < len(titles) else "", urls[i] if i < len(urls) else ""))
    conn.commit(); conn.close()
    return redirect(url_for("admin") + "?tab=series&success=1")

@app.route("/add_trailer", methods=["POST"])
def add_trailer():
    if not is_admin(): return redirect('/login')
    conn = get_db()
    conn.execute("INSERT INTO trailers (title,description,trailer_url,poster,trailer_type) VALUES (?,?,?,?,?)",
                 (request.form.get("title",""), request.form.get("description",""),
                  request.form.get("trailer_url",""), save_poster(request.files.get("poster")),
                  request.form.get("trailer_type","movie")))
    conn.commit(); conn.close()
    return redirect(url_for("admin") + "?tab=trailers&success=1")

@app.route('/admin/edit_movie', methods=['POST'])
def edit_movie():
    if not is_admin(): return jsonify({'success': False})
    data = request.get_json(); conn = get_db()
    try:
        conn.execute("UPDATE movies SET title=?,rating=?,year=?,description=? WHERE id=?",
                     (data.get('title'),data.get('rating'),data.get('year'),data.get('description'),data.get('movie_id')))
        conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/edit_series', methods=['POST'])
def edit_series():
    if not is_admin(): return jsonify({'success': False})
    data = request.get_json(); sid = data.get('series_id') or data.get('movie_id'); conn = get_db()
    try:
        conn.execute("UPDATE series SET title=?,rating=?,year=?,description=? WHERE id=?",
                     (data.get('title'),data.get('rating'),data.get('year'),data.get('description'),sid))
        conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/delete_movie', methods=['POST'])
def delete_movie():
    if not is_admin(): return jsonify({'success': False})
    mid = (request.get_json() or {}).get('movie_id'); conn = get_db()
    try:
        for t in ['favorites','ratings','movie_images']:
            conn.execute(f"DELETE FROM {t} WHERE movie_id=?", (mid,))
        conn.execute("DELETE FROM movies WHERE id=?", (mid,)); conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/delete_series', methods=['POST'])
def delete_series():
    if not is_admin(): return jsonify({'success': False})
    data = request.get_json(); sid = data.get('series_id') or data.get('movie_id'); conn = get_db()
    try:
        conn.execute("DELETE FROM episodes WHERE series_id=?", (sid,))
        conn.execute("DELETE FROM series WHERE id=?", (sid,)); conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/delete_trailer', methods=['POST'])
def delete_trailer():
    if not is_admin(): return jsonify({'success': False})
    tid = (request.get_json() or {}).get('trailer_id'); conn = get_db()
    try:
        conn.execute("DELETE FROM trailers WHERE id=?", (tid,)); conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/ban_user', methods=['POST'])
def ban_user():
    if not is_admin(): return jsonify({'success': False})
    data = request.get_json(); conn = get_db()
    conn.execute("UPDATE users SET is_banned=? WHERE id=?",
                 (1 if data.get('action')=='ban' else 0, data.get('user_id')))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if not is_admin(): return jsonify({'success': False})
    uid = (request.get_json() or {}).get('user_id'); conn = get_db()
    try:
        for t in ['favorites','ratings','user_subscriptions']:
            conn.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,)); conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/set_role', methods=['POST'])
def set_role():
    if not is_admin(): return jsonify({'success': False}), 403
    data = request.get_json(); username = (data.get('username') or '').strip(); role = data.get('role','user')
    if role not in ('admin','user'): return jsonify({'success': False, 'message': 'Неверная роль'})
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE name=?", (username,)).fetchone()
    if not user: conn.close(); return jsonify({'success': False, 'message': f'«{username}» не найден'})
    conn.execute("UPDATE users SET role=? WHERE name=?", (role, username))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': f'Роль «{role}» выдана {username}'})

@app.route('/admin/add_channel', methods=['POST'])
def add_channel():
    if not is_admin(): return redirect('/login')
    name = request.form.get('name','').strip(); url = request.form.get('stream_url','').strip()
    if name and url:
        conn = get_db()
        conn.execute("INSERT INTO tv_channels (name,category,stream_url,logo_color) VALUES (?,?,?,?)",
                     (name, request.form.get('category',''), url, request.form.get('logo_color','#800000')))
        conn.commit(); conn.close()
    return redirect(url_for('admin') + '?tab=channels&success=1')

@app.route('/admin/delete_channel', methods=['POST'])
def delete_channel():
    if not is_admin(): return jsonify({'success': False})
    cid = (request.get_json() or {}).get('channel_id'); conn = get_db()
    try:
        conn.execute("DELETE FROM tv_channels WHERE id=?", (cid,)); conn.commit(); return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()

@app.route('/admin/toggle_channel', methods=['POST'])
def toggle_channel():
    if not is_admin(): return jsonify({'success': False})
    cid = (request.get_json() or {}).get('channel_id'); conn = get_db()
    try:
        ch = conn.execute("SELECT is_active FROM tv_channels WHERE id=?", (cid,)).fetchone()
        if ch:
            new = 0 if ch['is_active'] else 1
            conn.execute("UPDATE tv_channels SET is_active=? WHERE id=?", (new, cid))
            conn.commit(); return jsonify({'success': True, 'is_active': new})
        return jsonify({'success': False})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})
    finally: conn.close()


# ================================================================
# ПРОКСИ СТРИМИНГ  — оптимизирован для TV без лагов
# Логика: ts-сегменты проксируем, m3u8 перезаписываем пути
# ================================================================

_proxy_session = requests.Session()
_proxy_session.verify = False

@app.route('/proxy/stream')
def proxy_stream():
    url = request.args.get('url', '').strip()
    if not url: return 'Missing url', 400
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc: return 'Invalid url', 400

    referer = f"https://{parsed.netloc}/"
    hdrs = {
        'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept':          '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.9',
        'Referer':         referer,
        'Origin':          referer.rstrip('/'),
        'Connection':      'keep-alive',
    }

    try:
        r = _proxy_session.get(url, headers=hdrs, timeout=15, stream=True, allow_redirects=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return f'HTTP {e.response.status_code}', 502
    except requests.exceptions.Timeout:
        return 'Timeout', 504
    except Exception as e:
        return str(e), 502

    ct        = r.headers.get('Content-Type', 'application/octet-stream')
    final_url = r.url
    is_m3u8   = 'm3u8' in url.lower() or 'm3u8' in final_url.lower() or 'mpegurl' in ct.lower()

    if is_m3u8:
        base_url = final_url.rsplit('/', 1)[0] + '/'
        lines    = []
        for line in r.text.splitlines():
            s = line.strip()
            if s.startswith('#'):
                # Перезаписываем URI= внутри тегов
                line = re.sub(
                    r'URI="([^"]+)"',
                    lambda m: 'URI="/proxy/stream?url=' + quote(
                        m.group(1) if m.group(1).startswith('http') else urljoin(base_url, m.group(1)),
                        safe='') + '"',
                    line)
                lines.append(line)
            elif s:
                abs_url = s if s.startswith('http') else urljoin(base_url, s)
                lines.append('/proxy/stream?url=' + quote(abs_url, safe=''))
            else:
                lines.append(line)
        resp = Response('\n'.join(lines), status=200,
                        content_type='application/vnd.apple.mpegurl')
    else:
        # ts-сегмент — стримим чанками для скорости
        resp = Response(
            stream_with_context(r.iter_content(chunk_size=1024 * 64)),
            status=r.status_code, content_type=ct)

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control']               = 'no-cache'
    return resp


# ================================================================
# ЧАТ С ДРУЗЬЯМИ  (личные сообщения)
# ================================================================

@app.route('/chat')
@login_required
def chat_page():
    conn    = get_db()
    uid     = session['user_id']
    friends = [dict(r) for r in conn.execute("""
        SELECT u.id,u.name,u.profile_pic,
               (SELECT COUNT(*) FROM messages m WHERE m.sender_id=u.id AND m.receiver_id=? AND m.is_read=0 AND m.group_id IS NULL) as unread
        FROM users u JOIN friends f ON u.id=f.friend_id WHERE f.user_id=?
    """, (uid, uid)).fetchall()]
    groups  = [dict(r) for r in conn.execute("""
        SELECT g.id,g.name,g.avatar,
               (SELECT COUNT(*) FROM group_messages gm WHERE gm.group_id=g.id
                AND gm.created_at > COALESCE((SELECT gm2.created_at FROM group_messages gm2 WHERE gm2.group_id=g.id AND gm2.sender_id=? ORDER BY gm2.id DESC LIMIT 1),'1970-01-01')) as unread
        FROM chat_groups g JOIN chat_group_members cgm ON g.id=cgm.group_id WHERE cgm.user_id=?
        ORDER BY g.created_at DESC
    """, (uid, uid)).fetchall()]
    conn.close()
    return render_template('chat.html', friends=friends, groups=groups)

@app.route('/api/messages/<int:friend_id>')
@login_required
def get_messages(friend_id):
    uid  = session['user_id']
    conn = get_db()
    conn.execute("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=? AND group_id IS NULL", (friend_id, uid))
    conn.commit()
    rows = conn.execute("""
        SELECT m.id,m.content,m.created_at,m.is_read,m.sender_id,
               u.name as sender_name,u.profile_pic as sender_pic
        FROM messages m JOIN users u ON m.sender_id=u.id
        WHERE ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
          AND m.group_id IS NULL
        ORDER BY m.created_at ASC LIMIT 100
    """, (uid, friend_id, friend_id, uid)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data     = request.get_json()
    receiver = data.get('receiver_id')
    content  = (data.get('content') or '').strip()
    if not content or not receiver:
        return jsonify({'success': False, 'message': 'Пустое сообщение'})
    if len(content) > 2000:
        return jsonify({'success': False, 'message': 'Максимум 2000 символов'})
    uid  = session['user_id']
    conn = get_db()
    if not conn.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=?", (uid, receiver)).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Можно писать только друзьям'})
    cursor = conn.execute("INSERT INTO messages (sender_id,receiver_id,content) VALUES (?,?,?)", (uid, receiver, content))
    msg_id = cursor.lastrowid
    row    = conn.execute("""
        SELECT m.id,m.content,m.created_at,m.sender_id,u.name as sender_name,u.profile_pic as sender_pic
        FROM messages m JOIN users u ON m.sender_id=u.id WHERE m.id=?
    """, (msg_id,)).fetchone()
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': dict(row)})

@app.route('/api/messages/unread')
@login_required
def unread_count():
    conn  = get_db()
    uid   = session['user_id']
    dm    = conn.execute("SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0 AND group_id IS NULL", (uid,)).fetchone()[0]
    conn.close()
    return jsonify({'unread': dm})


# ================================================================
# ГРУППОВЫЕ ЧАТЫ  ← НОВОЕ
# ================================================================

@app.route('/api/groups', methods=['GET'])
@login_required
def get_groups():
    conn = get_db()
    uid  = session['user_id']
    rows = conn.execute("""
        SELECT g.id,g.name,g.avatar,g.created_by,
               (SELECT gm.content FROM group_messages gm WHERE gm.group_id=g.id ORDER BY gm.id DESC LIMIT 1) as last_msg,
               (SELECT COUNT(*) FROM chat_group_members cgm WHERE cgm.group_id=g.id) as members_count
        FROM chat_groups g JOIN chat_group_members cgm ON g.id=cgm.group_id
        WHERE cgm.user_id=? ORDER BY g.created_at DESC
    """, (uid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/groups/create', methods=['POST'])
@login_required
def create_group():
    data    = request.get_json()
    name    = (data.get('name') or '').strip()
    members = data.get('members', [])   # список user_id
    if not name:
        return jsonify({'success': False, 'message': 'Введите название группы'})
    if len(name) > 50:
        return jsonify({'success': False, 'message': 'Максимум 50 символов'})
    uid  = session['user_id']
    conn = get_db()
    cur  = conn.execute("INSERT INTO chat_groups (name,created_by) VALUES (?,?)", (name, uid))
    gid  = cur.lastrowid
    # Добавляем создателя как admin
    conn.execute("INSERT INTO chat_group_members (group_id,user_id,role) VALUES (?,?,?)", (gid, uid, 'admin'))
    # Добавляем остальных (только друзей)
    for mid in members:
        if mid != uid:
            is_friend = conn.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=?", (uid, mid)).fetchone()
            if is_friend:
                conn.execute("INSERT OR IGNORE INTO chat_group_members (group_id,user_id,role) VALUES (?,?,?)", (gid, mid, 'member'))
    conn.commit()
    group = dict(conn.execute("SELECT * FROM chat_groups WHERE id=?", (gid,)).fetchone())
    conn.close()
    return jsonify({'success': True, 'group': group})

@app.route('/api/groups/<int:group_id>/messages', methods=['GET'])
@login_required
def get_group_messages(group_id):
    uid  = session['user_id']
    conn = get_db()
    # Проверяем что юзер в группе
    if not conn.execute("SELECT 1 FROM chat_group_members WHERE group_id=? AND user_id=?", (group_id, uid)).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Нет доступа'}), 403
    rows = conn.execute("""
        SELECT gm.id,gm.content,gm.created_at,gm.sender_id,
               u.name as sender_name,u.profile_pic as sender_pic
        FROM group_messages gm JOIN users u ON gm.sender_id=u.id
        WHERE gm.group_id=? ORDER BY gm.created_at ASC LIMIT 100
    """, (group_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/groups/<int:group_id>/send', methods=['POST'])
@login_required
def send_group_message(group_id):
    uid     = session['user_id']
    data    = request.get_json()
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'Пустое сообщение'})
    if len(content) > 2000:
        return jsonify({'success': False, 'message': 'Максимум 2000 символов'})
    conn = get_db()
    if not conn.execute("SELECT 1 FROM chat_group_members WHERE group_id=? AND user_id=?", (group_id, uid)).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Нет доступа'}), 403
    cursor = conn.execute("INSERT INTO group_messages (group_id,sender_id,content) VALUES (?,?,?)", (group_id, uid, content))
    msg_id = cursor.lastrowid
    row    = conn.execute("""
        SELECT gm.id,gm.content,gm.created_at,gm.sender_id,u.name as sender_name,u.profile_pic as sender_pic
        FROM group_messages gm JOIN users u ON gm.sender_id=u.id WHERE gm.id=?
    """, (msg_id,)).fetchone()
    conn.commit(); conn.close()
    return jsonify({'success': True, 'message': dict(row)})

@app.route('/api/groups/<int:group_id>/members', methods=['GET'])
@login_required
def get_group_members(group_id):
    uid  = session['user_id']
    conn = get_db()
    if not conn.execute("SELECT 1 FROM chat_group_members WHERE group_id=? AND user_id=?", (group_id, uid)).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Нет доступа'}), 403
    rows = conn.execute("""
        SELECT u.id,u.name,u.profile_pic,cgm.role FROM users u
        JOIN chat_group_members cgm ON u.id=cgm.user_id WHERE cgm.group_id=?
    """, (group_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/groups/<int:group_id>/add_member', methods=['POST'])
@login_required
def add_group_member(group_id):
    uid  = session['user_id']
    data = request.get_json()
    conn = get_db()
    me   = conn.execute("SELECT role FROM chat_group_members WHERE group_id=? AND user_id=?", (group_id, uid)).fetchone()
    if not me or me['role'] != 'admin':
        conn.close(); return jsonify({'success': False, 'message': 'Только администратор группы может добавлять'}), 403
    new_uid = data.get('user_id')
    if not conn.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=?", (uid, new_uid)).fetchone():
        conn.close(); return jsonify({'success': False, 'message': 'Можно добавить только друга'})
    conn.execute("INSERT OR IGNORE INTO chat_group_members (group_id,user_id,role) VALUES (?,?,?)", (group_id, new_uid, 'member'))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/groups/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    uid  = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM chat_group_members WHERE group_id=? AND user_id=?", (group_id, uid))
    # Если никого не осталось — удаляем группу
    cnt = conn.execute("SELECT COUNT(*) FROM chat_group_members WHERE group_id=?", (group_id,)).fetchone()[0]
    if cnt == 0:
        conn.execute("DELETE FROM group_messages WHERE group_id=?", (group_id,))
        conn.execute("DELETE FROM chat_groups WHERE id=?", (group_id,))
    conn.commit(); conn.close()
    return jsonify({'success': True})


# ================================================================
# AI ПОДБОРЩИК
# ================================================================

@app.route('/ai-pick')
@login_required
def ai_pick_page():
    return render_template('ai_pick.html')

@app.route('/api/ai-pick', methods=['POST'])
@login_required
def ai_pick():
    data = request.get_json()
    mood = (data.get('mood') or '').strip()
    if not mood:
        return jsonify({'success': False, 'message': 'Опишите настроение'})
    conn   = get_db()
    movies = [dict(m) for m in conn.execute(
        "SELECT id,title,genre,rating,year,description FROM movies ORDER BY rating DESC LIMIT 200").fetchall()]
    conn.close()
    catalog = "\n".join([f"ID:{m['id']} | {m['title']} ({m['year']}) | {m['genre']} | ★{m['rating']}" for m in movies[:150]])
    prompt  = f"""Ты — кинокритик KinoFlik. Пользователь: "{mood}"
Каталог (ID | Название | Жанр | Рейтинг):
{catalog}
Выбери РОВНО 6 фильмов. Ответь ТОЛЬКО JSON:
[{{"id": 1, "reason": "Почему подходит (1 предложение)"}}]"""
    try:
        resp  = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":os.environ.get('ANTHROPIC_API_KEY','')},
            json={"model":"claude-sonnet-4-20250514","max_tokens":800,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        raw   = resp.json()['content'][0]['text'].strip()
        if raw.startswith("```"): raw = raw.split("\n",1)[1].rsplit("```",1)[0]
        picks  = json.loads(raw)
        id_map = {m['id']: m for m in movies}
        result = []
        for p in picks:
            m = id_map.get(p['id'])
            if m: m['reason'] = p.get('reason',''); result.append(m)
        return jsonify({'success': True, 'movies': result})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка AI: {e}'})


# ================================================================
# ЛИЧНАЯ СТАТИСТИКА
# ================================================================

@app.route('/stats')
@login_required
def stats_page():
    uid  = session['user_id']
    conn = get_db()
    total_watched = conn.execute("SELECT COUNT(*) FROM watch_history WHERE user_id=?", (uid,)).fetchone()[0]
    genres_raw    = conn.execute("""SELECT m.genre FROM movies m JOIN watch_history wh ON m.id=wh.movie_id
        WHERE wh.user_id=? AND m.genre IS NOT NULL""", (uid,)).fetchall()
    genre_count = {}
    for row in genres_raw:
        for g in (row['genre'] or '').split(','):
            g = g.strip()
            if g: genre_count[g] = genre_count.get(g,0) + 1
    top_genres    = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:6]
    avg_rating    = conn.execute("SELECT ROUND(AVG(rating),1) FROM ratings WHERE user_id=?", (uid,)).fetchone()[0] or 0
    total_ratings = conn.execute("SELECT COUNT(*) FROM ratings WHERE user_id=?", (uid,)).fetchone()[0]
    days_activity = conn.execute("""SELECT DATE(watched_at) as day,COUNT(*) as cnt FROM watch_history
        WHERE user_id=? AND watched_at>=DATE('now','-14 days') GROUP BY DATE(watched_at) ORDER BY day""", (uid,)).fetchall()
    top_rated     = conn.execute("""SELECT m.id,m.title,m.poster,m.year,r.rating as my_rating
        FROM ratings r JOIN movies m ON r.movie_id=m.id WHERE r.user_id=? ORDER BY r.rating DESC LIMIT 5""", (uid,)).fetchall()
    years_raw     = conn.execute("""SELECT m.year,COUNT(*) as cnt FROM movies m
        JOIN watch_history wh ON m.id=wh.movie_id WHERE wh.user_id=? AND m.year IS NOT NULL
        GROUP BY m.year ORDER BY cnt DESC LIMIT 5""", (uid,)).fetchall()
    friend_count  = conn.execute("SELECT COUNT(*) FROM friends WHERE user_id=?", (uid,)).fetchone()[0]
    comment_count = conn.execute("SELECT COUNT(*) FROM comments WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    return render_template('stats.html', total_watched=total_watched, top_genres=top_genres,
        avg_rating=avg_rating, total_ratings=total_ratings,
        days_activity=[dict(d) for d in days_activity], top_rated=[dict(r) for r in top_rated],
        years_raw=[dict(y) for y in years_raw], friend_count=friend_count, comment_count=comment_count)


# ================================================================
# ПРОЧЕЕ
# ================================================================

@app.route('/tickets')
def tickets():
    return redirect("https://kino.kz/afisha")

@app.route('/debug_db')
def debug_db():
    if not is_admin(): abort(403)
    try:
        conn   = get_db()
        tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        stats  = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ['users','movies','series','favorites','watch_history','messages'] if t in tables}
        db_size = os.path.getsize(db_path) // 1024
        conn.close()
        return jsonify({'status':'ok', 'db_kb': db_size, 'tables': tables, 'stats': stats})
    except Exception as e:
        logger.error(f"debug_db: {e}")
        return jsonify({'status':'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    try:
        conn = get_db(); users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]; conn.close()
        return jsonify({'status':'ok','users':users,'time':datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# ================================================================
# ОШИБКИ
# ================================================================

@app.errorhandler(404)
def page_not_found(e):
    logger.info(f"404: {request.url}")
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500: {request.url} — {traceback.format_exc()}")
    return render_template("404.html"), 500

@app.errorhandler(403)
def forbidden(e):
    logger.warning(f"403: {request.url} user={session.get('user_id')}")
    return render_template("404.html"), 403


# ================================================================
# ЗАПУСК
# ================================================================

def auto_import_series():
    """Авто-импорт популярных сериалов при первом запуске."""
    import os, time as _time
    TMDB_KEY   = '15d2ea6d0dc1d476efbca3eba2b9bbfb'
    POSTER_DIR = os.path.join(os.path.dirname(__file__), 'static', 'posters')
    os.makedirs(POSTER_DIR, exist_ok=True)
    BAD_LANGS  = set()  # no language blocking — all languages are allowed
    SKIP_GENRE = {10767, 10764}
    MUST_HAVE  = [
        # Культовые
        1399,1396,60625,66732,1402,67136,71446,93405,1418,1100,2316,
        456,76479,87108,48866,44217,83867,71712,1622,1416,63174,84773,
        114461,202555,106311,84958,82856,63333,
        # Дополнительные топ-сериалы
        1398,1405,1408,1409,1411,1413,1421,1425,1434,1438,
        4607,4613,18347,1911,60574,60622,62560,63351,63247,67744,
        69478,70523,73586,74952,76312,85552,68507,95281,91239,
        85271,97546,94997,87739,95396,97180,65495,79501,
        90462,77169,46648,62126,2778,35,2288,4614,
        # Новые хиты
        100088,119051,120168,130392,136315,202250,
        71912,1307,15260,40,37680,19885,30983,
        # Документальные / научпоп
        99217,106005,76011,91185,
    ]

    def dl_poster(path, tid):
        if not path: return None
        fname = f's{tid}.jpg'
        fpath = os.path.join(POSTER_DIR, fname)
        if os.path.exists(fpath): return fname
        try:
            r = requests.get(f'https://image.tmdb.org/t/p/w500{path}', timeout=10)
            if r.status_code == 200 and len(r.content) > 500:
                open(fpath, 'wb').write(r.content)
                return fname
        except Exception:
            pass
        return None

    def insert_series(d, tid, conn):
        lang   = d.get('original_language', '')
        if lang in BAD_LANGS: return False
        gids   = [g['id'] for g in d.get('genres', [])]
        if any(g in gids for g in SKIP_GENRE): return False
        genre  = ', '.join(g['name'] for g in d.get('genres', [])[:3])
        if any(x in genre.lower() for x in ['аниме', 'anime']): return False
        if lang == 'ja' and 16 in gids: return False
        title  = d.get('name') or d.get('original_name', '')
        poster = dl_poster(d.get('poster_path'), tid)
        conn.execute(
            "INSERT OR IGNORE INTO series (title,description,rating,poster,year,genre,seasons,status,tmdb_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, (d.get('overview') or '')[:500], round(d.get('vote_average', 0), 1), poster,
             (d.get('first_air_date') or '')[:4] or None, genre,
             d.get('number_of_seasons', 1),
             'ongoing' if d.get('status') in ('Returning Series', 'In Production') else 'ended',
             tid))
        conn.commit()
        return True

    conn = get_db()
    imported = 0

    # 1. MUST_HAVE список
    for tmdb_id in MUST_HAVE:
        if conn.execute("SELECT 1 FROM series WHERE tmdb_id=?", (tmdb_id,)).fetchone():
            continue
        try:
            r = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}",
                params={'api_key': TMDB_KEY, 'language': 'ru-RU'}, timeout=8)
            if r.status_code != 200: continue
            if insert_series(r.json(), tmdb_id, conn):
                imported += 1
        except Exception:
            pass
        _time.sleep(0.2)

    # 2. Популярные / топ / в эфире — страницы 1-20
    existing = set(r[0] for r in conn.execute("SELECT tmdb_id FROM series WHERE tmdb_id IS NOT NULL").fetchall())
    for endpoint in ['popular', 'top_rated', 'on_the_air']:
        for page in range(1, 21):
            try:
                r = requests.get(
                    f'https://api.themoviedb.org/3/tv/{endpoint}',
                    params={'api_key': TMDB_KEY, 'language': 'ru-RU', 'page': page}, timeout=10)
                items = r.json().get('results', [])
            except Exception:
                continue
            for item in items:
                tid = item.get('id')
                if not tid or tid in existing: continue
                if item.get('vote_average', 0) < 5.0: continue
                lang = item.get('original_language', '')
                gids = item.get('genre_ids', [])
                if lang in BAD_LANGS: continue
                if any(g in gids for g in SKIP_GENRE): continue
                if lang == 'ja' and 16 in gids: continue
                try:
                    d = requests.get(f"https://api.themoviedb.org/3/tv/{tid}",
                        params={'api_key': TMDB_KEY, 'language': 'ru-RU'}, timeout=8).json()
                    if insert_series(d, tid, conn):
                        existing.add(tid)
                        imported += 1
                except Exception:
                    pass
                _time.sleep(0.15)
            _time.sleep(0.1)

    conn.close()
    if imported:
        logger.info(f"auto_import_series: добавлено {imported} сериалов")


if __name__ == "__main__":
    init_db()
    import threading
    threading.Thread(target=auto_import_series, daemon=True).start()
    app.run(debug=True, port=7777, use_reloader=False)

# ================================================================
# ИМПОРТ ФИЛЬМОВ С TMDB  ← НОВОЕ
# ================================================================

def _tmdb_fetch_genres():
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/genre/movie/list",
            params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru-RU'},
            timeout=8)
        return {g['id']: g['name'].capitalize() for g in r.json().get('genres', [])}
    except Exception:
        return {}

def _tmdb_download_poster(poster_path, tmdb_id):
    if not poster_path:
        return None
    filename = f"tmdb_{tmdb_id}.jpg"
    filepath = os.path.join(basedir, "static", "posters", filename)
    if not os.path.exists(filepath):
        try:
            r = requests.get(f"https://image.tmdb.org/t/p/w500{poster_path}", timeout=10)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(r.content)
        except Exception:
            return None
    return filename

def _tmdb_import_movies(pages=5, category='popular'):
    genres_map = _tmdb_fetch_genres()
    conn       = get_db()
    added = skipped = errors = 0

    for page in range(1, pages + 1):
        try:
            r = requests.get(
                f"https://api.themoviedb.org/3/movie/{category}",
                params={'api_key': '15d2ea6d0dc1d476efbca3eba2b9bbfb', 'language': 'ru-RU', 'page': page},
                timeout=10)
            data = r.json()
        except Exception:
            errors += 1
            continue

        for item in data.get('results', []):
            tmdb_id = item.get('id')
            if not tmdb_id:
                continue
            if conn.execute("SELECT 1 FROM movies WHERE tmdb_id=?", (tmdb_id,)).fetchone():
                skipped += 1
                continue

            title      = item.get('title') or item.get('original_title', '')
            orig_title = item.get('original_title', '')
            desc       = item.get('overview', '')
            rating     = round(item.get('vote_average', 0), 1)
            year       = (item.get('release_date') or '')[:4] or None
            orig_lang  = item.get('original_language', 'en')

            g_names = [genres_map.get(gid, '') for gid in item.get('genre_ids', [])]
            genre   = ', '.join(filter(None, g_names))
            if is_blocked_content(orig_lang, genre, title, '', item.get('genre_ids', [])):
                skipped += 1
                continue
            if item.get('adult', False):
                skipped += 1
                continue
            poster  = _tmdb_download_poster(item.get('poster_path'), tmdb_id)

            try:
                conn.execute("""
                    INSERT INTO movies
                        (title, original_title, description, rating, poster, year, genre,
                         tmdb_id, original_language, age_rating)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (title, orig_title, desc, rating, poster, year, genre,
                      tmdb_id, orig_lang, '16+'))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
            except Exception:
                errors += 1

        conn.commit()
        time.sleep(0.3)

    conn.close()
    return added, skipped, errors

@app.route('/admin/import_tmdb', methods=['GET', 'POST'])
def admin_import_tmdb():
    if not is_admin():
        return redirect('/login')

    if request.method == 'POST':
        data     = request.get_json(silent=True) or {}
        pages    = min(max(int(data.get('pages', 5)), 1), 50)
        category = data.get('category', 'popular')
        if category not in ('popular', 'top_rated', 'upcoming', 'now_playing'):
            category = 'popular'
        try:
            added, skipped, errors = _tmdb_import_movies(pages, category)
            return jsonify({
                'success': True,
                'added':   added,
                'skipped': skipped,
                'errors':  errors,
                'message': f'Добавлено: {added}, пропущено: {skipped}, ошибок: {errors}'
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    # GET — HTML страница
    conn         = get_db()
    total_movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()
    cats = {'popular': 'Популярные', 'top_rated': 'Топ рейтинга',
            'upcoming': 'Скоро выйдут', 'now_playing': 'Сейчас в кино'}
    options = ''.join(f'<option value="{k}">{v}</option>' for k,v in cats.items())
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Импорт с TMDB</title>
<style>
*{{box-sizing:border-box}}body{{font-family:sans-serif;background:#111;color:#fff;min-height:100vh;margin:0;display:flex;align-items:center;justify-content:center}}
.box{{background:#1a1a1a;border:1px solid #333;border-radius:16px;padding:40px;max-width:500px;width:100%}}
h2{{color:#800000;margin-top:0}}p{{color:#aaa}}
label{{display:block;margin-bottom:6px;color:#aaa;font-size:14px}}
select,input{{width:100%;padding:12px;background:#222;border:1px solid #444;border-radius:8px;color:#fff;font-size:15px;margin-bottom:16px}}
.btn{{width:100%;padding:14px;background:#800000;border:none;border-radius:8px;color:#fff;font-size:16px;font-weight:700;cursor:pointer}}
.btn:hover{{background:#b30000}}.btn:disabled{{background:#555;cursor:not-allowed}}
.result{{margin-top:20px;padding:16px;border-radius:8px;font-size:15px;display:none}}
.ok{{background:#1a3a1a;border:1px solid #2d6b2d;color:#6fcf6f}}
.err{{background:#3a1a1a;border:1px solid #6b2d2d;color:#cf6f6f}}
.info{{color:#888;font-size:13px;margin-top:8px}}
.back{{display:inline-block;margin-bottom:20px;color:#800000;text-decoration:none;font-size:14px}}
.progress{{height:6px;background:#333;border-radius:3px;margin-top:12px;overflow:hidden;display:none}}
.progress-bar{{height:100%;background:#800000;border-radius:3px;transition:width 0.3s;width:0%}}
</style></head><body>
<div class="box">
  <a href="/admin" class="back">← Назад в админку</a>
  <h2>📥 Импорт фильмов с TMDB</h2>
  <p>В базе сейчас: <b>{total_movies}</b> фильмов</p>
  <label>Категория</label>
  <select id="cat">{options}</select>
  <label>Количество страниц (1 стр = 20 фильмов)</label>
  <input type="number" id="pages" value="5" min="1" max="50">
  <div class="info">5 стр = ~100 фильмов · 10 стр = ~200 · 50 стр = ~1000</div><br>
  <button class="btn" id="btn" onclick="doImport()">🚀 Начать импорт</button>
  <div class="progress" id="prog"><div class="progress-bar" id="bar"></div></div>
  <div class="result" id="res"></div>
</div>
<script>
async function doImport(){{
  const btn  = document.getElementById('btn');
  const res  = document.getElementById('res');
  const prog = document.getElementById('prog');
  const bar  = document.getElementById('bar');
  const pages = parseInt(document.getElementById('pages').value) || 5;
  const cat   = document.getElementById('cat').value;
  btn.disabled = true;
  btn.textContent = '⏳ Загружаем...';
  res.style.display = 'none';
  prog.style.display = 'block';
  // Анимация прогресса
  let pct = 0;
  const timer = setInterval(() => {{ pct = Math.min(pct + 100/pages/3, 92); bar.style.width = pct + '%'; }}, 800);
  try {{
    const r = await fetch('/admin/import_tmdb', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{pages, category: cat}})
    }});
    const d = await r.json();
    clearInterval(timer);
    bar.style.width = '100%';
    res.style.display = 'block';
    if(d.success) {{
      res.className = 'result ok';
      res.innerHTML = '✅ ' + d.message + '<br><small>Обновите страницу для проверки базы</small>';
    }} else {{
      res.className = 'result err';
      res.innerHTML = '❌ ' + d.message;
    }}
  }} catch(e) {{
    clearInterval(timer);
    res.style.display = 'block';
    res.className = 'result err';
    res.innerHTML = '❌ Ошибка: ' + e;
  }}
  btn.disabled = false;
  btn.textContent = '🚀 Начать импорт';
}}
</script></body></html>"""