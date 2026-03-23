-- АКТЕРЫ И СЪЕМОЧНАЯ ГРУППА
CREATE TABLE persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_en TEXT,
    photo TEXT,
    birth_date TEXT,
    birth_place TEXT,
    biography TEXT,
    profession TEXT -- actor, director, writer, producer
);

CREATE TABLE movie_persons (
    movie_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT, -- "Главная роль", "Режиссер"
    character_name TEXT, -- Имя персонажа
    PRIMARY KEY (movie_id, person_id, role),
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- КОЛЛЕКЦИИ ПОЛЬЗОВАТЕЛЕЙ
CREATE TABLE user_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_public INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE collection_items (
    collection_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, movie_id)
);

-- РЕЦЕНЗИИ (расширение comments)
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'neutral', -- positive, negative, neutral
    likes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);

-- ПОДБОРКИ (редакционные)
CREATE TABLE compilations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    cover_image TEXT,
    is_featured INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Добавить в movies
ALTER TABLE movies ADD COLUMN countries TEXT;
ALTER TABLE movies ADD COLUMN budget INTEGER;
ALTER TABLE movies ADD COLUMN box_office INTEGER;
ALTER TABLE movies ADD COLUMN slogan TEXT;