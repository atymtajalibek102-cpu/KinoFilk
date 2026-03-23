
(function () {
    let _hi = 0, _muted = true, _timer = null;
    const HERO = window.__HERO_DATA || [];

    function mkSrc(url, muted) {
        const m = muted ? 1 : 0;
        if (!url) return '';
        if (url.includes('youtube.com/watch')) {
            const v = new URL(url).searchParams.get('v');
            return `https://www.youtube.com/embed/${v}?autoplay=1&mute=${m}&loop=1&playlist=${v}&controls=0&rel=0`;
        }
        if (url.includes('youtu.be/')) {
            const v = url.split('youtu.be/')[1].split(/[?#]/)[0];
            return `https://www.youtube.com/embed/${v}?autoplay=1&mute=${m}&loop=1&playlist=${v}&controls=0`;
        }
        return url;
    }

    window.heroGo = function (n) {
        if (!HERO.length) return;
        _hi = ((n % HERO.length) + HERO.length) % HERO.length;
        const d = HERO[_hi];
        const bg = document.getElementById('heroBg');
        if (bg) bg.style.backgroundImage = d.poster ? `url('${d.poster}')` : 'none';

        const tr = document.getElementById('heroTrailer');
        if (tr) {
            if (d.trailer) {
                const src = mkSrc(d.trailer, _muted);
                tr.innerHTML = `<iframe id="heroIframe" src="${src}" allow="autoplay; fullscreen"></iframe>`;
                tr.classList.add('show');
            } else {
                tr.innerHTML = '';
                tr.classList.remove('show');
            }
        }
        document.getElementById('heroTitle').textContent = d.title;
        const desc = document.getElementById('heroDesc');
        if (desc) desc.textContent = d.desc || '';

        document.querySelectorAll('.hero-dot').forEach((dot, i) => dot.classList.toggle('active', i === _hi));
    };

    window.toggleSound = function () {
        _muted = !_muted;
        const d = HERO[_hi];
        if (!d || !d.trailer) return;
        const iframe = document.getElementById('heroIframe');
        if (iframe) iframe.src = mkSrc(d.trailer, _muted);
        document.getElementById('heroSoundIcon').className = _muted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
    };

    if (HERO.length > 1) {
        _timer = setInterval(() => heroGo(_hi + 1), 8000);
    }

    // TMDB
    async function fetchTMDB(url, gridId, type) {
        const API_KEY = '15d2ea6d0dc1d476efbca3eba2b9bbfb';
        try {
            const res = await fetch(url + '&api_key=' + API_KEY + '&language=ru-RU&page=1');
            const data = await res.json();
            const grid = document.getElementById(gridId);
            if (!grid) return;
            grid.innerHTML = data.results.slice(0, 12).map(m => {
                const title = (m.title || m.name || '').replace(/</g,'&lt;');
                const year = (m.release_date || m.first_air_date || '').split('-')[0];
                const rating = m.vote_average ? m.vote_average.toFixed(1) : '—';
                const poster = m.poster_path ? `https://image.tmdb.org/t/p/w342${m.poster_path}` : '/static/img/no_poster.svg';
                const isMovie = type === 'Кино';
                const watchUrl = isMovie ? `/watch/tmdb/${m.id}` : `/watch/tv/${m.id}`;
                const detailUrl = isMovie ? `/movie/tmdb/${m.id}` : `/series/tmdb/${m.id}`;
                return `
                    <a href="${detailUrl}" class="movie-card">
                        <div class="movie-poster-wrap">
                            <img src="${poster}" class="movie-img" loading="lazy" onerror="this.src='/static/img/no_poster.svg'">
                            <div class="movie-badge-top">★ ${rating}</div>
                            <div class="hover-info">
                                <div class="hi-play-icon"><i class="fas fa-play"></i></div>
                                <div class="hi-title">${title}</div>
                                <div class="hi-year">${year} · ${isMovie ? 'Фильм' : 'Сериал'}</div>
                                <a href="${watchUrl}" class="hi-btn" onclick="event.stopPropagation()">▶ Смотреть</a>
                            </div>
                        </div>
                        <div class="movie-meta-bottom">
                            <div class="movie-title">${title}</div>
                            <div class="movie-year">${year}</div>
                        </div>
                    </a>
                `;
            }).join('');
        } catch (e) { console.error(e); }
    }

    fetchTMDB('https://api.themoviedb.org/3/movie/popular?', 'tmdb-grid', 'Кино');
    fetchTMDB('https://api.themoviedb.org/3/tv/popular?', 'tmdb-tv-grid', 'Сериал');
})();
