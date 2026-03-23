"""
fix_ids_admin.py — KinoFlik
===========================
1. Переделывает ID фильмов/сериалов на 8-значные случайные числа
2. Выдаёт права администратора пользователю по его ID

Запуск из папки KinoFlik:
    python fix_ids_admin.py

Или только выдать админку:
    python fix_ids_admin.py --admin 12345678
"""

import sqlite3, random, os, sys, argparse

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

# ─── генерация уникального 8-значного ID ───────────────────
def gen_id(cursor, table):
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        cursor.execute(f'SELECT 1 FROM {table} WHERE id=?', (new_id,))
        if not cursor.fetchone():
            return new_id

# ─── перемиграция таблицы с новыми ID ──────────────────────
def remap_table(conn, table, fk_refs=None):
    """
    fk_refs — список кортежей (таблица, колонка) которые ссылаются на этот table.id
    """
    cur = conn.cursor()
    cur.execute(f'SELECT id FROM {table}')
    old_ids = [r[0] for r in cur.fetchall()]

    if not old_ids:
        print(f'  {table}: нет записей, пропускаем')
        return {}

    mapping = {}   # old_id -> new_id

    print(f'  {table}: {len(old_ids)} записей...')

    # Сначала сдвигаем все ID в отрицательную зону чтобы избежать конфликтов
    for old in old_ids:
        cur.execute(f'UPDATE {table} SET id=? WHERE id=?', (-old, old))

    # Потом присваиваем новые 8-значные
    for old in old_ids:
        new = gen_id(cur, table)
        cur.execute(f'UPDATE {table} SET id=? WHERE id=?', (new, -old))
        mapping[old] = new
        print(f'    {old:>12} → {new}')

    # Обновляем внешние ключи
    if fk_refs:
        for fk_table, fk_col in fk_refs:
            # проверяем что таблица и колонка существуют
            try:
                for old, new in mapping.items():
                    cur.execute(
                        f'UPDATE {fk_table} SET {fk_col}=? WHERE {fk_col}=?',
                        (new, old)
                    )
                print(f'    ↳ внешний ключ обновлён: {fk_table}.{fk_col}')
            except Exception as e:
                print(f'    ↳ предупреждение {fk_table}.{fk_col}: {e}')

    return mapping


# ─── выдать/снять админку ──────────────────────────────────
def set_admin(conn, user_id, admin=True):
    cur = conn.cursor()
    cur.execute('SELECT id, name, email, role FROM users WHERE id=?', (user_id,))
    row = cur.fetchone()
    if not row:
        print(f'\n❌  Пользователь с ID={user_id} не найден в базе!')
        print('   Зарегистрируйся на сайте, потом узнай свой ID в профиле и запусти снова.')
        return False

    uid, name, email, current_role = row
    new_role = 'admin' if admin else 'user'
    cur.execute('UPDATE users SET role=? WHERE id=?', (new_role, uid))
    conn.commit()

    action = 'выдана' if admin else 'снята'
    print(f'\n✅  Готово! Роль "{new_role}" {action} для пользователя:')
    print(f'   ID:    {uid}')
    print(f'   Имя:   {name}')
    print(f'   Email: {email}')
    print(f'   Была:  {current_role}  →  Стала: {new_role}')
    return True


# ─── показать всех пользователей ──────────────────────────
def list_users(conn):
    cur = conn.cursor()
    cur.execute('SELECT id, name, email, role FROM users ORDER BY id')
    rows = cur.fetchall()
    if not rows:
        print('В базе нет пользователей. Зарегистрируйся на сайте.')
        return
    print(f'\n{"ID":>12}  {"Имя":<20}  {"Email":<30}  Роль')
    print('─' * 75)
    for uid, name, email, role in rows:
        marker = ' ← ТЫ?' if role == 'admin' else ''
        print(f'{uid:>12}  {(name or "—"):<20}  {(email or "—"):<30}  {role}{marker}')


# ─── главная функция ──────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='KinoFlik — управление ID и правами')
    parser.add_argument('--admin',       type=int, help='Выдать права admin пользователю с этим ID')
    parser.add_argument('--remove-admin',type=int, help='Снять права admin у пользователя с этим ID')
    parser.add_argument('--users',       action='store_true', help='Показать всех пользователей')
    parser.add_argument('--fix-ids',     action='store_true', help='Сделать ID фильмов 8-значными')
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f'❌  База данных не найдена: {DB_PATH}')
        print('   Убедись что запускаешь скрипт из папки KinoFlik')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # Показать пользователей
    if args.users:
        list_users(conn)
        conn.close()
        return

    # Выдать/снять админку
    if args.admin:
        set_admin(conn, args.admin, admin=True)
        conn.close()
        return

    if args.remove_admin:
        set_admin(conn, args.remove_admin, admin=False)
        conn.close()
        return

    # Переделать ID
    if args.fix_ids:
        print('\n🔄  Переделываем ID фильмов и сериалов на 8-значные...\n')
        conn.execute('PRAGMA foreign_keys = OFF')
        conn.execute('BEGIN')

        try:
            # movies
            m_map = remap_table(conn, 'movies', fk_refs=[
                ('favorites',     'movie_id'),
                ('ratings',       'movie_id'),
                ('movie_images',  'movie_id'),
                ('watch_history', 'movie_id'),
                ('watch_later',   'movie_id'),
                ('comments',      'movie_id'),
                ('trailers',      'movie_id'),
            ])

            # series
            s_map = remap_table(conn, 'series', fk_refs=[
                ('episodes',      'series_id'),
                ('favorites',     'series_id'),
                ('watch_history', 'series_id'),
                ('watch_later',   'series_id'),
                ('comments',      'series_id'),
            ])

            conn.commit()
            conn.execute('PRAGMA foreign_keys = ON')
            print(f'\n✅  Готово! Обновлено: {len(m_map)} фильмов, {len(s_map)} сериалов.')
            print('   Перезапусти Flask: python app.py')

        except Exception as e:
            conn.rollback()
            print(f'\n❌  Ошибка: {e}')
            print('   Изменения откачены, база не изменена.')

        conn.close()
        return

    # Если аргументов нет — интерактивный режим
    print('\n╔══════════════════════════════════════╗')
    print('║   KinoFlik — Управление базой данных ║')
    print('╚══════════════════════════════════════╝')
    print('\nЧто сделать?')
    print('  1. Показать всех пользователей и их ID')
    print('  2. Выдать себе права администратора')
    print('  3. Переделать ID фильмов на 8-значные')
    print('  0. Выход')

    choice = input('\nВыбери (0-3): ').strip()

    if choice == '1':
        list_users(conn)

    elif choice == '2':
        list_users(conn)
        uid = input('\nВведи свой ID (из таблицы выше): ').strip()
        try:
            set_admin(conn, int(uid), admin=True)
            conn.commit()
            print('\n   Перезайди на сайт — в профиле появится роль Администратор.')
        except ValueError:
            print('❌  Неверный ID')

    elif choice == '3':
        confirm = input('\nПеределать все ID фильмов на 8-значные? (да/нет): ').strip().lower()
        if confirm in ('да', 'yes', 'y', 'd'):
            conn.execute('PRAGMA foreign_keys = OFF')
            conn.execute('BEGIN')
            try:
                m_map = remap_table(conn, 'movies', fk_refs=[
                    ('favorites','movie_id'),('ratings','movie_id'),
                    ('movie_images','movie_id'),('watch_history','movie_id'),
                    ('watch_later','movie_id'),('comments','movie_id'),('trailers','movie_id'),
                ])
                s_map = remap_table(conn, 'series', fk_refs=[
                    ('episodes','series_id'),('favorites','series_id'),
                    ('watch_history','series_id'),('watch_later','series_id'),('comments','series_id'),
                ])
                conn.commit()
                conn.execute('PRAGMA foreign_keys = ON')
                print(f'\n✅  Готово! Обновлено: {len(m_map)} фильмов, {len(s_map)} сериалов.')
            except Exception as e:
                conn.rollback()
                print(f'\n❌  Ошибка: {e}. Изменения откачены.')

    conn.close()


if __name__ == '__main__':
    main()