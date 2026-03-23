"""
KinoFlik — добавление фильмов в базу данных
Запуск: python fix_videos.py
"""
import sqlite3
import os
import requests

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
POSTERS_DIR = os.path.join(BASE_DIR, "static", "posters")

# Создаем папку для постеров, если нет
if not os.path.exists(POSTERS_DIR):
    os.makedirs(POSTERS_DIR)

MOVIES = [
    # (title, original_title, description, rating, poster_url, year, duration, genre, age_rating, trailer_url, tmdb_id, original_language)
    # ── БОЕВИКИ ──
    ("Начало", "Inception", "Вор, способный проникать в сны людей, получает последний шанс — внедрить идею в разум жертвы.", 8.8, "https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg", 2010, 148, "Фантастика, Боевик", "12+", "https://www.youtube.com/embed/YoHD9XEInc0", 27205, "en"),
    ("Интерстеллар", "Interstellar", "Команда исследователей отправляется сквозь червоточину в поисках нового дома для человечества.", 8.6, "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", 2014, 169, "Фантастика, Драма", "12+", "https://www.youtube.com/embed/zSWdZVtXT7E", 157336, "en"),
    ("Тёмный рыцарь", "The Dark Knight", "Бэтмен противостоит Джокеру — преступному гению, сеющему анархию в Готэм-сити.", 9.0, "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", 2008, 152, "Боевик, Криминал", "16+", "https://www.youtube.com/embed/EXeTwQWrcwY", 155, "en"),
    ("Матрица", "The Matrix", "Хакер Нео узнаёт, что реальность — это симуляция, и присоединяется к борьбе против машин.", 8.7, "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", 1999, 136, "Фантастика, Боевик", "16+", "https://www.youtube.com/embed/vKQi3bBA1y8", 603, "en"),
    ("Гладиатор", "Gladiator", "Бывший римский генерал жаждет мести против императора, убившего его семью.", 8.5, "https://image.tmdb.org/t/p/w500/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg", 2000, 155, "Боевик, Драма", "16+", "https://www.youtube.com/embed/owK1qxDselE", 98, "en"),
    ("Джон Уик", "John Wick", "Бывший наёмный убийца мстит за убийство своей собаки — последнего подарка умершей жены.", 7.4, "https://image.tmdb.org/t/p/w500/fZPSd91yGE9fCcCe6OoQr6E3Bev.jpg", 2014, 101, "Боевик, Криминал", "18+", "https://www.youtube.com/embed/2AUmvWm5ZDQ", 245891, "en"),
    ("Миссия невыполнима: Последствия", "Mission: Impossible - Fallout", "Итан Хант должен остановить ядерную катастрофу вместе со старыми и новыми союзниками.", 7.7, "https://image.tmdb.org/t/p/w500/AkJQpZp9WoNdj7pLYSj1L0RcMMN.jpg", 2018, 147, "Боевик, Приключения", "12+", "https://www.youtube.com/embed/wb49-oV0F78", 353081, "en"),
    ("Безумный Макс: Дорога ярости", "Mad Max: Fury Road", "В постапокалиптической пустыне Макс помогает освободить женщин от тирана Несмертного Джо.", 8.1, "https://image.tmdb.org/t/p/w500/8tZYtuWezp8JbcsvHYO0O46tFbo.jpg", 2015, 120, "Боевик, Фантастика", "16+", "https://www.youtube.com/embed/hEJnMQG9ev8", 76341, "en"),
    ("Мстители: Финал", "Avengers: Endgame", "Оставшиеся герои объединяются для последней битвы, чтобы отменить действия Таноса.", 8.4, "https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9sl16pB3iy.jpg", 2019, 181, "Боевик, Фантастика", "12+", "https://www.youtube.com/embed/TcMBFSGVi1c", 299536, "en"),
    ("Топ Ган: Мэверик", "Top Gun: Maverick", "Легендарный лётчик Мэверик обучает новое поколение пилотов для опасной миссии.", 8.3, "https://image.tmdb.org/t/p/w500/62HCnUTHjWTObPnWDypewlyaQBg.jpg", 2022, 130, "Боевик, Драма", "12+", "https://www.youtube.com/embed/giXco2jaZ_4", 361743, "en"),

    # ── ДРАМЫ ──
    ("Побег из Шоушенка", "The Shawshank Redemption", "Невинно осуждённый банкир Энди Дюфрейн выживает в жестокой тюрьме благодаря надежде.", 9.3, "https://image.tmdb.org/t/p/w500/lyQBXzOQSuE59IsHyhrp0qIiPAz.jpg", 1994, 142, "Драма, Криминал", "16+", "https://www.youtube.com/embed/6hB3S9bIaco", 278, "en"),
    ("Крёстный отец", "The Godfather", "История семьи Корлеоне — самой влиятельной мафиозной династии Америки.", 9.2, "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsLlegkAozFAn.jpg", 1972, 175, "Драма, Криминал", "18+", "https://www.youtube.com/embed/sY1S34973zA", 238, "en"),
    ("Список Шиндлера", "Schindler's List", "Немецкий предприниматель спасает более тысячи евреев во время Холокоста.", 9.0, "https://image.tmdb.org/t/p/w500/sF1U4EUQS8YHUYjNl3pMGNIQyr0.jpg", 1993, 195, "Драма, История", "16+", "https://www.youtube.com/embed/gG22XNhtnoY", 424, "en"),
    ("1+1 (Неприкасаемые)", "Intouchables", "Богатый аристократ-инвалид и выходец из трущоб неожиданно становятся лучшими друзьями.", 8.5, "https://image.tmdb.org/t/p/w500/3UkDGEwv6sFzP7WKLDULOEAGMgr.jpg", 2011, 112, "Драма, Комедия", "12+", "https://www.youtube.com/embed/v0UsVqeB-AI", 76203, "fr"),
    ("Форрест Гамп", "Forrest Gump", "Простодушный, но добросердечный человек невольно становится участником ключевых событий истории США.", 8.8, "https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg", 1994, 142, "Драма, Романтика", "12+", "https://www.youtube.com/embed/bLvqoHBptjg", 13, "en"),
    ("Пианист", "The Pianist", "Польский пианист-еврей борется за выживание в Варшавском гетто во Второй мировой войне.", 8.5, "https://image.tmdb.org/t/p/w500/2hFvxCCWrTmCYwfy7yum0GKRi3Y.jpg", 2002, 150, "Драма, История", "16+", "https://www.youtube.com/embed/BFwGqLa_oAo", 423, "en"),
    ("Зелёная миля", "The Green Mile", "Охранник в тюрьме открывает удивительный дар у осуждённого на смертную казнь великана.", 8.6, "https://image.tmdb.org/t/p/w500/velWPhVMQeQKcxggNEU8YmIo52R.jpg", 1999, 189, "Драма, Фэнтези", "16+", "https://www.youtube.com/embed/Ki4haFrqSrw", 497, "en"),
    ("Достучаться до небес", "Knockin' on Heaven's Door", "Два смертельно больных незнакомца угоняют машину и отправляются к морю — впервые в жизни.", 8.1, "https://image.tmdb.org/t/p/w500/2j0NXlbdNJasZM0t3dVbFf67t6A.jpg", 1997, 87, "Драма, Комедия", "16+", "", 18572, "de"),
    ("Жизнь прекрасна", "La vita è bella", "Отец придумывает игру, чтобы защитить сына от ужасов концентрационного лагеря.", 8.6, "https://image.tmdb.org/t/p/w500/mfnkSeeNOry7bRe2JxnlNfwEYlz.jpg", 1997, 116, "Драма, Комедия", "12+", "https://www.youtube.com/embed/mEkU2HoBGMQ", 637, "it"),
    ("Бойцовский клуб", "Fight Club", "Офисный клерк вместе с хаотичным мыльным торговцем создаёт подпольный бойцовский клуб.", 8.8, "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", 1999, 139, "Драма, Триллер", "18+", "https://www.youtube.com/embed/SUXWAEX2jlg", 550, "en"),

    # ── ТРИЛЛЕРЫ ──
    ("Молчание ягнят", "The Silence of the Lambs", "Агент ФБР охотится на серийного убийцу с помощью заключённого психопата-каннибала Лектера.", 8.6, "https://image.tmdb.org/t/p/w500/uS9m8OBk1A8eM9I042bx8XXpqAq.jpg", 1991, 118, "Триллер, Криминал", "18+", "https://www.youtube.com/embed/RuX2MQeb8UM", 274, "en"),
    ("Остров проклятых", "Shutter Island", "Маршал расследует побег пациента из психиатрической больницы на острове и сталкивается с тайнами.", 8.1, "https://image.tmdb.org/t/p/w500/kYFwqiqS5VXiPXDPZKEJimjWLzO.jpg", 2010, 138, "Триллер, Детектив", "16+", "https://www.youtube.com/embed/5iaYLCiq5RM", 11324, "en"),
    ("Семь", "Se7en", "Два детектива расследуют серию убийств, в основе каждого из которых — один из семи смертных грехов.", 8.6, "https://image.tmdb.org/t/p/w500/69Sns8WoET6CfaYlIkHbla4l7nC.jpg", 1995, 127, "Триллер, Криминал", "18+", "https://www.youtube.com/embed/znmZoVkCjpI", 807, "en"),
    ("Исчезнувшая", "Gone Girl", "После исчезновения жены муж становится главным подозреваемым в её убийстве.", 8.1, "https://image.tmdb.org/t/p/w500/pndMSgmHFBvPJFTNEXPbggkPWO3.jpg", 2014, 149, "Триллер, Детектив", "18+", "https://www.youtube.com/embed/p6AuNl2y7F4", 209112, "en"),
    ("Достать ножи", "Knives Out", "Детектив расследует смерть знаменитого писателя, когда вся его семья оказывается под подозрением.", 7.9, "https://image.tmdb.org/t/p/w500/pThyQovXQrws2hmDown1z08Vg4E.jpg", 2019, 130, "Триллер, Комедия", "16+", "https://www.youtube.com/embed/xi-1NchUqMA", 546554, "en"),
    ("Зодиак", "Zodiac", "Репортёр и детектив одержимо ищут маньяка «Зодиак», терроризировавшего Калифорнию в 60–70-е.", 7.7, "https://image.tmdb.org/t/p/w500/e0M5OHKB7iCGnO1CNLFF2YFRoOB.jpg", 2007, 157, "Триллер, Криминал", "16+", "https://www.youtube.com/embed/rOG5rKHrCMU", 1949, "en"),
    ("Игра", "The Game", "Богатому бизнесмену брат дарит необычный подарок — и вскоре его жизнь превращается в кошмар.", 7.8, "https://image.tmdb.org/t/p/w500/hCHXv2IlUQa8jaRKIVNTRKVOWG8.jpg", 1997, 129, "Триллер, Детектив", "16+", "https://www.youtube.com/embed/3S3M0bDxiJE", 714, "en"),

    # ── КОМЕДИИ ──
    ("Один дома", "Home Alone", "Восьмилетний Кевин остался дома один и защищает дом от двух незадачливых воров.", 7.7, "https://image.tmdb.org/t/p/w500/onTSipViPlXcO2enKLkJU7nPvbV.jpg", 1990, 103, "Комедия, Семейный", "6+", "https://www.youtube.com/embed/1BSCO3n7pig", 771, "en"),
    ("Большой Лебовски", "The Big Lebowski", "Праздный лентяй вовлекается в цепь абсурдных событий после того, как его путают с миллионером.", 8.1, "https://image.tmdb.org/t/p/w500/t8QIQzRArHjlqCMEKFMnRJJ0vJV.jpg", 1998, 117, "Комедия, Криминал", "16+", "https://www.youtube.com/embed/cd-go0oBF4Y", 115, "en"),
    ("Брат", "", "Молодой парень из провинции приезжает в Питер и становится киллером вопреки своей воле.", 8.1, "https://image.tmdb.org/t/p/w500/qCRBzZ4Pj28Vj7kMN4c2bIYq59a.jpg", 1997, 100, "Криминал, Драма", "18+", "", 43583, "ru"),
    ("Такси", "Taxi", "Бесстрашный таксист помогает неумелому полицейскому ловить банду румынских грабителей.", 7.3, "https://image.tmdb.org/t/p/w500/iKx1WQ4zCrWBiMHO5FPZHTdE7lA.jpg", 1998, 86, "Комедия, Боевик", "12+", "https://www.youtube.com/embed/DtFKMLfxEq4", 11688, "fr"),
    ("Дьявол носит Prada", "The Devil Wears Prada", "Наивная выпускница попадает ассистентом к самой влиятельной и требовательной редакторше в мире моды.", 6.9, "https://image.tmdb.org/t/p/w500/5TBDLJccjRKlQX0EXcZJEJnxjex.jpg", 2006, 109, "Комедия, Драма", "12+", "https://www.youtube.com/embed/2KGMiNKaTqY", 349, "en"),
    ("Игра на понижение", "The Big Short", "Несколько финансистов предсказали крах ипотечного рынка США и сделали ставки против всей системы.", 7.8, "https://image.tmdb.org/t/p/w500/dXwdTCONZHH4I1B1s9FmEHmkjlE.jpg", 2015, 130, "Комедия, Драма", "16+", "https://www.youtube.com/embed/vgqG3ITMv1Q", 318846, "en"),

    # ── ФАНТАСТИКА ──
    ("Дюна", "Dune", "Юный Пол Атрейдес прибывает на смертоносную пустынную планету Арракис — источник ценнейшего вещества.", 8.0, "https://image.tmdb.org/t/p/w500/d5NXSklpcvwE3HP2SmweEvLqdVU.jpg", 2021, 155, "Фантастика, Приключения", "12+", "https://www.youtube.com/embed/8g18jFHCLXk", 438631, "en"),
    ("Прибытие", "Arrival", "Лингвист пытается установить контакт с инопланетными существами, прибывшими на Землю.", 7.9, "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg", 2016, 116, "Фантастика, Драма", "12+", "https://www.youtube.com/embed/tFMo3UJ4B4g", 329865, "en"),
    ("Марсианин", "The Martian", "Астронавт остаётся брошенным на Марсе и должен выжить, используя лишь науку и смекалку.", 8.0, "https://image.tmdb.org/t/p/w500/5aGhaIHYuQbqlHWvWYqMCnj40y2.jpg", 2015, 144, "Фантастика, Приключения", "12+", "https://www.youtube.com/embed/ej3ioOneTy8", 286217, "en"),
    ("Gravity", "Gravity", "Двое астронавтов выживают в открытом космосе после катастрофы, уничтожившей их шаттл.", 7.7, "https://image.tmdb.org/t/p/w500/44tcBBapFBiDIxklNJbFNZ2IQGW.jpg", 2013, 91, "Фантастика, Триллер", "12+", "https://www.youtube.com/embed/OiTiKOy59o4", 49047, "en"),
    ("Звёздные войны: Новая надежда", "Star Wars: A New Hope", "Молодой фермер Люк Скайуокер вступает в ряды повстанцев, чтобы спасти галактику от тирании Империи.", 8.6, "https://image.tmdb.org/t/p/w500/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg", 1977, 121, "Фантастика, Приключения", "6+", "https://www.youtube.com/embed/1g3_CFmnU7k", 11, "en"),
    ("Бегущий по лезвию 2049", "Blade Runner 2049", "Полицейский К расследует старое дело, которое ставит под угрозу существование цивилизации.", 8.0, "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg", 2017, 164, "Фантастика, Детектив", "16+", "https://www.youtube.com/embed/haAVnXSUXGg", 335984, "en"),
    ("Терминатор 2", "Terminator 2: Judgment Day", "Терминатор из будущего теперь защищает Джона Коннора от более совершенного убийцы Т-1000.", 8.6, "https://image.tmdb.org/t/p/w500/5M0j0B18abtBI5gi3JOGmzIMbFR.jpg", 1991, 137, "Фантастика, Боевик", "16+", "https://www.youtube.com/embed/CRRlbK5w8AE", 280, "en"),
    ("WALL·E", "WALL-E", "Маленький робот-мусорщик на опустевшей Земле влюбляется в робота-разведчика и меняет судьбу человечества.", 8.4, "https://image.tmdb.org/t/p/w500/hbhFnRzzg6ZDmm8YAmxBnQpQIPh.jpg", 2008, 98, "Мультфильм, Фантастика", "0+", "https://www.youtube.com/embed/alIq_wG9FNk", 10681, "en"),

    # ── ПРИКЛЮЧЕНИЯ ──
    ("Индиана Джонс: В поисках утраченного ковчега", "Raiders of the Lost Ark", "Отважный археолог Индиана Джонс ищет Ковчег Завета раньше нацистов.", 8.4, "https://image.tmdb.org/t/p/w500/ceG9VzoRAVGwivFU403Wc3AHRys.jpg", 1981, 115, "Приключения, Боевик", "12+", "https://www.youtube.com/embed/0MUEH6W2oUE", 85, "en"),
    ("Пираты Карибского моря", "Pirates of the Caribbean", "Харизматичный пират Джек Воробей помогает кузнецу спасти возлюбленную от проклятых моряков.", 8.0, "https://image.tmdb.org/t/p/w500/z8onk7LV9Mmw6zKz4hT6pzzvmvl.jpg", 2003, 143, "Приключения, Боевик", "12+", "https://www.youtube.com/embed/naQr0uTrH_s", 22, "en"),
    ("Властелин колец: Братство кольца", "The Lord of the Rings: The Fellowship of the Ring", "Хоббит Фродо вместе с отрядом героев отправляется в опасный поход, чтобы уничтожить Кольцо всевластия.", 8.8, "https://image.tmdb.org/t/p/w500/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg", 2001, 178, "Фэнтези, Приключения", "12+", "https://www.youtube.com/embed/V75dMMIW2B4", 120, "en"),
    ("Хоббит: Нежданное путешествие", "The Hobbit: An Unexpected Journey", "Бильбо Бэггинс отправляется с гномами и волшебником Гэндальфом, чтобы вернуть Одинокую Гору.", 7.8, "https://image.tmdb.org/t/p/w500/yHA9Fc37VmpUA5UncTxxo3rTGVA.jpg", 2012, 169, "Фэнтези, Приключения", "12+", "https://www.youtube.com/embed/SDnYMbYB-nU", 49051, "en"),
    ("Аватар", "Avatar", "Парализованный морпех переселяется в тело аборигена на далёкой планете и встаёт на защиту её жителей.", 7.9, "https://image.tmdb.org/t/p/w500/jRXYjXNq0Cs2TcJjLkki24MLp7u.jpg", 2009, 162, "Фантастика, Приключения", "12+", "https://www.youtube.com/embed/5PSNL1qE6VY", 19995, "en"),
    ("Король Лев", "The Lion King", "Молодой лев Симба бежит от ответственности после гибели отца, но судьба заставляет его вернуться.", 8.5, "https://image.tmdb.org/t/p/w500/sKCr78MXSLixwmZ8DyJLrpMsd15.jpg", 1994, 88, "Мультфильм, Приключения", "0+", "https://www.youtube.com/embed/4sj1MT05lAA", 8587, "en"),

    # ── КРИМИНАЛ ──
    ("Криминальное чтиво", "Pulp Fiction", "Переплетающиеся истории о гангстерах, боксёре и кинорежиссёре в причудливом голливудском андеграунде.", 8.9, "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg", 1994, 154, "Криминал, Драма", "18+", "https://www.youtube.com/embed/s7EdQ4FqbhY", 680, "en"),
    ("Однажды в Голливуде", "Once Upon a Time in Hollywood", "Актёр и его дублёр пытаются найти себя в меняющемся Голливуде 1969 года.", 7.6, "https://image.tmdb.org/t/p/w500/8j58iEBw9pOXFD2L0nt0ZXeHviB.jpg", 2019, 161, "Драма, Криминал", "18+", "https://www.youtube.com/embed/ELeMaP8EPAA", 466272, "en"),
    ("Бешеные псы", "Reservoir Dogs", "Ограбление ювелирного магазина проваливается — и выжившие начинают подозревать друг друга в предательстве.", 8.3, "https://image.tmdb.org/t/p/w500/xi8Iu6qyTfyZVDVy60raIOYJJmk.jpg", 1992, 99, "Криминал, Триллер", "18+", "https://www.youtube.com/embed/6Y-vOQLnCDk", 500, "en"),
    ("Отступники", "The Departed", "Внедрённый агент в банде и крот в полиции охотятся друг за другом в Бостоне.", 8.5, "https://image.tmdb.org/t/p/w500/nT97ifVT2J1yMQmeq20Qblg61T.jpg", 2006, 151, "Криминал, Триллер", "18+", "https://www.youtube.com/embed/SGWjGM1gWMY", 1422, "en"),
    ("Хороший, плохой, злой", "The Good, the Bad and the Ugly", "Три стрелка ищут золото в жестоком мире Дикого Запада времён Гражданской войны.", 8.8, "https://image.tmdb.org/t/p/w500/bX2xnavhMYjWDoZp1VM6VnU1xwe.jpg", 1966, 178, "Вестерн, Криминал", "12+", "https://www.youtube.com/embed/WCN5JJY_wiA", 1429, "it"),

    # ── РОССИЙСКИЕ ──
    ("Иван Васильевич меняет профессию", "", "Изобретатель случайно переносит царя Ивана Грозного в современную Москву.", 8.6, "https://image.tmdb.org/t/p/w500/cQyEiQXWqJbWScSTOGHQAolzwMl.jpg", 1973, 88, "Комедия, Фантастика", "0+", "", None, "ru"),
    ("Брат 2", "", "Данила Багров отправляется в Америку, чтобы восстановить справедливость.", 7.9, "https://image.tmdb.org/t/p/w500/4PXAjFDEXOy27BgNJxpXFI4JjHY.jpg", 2000, 127, "Криминал, Боевик", "18+", "", None, "ru"),
    ("Морозко", "", "Добрая девушка Настенька получает награду от Морозко, а злая Марфушенька — нет.", 8.3, "https://image.tmdb.org/t/p/w500/7DxJAP5DQ6BqgW7lHMoMjNjFCpT.jpg", 1964, 84, "Сказка, Семейный", "0+", "", None, "ru"),
    ("Сталкер", "", "Проводник ведёт двух людей через таинственную Зону к комнате, где исполняются желания.", 8.1, "https://image.tmdb.org/t/p/w500/cFnvSM0HIZS2EcJLTZDFKR0H3YZ.jpg", 1979, 162, "Фантастика, Драма", "12+", "", 10929, "ru"),
    ("Экипаж", "", "Советский экипаж самолёта спасает пассажиров во время катастрофы на острове.", 7.8, "https://image.tmdb.org/t/p/w500/pDtLlCZHdBqnEiJA1C8rPMKMOOH.jpg", 1979, 138, "Драма, Боевик", "12+", "", None, "ru"),
    ("Движение вверх", "", "История легендарной победы советской сборной по баскетболу на Олимпиаде-1972.", 7.8, "https://image.tmdb.org/t/p/w500/6YbLRFkm3StMmfK6Oq8B1fkl0i2.jpg", 2017, 138, "Спорт, Драма", "12+", "https://www.youtube.com/embed/wXYA-FE3oYU", None, "ru"),

    # ── МУЛЬТФИЛЬМЫ ──
    ("Вверх", "Up", "Пожилой воздухоплаватель отправляется в путешествие мечты, привязав к дому тысячи воздушных шаров.", 8.3, "https://image.tmdb.org/t/p/w500/vpiaT169BzvU2UIiMc2bUDMeIBc.jpg", 2009, 96, "Мультфильм, Приключения", "0+", "https://www.youtube.com/embed/ORFWdXl_zJ4", 14160, "en"),
    ("Головоломка", "Inside Out", "Эмоции в голове маленькой девочки переживают настоящий кризис, когда она переезжает в новый город.", 8.2, "https://image.tmdb.org/t/p/w500/aAmfIX37osiPawIpY9N9TJgL2g5.jpg", 2015, 95, "Мультфильм, Комедия", "0+", "https://www.youtube.com/embed/yRUAzGQ3nSY", 150540, "en"),
    ("Тайна Коко", "Coco", "Мальчик-музыкант попадает в страну мёртвых и открывает тайну своей семьи.", 8.4, "https://image.tmdb.org/t/p/w500/gGEsBPAijhVUFoiNpgZXqRVWJt2.jpg", 2017, 105, "Мультфильм, Музыка", "0+", "https://www.youtube.com/embed/Rvr68u6k5sI", 354912, "en"),
    ("Паук-человек: Через вселенные", "Spider-Man: Into the Spider-Verse", "Подросток Майлз Моралес открывает удивительный мультивёрс, встречая множество версий Человека-Паука.", 8.4, "https://image.tmdb.org/t/p/w500/iiZZdoQBEYBv6id8su7ImL0oCbD.jpg", 2018, 117, "Мультфильм, Боевик", "6+", "https://www.youtube.com/embed/tg52up16eq0", 324857, "en"),
    ("Унесённые призраками", "Spirited Away", "Девочка попадает в загадочный мир духов и должна спасти превращённых в свиней родителей.", 8.6, "https://image.tmdb.org/t/p/w500/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg", 2001, 125, "Мультфильм, Фэнтези", "6+", "https://www.youtube.com/embed/ByXuk9QqQkk", 129, "ja"),
    ("Принцесса Мононоке", "Princess Mononoke", "В древней Японии молодой принц ищет лекарство от проклятия среди богов природы и людей.", 8.4, "https://image.tmdb.org/t/p/w500/wrFpXMNBZj lZjFOKcVaDv4yHbKV.jpg", 1997, 134, "Мультфильм, Фэнтези", "12+", "https://www.youtube.com/embed/4OiMOHRDs14", 128, "ja"),

    # ── РОМАНТИКА ──
    ("Ла-Ла Ленд", "La La Land", "В Лос-Анджелесе встречаются мечтательница-актриса и джазовый пианист, которые вдохновляют друг друга.", 8.0, "https://image.tmdb.org/t/p/w500/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg", 2016, 128, "Мелодрама, Музыка", "12+", "https://www.youtube.com/embed/0pdqf4P9MB8", 313369, "en"),
    ("Дневник памяти", "The Notebook", "Пожилой мужчина читает своей любимой историю о двух влюблённых из разных социальных слоёв.", 7.8, "https://image.tmdb.org/t/p/w500/rNzQyW4f8B8cQeg7Dgj3n6eT5k9.jpg", 2004, 123, "Мелодрама, Драма", "12+", "https://www.youtube.com/embed/DFPAMcGhAos", 16987, "en"),
    ("Красавица и чудовище", "Beauty and the Beast", "Юная Белль в заколдованном замке открывает истинную красоту чудовища — принца под проклятием.", 8.0, "https://image.tmdb.org/t/p/w500/tBiUBdskU3SR4HkXH7UB25OL4AV.jpg", 1991, 84, "Мультфильм, Романтика", "0+", "https://www.youtube.com/embed/tXbCRUuSFlM", 10020, "en"),
    ("Титаник", "Titanic", "Любовь между бедным художником и богатой аристократкой расцветает на борту обречённого лайнера.", 7.9, "https://image.tmdb.org/t/p/w500/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg", 1997, 194, "Мелодрама, Драма", "12+", "https://www.youtube.com/embed/kVrqfYjkTdQ", 597, "en"),

    # ── УЖАСЫ ──
    ("Оно", "It", "Группа детей сталкивается с древним злом, принимающим облик клоуна Пеннивайза.", 7.3, "https://image.tmdb.org/t/p/w500/9E2y5Q7WlCVNEhP5GkVComRqLGy.jpg", 2017, 135, "Ужасы, Триллер", "18+", "https://www.youtube.com/embed/FnCdOQsX5kc", 346648, "en"),
    ("Сияние", "The Shining", "Писатель с семьёй заселяется на зиму в отель, где темнота и одиночество доводят его до безумия.", 8.4, "https://image.tmdb.org/t/p/w500/b6ko0IKC8MdYBBPkkA1aBPLe2yz.jpg", 1980, 146, "Ужасы, Триллер", "18+", "https://www.youtube.com/embed/5Cb3ik6zP2I", 694, "en"),
    ("Прочь", "Get Out", "Темнокожий парень едет знакомиться с родителями подруги и обнаруживает жуткую правду о них.", 7.7, "https://image.tmdb.org/t/p/w500/tFXcEccSQMf3lfhfXKSU9iRBpa3.jpg", 2017, 104, "Ужасы, Триллер", "16+", "https://www.youtube.com/embed/sRfnevzM9kQ", 419430, "en"),
    ("Реквием по мечте", "Requiem for a Dream", "Истории наркозависимых людей, чьи мечты рушатся под натиском разрушительной зависимости.", 8.3, "https://image.tmdb.org/t/p/w500/nOd6vjEmzCT0k4VYqsA2hwyi87C.jpg", 2000, 102, "Драма, Ужасы", "18+", "https://www.youtube.com/embed/24ylMBfKhEQ", 641, "en"),

    # ── ДОКУМЕНТАЛЬНЫЕ ──
    ("Планета Земля 2", "Planet Earth II", "Сэр Дэвид Аттенборо рассказывает об удивительных историях выживания животных в дикой природе.", 9.5, "https://image.tmdb.org/t/p/w500/kVEFZg47Y0i1rFVuQRfNX8PBrhs.jpg", 2016, 60, "Документальный", "0+", "", 65588, "en"),
    ("Социальная дилемма", "The Social Dilemma", "Бывшие сотрудники технологических компаний рассказывают, как соцсети манипулируют нашим сознанием.", 7.6, "https://image.tmdb.org/t/p/w500/kuSHoUHVJKTYMRDNQf43LxOi3dA.jpg", 2020, 94, "Документальный, Драма", "12+", "https://www.youtube.com/embed/uaaC57tcci0", 706745, "en"),

    # ── ИСТОРИЧЕСКИЕ ──
    ("Операция Арго", "Argo", "Агент ЦРУ планирует дерзкую операцию под прикрытием съёмок фантастического фильма, чтобы спасти заложников.", 7.7, "https://image.tmdb.org/t/p/w500/fxgbLnXn7A8diqLQMjNl4GlZMQm.jpg", 2012, 120, "История, Триллер", "12+", "https://www.youtube.com/embed/6MeCs8BNV5o", 68734, "en"),
    ("Король говорит!", "The King's Speech", "Король Георг VI преодолевает заикание с помощью необычного логопеда накануне Второй мировой войны.", 8.0, "https://image.tmdb.org/t/p/w500/qwfzEMCpkxGMYPiCqkzpkSZdCuL.jpg", 2010, 118, "История, Драма", "12+", "https://www.youtube.com/embed/EcxBrTvLbBM", 45269, "en"),
    ("Игра в имитацию", "The Imitation Game", "Математик Алан Тьюринг взламывает «Энигму» — секретный шифр нацистской Германии.", 8.0, "https://image.tmdb.org/t/p/w500/noUp0XOqIcmgefRnRZa1nhtRvWO.jpg", 2014, 114, "История, Драма", "12+", "https://www.youtube.com/embed/S5CjKEFb-sM", 205596, "en"),
    ("Оппенгеймер", "Oppenheimer", "История создателя атомной бомбы и нравственных последствий величайшего научного открытия XX века.", 8.9, "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg", 2023, 180, "История, Драма", "16+", "https://www.youtube.com/embed/uYPbbksJxIg", 872585, "en"),
    ("Ярость", "Fury", "Командир танка ведёт свой экипаж в последние дни Второй мировой войны вглубь нацистской Германии.", 7.6, "https://image.tmdb.org/t/p/w500/pfte7wdMobmaHOfOZved71xaFxR.jpg", 2014, 134, "Война, Боевик", "18+", "https://www.youtube.com/embed/e7U0NzCNTDc", 228150, "en"),
    ("Дюнкерк", "Dunkirk", "Британские войска в 1940 году ждут эвакуации с пляжей Дюнкерка под огнём немецких войск.", 7.9, "https://image.tmdb.org/t/p/w500/ebSnOjox4w93fAImf3LUVGFOnYO.jpg", 2017, 106, "Война, Боевик", "12+", "https://www.youtube.com/embed/F-eMt3SrfOY", 374720, "en"),

    # ── СПОРТ ──
    ("Рокки", "Rocky", "Боксёр-любитель из трущоб получает шанс бороться за чемпионский титр с непобедимым Аполло Кридом.", 8.1, "https://image.tmdb.org/t/p/w500/sRBsB67gFhKGhHhxe0bKGGgAAE7.jpg", 1976, 120, "Спорт, Драма", "12+", "https://www.youtube.com/embed/5pTQX6endGw", 1366, "en"),
    ("Легенда 17", "", "История легендарного хоккеиста Валерия Харламова и его пути к победе над командой Канады.", 8.0, "https://image.tmdb.org/t/p/w500/h42r0pAHClkHuLiHHZ6gZiHCEHs.jpg", 2013, 136, "Спорт, Драма", "12+", "https://www.youtube.com/embed/1ZMlWU1JfYs", None, "ru"),

    # ── БИОГРАФИИ ──
    ("Социальная сеть", "The Social Network", "Амбициозный студент Гарварда создаёт Facebook и становится самым молодым миллиардером в истории.", 7.7, "https://image.tmdb.org/t/p/w500/n0ybibhJtQ5icDqTp8eRytcIHJx.jpg", 2010, 120, "Биография, Драма", "12+", "https://www.youtube.com/embed/lB95KLmpLR4", 37799, "en"),
    ("Стив Джобс", "Steve Jobs", "Три запуска продуктов раскрывают сложный характер основателя Apple перед аудиторией и командой.", 7.2, "https://image.tmdb.org/t/p/w500/rDfzZcXkf1bV9I9v15pKlaqVxJj.jpg", 2015, 122, "Биография, Драма", "12+", "https://www.youtube.com/embed/aELGJ2HkR3g", 321697, "en"),
    ("Поймай меня, если сможешь", "Catch Me If You Can", "Молодой аферист Фрэнк Абигнейл десятилетиями обманывает авиакомпании и банки, а ФБР гонится за ним.", 8.1, "https://image.tmdb.org/t/p/w500/lyJHUZmukoTeaE3RaFplH4ASSPZ.jpg", 2002, 141, "Биография, Криминал", "12+", "https://www.youtube.com/embed/jEBgFXENKCc", 640, "en"),

    # ── АЗИАТСКОЕ КИНО ──
    ("Паразиты", "Parasite", "Бедная корейская семья хитростью проникает в жизнь богатых соседей и запускает роковую цепь событий.", 8.5, "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", 2019, 132, "Триллер, Драма", "16+", "https://www.youtube.com/embed/5xH0HfJHsaY", 496243, "ko"),
    ("Олдбой", "Oldboy", "Мужчина, 15 лет проведший в заточении, пытается выяснить, кто его запер и за что.", 8.4, "https://image.tmdb.org/t/p/w500/pWDtjs568ZfOTMbURQBYuT4Qxka.jpg", 2003, 120, "Триллер, Криминал", "18+", "https://www.youtube.com/embed/2GrqXbL0iLo", 670, "ko"),
    ("Воин из стали", "IP Man", "Реальная история мастера боевых искусств, защищавшего честь Китая в японской оккупации.", 8.0, "https://image.tmdb.org/t/p/w500/mPpkEHAKdTPfiBfkSUzlnXqNJTM.jpg", 2008, 106, "Боевик, Биография", "16+", "https://www.youtube.com/embed/bSS4TmVd3dU", 19275, "zh"),
]


def download_poster(url):
    if not url:
        return None
    try:
        filename = url.split('/')[-1]
        filepath = os.path.join(POSTERS_DIR, filename)
        
        # Если файл уже есть, не качаем заново
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


def add_movies():
    if not os.path.exists(DB_PATH):
        print(f"ОШИБКА: база данных не найдена по пути: {DB_PATH}")
        print("Убедитесь, что скрипт лежит в той же папке, что и database.db")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    added   = 0
    skipped = 0

    for m in MOVIES:
        (title, orig_title, desc, rating, poster, year,
         duration, genre, age_rating, trailer_url, tmdb_id, orig_lang) = m

        # Скачиваем постер
        poster_filename = download_poster(poster)

        # Проверяем дубликат по названию
        exists = conn.execute(
            "SELECT id FROM movies WHERE title = ?", (title,)
        ).fetchone()

        if exists:
            skipped += 1
            continue

        try:
            conn.execute("""
                INSERT INTO movies
                    (title, original_title, description, rating, poster,
                     year, duration, genre, age_rating, trailer_url,
                     tmdb_id, original_language)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (title, orig_title, desc, rating, poster_filename,
                  year, str(duration), genre, age_rating, trailer_url,
                  tmdb_id, orig_lang))
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()

    print(f"✓ Добавлено:  {added} фильмов")
    print(f"  Пропущено:  {skipped} (уже были в базе)")
    print(f"  Итого в БД: {total} фильмов")
    print()
    print("Готово! Перезапусти Flask и обнови страницу /movie")


if __name__ == "__main__":
    add_movies()
