document.addEventListener('DOMContentLoaded', function () {
    const bell = document.getElementById('notificationBell');
    const dropdown = document.getElementById('notificationDropdown');
    const countEl = document.getElementById('notificationCount');
    const listEl = document.getElementById('notificationList');
    const markReadBtn = document.getElementById('markAllReadBtn');

    if (!isLoggedIn || !bell) {
        if (bell) bell.style.display = 'none';
        return;
    }

    bell.addEventListener('click', function (e) {
        e.stopPropagation();
        bell.classList.toggle('open');
        if (bell.classList.contains('open') && parseInt(countEl.textContent || '0') > 0) {
            setTimeout(markAllAsRead, 2500);
        }
    });

    document.addEventListener('click', function () {
        bell.classList.remove('open');
    });

    dropdown.addEventListener('click', function (e) {
        e.stopPropagation();
    });

    async function fetchNotifications() {
        try {
            const res = await fetch('/api/notifications');
            if (!res.ok) return;
            const data = await res.json();
            renderNotifications(data.notifications, data.unread_count);
        } catch (e) {
            console.error("Failed to fetch notifications", e);
        }
    }

    function renderNotifications(notifications, unread_count) {
        if (unread_count > 0) {
            countEl.textContent = unread_count > 9 ? '9+' : unread_count;
            countEl.classList.add('visible');
        } else {
            countEl.classList.remove('visible');
        }

        if (!listEl) return;

        if (notifications.length === 0) {
            listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Уведомлений нет</div>';
            return;
        }

        listEl.innerHTML = notifications.map(n => `
            <a href="${n.link || '#'}" class="notification-item ${n.is_read ? '' : 'unread'}">
                <p>${n.message}</p>
                <span class="time">${timeAgo(n.created_at)}</span>
            </a>
        `).join('');
    }

    async function markAllAsRead() {
        try {
            await fetch('/api/notifications/mark_read', { method: 'POST' });
            countEl.classList.remove('visible');
            countEl.textContent = '0';
            document.querySelectorAll('.notification-item.unread').forEach(item => {
                item.classList.remove('unread');
            });
        } catch (e) {
            console.error("Failed to mark notifications as read", e);
        }
    }

    if (markReadBtn) {
        markReadBtn.addEventListener('click', function (e) {
            e.preventDefault();
            markAllAsRead();
        });
    }

    function timeAgo(dateString) {
        const date = new Date(dateString);
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " г. назад";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " мес. назад";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " д. назад";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " ч. назад";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " мин. назад";
        return "только что";
    }

    fetchNotifications();
    setInterval(fetchNotifications, 60000); // Проверять новые раз в минуту
});