(function () {
    'use strict';

    const CONFIG = {
        API_BASE: '',
        ANIMATION_DURATION: 300,
        LAZY_LOAD_THRESHOLD: 0.2,
        INFINITE_SCROLL_THRESHOLD: 200,
        TOAST_DURATION: 3000,
        DEFAULT_USER_AVATAR: '/static/img/no_poster.svg',
        STORAGE_KEYS: {
            THEME: 'kinoflik_theme',
            FAVORITES: 'kinoflik_favorites',
            WATCH_LATER: 'kinoflik_watch_later',
            USER: 'kinoflik_user',
            SETTINGS: 'kinoflik_settings'
        }
    };

    const state = {
        currentUser: null,
        favorites: new Set(),
        watchLater: new Set(),
        currentPage: 'home',
        moviesCache: new Map(),
        searchResults: [],
        infiniteScrollPage: 1,
        isLoading: false,
        theme: 'dark',
        settings: {
            autoplayTrailer: true,
            showAdultContent: false,
            language: 'ru'
        }
    };

    const Utils = {
        getStorage(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn(`Failed to parse ${key} from localStorage`, e);
                return defaultValue;
            }
        },

        setStorage(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn(`Failed to save ${key} to localStorage`, e);
            }
        },

        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        getUrlParams() {
            const params = new URLSearchParams(window.location.search);
            return Object.fromEntries(params.entries());
        },

        escapeHtml(unsafe) {
            return unsafe.replace(/[&<>"']/g, function (m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                if (m === '"') return '&quot;';
                return '&#039;';
            });
        }
    };

    const API = {
        async request(endpoint, options = {}) {
            const url = `${CONFIG.API_BASE}${endpoint}`;
            const headers = {
                'Content-Type': 'application/json',
                ...(state.currentUser?.token && { 'Authorization': `Bearer ${state.currentUser.token}` }),
                ...options.headers
            };

            try {
                const response = await fetch(url, { ...options, headers });
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.message || `HTTP ${response.status}`);
                }
                return await response.json();
            } catch (error) {
                console.error(`API request failed: ${endpoint}`, error);
                throw error;
            }
        },

        get(endpoint) {
            return this.request(endpoint, { method: 'GET' });
        },

        post(endpoint, data) {
            return this.request(endpoint, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },

        put(endpoint, data) {
            return this.request(endpoint, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },

        delete(endpoint) {
            return this.request(endpoint, { method: 'DELETE' });
        },

        async searchMovies(query) {
            return this.get(`/ajax/search?q=${encodeURIComponent(query)}`);
        },

        async getMovie(id) {
            if (state.moviesCache.has(id)) {
                return state.moviesCache.get(id);
            }
            const movie = await this.get(`/movie/${id}`);
            state.moviesCache.set(id, movie);
            return movie;
        },

        async toggleFavorite(movieId) {
            const result = await this.post('/ajax/favorite', { movie_id: movieId });
            if (result.status === 'added') {
                state.favorites.add(movieId);
            } else {
                state.favorites.delete(movieId);
            }
            this.updateFavoritesUI();
            return result;
        },

        async rateMovie(movieId, rating) {
            return this.post('/ajax/rate', { movie_id: movieId, rating });
        },

        async loadMoreMovies(page = state.infiniteScrollPage) {
            const movies = await this.get(`/ajax/load?page=${page}`);
            state.infiniteScrollPage++;
            return movies;
        },

        async login(credentials) {
            const user = await this.post('/api/login', credentials);
            state.currentUser = user;
            Utils.setStorage(CONFIG.STORAGE_KEYS.USER, user);
            this.updateAuthUI();
            return user;
        },

        async register(data) {
            const user = await this.post('/api/register', data);
            return user;
        },

        async logout() {
            await this.post('/api/logout');
            state.currentUser = null;
            Utils.setStorage(CONFIG.STORAGE_KEYS.USER, null);
            this.updateAuthUI();
        },

        async updateProfile(data) {
            const user = await this.put('/api/profile', data);
            state.currentUser = user;
            Utils.setStorage(CONFIG.STORAGE_KEYS.USER, user);
            this.updateAuthUI();
            return user;
        },

        async fetchFavorites() {
            const favorites = await this.get('/api/favorites');
            state.favorites = new Set(favorites.map(f => f.id));
            this.updateFavoritesUI();
            return favorites;
        },

        updateAuthUI() {
            const loginLinks = document.querySelectorAll('.login-btn, a[href="/login"]');
            const userMenu = document.querySelector('.user-menu');
            if (state.currentUser) {
                loginLinks.forEach(link => link.style.display = 'none');
                if (userMenu) {
                    userMenu.innerHTML = `
                        <div class="user-profile">
                            <i class="fas fa-user-circle"></i>
                            <span>${Utils.escapeHtml(state.currentUser.name)}</span>
                            <div class="user-dropdown">
                                <a href="/profile">Профиль</a>
                                <a href="#" data-page="favorites">Избранное</a>
                                <a href="#" id="logoutBtn">Выйти</a>
                            </div>
                        </div>
                    `;
                }
            } else {
                loginLinks.forEach(link => link.style.display = '');
                if (userMenu) {
                    userMenu.innerHTML = `<a href="/login" class="login-btn">Войти</a>`;
                }
            }
        },

        updateFavoritesUI() {
            document.querySelectorAll('.favorite-btn').forEach(btn => {
                const movieId = btn.dataset.id;
                if (movieId && state.favorites.has(parseInt(movieId))) {
                    btn.classList.add('active');
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                    } else {
                        btn.innerHTML = '💖';
                    }
                } else {
                    btn.classList.remove('active');
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('fas');
                        icon.classList.add('far');
                    } else {
                        btn.innerHTML = '❤️';
                    }
                }
            });
        }
    };

    const Router = {
        routes: {
            '/': 'home',
            '/movie/:id': 'movie',
            '/profile': 'profile',
            '/favorites': 'favorites',
            '/admin': 'admin',
            '/login': 'login',
            '/register': 'register',
            '/search': 'search',
            '/genre/:genre': 'genre'
        },

        init() {
            window.addEventListener('popstate', () => this.handleRoute());
            document.querySelectorAll('a[data-page]').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const page = link.dataset.page;
                    this.navigate(page);
                });
            });
            this.handleRoute();
        },

        handleRoute() {
            const path = window.location.pathname;
            const matched = this.matchRoute(path);
            if (matched) {
                this.render(matched.page, matched.params);
            } else {
                this.render('404');
            }
        },

        matchRoute(path) {
            for (const [route, page] of Object.entries(this.routes)) {
                const pattern = route.replace(/:\w+/g, '([^/]+)');
                const regex = new RegExp(`^${pattern}$`);
                const match = path.match(regex);
                if (match) {
                    const paramNames = (route.match(/:\w+/g) || []).map(p => p.slice(1));
                    const params = {};
                    paramNames.forEach((name, index) => {
                        params[name] = match[index + 1];
                    });
                    return { page, params };
                }
            }
            return null;
        },

        navigate(page, params = {}) {
            let path = this.getPathFromPage(page, params);
            window.history.pushState({}, '', path);
            this.render(page, params);
        },

        getPathFromPage(page, params) {
            for (const [route, p] of Object.entries(this.routes)) {
                if (p === page) {
                    let path = route;
                    for (const [key, value] of Object.entries(params)) {
                        path = path.replace(`:${key}`, value);
                    }
                    return path;
                }
            }
            return '/';
        },

        async render(page, params) {
            const app = document.getElementById('app');
            if (!app) return;

            state.currentPage = page;
            this.updateActiveNav(page);

            let content = '';
            switch (page) {
                case 'home':
                    content = await this.renderHome();
                    break;
                case 'movie':
                    content = await this.renderMovie(params.id);
                    break;
                case 'profile':
                    content = await this.renderProfile();
                    break;
                case 'favorites':
                    content = await this.renderFavorites();
                    break;
                case 'admin':
                    content = await this.renderAdmin();
                    break;
                case 'login':
                    content = this.renderLogin();
                    break;
                case 'register':
                    content = this.renderRegister();
                    break;
                case 'search':
                    content = await this.renderSearch(Utils.getUrlParams().q);
                    break;
                case 'genre':
                    content = await this.renderGenre(params.genre);
                    break;
                default:
                    content = this.render404();
            }

            app.innerHTML = content;
            this.afterRender(page);
        },

        updateActiveNav(page) {
            document.querySelectorAll('nav a, .sidebar-link').forEach(link => {
                link.classList.remove('active');
                if (link.dataset.page === page) {
                    link.classList.add('active');
                }
            });
        },

        async renderHome() {
            const movies = await API.get('/movies/popular');
            const genres = await API.get('/genres');
            return `
                <section class="hero">
                    <div class="hero-content">
                        <h2>Лучшие фильмы и сериалы</h2>
                        <p>Смотри онлайн в высоком качестве</p>
                        <button class="hero-btn" onclick="location.href='/movie/1'">Смотреть сейчас</button>
                        <button class="hero-btn" onclick="location.href='/trailer'">Трейлер</button>
                    </div>
                </section>
                <h2 class="section-title">🎭 Жанры</h2>
                <section class="genres">
                    ${genres.map(g => `<a href="/genre/${g.slug}" class="genre-link"><div class="genre" style="background: ${g.color}">${g.name}</div></a>`).join('')}
                </section>
                <h2 class="section-title">🔥 Популярное</h2>
                <section class="movies">
                    ${movies.map(m => this.renderMovieCard(m)).join('')}
                </section>
            `;
        },

        renderMovieCard(movie) {
            return `
                <div class="movie-card" data-id="${movie.id}">
                    <a href="/movie/${movie.id}">
                        <img src="${movie.poster || '/static/img/no_poster.svg'}" alt="${movie.title}" loading="lazy">
                    </a>
                    <h3>${movie.title}</h3>
                    <div class="movie-actions">
                        <span class="rating">⭐ ${movie.rating || '8.5'}</span>
                        <button class="favorite-btn ${state.favorites.has(movie.id) ? 'active' : ''}" data-id="${movie.id}">
                            <i class="${state.favorites.has(movie.id) ? 'fas' : 'far'} fa-heart"></i>
                        </button>
                    </div>
                </div>
            `;
        },

        async renderMovie(id) {
            const movie = await API.getMovie(id);
            const similar = await API.get(`/movies/${id}/similar`);
            return `
                <div class="movie-page-container">
                    <div class="movie-page-content">
                        <div class="movie-poster-section">
                            <img class="movie-page-poster" src="${movie.poster}" alt="${movie.title}">
                            <div class="movie-rating-large">⭐ ${movie.rating}</div>
                            <div class="movie-actions-side">
                                <button class="movie-favorite-btn big ${state.favorites.has(movie.id) ? 'active' : ''}" data-id="${movie.id}">
                                    <i class="${state.favorites.has(movie.id) ? 'fas' : 'far'} fa-heart"></i> В избранное
                                </button>
                                ${state.currentUser?.isAdmin ? `<button class="movie-edit-btn" onclick="location.href='/admin/edit/${movie.id}'"><i class="fas fa-edit"></i> Редактировать</button>` : ''}
                            </div>
                        </div>
                        <div class="movie-details-section">
                            <h2 class="movie-page-title">${movie.title}</h2>
                            <div class="movie-meta-info">
                                <span><i class="fas fa-calendar"></i> ${movie.year}</span>
                                <span><i class="fas fa-clock"></i> ${movie.duration}</span>
                                <span class="movie-quality">${movie.quality}</span>
                            </div>
                            <div class="movie-genre-tags">
                                ${movie.genres.map(g => `<span class="genre-tag">${g}</span>`).join('')}
                            </div>
                            <p class="movie-page-description">${movie.description}</p>
                            <div class="movie-cast-section">
                                <h3>В главных ролях:</h3>
                                <div class="cast-list">
                                    ${movie.cast.map(actor => `<span class="cast-item">${actor}</span>`).join('')}
                                </div>
                            </div>
                            <div class="movie-actions-section">
                                <button class="movie-play-btn" onclick="playMovie(${movie.id})"><i class="fas fa-play"></i> Смотреть</button>
                                <button class="movie-trailer-btn" onclick="watchTrailer('${movie.trailer}')"><i class="fas fa-film"></i> Трейлер</button>
                            </div>
                            <div class="movie-rating-section">
                                <h3>Оценить фильм:</h3>
                                <div class="rating-stars" data-id="${movie.id}">
                                    ${Array.from({ length: 10 }, (_, i) => `<span class="star ${movie.userRating > i ? 'active' : ''}" data-value="${i + 1}">★</span>`).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="similar-movies-section">
                        <h2 class="section-title">Похожие фильмы</h2>
                        <div class="movies-row">
                            ${similar.map(s => this.renderMovieCard(s)).join('')}
                        </div>
                    </div>
                </div>
            `;
        },

        async renderProfile() {
            if (!state.currentUser) {
                Router.navigate('login');
                return '';
            }
            const favorites = await API.fetchFavorites();
            return `
                <div class="profile-container">
                    <div class="profile-header">
                        <div class="profile-avatar">
                            <i class="fas fa-user-circle"></i>
                        </div>
                        <div class="profile-info">
                            <h1>${state.currentUser.name}</h1>
                            <p class="profile-email">${state.currentUser.email}</p>
                            <div class="profile-stats">
                                <div class="stat"><span class="stat-value">${favorites.length}</span><span class="stat-label">В избранном</span></div>
                                <div class="stat"><span class="stat-value">24</span><span class="stat-label">Просмотрено</span></div>
                                <div class="stat"><span class="stat-value">3</span><span class="stat-label">Сейчас смотрят</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="profile-tabs">
                        <button class="profile-tab active" data-tab="favorites">Избранное</button>
                        <button class="profile-tab" data-tab="watchlist">Буду смотреть</button>
                        <button class="profile-tab" data-tab="history">История</button>
                        <button class="profile-tab" data-tab="settings">Настройки</button>
                    </div>
                    <div class="profile-content">
                        <div class="tab-content active" id="favorites-tab">
                            <h2>Избранное</h2>
                            <div class="movies-grid">
                                ${favorites.map(f => this.renderMovieCard(f)).join('')}
                            </div>
                        </div>
                        <div class="tab-content" id="settings-tab">
                            <h2>Настройки</h2>
                            <form class="profile-settings-form">
                                <div class="form-group">
                                    <label>Имя</label>
                                    <input type="text" name="name" value="${state.currentUser.name}">
                                </div>
                                <div class="form-group">
                                    <label>Email</label>
                                    <input type="email" name="email" value="${state.currentUser.email}">
                                </div>
                                <div class="form-group">
                                    <label>Новый пароль</label>
                                    <input type="password" name="password">
                                </div>
                                <button type="submit" class="auth-submit">Сохранить</button>
                            </form>
                        </div>
                    </div>
                </div>
            `;
        },

        async renderFavorites() {
            if (!state.currentUser) {
                Router.navigate('login');
                return '';
            }
            const favorites = await API.fetchFavorites();
            return `
                <div class="container">
                    <h2 class="section-title">Избранное</h2>
                    <div class="movies-grid">
                        ${favorites.length ? favorites.map(f => this.renderMovieCard(f)).join('') : '<div class="empty-state"><i class="fas fa-heart-broken"></i><p>У вас пока нет избранных фильмов</p><a href="/" class="btn-primary">Перейти к фильмам</a></div>'}
                    </div>
                </div>
            `;
        },

        renderLogin() {
            return `
                <div class="auth-container">
                    <div class="auth-card">
                        <h2>Вход</h2>
                        <form id="loginForm">
                            <div class="input-group">
                                <i class="fas fa-user"></i>
                                <input type="text" name="username" placeholder="Логин" required>
                            </div>
                            <div class="input-group">
                                <i class="fas fa-lock"></i>
                                <input type="password" name="password" placeholder="Пароль" required>
                            </div>
                            <button type="submit" class="auth-submit">Войти</button>
                        </form>
                        <p class="auth-link">Нет аккаунта? <a href="/register">Зарегистрироваться</a></p>
                    </div>
                </div>
            `;
        },

        renderRegister() {
            return `
                <div class="auth-container">
                    <div class="auth-card">
                        <h2>Регистрация</h2>
                        <form id="registerForm">
                            <div class="input-group">
                                <i class="fas fa-user"></i>
                                <input type="text" name="name" placeholder="Имя" required>
                            </div>
                            <div class="input-group">
                                <i class="fas fa-envelope"></i>
                                <input type="email" name="email" placeholder="Email" required>
                            </div>
                            <div class="input-group">
                                <i class="fas fa-lock"></i>
                                <input type="password" name="password" placeholder="Пароль" required>
                            </div>
                            <div class="input-group">
                                <i class="fas fa-lock"></i>
                                <input type="password" name="confirm_password" placeholder="Подтвердите пароль" required>
                            </div>
                            <button type="submit" class="auth-submit">Зарегистрироваться</button>
                        </form>
                        <p class="auth-link">Уже есть аккаунт? <a href="/login">Войти</a></p>
                    </div>
                </div>
            `;
        },

        async renderAdmin() {
            if (!state.currentUser?.isAdmin) return '<div class="error">Доступ запрещён</div>';
            const movies = await API.get('/admin/movies');
            return `
                <div class="admin-section">
                    <h2 class="section-title">Админ панель</h2>
                    <div class="admin-stats">
                        <div class="stat-card"><div class="stat-icon"><i class="fas fa-film"></i></div><div class="stat-info"><h3>${movies.length}</h3><p>Фильмов</p></div></div>
                        <div class="stat-card"><div class="stat-icon"><i class="fas fa-users"></i></div><div class="stat-info"><h3>1250</h3><p>Пользователей</p></div></div>
                    </div>
                    <div class="admin-card">
                        <h3>Добавить фильм</h3>
                        <form id="addMovieForm" enctype="multipart/form-data">
                            <div class="form-group"><input type="text" name="title" placeholder="Название" required></div>
                            <div class="form-group"><textarea name="description" placeholder="Описание"></textarea></div>
                            <div class="form-row">
                                <input type="number" name="rating" placeholder="Рейтинг" step="0.1">
                                <input type="number" name="year" placeholder="Год">
                                <input type="file" name="poster" accept="image/*" required>
                            </div>
                            <button type="submit" class="btn-submit">Добавить</button>
                        </form>
                    </div>
                    <div class="admin-card">
                        <h3>Управление фильмами</h3>
                        <div class="movies-table">
                            <div class="table-header">
                                <div>Постер</div><div>Название</div><div>Год</div><div>Рейтинг</div><div>Действия</div>
                            </div>
                            ${movies.map(m => `
                                <div class="table-row" data-id="${m.id}">
                                    <div><img src="${m.poster}" class="movie-thumb"></div>
                                    <div>${m.title}</div>
                                    <div>${m.year}</div>
                                    <div>⭐ ${m.rating}</div>
                                    <div class="action-btns">
                                        <button class="edit-btn" onclick="editMovie(${m.id})"><i class="fas fa-edit"></i></button>
                                        <button class="delete-btn" onclick="deleteMovie(${m.id})"><i class="fas fa-trash"></i></button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        },

        render404() {
            return '<h1>404 - Страница не найдена</h1>';
        },

        afterRender(page) {
            this.initPageHandlers(page);
            LazyLoader.observe();
            Favorites.initButtons();
            Rating.initStars();
            Forms.init();
            if (page === 'profile') ProfileTabs.init();
            if (page === 'home') InfiniteScroll.init();
        },

        initPageHandlers(page) {
        }
    };

    const UI = {
        showToast(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => toast.classList.add('show'), 10);
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        },

        showConfirm(message) {
            return new Promise((resolve) => {
                const modal = document.createElement('div');
                modal.className = 'modal show';
                modal.innerHTML = `
                    <div class="modal-content" style="max-width: 400px;">
                        <h3>Подтверждение</h3>
                        <p>${message}</p>
                        <div style="display: flex; gap: 10px; justify-content: center;">
                            <button class="btn-primary" id="confirmOk">Да</button>
                            <button class="btn-secondary" id="confirmCancel">Нет</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
                modal.querySelector('#confirmOk').addEventListener('click', () => {
                    modal.remove();
                    resolve(true);
                });
                modal.querySelector('#confirmCancel').addEventListener('click', () => {
                    modal.remove();
                    resolve(false);
                });
            });
        }
    };

    const Favorites = {
        initButtons() {
            document.querySelectorAll('.favorite-btn').forEach(btn => {
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                newBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const movieId = newBtn.dataset.id;
                    if (!movieId) return;
                    try {
                        await API.toggleFavorite(movieId);
                        UI.showToast(state.favorites.has(parseInt(movieId)) ? 'Добавлено в избранное' : 'Удалено из избранного');
                    } catch (err) {
                        UI.showToast('Ошибка', 'error');
                    }
                });
            });
        }
    };

    const Rating = {
        initStars() {
            document.querySelectorAll('.rating-stars').forEach(container => {
                const stars = container.querySelectorAll('.star');
                const movieId = container.dataset.id;
                stars.forEach(star => {
                    star.addEventListener('click', async () => {
                        const value = star.dataset.value;
                        try {
                            await API.rateMovie(movieId, value);
                            stars.forEach(s => s.classList.remove('active'));
                            for (let i = 0; i < value; i++) stars[i].classList.add('active');
                            UI.showToast('Спасибо за оценку!');
                        } catch (err) {
                            UI.showToast('Ошибка при оценке', 'error');
                        }
                    });
                });
            });
        }
    };

    const Search = {
        init() {
            const input = document.getElementById('searchInput');
            if (!input) return;
            const debouncedSearch = Utils.debounce(this.performSearch.bind(this), 500);
            input.addEventListener('input', debouncedSearch);
        },

        async performSearch(e) {
            const query = e.target.value.trim();
            const container = document.getElementById('searchResults') || document.querySelector('.search-results');
            if (!query || query.length < 2) {
                if (container) container.innerHTML = '';
                return;
            }
            try {
                const results = await API.searchMovies(query);
                state.searchResults = results;
                this.showResults(results);
            } catch (err) {
                console.error(err);
                if (container) container.innerHTML = '';
            }
        },

        showResults(results) {
            const container = document.getElementById('searchResults') || document.querySelector('.search-results');
            if (!container) return;
            if (!Array.isArray(results) || !results.length) {
                container.innerHTML = '<div style="padding:12px 14px;color:var(--text-muted);font-size:.85rem;text-align:center">Ничего не найдено</div>';
                return;
            }
            const html = results.map(m => `
                <a href="/movie/${m.id}" class="search-result-item">
                    <div class="sr-poster" style="width:36px;height:36px;border-radius:8px;background:var(--bg-card);display:flex;align-items:center;justify-content:center;color:var(--accent);flex-shrink:0"><i class="fas fa-film"></i></div>
                    <div style="overflow:hidden">
                        <div class="sr-title" style="font-weight:700;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${m.title || ''}</div>
                        <div class="sr-meta" style="font-size:.78rem;color:var(--text-muted)">${m.year || ''}</div>
                    </div>
                </a>
            `).join('');
            container.innerHTML = html;
        }
    };

    const LazyLoader = {
        observer: null,

        init() {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.add('loaded');
                        this.observer.unobserve(img);
                    }
                });
            }, { threshold: CONFIG.LAZY_LOAD_THRESHOLD });

            this.observe();
        },

        observe() {
            document.querySelectorAll('img[data-src]').forEach(img => this.observer.observe(img));
        }
    };

    const InfiniteScroll = {
        enabled: true,

        init() {
            // Включаем только если есть контейнер с фильмами
            const container = document.querySelector('.movies, .cards-grid');
            if (!container) return;
            window.addEventListener('scroll', Utils.debounce(this.checkScroll.bind(this), 150));
        },

        checkScroll() {
            if (!this.enabled || state.isLoading) return;
            const scrollY = window.scrollY;
            const height = document.documentElement.scrollHeight - window.innerHeight;
            if (height > 0 && scrollY > height - CONFIG.INFINITE_SCROLL_THRESHOLD) {
                this.loadMore();
            }
        },

        async loadMore() {
            state.isLoading = true;
            try {
                const movies = await API.loadMoreMovies();
                if (!movies || !movies.length) {
                    // Больше данных нет — отключаем скролл
                    this.enabled = false;
                    return;
                }
                const container = document.querySelector('.movies');
                if (container) {
                    movies.forEach(m => container.insertAdjacentHTML('beforeend', Router.renderMovieCard(m)));
                    Favorites.initButtons();
                    LazyLoader.observe();
                }
            } catch (e) {
                // Ошибка загрузки — не крашим страницу
                this.enabled = false;
            } finally {
                state.isLoading = false;
            }
        }
    };

    const Forms = {
        init() {
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', this.handleSubmit);
            });
        },

        async handleSubmit(e) {
            e.preventDefault();
            const form = e.target;
            const action = form.action || form.getAttribute('action');
            const method = form.method || 'POST';

            if (form.id === 'loginForm') {
                const data = new FormData(form);
                try {
                    await API.login(Object.fromEntries(data));
                    Router.navigate('home');
                } catch (err) {
                    UI.showToast(err.message, 'error');
                }
            } else if (form.id === 'registerForm') {
                const data = new FormData(form);
                if (data.get('password') !== data.get('confirm_password')) {
                    UI.showToast('Пароли не совпадают', 'error');
                    return;
                }
                try {
                    await API.register(Object.fromEntries(data));
                    UI.showToast('Регистрация успешна! Войдите');
                    Router.navigate('login');
                } catch (err) {
                    UI.showToast(err.message, 'error');
                }
            } else if (form.id === 'addMovieForm') {
                const data = new FormData(form);
                try {
                    await API.post('/admin/add_movie', data);
                    UI.showToast('Фильм добавлен');
                    Router.navigate('admin');
                } catch (err) {
                    UI.showToast(err.message, 'error');
                }
            }
        }
    };

    const ProfileTabs = {
        init() {
            const tabs = document.querySelectorAll('.profile-tab');
            const contents = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabId = tab.dataset.tab;
                    tabs.forEach(t => t.classList.remove('active'));
                    contents.forEach(c => c.classList.remove('active'));
                    tab.classList.add('active');
                    document.getElementById(tabId + '-tab').classList.add('active');
                });
            });
        }
    };

    const BurgerMenu = {
        init() {
            const burger = document.getElementById('burgerMenu');
            const navWrapper = document.getElementById('navWrapper');
            if (!burger || !navWrapper) return;

            burger.innerHTML = '<i class="fas fa-bars"></i>';
            burger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                navWrapper.classList.toggle('show');
                const icon = burger.querySelector('i');
                if (navWrapper.classList.contains('show')) {
                    icon.classList.replace('fa-bars', 'fa-times');
                    document.body.style.overflow = 'hidden';
                } else {
                    icon.classList.replace('fa-times', 'fa-bars');
                    document.body.style.overflow = '';
                }
            });

            navWrapper.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', () => {
                    navWrapper.classList.remove('show');
                    const icon = burger.querySelector('i');
                    icon?.classList.replace('fa-times', 'fa-bars');
                    document.body.style.overflow = '';
                });
            });

            document.addEventListener('click', (e) => {
                if (navWrapper.classList.contains('show') && !navWrapper.contains(e.target) && !burger.contains(e.target)) {
                    navWrapper.classList.remove('show');
                    const icon = burger.querySelector('i');
                    icon?.classList.replace('fa-times', 'fa-bars');
                    document.body.style.overflow = '';
                }
            });

            window.addEventListener('resize', () => {
                if (window.innerWidth > 768 && navWrapper.classList.contains('show')) {
                    navWrapper.classList.remove('show');
                    const icon = burger.querySelector('i');
                    if (icon) icon.classList.replace('fa-times', 'fa-bars');
                    document.body.style.overflow = '';
                }
            });
        }
    };

    const Sidebar = {
        init() {
            const burger = document.getElementById('burgerMenu');
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('overlay');
            if (!burger || !sidebar || !overlay) return;

            burger.addEventListener('click', () => {
                sidebar.classList.toggle('active');
                overlay.classList.toggle('active');
                const icon = burger.querySelector('i');
                if (sidebar.classList.contains('active')) {
                    icon.classList.replace('fa-bars', 'fa-times');
                } else {
                    icon.classList.replace('fa-times', 'fa-bars');
                }
            });

            overlay.addEventListener('click', () => {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                const icon = burger.querySelector('i');
                icon?.classList.replace('fa-times', 'fa-bars');
            });

            sidebar.querySelectorAll('.sidebar-link').forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth <= 992) {
                        sidebar.classList.remove('active');
                        overlay.classList.remove('active');
                        const icon = burger.querySelector('i');
                        icon?.classList.replace('fa-times', 'fa-bars');
                    }
                });
            });

            window.addEventListener('resize', () => {
                if (window.innerWidth > 992) {
                    sidebar.classList.remove('active');
                    overlay.classList.remove('active');
                    const icon = burger.querySelector('i');
                    if (icon) icon.classList.replace('fa-times', 'fa-bars');
                }
            });
        }
    };

    const FadeInObserver = {
        init() {
            const faders = document.querySelectorAll('.fade-in');
            if (!faders.length) return;
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('show');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: CONFIG.LAZY_LOAD_THRESHOLD });
            faders.forEach(f => observer.observe(f));
        }
    };

    // --- Hero Slider Module ---
    const HeroSlider = {
        data: window.__HERO_DATA || [],
        currentIndex: 0,
        muted: true,
        timer: null,

        init() {
            if (!this.data.length) return;
            this.goTo(0);
            this.startTimer();
            const wrap = document.getElementById('heroWrap');
            if (wrap) {
                wrap.addEventListener('mouseenter', () => this.stopTimer());
                wrap.addEventListener('mouseleave', () => this.startTimer());
            }
        },

        mkSrc(url, muted) {
            if (!url) return '';
            const m = muted ? 1 : 0;
            try {
                if (url.includes('youtube.com/watch')) {
                    const v = new URL(url).searchParams.get('v');
                    return `https://www.youtube.com/embed/${v}?autoplay=1&mute=${m}&loop=1&playlist=${v}&controls=0&rel=0`;
                }
                if (url.includes('youtu.be/')) {
                    const v = url.split('youtu.be/')[1].split(/[?#]/)[0];
                    return `https://www.youtube.com/embed/${v}?autoplay=1&mute=${m}&loop=1&playlist=${v}&controls=0`;
                }
                if (url.includes('rutube.ru')) {
                    let v = '';
                    if (url.includes('/embed/')) {
                        v = url.split('/embed/')[1].split(/[?#]/)[0];
                    } else {
                        const match = url.match(/\/video\/([a-zA-Z0-9]+)/);
                        v = match ? match[1] : '';
                    }
                    return `https://rutube.ru/play/embed/${v}?autoplay=1&mute=${m}`;
                }
            } catch (e) {
                console.error("Ошибка парсинга URL:", e);
            }
            return url;
        },

        goTo(n) {
            if (!this.data.length) return;
            this.currentIndex = ((n % this.data.length) + this.data.length) % this.data.length;
            const d = this.data[this.currentIndex];

            const bg = document.getElementById('heroBg');
            if (bg) bg.style.backgroundImage = d.poster ? `url('${d.poster}')` : 'none';

            const tr = document.getElementById('heroTrailer');
            const sb = document.getElementById('heroSoundBtn');
            if (tr) {
                tr.classList.remove('show');
                if (d.trailer) {
                    const src = this.mkSrc(d.trailer, this.muted);
                    let iframe = document.getElementById('heroIframe');
                    if (!iframe) {
                        tr.innerHTML = `<iframe id="heroIframe" src="${src}" allow="autoplay; fullscreen"></iframe>`;
                        iframe = document.getElementById('heroIframe');
                    } else {
                        iframe.src = src;
                    }
                    iframe.onload = () => setTimeout(() => tr.classList.add('show'), 600);
                    if (sb) sb.classList.add('vis');
                } else {
                    if (sb) sb.classList.remove('vis');
                }
            }

            const tel = document.getElementById('heroTitle');
            if (tel) tel.textContent = d.title;

            const del = document.getElementById('heroDesc');
            if (del) {
                del.textContent = d.desc || '';
                del.style.display = d.desc ? '' : 'none';
            }

            const mel = document.getElementById('heroMeta');
            if (mel) {
                let h = '';
                if (d.year) h += `<div class="hero-meta-item"><span class="meta-label">Год</span><span class="meta-value">${d.year}</span></div>`;
                if (d.rating) h += `<div class="hero-meta-item"><span class="meta-label">Рейтинг</span><div class="hero-rating-badge"><i class="fas fa-star"></i> ${d.rating}</div></div>`;
                if (d.genre) h += `<div class="hero-meta-item"><span class="meta-label">Жанр</span><span class="meta-value">${d.genre}</span></div>`;
                mel.innerHTML = h;
            }

            ['heroBtnPlay', 'heroBtnInfo'].forEach(id => {
                const b = document.getElementById(id);
                if (b) b.onclick = () => location.href = '/movie/' + d.id;
            });

            document.querySelectorAll('.hero-dot').forEach((dot, i) => {
                dot.classList.toggle('active', i === this.currentIndex);
            });
        },

        next() {
            this.goTo(this.currentIndex + 1);
        },

        startTimer() {
            if (this.data.length > 1) {
                this.timer = setInterval(() => this.next(), 8000);
            }
        },

        stopTimer() {
            clearInterval(this.timer);
        },

        toggleSound() {
            this.muted = !this.muted;
            const d = this.data[this.currentIndex];
            if (!d || !d.trailer) return;
            const iframe = document.getElementById('heroIframe');
            if (iframe) iframe.src = this.mkSrc(d.trailer, this.muted);
            const ico = document.getElementById('heroSoundIcon');
            if (ico) ico.className = this.muted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
        }
    };

    // Глобальные функции, вызываемые из HTML
    window.toggleSound = () => HeroSlider.toggleSound();
    window.editMovie = async function (id) {
        const newTitle = prompt('Введите новое название:');
        if (!newTitle) return;
        try {
            await API.put(`/admin/edit_movie/${id}`, { title: newTitle });
            UI.showToast('Фильм обновлён');
            location.reload();
        } catch (err) {
            UI.showToast(err.message, 'error');
        }
    };
    window.deleteMovie = async function (id) {
        const confirmed = await UI.showConfirm('Удалить фильм?');
        if (!confirmed) return;
        try {
            await API.delete(`/admin/delete_movie/${id}`);
            UI.showToast('Фильм удалён');
            const row = document.querySelector(`.table-row[data-id="${id}"]`);
            if (row) row.remove();
        } catch (err) {
            UI.showToast(err.message, 'error');
        }
    };
    window.playMovie = function (id) {
        window.location.href = `/player/${id}`;
    };
    window.watchTrailer = function (url) {
        if (url) window.open(url, '_blank');
        else UI.showToast('Трейлер недоступен', 'error');
    };

    // Основная инициализация при загрузке DOM
    document.addEventListener('DOMContentLoaded', () => {
        console.log('KinoFlik JS инициализирован');

        // Загрузка состояния из localStorage
        state.currentUser = Utils.getStorage(CONFIG.STORAGE_KEYS.USER, null);
        state.favorites = new Set(Utils.getStorage(CONFIG.STORAGE_KEYS.FAVORITES, []));
        state.theme = Utils.getStorage(CONFIG.STORAGE_KEYS.THEME, 'dark');
        state.settings = Utils.getStorage(CONFIG.STORAGE_KEYS.SETTINGS, state.settings);

        document.documentElement.setAttribute('data-theme', state.theme);

        // Инициализация модулей
        BurgerMenu.init();
        Sidebar.init();
        Search.init();
        LazyLoader.init();
        InfiniteScroll.init();
        FadeInObserver.init();
        API.updateAuthUI();
        Favorites.initButtons();
        Rating.initStars();
        Forms.init();
        Router.init();

        // Инициализация Hero Slider (данные должны быть в window.__HERO_DATA)
        HeroSlider.init();

        // Закрытие модалок
        document.querySelectorAll('.modal .close').forEach(btn => {
            btn.addEventListener('click', () => btn.closest('.modal').classList.remove('show'));
        });
    });

})();