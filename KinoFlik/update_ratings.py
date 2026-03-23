"""
Скрипт для обновления рейтингов фильмов и сериалов через TMDB API.
Запуск: python update_ratings.py
"""
import sqlite3
import requests
import time
import os

# Настройки путей и ключей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
TMDB_API_KEY = '15d2ea6d0dc1d476efbca3eba2b9bbfb'  # Ваш ключ из app.py

def update_ratings():
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return

    print(f"🔌 Подключение к базе: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # === 1. ОБНОВЛЕНИЕ СЕРИАЛОВ ===
    print("\n📺 Обновление рейтингов СЕРИАЛОВ...")
    series_list = cursor.execute("SELECT id, title, tmdb_id, rating FROM series WHERE tmdb_id IS NOT NULL").fetchall()
    
    updated_count = 0
    for item in series_list:
        tmdb_id = item['tmdb_id']
        try:
            # Запрос к API
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=ru-RU"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                new_rating = data.get('vote_average')
                
                if new_rating:
                    new_rating = round(float(new_rating), 1)
                    # Если рейтинг изменился — обновляем
                    if new_rating != item['rating']:
                        cursor.execute("UPDATE series SET rating = ? WHERE id = ?", (new_rating, item['id']))
                        print(f"  ✓ {item['title']}: {item['rating']} -> {new_rating}")
                        updated_count += 1
                    else:
                        print(f"  = {item['title']}: без изменений ({new_rating})")
            else:
                print(f"  ⚠️ Ошибка API для {item['title']} (ID: {tmdb_id}): {response.status_code}")

        except Exception as e:
            print(f"  ❌ Ошибка при обновлении {item['title']}: {e}")
        
        # Пауза, чтобы не превысить лимиты API
        time.sleep(0.25)

    # === 2. ОБНОВЛЕНИЕ ФИЛЬМОВ ===
    print("\n🎬 Обновление рейтингов ФИЛЬМОВ...")
    movies_list = cursor.execute("SELECT id, title, tmdb_id, rating FROM movies WHERE tmdb_id IS NOT NULL").fetchall()
    
    for item in movies_list:
        tmdb_id = item['tmdb_id']
        try:
            url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=ru-RU"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                new_rating = data.get('vote_average')
                
                if new_rating:
                    new_rating = round(float(new_rating), 1)
                    if new_rating != item['rating']:
                        cursor.execute("UPDATE movies SET rating = ? WHERE id = ?", (new_rating, item['id']))
                        print(f"  ✓ {item['title']}: {item['rating']} -> {new_rating}")
                        updated_count += 1
                    else:
                        print(f"  = {item['title']}: без изменений ({new_rating})")
        except Exception:
            pass
        time.sleep(0.25)

    conn.commit()
    conn.close()
    print(f"\n✅ Готово! Обновлено записей: {updated_count}")

if __name__ == "__main__":
    update_ratings()
