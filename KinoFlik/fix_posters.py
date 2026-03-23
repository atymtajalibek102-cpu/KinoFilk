import sqlite3, requests, os, time, re

TMDB_KEY   = '15d2ea6d0dc1d476efbca3eba2b9bbfb'
POSTER_DIR = 'static/posters'
os.makedirs(POSTER_DIR, exist_ok=True)

conn = sqlite3.connect('database.db', timeout=60, isolation_level=None)
conn.row_factory = sqlite3.Row

def dl(url, fname):
    path = os.path.join(POSTER_DIR, fname)
    if os.path.exists(path):
        return fname
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200 and len(r.content) > 1000:
            open(path, 'wb').write(r.content)
            print(f'  OK  {fname}')
            return fname
    except Exception as e:
        print(f'  ERR {fname}: {e}')
    return None

fixed = 0

# ── 1. poster = full URL (needs download + DB update) ──────────────────────
print('=== Постеры — полные URL ===')
for table, pfx, id_col, watch_col in [
    ('movies', 'm', 'id', 'tmdb_id'),
    ('series', 's', 'id', 'tmdb_id'),
]:
    rows = conn.execute(
        f"SELECT {id_col}, tmdb_id, poster FROM {table} "
        f"WHERE poster LIKE 'http%'"
    ).fetchall()
    for row in rows:
        url  = row['poster']
        tid  = row['tmdb_id']
        rid  = row[id_col]
        # derive local filename
        # try to extract the TMDB path filename
        m = re.search(r'/([^/]+\.jpg)', url)
        if m:
            fname = pfx + str(tid) + '.jpg' if tid else m.group(1)
        else:
            fname = pfx + str(rid) + '.jpg'
        result = dl(url, fname)
        if result:
            conn.execute(f'UPDATE {table} SET poster=? WHERE {id_col}=?', (result, rid))
            fixed += 1
        time.sleep(0.1)

# ── 2. poster = local filename but file missing ─────────────────────────────
print('\n=== Постеры — файл отсутствует, повторная загрузка ===')
for table, pfx in [('movies', 'm'), ('series', 's')]:
    rows = conn.execute(
        f"SELECT id, tmdb_id, poster FROM {table} "
        f"WHERE poster IS NOT NULL AND poster != '' AND poster NOT LIKE 'http%'"
    ).fetchall()
    for row in rows:
        fname = row['poster']
        path  = os.path.join(POSTER_DIR, fname)
        if os.path.exists(path):
            continue
        tid = row['tmdb_id']
        if not tid:
            print(f'  SKIP (no tmdb_id) {table} id={row["id"]} poster={fname}')
            continue
        ep = 'movie' if table == 'movies' else 'tv'
        try:
            d = requests.get(
                f'https://api.themoviedb.org/3/{ep}/{tid}',
                params={'api_key': TMDB_KEY}, timeout=8).json()
            ppath = d.get('poster_path')
            if ppath:
                new_fname = pfx + str(tid) + '.jpg'
                url = f'https://image.tmdb.org/t/p/w500{ppath}'
                result = dl(url, new_fname)
                if result:
                    conn.execute(f'UPDATE {table} SET poster=? WHERE id=?', (result, row['id']))
                    fixed += 1
        except Exception as e:
            print(f'  ERR {table} id={row["id"]}: {e}')
        time.sleep(0.15)

# ── 3. poster IS NULL but tmdb_id exists ───────────────────────────────────
print('\n=== Постеры — NULL, есть tmdb_id ===')
for table, pfx in [('movies', 'm'), ('series', 's')]:
    rows = conn.execute(
        f"SELECT id, tmdb_id FROM {table} WHERE (poster IS NULL OR poster='') AND tmdb_id IS NOT NULL"
    ).fetchall()
    for row in rows:
        tid = row['tmdb_id']
        ep  = 'movie' if table == 'movies' else 'tv'
        try:
            d = requests.get(
                f'https://api.themoviedb.org/3/{ep}/{tid}',
                params={'api_key': TMDB_KEY}, timeout=8).json()
            ppath = d.get('poster_path')
            if ppath:
                fname  = pfx + str(tid) + '.jpg'
                url    = f'https://image.tmdb.org/t/p/w500{ppath}'
                result = dl(url, fname)
                if result:
                    conn.execute(f'UPDATE {table} SET poster=? WHERE id=?', (result, row['id']))
                    fixed += 1
        except Exception as e:
            print(f'  ERR {table} id={row["id"]}: {e}')
        time.sleep(0.15)

conn.close()
print(f'\nГотово! Исправлено: {fixed}')
