/* ═══════════════════════════════════════════════════════════
   KINOFLIK — INDEX PAGE JS  v3.0
═══════════════════════════════════════════════════════════ */

var heroMovies  = typeof HERO_MOVIES !== 'undefined' ? HERO_MOVIES : [];
var currentHero = 0;
var heroBg      = document.getElementById('heroBg');
var heroTimer;

/* Postser URL helper */
function posterUrl(p) {
    if (!p) return '';
    return (p.indexOf('http://') === 0 || p.indexOf('https://') === 0) ? p : '/static/posters/' + p;
}

/* ── HERO SWITCHER ─────────────────────────────────────── */
function switchHero(idx, el) {
    if (!heroMovies[idx]) return;
    currentHero = idx;
    var m = heroMovies[idx];

    document.querySelectorAll('.hero-strip-item').forEach(function(s) { s.classList.remove('active'); });
    if (el) el.classList.add('active');

    if (heroBg) {
        heroBg.style.transition = 'opacity .4s ease, transform .4s ease';
        heroBg.style.opacity    = '0';
        heroBg.style.transform  = 'scale(1.1)';
        setTimeout(function() {
            if (m.poster) {
                heroBg.style.backgroundImage = "url('" + posterUrl(m.poster) + "')";
                heroBg.className = 'hero-background';
            }
            heroBg.style.opacity   = '1';
            heroBg.style.transform = 'scale(1.06)';
        }, 380);
    }

    var q = function(sel) { return document.querySelector(sel); };
    var title = q('.hero-title'),  sub   = q('.hero-subtitle'),
        desc  = q('.hero-description'), score = q('.hero-score'),
        play  = q('.hero-play-btn'),    addBtn = q('.hero-buttons .btn-secondary');

    if (title)  title.textContent  = m.title || '';
    if (sub)    sub.textContent    = m.original_title || '';
    if (desc)   desc.textContent   = m.description    || '';
    if (score)  score.innerHTML    = '<i class="fas fa-star"></i> ' + (m.rating || '—');
    if (play)   play.href          = '/movie/' + m.id;
    if (addBtn) addBtn.setAttribute('onclick', "addToList('" + m.id + "')");
}

/* Auto-rotate */
function startHeroTimer() {
    clearInterval(heroTimer);
    if (heroMovies.length <= 1) return;
    heroTimer = setInterval(function() {
        var strips = document.querySelectorAll('.hero-strip-item');
        var next = currentHero + 1;
        if (next >= Math.min(heroMovies.length, 6)) next = 1;
        if (strips[next - 1]) switchHero(next, strips[next - 1]);
    }, 7000);
}
(function() {
    var strip = document.getElementById('heroStrip');
    if (strip) {
        strip.addEventListener('mouseenter', function() { clearInterval(heroTimer); });
        strip.addEventListener('mouseleave', startHeroTimer);
    }
    startHeroTimer();
})();

/* ── CAROUSEL ──────────────────────────────────────────── */
function scrollCarousel(btn, dir) {
    var wrap = btn.closest('.carousel-wrap');
    var car  = wrap && wrap.querySelector('.carousel');
    if (!car) return;
    var itemW = (car.querySelector('.movie-card-wrap') || {}).offsetWidth || 160;
    car.scrollBy({ left: dir * (itemW + 14) * 3, behavior: 'smooth' });
}

/* ── SEARCH ────────────────────────────────────────────── */
(function() {
    var si = document.getElementById('searchInput');
    var sr = document.getElementById('searchResults');
    if (!si || !sr) return;
    var _t;
    si.addEventListener('input', function() {
        clearTimeout(_t);
        var q = this.value.trim();
        if (!q) { sr.classList.remove('show', 'active'); return; }
        _t = setTimeout(function() {
            fetch('/ajax/search?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data.length) {
                        sr.innerHTML = '<div class="search-no-results">Ничего не найдено</div>';
                    } else {
                        sr.innerHTML = data.slice(0, 8).map(function(m) {
                            var img = m.poster
                                ? '<img src="' + posterUrl(m.poster) + '" alt="">'
                                : '<i class="fas fa-film"></i>';
                            return '<a href="/movie/' + m.id + '" class="search-result-item">'
                                + '<div class="sr-poster">' + img + '</div>'
                                + '<div class="search-result-info"><h4>' + m.title + '</h4>'
                                + '<p>' + (m.year || '') + (m.rating ? ' · ★' + m.rating : '') + '</p></div></a>';
                        }).join('');
                    }
                    sr.classList.add('show', 'active');
                }).catch(function() {});
        }, 280);
    });
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-box')) sr.classList.remove('show', 'active');
    });
})();

/* ── ADD TO LIST ───────────────────────────────────────── */
function addToList(id) {
    fetch('/ajax/favorite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_id: parseInt(id) || id })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { showToast(d.status === 'added' ? '✓ Добавлено в список' : '✓ Удалено из списка', 'success'); })
    .catch(function() { showToast('Войдите в аккаунт', 'error'); });
}

/* ── TOAST ─────────────────────────────────────────────── */
function showToast(msg, type) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className   = 'toast show ' + (type || '');
    clearTimeout(t._hide);
    t._hide = setTimeout(function() { t.classList.remove('show'); }, 3000);
}

/* ── BACK TO TOP ───────────────────────────────────────── */
window.addEventListener('scroll', function() {
    var b = document.getElementById('backToTop');
    if (b) b.classList.toggle('show', window.scrollY > 500);
}, { passive: true });
document.getElementById('backToTop') && document.getElementById('backToTop').addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

/* ── REVEAL ON SCROLL ──────────────────────────────────── */
(function() {
    var els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    if (!window.IntersectionObserver) {
        els.forEach(function(el) { el.classList.add('revealed'); });
        return;
    }
    var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(e) {
            if (e.isIntersecting) { e.target.classList.add('revealed'); io.unobserve(e.target); }
        });
    }, { threshold: 0.07 });
    els.forEach(function(el) { io.observe(el); });
})();

/* ── HEADER SCROLL ─────────────────────────────────────── */
(function() {
    var h = document.getElementById('mainHeader');
    if (!h) return;
    window.addEventListener('scroll', function() {
        h.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
})();