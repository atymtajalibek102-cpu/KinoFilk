
(function () {
    'use strict';

    
    const HOVER_DELAY   = 420;   
    const HOVER_OUT     = 180;   
    const DEBOUNCE_MS   = 280;

    
    function getSet(key) {
        try { return new Set(JSON.parse(localStorage.getItem(key) || '[]')); }
        catch { return new Set(); }
    }
    function saveSet(key, set) {
        try { localStorage.setItem(key, JSON.stringify([...set])); } catch {}
    }

    let favorites  = getSet('kf_favorites');
    let watchLater = getSet('kf_watch_later');

    
    let miniToastEl = null;
    let miniToastTimer = null;

    function miniToast(msg, icon = 'fa-check', warn = false) {
        if (!miniToastEl) {
            miniToastEl = document.createElement('div');
            miniToastEl.className = 'mini-toast';
            document.body.appendChild(miniToastEl);
        }
        miniToastEl.className = 'mini-toast' + (warn ? ' warn' : '');
        miniToastEl.innerHTML = `<i class="fas ${icon}"></i> ${msg}`;
        miniToastEl.classList.add('show');
        clearTimeout(miniToastTimer);
        miniToastTimer = setTimeout(() => miniToastEl.classList.remove('show'), 2400);
    }

    
    async function toggleFavorite(movieId, btn) {
        const id = String(movieId);
        const isNow = favorites.has(id);
        try {
            const res = await fetch('/ajax/favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: parseInt(id) })
            });
            const data = await res.json();
            if (data.status === 'added') {
                favorites.add(id);
                saveSet('kf_favorites', favorites);
                miniToast('Добавлено в избранное', 'fa-heart');
            } else {
                favorites.delete(id);
                saveSet('kf_favorites', favorites);
                miniToast('Убрано из избранного', 'fa-heart-broken', true);
            }
        } catch {
            
            if (isNow) {
                favorites.delete(id);
                miniToast('Убрано из избранного', 'fa-heart-broken', true);
            } else {
                favorites.add(id);
                miniToast('Добавлено в избранное', 'fa-heart');
            }
            saveSet('kf_favorites', favorites);
        }
        updateFavButtons();
    }

    async function toggleLater(movieId, btn) {
        const id = String(movieId);
        const isNow = watchLater.has(id);
        try {
            const res = await fetch('/ajax/watch_later', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: parseInt(id) })
            });
            const data = await res.json();
            if (data.status === 'added') {
                watchLater.add(id);
                saveSet('kf_watch_later', watchLater);
                miniToast('Хочу посмотреть — добавлено', 'fa-clock');
            } else {
                watchLater.delete(id);
                saveSet('kf_watch_later', watchLater);
                miniToast('Убрано из «Хочу посмотреть»', 'fa-times', true);
            }
        } catch {
            if (isNow) {
                watchLater.delete(id);
                miniToast('Убрано из «Хочу посмотреть»', 'fa-times', true);
            } else {
                watchLater.add(id);
                miniToast('Хочу посмотреть — добавлено', 'fa-clock');
            }
            saveSet('kf_watch_later', watchLater);
        }
        updateLaterButtons();
    }

    function updateFavButtons() {
        document.querySelectorAll('[data-fav-id]').forEach(btn => {
            const active = favorites.has(String(btn.dataset.favId));
            btn.classList.toggle('active', active);
            btn.classList.toggle('active-fav', active);
            const tip = active ? 'Убрать из избранного' : 'В избранное';
            btn.setAttribute('data-tip', tip);
        });
    }

    function updateLaterButtons() {
        document.querySelectorAll('[data-later-id]').forEach(btn => {
            const active = watchLater.has(String(btn.dataset.laterId));
            btn.classList.toggle('active', active);
            btn.classList.toggle('active-later', active);
            const tip = active ? 'Убрать из «Хочу посмотреть»' : 'Хочу посмотреть';
            btn.setAttribute('data-tip', tip);
        });
    }

    
    let popup = null;
    let showTimer = null;
    let hideTimer = null;
    let currentCard = null;

    function buildPopup() {
        const p = document.createElement('div');
        p.className = 'qp-popup';
        p.id = 'qpPopup';
        document.body.appendChild(p);
        p.addEventListener('mouseenter', () => clearTimeout(hideTimer));
        p.addEventListener('mouseleave', () => scheduleHide());
        return p;
    }

    function getRatingClass(r) {
        const n = parseFloat(r);
        if (n >= 7) return 'high';
        if (n >= 5) return 'medium';
        return 'low';
    }

    async function showPopup(card) {
        clearTimeout(hideTimer);
        const movieId = card.dataset.movieId;
        if (!movieId) return;

        if (!popup) popup = buildPopup();

        
        const title  = card.dataset.title  || '—';
        const orig   = card.dataset.orig   || '';
        const year   = card.dataset.year   || '';
        const genre  = card.dataset.genre  || '';
        const rating = card.dataset.rating || '';
        const desc   = card.dataset.desc   || '';
        const poster = card.dataset.poster || '';
        const dur    = card.dataset.dur    || '';
        const age    = card.dataset.age    || '';

        const rClass = getRatingClass(rating);
        const isFav   = favorites.has(String(movieId));
        const isLater = watchLater.has(String(movieId));

        const genres = genre ? genre.split(',').slice(0, 3).map(g => {
            const t = g.trim();
            return `<a href="/movie?genre=${encodeURIComponent(t)}" class="qp-tag">${t}</a>`;
        }).join('') : '';

        popup.innerHTML = `
            <div style="position:relative">
                ${poster
                    ? `<img class="qp-poster" src="/static/posters/${poster}" alt="${title}" loading="lazy" onerror="this.style.display='none'">`
                    : `<div class="qp-poster-empty"><i class="fas fa-film"></i></div>`
                }
                <div class="qp-gradient"></div>
                ${rating ? `<span class="qp-rating-badge ${rClass}">★ ${parseFloat(rating).toFixed(1)}</span>` : ''}
            </div>
            <div class="qp-body">
                <div class="qp-title">${escHtml(title)}</div>
                ${orig ? `<div class="qp-orig">${escHtml(orig)}</div>` : ''}
                <div class="qp-meta">
                    ${year ? `<span class="qp-meta-item"><i class="fas fa-calendar"></i>${year}</span>` : ''}
                    ${dur  ? `<span class="qp-meta-item"><i class="fas fa-clock"></i>${dur} мин.</span>` : ''}
                    ${age  ? `<span class="qp-meta-item"><i class="fas fa-shield-alt"></i>${age}</span>` : ''}
                </div>
                ${genres ? `<div class="qp-tags">${genres}</div>` : ''}
                ${desc ? `<div class="qp-desc">${escHtml(desc)}</div>` : ''}
                <div class="qp-actions">
                    <a href="/movie/${movieId}" class="qp-btn qp-btn-play">
                        <i class="fas fa-play"></i> Смотреть
                    </a>
                    <button class="qp-btn qp-btn-fav ${isFav ? 'active' : ''}"
                            data-fav-id="${movieId}"
                            onclick="window._kpFav(${movieId},this)"
                            data-tip="${isFav ? 'Убрать из избранного' : 'В избранное'}">
                        <i class="fas fa-heart"></i>
                    </button>
                    <button class="qp-btn qp-btn-later ${isLater ? 'active' : ''}"
                            data-later-id="${movieId}"
                            onclick="window._kpLater(${movieId},this)"
                            data-tip="${isLater ? 'Убрать' : 'Хочу посмотреть'}">
                        <i class="fas fa-bookmark"></i>
                    </button>
                </div>
            </div>
        `;

        positionPopup(card);
        popup.classList.add('visible');
    }

    function positionPopup(card) {
        const rect = card.getBoundingClientRect();
        const pw = 320;
        const margin = 12;
        let left = rect.right + margin;
        if (left + pw > window.innerWidth - 10) {
            left = rect.left - pw - margin;
        }
        if (left < 8) left = 8;

        let top = rect.top + rect.height / 2 - 200;
        if (top < 10) top = 10;
        if (top + 420 > window.innerHeight) top = window.innerHeight - 430;

        popup.style.left = `${left}px`;
        popup.style.top  = `${top}px`;
    }

    function scheduleHide() {
        hideTimer = setTimeout(() => {
            if (popup) popup.classList.remove('visible');
        }, HOVER_OUT);
    }

    function escHtml(str) {
        return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    
    function enrichCards() {
        
        document.querySelectorAll('a.movie-card, a.series-card, .movie-tile').forEach(card => {
            
            const href = card.getAttribute('href') || '';
            const match = href.match(/\/(?:movie|series)\/(\d+)/);
            if (match && !card.dataset.movieId) {
                card.dataset.movieId = match[1];
            }
        });
    }

    
    function addCardButtons() {
        document.querySelectorAll(
            'a.movie-card:not([data-kp-done]), a.series-card:not([data-kp-done])'
        ).forEach(card => {
            card.dataset.kpDone = '1';
            const href = card.getAttribute('href') || '';
            const match = href.match(/\/(?:movie|series)\/(\d+)/);
            if (!match) return;
            const id = match[1];

            const wrap = card.querySelector('.poster-wrap, .series-poster-wrap, .movie-poster');
            if (!wrap) return;
            if (wrap.style.position !== 'absolute') wrap.style.position = 'relative';

            const isFav   = favorites.has(id);
            const isLater = watchLater.has(id);

            const btns = document.createElement('div');
            btns.className = 'card-quick-actions';
            btns.innerHTML = `
                <button class="cqa-btn ${isFav ? 'active-fav' : ''}"
                        data-fav-id="${id}"
                        onclick="event.preventDefault();event.stopPropagation();window._kpFav(${id},this)"
                        data-tip="${isFav ? 'Убрать из избранного' : 'В избранное'}">
                    <i class="fas fa-heart"></i>
                </button>
                <button class="cqa-btn ${isLater ? 'active-later' : ''}"
                        data-later-id="${id}"
                        onclick="event.preventDefault();event.stopPropagation();window._kpLater(${id},this)"
                        data-tip="${isLater ? 'Убрать' : 'Хочу посмотреть'}">
                    <i class="fas fa-bookmark"></i>
                </button>
            `;
            wrap.appendChild(btns);

            
            card.addEventListener('mouseenter', () => {
                currentCard = card;
                clearTimeout(hideTimer);
                showTimer = setTimeout(() => showPopup(card), HOVER_DELAY);
            });
            card.addEventListener('mouseleave', () => {
                clearTimeout(showTimer);
                scheduleHide();
            });
        });
    }

    
    function initSearch() {
        const input = document.getElementById('searchInput');
        const dropdown = document.getElementById('searchResults')
                      || document.querySelector('.search-results');
        if (!input || !dropdown) return;

        
        const newInput = input.cloneNode(true);
        input.parentNode.replaceChild(newInput, input);

        function debounce(fn, ms) {
            let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
        }

        const doSearch = debounce(async (q) => {
            q = q.trim();
            if (q.length < 2) { dropdown.innerHTML = ''; dropdown.style.display = 'none'; return; }

            try {
                const res = await fetch(`/ajax/search?q=${encodeURIComponent(q)}`);
                const data = await res.json();
                renderSearch(data, q, dropdown);
            } catch {
                dropdown.innerHTML = '';
                dropdown.style.display = 'none';
            }
        }, DEBOUNCE_MS);

        newInput.addEventListener('input', e => doSearch(e.target.value));
        newInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                const q = newInput.value.trim();
                if (q) window.location.href = `/search?q=${encodeURIComponent(q)}`;
            }
        });
    }

    function renderSearch(results, query, container) {
        if (!results || !results.length) {
            container.innerHTML = `<div style="padding:16px;text-align:center;color:rgba(255,255,255,.3);font-size:13px"><i class="fas fa-search" style="margin-right:8px"></i>Ничего не найдено</div>`;
            container.style.display = '';
            return;
        }

        const items = results.slice(0, 6).map(m => {
            const r = parseFloat(m.rating);
            const rc = r >= 7 ? 'high' : r >= 5 ? 'medium' : 'low';
            return `
                <a href="/movie/${m.id}" class="search-result-item">
                    ${m.poster
                        ? `<div class="sr-thumb"><img src="/static/posters/${m.poster}" alt="${m.title}" loading="lazy" onerror="this.parentElement.innerHTML='<i class=\\'fas fa-film\\'></i>'" ></div>`
                        : `<div class="sr-thumb-empty"><i class="fas fa-film"></i></div>`
                    }
                    <div class="sr-info">
                        <div class="sr-title">${highlight(m.title, query)}</div>
                        <div class="sr-meta">
                            ${m.year ? `<span>${m.year}</span>` : ''}
                            ${m.genre ? `<span>${(m.genre+'').split(',')[0].trim()}</span>` : ''}
                        </div>
                    </div>
                    ${m.rating ? `<span class="sr-rating ${rc}">★ ${parseFloat(m.rating).toFixed(1)}</span>` : ''}
                </a>
            `;
        }).join('');

        container.innerHTML = `
            <div class="search-results-header">Результаты</div>
            ${items}
            <a href="/search?q=${encodeURIComponent(query)}" class="search-results-all">
                <i class="fas fa-search"></i> Все результаты для «${escHtml(query)}»
            </a>
        `;
        container.style.display = '';
    }

    function highlight(text, query) {
        if (!text || !query) return escHtml(text || '');
        const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return escHtml(text).replace(new RegExp(escaped, 'gi'), m => `<mark style="background:rgba(200,0,0,.3);color:#ff8080;border-radius:2px">${m}</mark>`);
    }

    
    window._kpFav   = (id, btn) => toggleFavorite(id, btn);
    window._kpLater = (id, btn) => toggleLater(id, btn);

    function init() {
        enrichCards();
        addCardButtons();
        updateFavButtons();
        updateLaterButtons();
        initSearch();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    
    const observer = new MutationObserver(() => {
        addCardButtons();
        updateFavButtons();
        updateLaterButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });

})();
