"""
KinoFlik — Утилита управления пользователями
─────────────────────────────────────────────
Использование:
    python manage.py list_users                      — список всех пользователей
    python manage.py whoami <id>                     — информация о пользователе
    python manage.py make_admin <id>                 — выдать права админа
    python manage.py revoke_admin <id>               — снять права админа
    python manage.py ban <id>                        — заблокировать пользователя
    python manage.py unban <id>                      — разблокировать пользователя
    python manage.py delete <id>                     — удалить пользователя (с подтверждением)
    python manage.py reset_password <id> <пароль>    — сбросить пароль
    python manage.py stats                           — статистика БД
"""
import sys
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def get_conn():
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        print("   Запусти приложение хотя бы один раз, чтобы создать БД.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ================================================================

def list_users():
    conn  = get_conn()
    users = conn.execute(
        "SELECT id, name, email, role, is_banned FROM users ORDER BY id"
    ).fetchall()
    conn.close()

    if not users:
        print("Пользователей нет.")
        return

    print(f"\n{'ID':>4}  {'Имя':<22} {'Email':<32} {'Роль':<14} Статус")
    print("─" * 80)
    for u in users:
        status    = "⛔ БАН"     if u['is_banned'] else "✓ активен"
        role_icon = "👑 admin"   if u['role'] == 'admin' else (u['role'] or 'user')
        print(f"{u['id']:>4}  {str(u['name']):<22} {str(u['email']):<32} {role_icon:<14} {status}")
    print(f"\nВсего пользователей: {len(users)}")


# ================================================================
# ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
# ================================================================

def whoami(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, email, role, is_banned, friend_code FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    # Дополнительная статистика
    fav_count  = conn.execute("SELECT COUNT(*) FROM favorites    WHERE user_id = ?", (user_id,)).fetchone()[0]
    hist_count = conn.execute("SELECT COUNT(*) FROM watch_history WHERE user_id = ?", (user_id,)).fetchone()[0]
    sub        = conn.execute(
        "SELECT p.name, us.end_date FROM user_subscriptions us "
        "JOIN plans p ON us.plan_id = p.id "
        "WHERE us.user_id = ? AND us.is_active = 1 AND us.end_date >= date('now') "
        "ORDER BY us.id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()

    print(f"\n👤 Пользователь #{user['id']}")
    print(f"   Имя:            {user['name']}")
    print(f"   Email:          {user['email']}")
    print(f"   Роль:           {'👑 ADMIN' if user['role'] == 'admin' else user['role'] or 'user'}")
    print(f"   Заблокирован:   {'⛔ ДА' if user['is_banned'] else '✓ Нет'}")
    print(f"   Код друга:      {user['friend_code'] or '—'}")
    print(f"   Избранное:      {fav_count} фильм(ов)")
    print(f"   Просмотрено:    {hist_count} фильм(ов)")
    if sub:
        print(f"   Подписка:       {sub['name']} (до {sub['end_date']})")
    else:
        print(f"   Подписка:       нет активной")


# ================================================================
# УПРАВЛЕНИЕ РОЛЯМИ
# ================================================================

def make_admin(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    if user['role'] == 'admin':
        print(f"ℹ️  '{user['name']}' (id={user_id}) уже является администратором.")
        conn.close()
        return

    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"✅ Пользователю '{user['name']}' (id={user_id}) выданы права администратора!")
    print(f"\n💡 Для мгновенного доступа без перезапуска сервера:")
    print(f"   export ADMIN_IDS={user_id}")


def revoke_admin(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    if user['role'] != 'admin':
        print(f"ℹ️  '{user['name']}' (id={user_id}) и так не является администратором.")
        conn.close()
        return

    conn.execute("UPDATE users SET role = 'user' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"✅ Права администратора сняты с '{user['name']}' (id={user_id})")


# ================================================================
# БЛОКИРОВКА
# ================================================================

def ban_user(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, is_banned FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    if user['is_banned']:
        print(f"ℹ️  '{user['name']}' (id={user_id}) уже заблокирован.")
        conn.close()
        return

    conn.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"⛔ Пользователь '{user['name']}' (id={user_id}) заблокирован.")


def unban_user(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, is_banned FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    if not user['is_banned']:
        print(f"ℹ️  '{user['name']}' (id={user_id}) не заблокирован.")
        conn.close()
        return

    conn.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"✅ Блокировка снята с '{user['name']}' (id={user_id})")


# ================================================================
# УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ================================================================

def delete_user(user_id: int):
    conn = get_conn()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    print(f"\n⚠️  Вы собираетесь УДАЛИТЬ пользователя:")
    print(f"   id={user['id']}, имя='{user['name']}', email='{user['email']}'")
    print(f"   Это действие НЕОБРАТИМО. Все данные пользователя будут удалены.")
    confirm = input("\n   Введите 'ДА' для подтверждения: ").strip()

    if confirm != 'ДА':
        print("❌ Отменено.")
        conn.close()
        return

    # Удаляем все связанные данные
    conn.execute("DELETE FROM favorites            WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM ratings              WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM watch_history        WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM watch_later          WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM friends              WHERE user_id = ? OR friend_id = ?", (user_id, user_id))
    conn.execute("DELETE FROM user_subscriptions   WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM comment_likes        WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM comments             WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM follows              WHERE follower_id = ? OR following_id = ?", (user_id, user_id))
    conn.execute("DELETE FROM users                WHERE id = ?",      (user_id,))
    conn.commit()
    conn.close()
    print(f"✅ Пользователь '{user['name']}' (id={user_id}) и все его данные удалены.")


# ================================================================
# СБРОС ПАРОЛЯ
# ================================================================

def reset_password(user_id: int, new_password: str):
    if len(new_password) < 6:
        print("❌ Пароль должен быть минимум 6 символов.")
        return

    # Хешируем пароль через werkzeug (тот же метод, что использует app.py)
    try:
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash(new_password)
    except ImportError:
        print("❌ Не найден модуль werkzeug. Установите: pip install werkzeug")
        return

    conn = get_conn()
    user = conn.execute(
        "SELECT id, name FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if not user:
        print(f"❌ Пользователь с id={user_id} не найден.")
        conn.close()
        return

    conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    conn.close()
    print(f"✅ Пароль пользователя '{user['name']}' (id={user_id}) успешно изменён.")


# ================================================================
# СТАТИСТИКА
# ================================================================

def stats():
    conn = get_conn()

    def count(table, where=''):
        try:
            q = f"SELECT COUNT(*) FROM {table}"
            if where:
                q += f" WHERE {where}"
            return conn.execute(q).fetchone()[0]
        except Exception:
            return '—'

    users_total  = count('users')
    users_admin  = count('users', "role = 'admin'")
    users_banned = count('users', "is_banned = 1")
    movies_total = count('movies')
    series_total = count('series')
    episodes     = count('episodes')
    comments     = count('comments')
    ratings      = count('ratings')
    favorites_n  = count('favorites')
    subs_active  = count('user_subscriptions', "is_active = 1 AND end_date >= date('now')")

    top_movies = conn.execute(
        "SELECT title, rating FROM movies ORDER BY rating DESC LIMIT 5"
    ).fetchall()

    conn.close()

    print("\n📊 Статистика KinoFlik")
    print("─" * 40)
    print(f"  Пользователи:        {users_total}")
    print(f"    — администраторов: {users_admin}")
    print(f"    — заблокированных: {users_banned}")
    print(f"  Фильмы:              {movies_total}")
    print(f"  Сериалы:             {series_total}")
    print(f"  Эпизоды:             {episodes}")
    print(f"  Комментарии:         {comments}")
    print(f"  Оценки:              {ratings}")
    print(f"  Избранное (записей): {favorites_n}")
    print(f"  Активных подписок:   {subs_active}")

    if top_movies:
        print("\n🏆 Топ-5 фильмов по рейтингу:")
        for i, m in enumerate(top_movies, 1):
            print(f"  {i}. {m['title']} — {m['rating']}")


# ================================================================
# ТОЧКА ВХОДА
# ================================================================

if __name__ == '__main__':
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    def need_id(cmd_name):
        """Проверяет наличие числового id в аргументах."""
        if len(args) < 2 or not args[1].isdigit():
            print(f"Использование: python manage.py {cmd_name} <user_id>")
            sys.exit(1)
        return int(args[1])

    if cmd == 'list_users':
        list_users()

    elif cmd == 'whoami':
        whoami(need_id('whoami'))

    elif cmd == 'make_admin':
        make_admin(need_id('make_admin'))

    elif cmd == 'revoke_admin':
        revoke_admin(need_id('revoke_admin'))

    elif cmd == 'ban':
        ban_user(need_id('ban'))

    elif cmd == 'unban':
        unban_user(need_id('unban'))

    elif cmd == 'delete':
        delete_user(need_id('delete'))

    elif cmd == 'reset_password':
        if len(args) < 3 or not args[1].isdigit():
            print("Использование: python manage.py reset_password <user_id> <новый_пароль>")
            sys.exit(1)
        reset_password(int(args[1]), args[2])

    elif cmd == 'stats':
        stats()

    else:
        print(f"❌ Неизвестная команда: '{cmd}'")
        print(__doc__)
        sys.exit(1)