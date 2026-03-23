document.addEventListener('DOMContentLoaded', function () {
    var tabs     = document.querySelectorAll('.profile-tab');
    var contents = document.querySelectorAll('.tab-content');

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var id = this.dataset.tab;
            tabs.forEach(function (t) { t.classList.remove('active'); });
            contents.forEach(function (c) { c.classList.remove('active'); });
            this.classList.add('active');
            document.getElementById(id + '-tab').classList.add('active');
        });
    });

    var avatarEdit = document.getElementById('avatarEdit');
    if (avatarEdit) {
        avatarEdit.addEventListener('click', function () {
            alert('Функция смены аватара будет доступна позже');
        });
    }

    var burger  = document.getElementById('burgerMenu');
    var sidebar = document.getElementById('sidebar');
    if (burger && sidebar) {
        burger.addEventListener('click', function () {
            // Переключаем класс open для открытия/закрытия меню по клику
            sidebar.classList.toggle('open');
        });
    }

    var searchInput   = document.getElementById('searchInput');
    var searchResults = document.getElementById('searchResults');
    var timer;

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(timer);
            var q = this.value.trim();
            if (!q) { searchResults.classList.remove('show'); return; }
            timer = setTimeout(function () {
                fetch('/ajax/search?q=' + encodeURIComponent(q))
                    .then(function (r) { return r.json(); })
                    .then(function (items) {
                        if (!items.length) {
                            searchResults.innerHTML = '<div class="sr-empty">Ничего не найдено</div>';
                        } else {
                            searchResults.innerHTML = items.map(function (m) {
                                var poster = m.poster
                                    ? '<img src="/static/posters/' + m.poster + '" alt="">'
                                    : '<i class="fas fa-film"></i>';
                                var rc = m.rating >= 7 ? '#22c55e' : m.rating >= 5 ? '#eab308' : '#ef4444';
                                return '<a href="/movie/' + m.id + '" class="sr-item">'
                                    + '<div class="sr-poster">' + poster + '</div>'
                                    + '<div><div class="sr-title">' + m.title + '</div>'
                                    + '<div class="sr-meta">' + (m.year || '') + ' · <span style="color:' + rc + '">★ ' + (m.rating || '—') + '</span></div></div>'
                                    + '</a>';
                            }).join('');
                        }
                        searchResults.classList.add('show');
                    });
            }, 300);
        });

        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && this.value.trim()) {
                location.href = '/search?q=' + encodeURIComponent(this.value.trim());
            }
        });

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.search-wrapper')) searchResults.classList.remove('show');
        });
    }
});
