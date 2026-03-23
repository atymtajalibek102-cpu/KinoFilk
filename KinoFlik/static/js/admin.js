/* ═══════════════════════════════════════════════════
   KinoFlik Admin JS — исправленная версия
   Исправлено:
   1. confirmDelete — fetch POST (не window.location GET!)
   2. openEditModal — fetch POST с JSON body
   3. editForm — preventDefault + AJAX
   4. deleteUser — через общий modal
═══════════════════════════════════════════════════ */

/* ══ ВКЛАДКИ ══════════════════════════════════════ */
function switchTab(name, btn) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
}

/* ══ ЖАНРЫ ════════════════════════════════════════ */
function toggleChip(label) {
    const cb = label.querySelector('input[type="checkbox"]');
    setTimeout(() => label.classList.toggle('checked', cb.checked), 0);
}

/* ══ ПРЕВЬЮ ПОСТЕРА ═══════════════════════════════ */
function previewImage(input, zoneId) {
    const zone = document.getElementById(zoneId);
    const preview = zone.querySelector('.preview-img');
    const icon = zone.querySelector('i');
    const text = zone.querySelector('p');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            preview.src = e.target.result;
            preview.style.display = 'block';
            if (icon) icon.style.display = 'none';
            if (text) text.style.display = 'none';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function previewImages(input, zoneId) {
    const zone = document.getElementById(zoneId);
    const previewGrid = zone.querySelector('.preview-grid');
    const icon = zone.querySelector('i');
    const text = zone.querySelector('p');
    previewGrid.innerHTML = '';
    if (input.files && input.files.length > 0) {
        if (icon) icon.style.display = 'none';
        if (text) text.style.display = 'none';
        previewGrid.style.display = 'grid';
        Array.from(input.files).forEach(file => {
            const reader = new FileReader();
            reader.onload = e => {
                previewGrid.innerHTML += `<img src="${e.target.result}" style="width:100%;border-radius:8px;aspect-ratio:16/9;object-fit:cover;">`;
            };
            reader.readAsDataURL(file);
        });
    }
}

/* ══ DRAG & DROP ══════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.upload-zone').forEach(zone => {
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('dragover');
            const input = zone.querySelector('input[type="file"]');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                if (input.multiple) previewImages(input, zone.id);
                else previewImage(input, zone.id);
            }
        });
    });
});

/* ══ ТРЕЙЛЕР ПРЕВЬЮ ═══════════════════════════════ */
function previewTrailer(inputId, previewId) {
    const url = document.getElementById(inputId).value.trim();
    const box = document.getElementById(previewId);
    if (!url) { showToast('Введите ссылку на трейлер', 'error'); return; }
    const embedUrl = ytToEmbed(url);
    if (!embedUrl) { showToast('Неверная ссылка YouTube', 'error'); return; }
    box.innerHTML = `<iframe src="${embedUrl}" allowfullscreen style="width:100%;height:200px;border:none;border-radius:12px;"></iframe>`;
    box.classList.add('visible');
}

function ytToEmbed(url) {
    try {
        const u = new URL(url);
        let id = null;
        if (u.hostname.includes('youtu.be')) id = u.pathname.slice(1);
        else if (u.hostname.includes('youtube.com')) id = u.searchParams.get('v');
        return id ? `https://www.youtube.com/embed/${id}` : null;
    } catch { return null; }
}

/* ══ ПОИСК В ТАБЛИЦЕ ══════════════════════════════ */
function filterTable(inputId, tableId) {
    const query = document.getElementById(inputId).value.toLowerCase();
    const table = document.getElementById(tableId);
    table.querySelectorAll('.table-row').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
    });
}

/* ══ СОРТИРОВКА ═══════════════════════════════════ */
let sortState = {};
function sortTable(tableId, colIndex) {
    const table = document.getElementById(tableId);
    const rows = Array.from(table.querySelectorAll('.table-row'));
    const key = tableId + colIndex;
    sortState[key] = !sortState[key];
    rows.sort((a, b) => {
        const aVal = a.children[colIndex]?.textContent.trim() || '';
        const bVal = b.children[colIndex]?.textContent.trim() || '';
        const aNum = parseFloat(aVal), bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) return sortState[key] ? aNum - bNum : bNum - aNum;
        return sortState[key] ? aVal.localeCompare(bVal, 'ru') : bVal.localeCompare(aVal, 'ru');
    });
    rows.forEach(r => table.appendChild(r));
}

/* ══ СЕРИИ ════════════════════════════════════════ */
let episodeCount = 1;
function addEpisode() {
    episodeCount++;
    const list = document.getElementById('episodeList');
    const item = document.createElement('div');
    item.className = 'episode-item';
    item.innerHTML = `
        <input type="number" name="ep_num[]" value="${episodeCount}" min="1" placeholder="№">
        <input type="text" name="ep_title[]" placeholder="Название серии">
        <input type="url" name="ep_url[]" placeholder="Ссылка на видео">
        <button type="button" class="btn-remove-ep" onclick="removeEpisode(this)"><i class="fas fa-times"></i></button>
    `;
    list.appendChild(item);
}

function removeEpisode(btn) {
    const list = document.getElementById('episodeList');
    if (list.children.length > 1) btn.closest('.episode-item').remove();
    else showToast('Должна быть хотя бы одна серия', 'error');
}

/* ══ ДЕТАЛИ ═══════════════════════════════════════ */
function viewDetails(row) {
    const posterPath = row.dataset.poster
        ? '/static/posters/' + row.dataset.poster
        : '/static/img/no_poster.svg';
    document.getElementById('detailPoster').src = posterPath;
    document.getElementById('detailTitle').textContent = row.dataset.title;
    document.getElementById('detailYear').textContent = row.dataset.year ? row.dataset.year + ' г.' : '';
    document.getElementById('detailRating').textContent = row.dataset.rating ? '⭐ ' + row.dataset.rating : '';
    document.getElementById('detailDescription').textContent = row.dataset.description || 'Описание отсутствует';
    document.getElementById('detailEditBtn').onclick = function () {
        closeModal('detailsModal');
        openEditModal(row.dataset.type, row.dataset.id);
    };
    document.getElementById('detailsModal').classList.add('open');
}

/* ══ РЕДАКТИРОВАНИЕ (AJAX) ════════════════════════
   ИСПРАВЛЕНО: было window.location / form submit
   Теперь: fetch POST с JSON, Flask маршруты /admin/edit_*
══════════════════════════════════════════════════ */
let _editType = '', _editId = '';

function openEditModal(type, id) {
    _editType = type;
    _editId = id;
    const title = document.getElementById('editModalTitle');
    title.innerHTML = `<i class="fas fa-edit" style="color:#3b82f6;margin-right:8px"></i> Редактировать ${
        type === 'movie' ? 'фильм' : type === 'series' ? 'сериал' : 'трейлер'
    }`;
    const tabId = type === 'movie' ? 'movies' : type === 'series' ? 'series' : 'trailers';
    const row = document.querySelector(`#tab-${tabId} [data-id="${id}"]`);
    if (row) {
        document.getElementById('editTitle').value = row.dataset.title || '';
        document.getElementById('editYear').value = row.dataset.year || '';
        document.getElementById('editRating').value = row.dataset.rating || '';
        document.getElementById('editDescription').value = row.dataset.description || '';
    }
    document.getElementById('editModal').classList.add('open');
}

/* ══ УДАЛЕНИЕ (AJAX) ══════════════════════════════
   ИСПРАВЛЕНО: было window.location.href = /delete_type/id
   Теперь: fetch POST /admin/delete_movie|series|trailer
══════════════════════════════════════════════════ */
let _deleteType = '', _deleteId = '';

function confirmDelete(type, id, name) {
    _deleteType = type;
    _deleteId = id;
    document.getElementById('deleteItemName').textContent = name;
    document.getElementById('deleteModal').classList.add('open');
}

function deleteUser(id, name) {
    _deleteType = 'user';
    _deleteId = id;
    document.getElementById('deleteItemName').textContent = name;
    document.getElementById('deleteModal').classList.add('open');
}

/* ══ БАН ══════════════════════════════════════════ */
function toggleBan(id, action) {
    fetch('/admin/ban_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: id, action })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(action === 'ban' ? 'Пользователь заблокирован' : 'Пользователь разблокирован');
            setTimeout(() => location.reload(), 600);
        } else showToast('Ошибка: ' + data.message, 'error');
    });
}

/* ══ МОДАЛЬНЫЕ ОКНА ═══════════════════════════════ */
function closeModal(id) {
    document.getElementById(id).classList.remove('open');
}

/* ══ TOAST ════════════════════════════════════════ */
let toastTimer;
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    const icon = toast.querySelector('i');
    document.getElementById('toastMsg').textContent = msg;
    toast.className = 'toast ' + type;
    icon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

function handleSubmit(e, form) {
    const btn = form.querySelector('.btn-submit');
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохраняем...';
    btn.disabled = true;
    setTimeout(() => { btn.innerHTML = original; btn.disabled = false; }, 5000);
}

/* ══ ИНИЦИАЛИЗАЦИЯ ════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

    /* Закрытие модалок по клику на оверлей / Escape */
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', e => {
            if (e.target === overlay) overlay.classList.remove('open');
        });
    });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape')
            document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    });

    /* ── Кнопка подтверждения удаления ── */
    const deleteConfirmBtn = document.getElementById('deleteConfirmBtn');
    if (deleteConfirmBtn) {
        deleteConfirmBtn.addEventListener('click', function () {
            const routes = {
                movie:   ['/admin/delete_movie',   'movie_id'],
                series:  ['/admin/delete_series',  'series_id'],
                trailer: ['/admin/delete_trailer', 'trailer_id'],
                user:    ['/admin/delete_user',    'user_id'],
            };
            const [url, idKey] = routes[_deleteType] || ['/admin/delete_movie', 'movie_id'];

            const orig = deleteConfirmBtn.innerHTML;
            deleteConfirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            deleteConfirmBtn.disabled = true;

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [idKey]: _deleteId })
            })
            .then(r => r.json())
            .then(data => {
                deleteConfirmBtn.innerHTML = orig;
                deleteConfirmBtn.disabled = false;
                closeModal('deleteModal');
                if (data.success) {
                    showToast('Удалено успешно');
                    if (_deleteType === 'user') {
                        const row = document.querySelector(`#tab-users [data-id="${_deleteId}"]`);
                        if (row) row.remove();
                    } else {
                        const tabId = _deleteType === 'movie' ? 'movies' : _deleteType === 'series' ? 'series' : 'trailers';
                        const row = document.querySelector(`#tab-${tabId} [data-id="${_deleteId}"]`);
                        if (row) row.remove();
                    }
                } else showToast('Ошибка: ' + (data.message || ''), 'error');
            })
            .catch(() => {
                deleteConfirmBtn.innerHTML = orig;
                deleteConfirmBtn.disabled = false;
                showToast('Ошибка соединения', 'error');
            });
        });
    }

    /* ── Форма редактирования — AJAX ── */
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const routes = {
                movie:   ['/admin/edit_movie',  'movie_id'],
                series:  ['/admin/edit_series', 'series_id'],
                trailer: ['/admin/edit_movie',  'movie_id'],
            };
            const [url, idKey] = routes[_editType] || ['/admin/edit_movie', 'movie_id'];

            const body = {
                [idKey]:     _editId,
                title:       document.getElementById('editTitle').value,
                rating:      document.getElementById('editRating').value,
                year:        document.getElementById('editYear').value,
                description: document.getElementById('editDescription').value,
            };

            const btn = editForm.querySelector('.btn-submit');
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохраняем...';
            btn.disabled = true;

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            .then(r => r.json())
            .then(data => {
                btn.innerHTML = orig;
                btn.disabled = false;
                if (data.success) {
                    showToast('Изменения сохранены!');
                    closeModal('editModal');
                    // Обновить строку в таблице без перезагрузки
                    const tabId = _editType === 'movie' ? 'movies' : _editType === 'series' ? 'series' : 'trailers';
                    const row = document.querySelector(`#tab-${tabId} [data-id="${_editId}"]`);
                    if (row) {
                        row.dataset.title = body.title;
                        row.dataset.year = body.year;
                        row.dataset.rating = body.rating;
                        row.dataset.description = body.description;
                        const cells = row.querySelectorAll('div');
                        if (cells[1]) cells[1].textContent = body.title;
                        if (cells[2]) cells[2].textContent = body.year;
                    }
                } else showToast('Ошибка: ' + (data.message || ''), 'error');
            })
            .catch(() => {
                btn.innerHTML = orig;
                btn.disabled = false;
                showToast('Ошибка соединения', 'error');
            });
        });
    }

    /* ── Глобальный поиск ── */
    const globalSearch = document.getElementById('searchInput');
    if (globalSearch) {
        globalSearch.addEventListener('keydown', e => {
            if (e.key === 'Enter' && globalSearch.value.trim())
                window.location.href = '/search?q=' + encodeURIComponent(globalSearch.value.trim());
        });
    }

    /* ── Бургер ── */
    const burger = document.getElementById('burgerMenu');
    const sidebar = document.getElementById('sidebar');
    if (burger && sidebar) {
        burger.addEventListener('click', () => sidebar.classList.toggle('open'));
    }

    /* ── Открыть нужную вкладку по URL ── */
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab) {
        const tabPane = document.getElementById('tab-' + tab);
        if (tabPane) {
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            tabPane.classList.add('active');
            const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b =>
                (b.getAttribute('onclick') || '').includes(`'${tab}'`)
            );
            if (btn) btn.classList.add('active');
        }
    }

    if (params.get('success')) showToast('Успешно сохранено!');
    if (params.get('deleted')) showToast('Запись удалена');
});