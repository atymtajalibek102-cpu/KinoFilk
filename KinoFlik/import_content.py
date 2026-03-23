import sqlite3, requests, os, time

TMDB_KEY = '15d2ea6d0dc1d476efbca3eba2b9bbfb'
POSTER_DIR = 'static/posters'
os.makedirs(POSTER_DIR, exist_ok=True)

BAD_LANGS   = {'hi','ta','te','kn','ml','mr','gu','zh','cn'}
ANIME_LANGS = {'ja'}
ANIM_GID    = 16
SKIP_TV_G   = {10767, 10764}

def is_blocked(lang, genre_ids, adult=False):
    if adult: return True
    if lang in BAD_LANGS: return True
    if lang in ANIME_LANGS and ANIM_GID in genre_ids: return True
    return False

def dl_poster(path, uid, pfx):
    if not path: return None
    fname = f'{pfx}{uid}.jpg'
    fpath = os.path.join(POSTER_DIR, fname)
    if os.path.exists(fpath): return fname
    try:
        r = requests.get(f'https://image.tmdb.org/t/p/w500{path}', timeout=10)
        if r.status_code == 200:
            open(fpath,'wb').write(r.content)
            return fname
    except:
        pass
    return None

conn = sqlite3.connect('database.db', timeout=60, isolation_level=None)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')

# ================================================================
# СЕРИАЛЫ
# ================================================================
print('=== СЕРИАЛЫ ===')
existing_s = set(r[0] for r in conn.execute(
    'SELECT tmdb_id FROM series WHERE tmdb_id IS NOT NULL').fetchall())
added_s = 0

MUST_TV = [
    1408,108978,70523,2288,18347,1911,4614,1409,1421,46648,
    79460,63351,2490,69050,130392,120168,84912,71712,77169,
    76669,95396,87739,97180,65495,79501,44778,62560,
    63174,37680,66084,15260,19885,30983,62126,2778,35,80276,
    67280,71446,60059,1425,70785,105349,
]

def add_tv(tid):
    global added_s
    if tid in existing_s:
        return
    try:
        d = requests.get(
            f'https://api.themoviedb.org/3/tv/{tid}',
            params={'api_key': TMDB_KEY, 'language': 'ru-RU'}, timeout=8).json()
        gids = [g['id'] for g in d.get('genres', [])]
        lang = d.get('original_language', '')
        if is_blocked(lang, gids):
            return
        title   = d.get('name') or d.get('original_name', '')
        poster  = dl_poster(d.get('poster_path'), tid, 's')
        rating  = round(d.get('vote_average', 0), 1)
        year    = (d.get('first_air_date') or '')[:4]
        genre   = ', '.join(g['name'] for g in d.get('genres', [])[:3])
        seasons = d.get('number_of_seasons', 1)
        status  = 'ongoing' if d.get('status') in (
            'Returning Series', 'In Production') else 'ended'
        conn.execute(
            '''INSERT OR IGNORE INTO series
               (title,description,rating,poster,year,genre,seasons,status,tmdb_id)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (title, d.get('overview', '')[:600], rating, poster,
             year, genre, seasons, status, tid))
        existing_s.add(tid)
        added_s += 1
        print(f'  TV: {title} ({year})')
    except Exception as e:
        print(f'  ERR {tid}: {e}')

for tid in MUST_TV:
    add_tv(tid)
    time.sleep(0.25)
conn.commit()

for endpoint in ['popular', 'top_rated', 'on_the_air']:
    for page in range(1, 10):
        try:
            r = requests.get(
                f'https://api.themoviedb.org/3/tv/{endpoint}',
                params={'api_key': TMDB_KEY, 'language': 'ru-RU', 'page': page},
                timeout=10)
            items = r.json().get('results', [])
        except:
            continue
        for item in items:
            tid = item.get('id')
            if not tid or tid in existing_s:
                continue
            lang = item.get('original_language', '')
            gids = item.get('genre_ids', [])
            if is_blocked(lang, gids):
                continue
            if item.get('vote_average', 0) < 5.5:
                continue
            if any(g in gids for g in SKIP_TV_G):
                continue
            add_tv(tid)
            time.sleep(0.2)
        conn.commit()
        print(f'  {endpoint} стр.{page} — добавлено {added_s}')

total_s = conn.execute('SELECT COUNT(*) FROM series').fetchone()[0]
print(f'Сериалов добавлено: {added_s}, всего: {total_s}')

# ================================================================
# ФИЛЬМЫ — дополнительные жанры и студии
# ================================================================
print('\n=== ДОПОЛНИТЕЛЬНЫЕ ФИЛЬМЫ ===')
existing_m = set(r[0] for r in conn.execute(
    'SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL').fetchall())
added_m = 0

def add_movie(item):
    global added_m
    tid = item.get('id')
    if not tid or tid in existing_m:
        return
    lang  = item.get('original_language', '')
    gids  = item.get('genre_ids', [])
    if is_blocked(lang, gids, item.get('adult', False)):
        return
    if item.get('vote_average', 0) < 4.5:
        return
    title  = item.get('title') or item.get('original_title', '')
    orig   = item.get('original_title', '')
    desc   = item.get('overview', '')
    rat    = round(item.get('vote_average', 0), 1)
    year   = (item.get('release_date') or '')[:4]
    poster = dl_poster(item.get('poster_path'), tid, 'm')
    try:
        conn.execute(
            '''INSERT OR IGNORE INTO movies
               (title,original_title,description,rating,poster,year,
                genre,tmdb_id,original_language,age_rating)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (title, orig, desc, rat, poster, year, '', tid, lang, '16+'))
        existing_m.add(tid)
        added_m += 1
    except:
        pass

# Disney/Pixar/DreamWorks/Warner/Universal + Cartoon Network
for company in [2, 3, 521, 7505, 6704, 174, 33, 2785]:
    for page in range(1, 6):
        try:
            r = requests.get(
                'https://api.themoviedb.org/3/discover/movie',
                params={'api_key': TMDB_KEY, 'language': 'ru-RU', 'page': page,
                        'with_companies': str(company),
                        'sort_by': 'vote_count.desc'}, timeout=10)
            for item in r.json().get('results', []):
                add_movie(item)
            time.sleep(0.2)
        except:
            pass
    conn.commit()
    print(f'  company {company} — фильмов {added_m}')

# Жанры (без инд/кит/аниме)
GENRES = [28,35,18,53,27,878,12,10751,99,80,36,10752,14,9648]
for gid in GENRES:
    for page in range(1, 8):
        try:
            r = requests.get(
                'https://api.themoviedb.org/3/discover/movie',
                params={'api_key': TMDB_KEY, 'language': 'ru-RU', 'page': page,
                        'with_genres': str(gid),
                        'sort_by': 'vote_count.desc',
                        'without_original_language': 'hi,ta,te,zh,ja,cn,ko'},
                timeout=10)
            for item in r.json().get('results', []):
                add_movie(item)
            time.sleep(0.15)
        except:
            pass
    conn.commit()
    print(f'  genre {gid} — фильмов {added_m}')

total_m = conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0]
print(f'Фильмов добавлено: {added_m}, всего: {total_m}')
conn.close()
print('\n=== ИМПОРТ ЗАВЕРШЁН ===')
