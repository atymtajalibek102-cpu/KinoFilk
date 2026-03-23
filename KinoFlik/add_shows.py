import sqlite3
import os
import requests

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
POSTERS_DIR = os.path.join(BASE_DIR, "static", "posters")

if not os.path.exists(POSTERS_DIR):
    os.makedirs(POSTERS_DIR)

def download_poster(url):
    if not url or not url.startswith('http'):
        return url  # Если это локальный файл или None, возвращаем как есть
    try:
        filename = url.split('/')[-1]
        filepath = os.path.join(POSTERS_DIR, filename)
        
        if os.path.exists(filepath):
            return filename
            
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filename
    except Exception as e:
        print(f"Ошибка загрузки постера {url}: {e}")
    return None

def add_shows():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Формат: (Название, Оригинал, Описание, Постер, Год, Рейтинг, Жанр, Возраст, Сезоны_Эпизоды (dict), TMDB_ID)
    shows = [
        ("Гравити Фолз", "Gravity Falls", "Близнецы Диппер и Мэйбл Пайнс отправляются на летние каникулы к своему двоюродному дедушке Стэну в городок Гравити Фолз, где их ждут невероятные мистические тайны.", "https://image.tmdb.org/t/p/w500/q32wRCJ7iv3aX8q38Fv68Xuz3iR.jpg", 2012, 8.9, "Мультфильм, Комедия, Фантастика", "12+", {1: 20, 2: 20}, 40075),
        ("Аватар: Легенда об Аанге", "Avatar: The Last Airbender", "Мир поделен на четыре нации...", "https://image.tmdb.org/t/p/w500/cHQF2x1n557077rQ9k8588c7rB.jpg", 2005, 9.3, "Мультфильм, Фэнтези, Боевик", "12+", {1: 20, 2: 20, 3: 21}, 246),
        ("Черепашки-ниндзя", "Teenage Mutant Ninja Turtles", "Четыре брата-мутанта сражаются со злом...", "https://image.tmdb.org/t/p/w500/s2d2d9x3z3z3z3z3.jpg", 2012, 8.1, "Мультфильм, Боевик, Фантастика", "12+", {1: 26, 2: 26, 3: 26, 4: 26, 5: 20}, 43140),
        
        # === НОВЫЙ СЕРИАЛ ===
        ("Рик и Морти", "Rick and Morty", "Гениальный ученый-алкоголик Рик Санчез вовлекает своего внука Морти в безумные межгалактические приключения.", "https://image.tmdb.org/t/p/w500/cvhNj9eoRBe5SxjCbQTkh05UP5K.jpg", 2013, 9.1, "Мультфильм, Комедия, Фантастика", "16+", {1: 11, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 10}, 60625),

        # === НОВЫЕ МУЛЬТСЕРИАЛЫ ===
        ("Губка Боб квадратные штаны", "SpongeBob SquarePants", "Население подводного городка Бикини Боттом составляют разные морские обитатели. Главный герой — Губка Боб, который работает поваром в закусочной.", "https://image.tmdb.org/t/p/w500/mabuNsGJgRuCTuGqjFkWe1xdu19.jpg", 1999, 7.6, "Мультфильм, Комедия, Семейный", "6+", {1: 20, 2: 39, 3: 37, 4: 38, 5: 41, 6: 47, 7: 50, 8: 47, 9: 49, 10: 22, 11: 50, 12: 48, 13: 26, 14: 13}, 3151),
        ("Симпсоны", "The Simpsons", "Многосерийный мультфильм, высмеивающий стиль жизни среднестатистического американца.", "https://image.tmdb.org/t/p/w500/vHGEg6i00A2OIfA0B69v9sQz2sS.jpg", 1989, 8.0, "Мультфильм, Комедия", "16+", {1: 13, 2: 22, 3: 24, 4: 22, 5: 22, 6: 25, 7: 25, 8: 25, 9: 25, 10: 23, 11: 22, 12: 21, 13: 22, 14: 22, 15: 22, 16: 21, 17: 22, 18: 22, 19: 20, 20: 21, 21: 23, 22: 22, 23: 22, 24: 22, 25: 22, 26: 22, 27: 22, 28: 22, 29: 21, 30: 23, 31: 22, 32: 22, 33: 22, 34: 22, 35: 18}, 456)
    ]

    for title, orig, desc, poster_url, year, rating, genre, age, seasons_dict, tmdb_id in shows:
        # Скачиваем постер
        poster = download_poster(poster_url)

        c.execute("SELECT id FROM series WHERE title=?", (title,))
        row = c.fetchone()
        if not row:
            print(f"Добавляем сериал: {title}")
            c.execute('''INSERT INTO series 
                (title, original_title, description, poster, year, rating, genre, seasons, tmdb_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (title, orig, desc, poster, year, rating, genre, len(seasons_dict), tmdb_id))
            series_id = c.lastrowid
        else:
            print(f"Сериал уже есть: {title}. Обновляем серии...")
            series_id = row[0]
            # Сначала удаляем старые серии-заглушки
            c.execute("DELETE FROM episodes WHERE series_id=?", (series_id,))
            c.execute("UPDATE series SET description=?, poster=?, seasons=?, tmdb_id=? WHERE id=?", 
                      (desc, poster, len(seasons_dict), tmdb_id, series_id))
            
        # Добавляем правильное количество эпизодов для каждого сезона
        for s, eps_count in seasons_dict.items():
            for e in range(1, eps_count + 1):
                c.execute('''INSERT INTO episodes 
                    (series_id, season, ep_num, title, video_url) 
                    VALUES (?, ?, ?, ?, ?)''',
                    (series_id, s, e, f"Серия {e}", "")) # Оставляем пустым, watch.html подгрузит через TMDB_ID

    conn.commit()
    conn.close()
    print("Готово! Сериалы добавлены.")

if __name__ == '__main__':
    add_shows()
