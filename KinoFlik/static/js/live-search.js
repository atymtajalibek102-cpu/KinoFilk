/**
 * KinoFlik Live Search & Favorites Module
 * Умный поиск и функция "Избранное"/"Буду смотреть"
 */

(function () {
    'use strict';

    // ===== LIVE SEARCH =====
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    if (searchInput) {
        let searchTimeout;

        searchInput.addEventListener('input', function (e) {
            const query = e.target.value.trim();
            clearTimeout(searchTimeout);

            if (query.length < 2) {
                searchResults.innerHTML = '';
                return;
            }

            searchTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`/ajax/search?q=${encodeURIComponent(query)}`);
                    const data = await response.json();

                    searchResults.innerHTML = '';

                    if (data.movies && data.movies.length > 0) {
                        data.movies.slice(0, 8).forEach(movie => {
                            const item = document.createElement('a');
                            item.href = `/movie/${movie.id}`;
                            item.className = 'search-result-item';
                            item.style.gap = '12px';
                            item.innerHTML = `
                                <img src="/static/posters/${movie.poster || 'no-poster.svg'}" 
                                     alt="${movie.title}" 
                                     style="width: 40px; height: 60px; border-radius: 4px; object-fit: cover;">
                                <div style="flex: 1; min-width: 0;">
                                    <div style="font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                        ${movie.title}
                                    </div>
                                    <div style="font-size: 12px; color: var(--text-muted);">
                                        ${movie.year || 'N/A'} • ⭐ ${movie.rating || '?.?'}
                                    </div>
                                </div>
                            `;
                            searchResults.appendChild(item);
                        });
                    }

                    if ((!data.movies || data.movies.length === 0) && query.length > 0) {
                        const noResults = document.createElement('div');
                        noResults.style.cssText = 'padding: 12px; text-align: center; color: var(--text-muted);';
                        noResults.textContent = '🔍 Ничего не найдено';
                        searchResults.appendChild(noResults);
                    }
                } catch (error) {
                    console.error('Ошибка поиска:', error);
                }
            }, 300);
        });

        // Закрываем результаты при клике вне
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-wrapper')) {
                searchResults.innerHTML = '';
            }
        });
    }

    // ===== FAVORITES / WISHLIST =====
    window.toggleFavorite = async function (movieId, event) {
        if (event) event.preventDefault();

        // Проверяем авторизацию
        if (!sessionStorage.getItem('user_id')) {
            window.location.href = '/login';
            return;
        }

        try {
            const response = await fetch('/ajax/favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: movieId })
            });

            const data = await response.json();

            // Обновляем сердечко
            const heart = event?.target?.closest('i');
            if (heart) {
                heart.classList.toggle('fas');
                heart.classList.toggle('far');
                if (heart.classList.contains('fas')) {
                    heart.style.color = '#800000';
                } else {
                    heart.style.color = 'inherit';
                }
            }

            // Показываем уведомление
            showToast(data.success ? '❤️ Добавлено в избранное' : '💔 Удалено из избранного');
        } catch (error) {
            console.error('Ошибка при добавлении в избранное:', error);
            showToast('⚠️ Что-то пошло не так');
        }
    };

    window.toggleWatchLater = async function (movieId, event) {
        if (event) event.preventDefault();

        if (!sessionStorage.getItem('user_id')) {
            window.location.href = '/login';
            return;
        }

        try {
            const response = await fetch('/ajax/watch_later', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: movieId })
            });

            const data = await response.json();
            showToast(data.success ? '📌 Добавлено в "Буду смотреть"' : '✓ Удалено из очереди');
        } catch (error) {
            console.error('Ошибка:', error);
        }
    };

    // ===== TOAST NOTIFICATIONS =====
    window.showToast = function (message, duration = 3000) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            padding: 12px 20px;
            border-radius: 8px;
            border: 1px solid rgba(128, 0, 0, 0.5);
            font-size: 14px;
            z-index: 10000;
            animation: slideInUp 0.3s ease;
        `;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    };

    // ===== LAZY LOADING =====
    if ('IntersectionObserver' in window) {
        const images = document.querySelectorAll('img[loading="lazy"]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px'
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // ===== SKELETON LOADERS =====
    window.createSkeletons = function (parentId, count = 8) {
        const parent = document.getElementById(parentId);
        if (!parent) return;

        parent.innerHTML = Array(count).fill().map(() => `
            <div class="skeleton-card" style="
                aspect-ratio: 2/3;
                background: linear-gradient(90deg, #222 25%, #333 50%, #222 75%);
                background-size: 200% 100%;
                animation: loading 1.5s infinite;
                border-radius: 8px;
            "></div>
        `).join('');
    };

    window.addCSSAnimation = function () {
        if (!document.getElementById('skeleton-animation')) {
            const style = document.createElement('style');
            style.id = 'skeleton-animation';
            style.textContent = `
                @keyframes loading {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
                @keyframes slideInUp {
                    from { transform: translateY(100px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes slideOutDown {
                    from { transform: translateY(0); opacity: 1; }
                    to { transform: translateY(100px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    };

    addCSSAnimation();
})();
