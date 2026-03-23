from flask import current_app
from models import db, User, Movie, Rating, WatchHistory, Comment, CommentLike, favorites, watch_later, follows
from sqlalchemy import func
from datetime import datetime


def init_db():
    """Инициализирует БД — создаёт все таблицы через SQLAlchemy"""
    db.create_all()


# ================================================================
# ПОЛЬЗОВАТЕЛИ
# ================================================================

def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


def create_user(username, email, password):
    """
    Создаёт нового пользователя.
    password — уже хешированный пароль (generate_password_hash).
    """
    user = User(username=username, email=email, password_hash=password)
    db.session.add(user)
    db.session.commit()
    return user.id


def update_user(user_id, **kwargs):
    """Обновляет любые поля пользователя по ключ=значение."""
    user = User.query.get(user_id)
    if user:
        for k, v in kwargs.items():
            if hasattr(user, k):
                setattr(user, k, v)
        db.session.commit()
        return True
    return False


def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False


# ================================================================
# ФИЛЬМЫ
# ================================================================

def get_all_movies(limit=50, offset=0):
    return Movie.query.order_by(Movie.created_at.desc()).limit(limit).offset(offset).all()


def get_movie(movie_id):
    return Movie.query.get(movie_id)


def create_movie(title, description, year, duration, rating, poster, trailer, genre):
    movie = Movie(
        title=title,
        description=description,
        year=year,
        duration=duration,
        rating=rating,
        poster=poster,
        trailer=trailer,
        genre=genre,
    )
    db.session.add(movie)
    db.session.commit()
    return movie.id


def update_movie(movie_id, **kwargs):
    movie = Movie.query.get(movie_id)
    if movie:
        for k, v in kwargs.items():
            if hasattr(movie, k):
                setattr(movie, k, v)
        db.session.commit()
        return True
    return False


def delete_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if movie:
        db.session.delete(movie)
        db.session.commit()
        return True
    return False


def get_popular_movies(period='week', limit=10):
    """Возвращает фильмы, отсортированные по рейтингу."""
    return Movie.query.order_by(Movie.rating.desc()).limit(limit).all()


def get_new_movies(limit=10):
    """Возвращает самые новые фильмы по году и дате добавления."""
    return Movie.query.order_by(Movie.year.desc(), Movie.created_at.desc()).limit(limit).all()


def search_movies(query):
    """Поиск фильмов по названию (case-insensitive)."""
    return Movie.query.filter(Movie.title.ilike(f'%{query}%')).limit(20).all()


# ================================================================
# ИЗБРАННОЕ
# ================================================================

def add_favorite(user_id, movie_id):
    user  = User.query.get(user_id)
    movie = Movie.query.get(movie_id)
    if user and movie and not is_favorite(user_id, movie_id):
        user.favorite_movies.append(movie)
        db.session.commit()
        return True
    return False


def remove_favorite(user_id, movie_id):
    user  = User.query.get(user_id)
    movie = Movie.query.get(movie_id)
    if user and movie and is_favorite(user_id, movie_id):
        user.favorite_movies.remove(movie)
        db.session.commit()
        return True
    return False


def toggle_favorite(user_id, movie_id):
    """Переключает избранное: добавляет если нет, удаляет если есть."""
    if is_favorite(user_id, movie_id):
        remove_favorite(user_id, movie_id)
        return 'removed'
    else:
        add_favorite(user_id, movie_id)
        return 'added'


def get_favorites(user_id):
    user = User.query.get(user_id)
    if not user:
        return []
    # favorite_movies — динамическое отношение, вызываем .all()
    return user.favorite_movies.all()


def is_favorite(user_id, movie_id):
    user = User.query.get(user_id)
    if not user:
        return False
    return user.favorite_movies.filter_by(id=movie_id).first() is not None


# ================================================================
# РЕЙТИНГИ
# ================================================================

def rate_movie(user_id, movie_id, rating):
    """
    Ставит или обновляет оценку фильма (1–10).
    Возвращает новый средний рейтинг фильма.

    ИСПРАВЛЕНО: было rating_val (NameError) → теперь rating.
    """
    # Валидация
    try:
        rating_val = int(rating)
        if not (1 <= rating_val <= 10):
            raise ValueError
    except (TypeError, ValueError):
        return None

    existing = Rating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    if existing:
        existing.rating = rating_val
    else:
        new_rating = Rating(user_id=user_id, movie_id=movie_id, rating=rating_val)
        db.session.add(new_rating)

    db.session.commit()

    # Пересчитываем средний рейтинг фильма
    avg = db.session.query(func.avg(Rating.rating)).filter_by(movie_id=movie_id).scalar()
    movie = Movie.query.get(movie_id)
    if movie:
        movie.rating = round(float(avg), 1) if avg else 0
        db.session.commit()

    return round(float(avg), 1) if avg else 0


def get_user_rating(user_id, movie_id):
    r = Rating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    return r.rating if r else None


def get_movie_avg_rating(movie_id):
    """Возвращает средний рейтинг и количество оценок."""
    result = db.session.query(
        func.avg(Rating.rating),
        func.count(Rating.id)
    ).filter_by(movie_id=movie_id).first()
    avg   = round(float(result[0]), 1) if result[0] else 0
    count = result[1] or 0
    return avg, count


# ================================================================
# ИСТОРИЯ ПРОСМОТРОВ
# ================================================================

def add_to_history(user_id, movie_id, progress=0):
    """Добавляет или обновляет запись в истории просмотра."""
    history = WatchHistory.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    if history:
        history.progress   = progress
        history.watched_at = datetime.utcnow()
    else:
        history = WatchHistory(user_id=user_id, movie_id=movie_id, progress=progress)
        db.session.add(history)
    db.session.commit()


def get_history(user_id, limit=20):
    """Возвращает историю просмотров пользователя."""
    return (
        WatchHistory.query
        .filter_by(user_id=user_id)
        .order_by(WatchHistory.watched_at.desc())
        .limit(limit)
        .all()
    )


def get_continue_watching(user_id):
    """Фильмы, которые смотрели, но не досмотрели (progress от 1 до 99)."""
    return (
        WatchHistory.query
        .filter(
            WatchHistory.user_id == user_id,
            WatchHistory.progress > 0,
            WatchHistory.progress < 100
        )
        .order_by(WatchHistory.watched_at.desc())
        .limit(10)
        .all()
    )


# ================================================================
# СМОТРЕТЬ ПОЗЖЕ
# ================================================================

def add_to_watch_later(user_id, movie_id):
    user  = User.query.get(user_id)
    movie = Movie.query.get(movie_id)
    if user and movie:
        if movie not in user.watch_later_movies:
            user.watch_later_movies.append(movie)
            db.session.commit()
            return True
    return False


def remove_from_watch_later(user_id, movie_id):
    user  = User.query.get(user_id)
    movie = Movie.query.get(movie_id)
    if user and movie:
        if movie in user.watch_later_movies:
            user.watch_later_movies.remove(movie)
            db.session.commit()
            return True
    return False


def toggle_watch_later(user_id, movie_id):
    """Переключает «Смотреть позже»."""
    user  = User.query.get(user_id)
    movie = Movie.query.get(movie_id)
    if not user or not movie:
        return None
    if movie in user.watch_later_movies:
        user.watch_later_movies.remove(movie)
        db.session.commit()
        return 'removed'
    else:
        user.watch_later_movies.append(movie)
        db.session.commit()
        return 'added'


def get_watch_later(user_id):
    user = User.query.get(user_id)
    if not user:
        return []
    return user.watch_later_movies.all()


# ================================================================
# КОММЕНТАРИИ
# ================================================================

def add_comment(user_id, movie_id, content, parent_id=None):
    if not content or not content.strip():
        return None
    comment = Comment(
        user_id=user_id,
        movie_id=movie_id,
        parent_id=parent_id,
        content=content.strip()
    )
    db.session.add(comment)
    db.session.commit()
    return comment.id


def get_comments(movie_id):
    """Возвращает корневые комментарии (без parent_id) к фильму."""
    return (
        Comment.query
        .filter_by(movie_id=movie_id, parent_id=None)
        .order_by(Comment.created_at.desc())
        .all()
    )


def get_replies(comment_id):
    """Возвращает ответы на комментарий."""
    return (
        Comment.query
        .filter_by(parent_id=comment_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def delete_comment(comment_id, requesting_user_id, is_admin=False):
    """Удаляет комментарий. Разрешено автору или админу."""
    comment = Comment.query.get(comment_id)
    if not comment:
        return False
    if comment.user_id != requesting_user_id and not is_admin:
        return False
    db.session.delete(comment)
    db.session.commit()
    return True


def toggle_comment_like(user_id, comment_id):
    """
    Переключает лайк на комментарий.
    Возвращает (liked: bool, count: int).
    """
    existing = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    comment  = Comment.query.get(comment_id)
    if not comment:
        return False, 0

    if existing:
        db.session.delete(existing)
        comment.likes = max(0, comment.likes - 1)
        liked = False
    else:
        cl = CommentLike(user_id=user_id, comment_id=comment_id)
        db.session.add(cl)
        comment.likes += 1
        liked = True

    db.session.commit()
    return liked, comment.likes


def like_comment(user_id, comment_id):
    """Ставит лайк (если ещё не поставлен)."""
    if not CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first():
        cl = CommentLike(user_id=user_id, comment_id=comment_id)
        db.session.add(cl)
        comment = Comment.query.get(comment_id)
        if comment:
            comment.likes += 1
        db.session.commit()


def unlike_comment(user_id, comment_id):
    """Снимает лайк."""
    cl = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    if cl:
        db.session.delete(cl)
        comment = Comment.query.get(comment_id)
        if comment:
            comment.likes = max(0, comment.likes - 1)
        db.session.commit()


# ================================================================
# ПОДПИСКИ (ФОЛЛОВЕРЫ)
# ================================================================

def follow_user(follower_id, following_id):
    """Подписаться на пользователя."""
    if follower_id == following_id:
        return False
    follower  = User.query.get(follower_id)
    following = User.query.get(following_id)
    if follower and following:
        if following not in follower.followed:
            follower.followed.append(following)
            db.session.commit()
            return True
    return False


def unfollow_user(follower_id, following_id):
    """Отписаться от пользователя."""
    follower  = User.query.get(follower_id)
    following = User.query.get(following_id)
    if follower and following:
        if following in follower.followed:
            follower.followed.remove(following)
            db.session.commit()
            return True
    return False


def toggle_follow(follower_id, following_id):
    """Переключает подписку. Возвращает True если подписался, False если отписался."""
    follower  = User.query.get(follower_id)
    following = User.query.get(following_id)
    if not follower or not following or follower_id == following_id:
        return None
    if following in follower.followed:
        follower.followed.remove(following)
        db.session.commit()
        return False
    else:
        follower.followed.append(following)
        db.session.commit()
        return True


def get_followers(user_id):
    """Список тех, кто подписан на пользователя."""
    user = User.query.get(user_id)
    return user.followers.all() if user else []


def get_following(user_id):
    """Список тех, на кого подписан пользователь."""
    user = User.query.get(user_id)
    return user.followed.all() if user else []


def is_following(follower_id, following_id):
    """Проверяет, подписан ли follower_id на following_id."""
    follower = User.query.get(follower_id)
    if not follower:
        return False
    return User.query.get(following_id) in follower.followed


def get_followers_count(user_id):
    user = User.query.get(user_id)
    return user.followers.count() if user else 0


def get_following_count(user_id):
    user = User.query.get(user_id)
    return user.followed.count() if user else 0