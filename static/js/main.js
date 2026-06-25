async function triggerBackup() {
    const statusEl = document.getElementById('backup-status');
    statusEl.className = '';
    statusEl.style.display = 'block';
    statusEl.textContent = 'Выполняется бэкап...';

    try {
        const response = await fetch('/api/backup', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            statusEl.className = 'success';
            statusEl.textContent = `Бэкап выполнен успешно! Файл: ${data.filename} (${formatSize(data.size)})`;
        } else if (data.status === 'skipped') {
            statusEl.className = 'error';
            statusEl.textContent = 'Бэкап пропущен: Dropbox не подключён';
        } else {
            statusEl.className = 'error';
            statusEl.textContent = `Ошибка: ${data.message}`;
        }
    } catch (error) {
        statusEl.className = 'error';
        statusEl.textContent = 'Ошибка сети при выполнении бэкапа';
    }
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function loadDropboxStatus() {
    const textEl = document.getElementById('dropbox-status-text');
    const actionsEl = document.getElementById('dropbox-actions');
    const backupBtn = document.getElementById('backup-btn');
    const backupHint = document.querySelector('.backup-hint');
    if (!textEl) return;

    try {
        const resp = await fetch('/api/dropbox/status');
        const data = await resp.json();

        if (data.connected) {
            textEl.innerHTML = `Dropbox подключён <span class="dropbox-account">${data.account_name || ''}</span>`;
            if (actionsEl) actionsEl.innerHTML = '<button onclick="disconnectDropbox()" class="btn btn-sm btn-danger">Отключить</button>';
            if (backupBtn) {
                backupBtn.textContent = 'Сделать бэкап сейчас';
                backupBtn.disabled = false;
                backupBtn.onclick = triggerBackup;
            }
            if (backupHint) backupHint.textContent = 'Автоматическое копирование в Dropbox ежедневно в 03:00';
        } else if (data.configured) {
            textEl.textContent = 'Dropbox не подключён';
            if (actionsEl) actionsEl.innerHTML = '';
            if (backupBtn) {
                backupBtn.textContent = 'Подключить Dropbox';
                backupBtn.disabled = false;
                backupBtn.onclick = connectDropbox;
                backupBtn.className = 'btn btn-primary';
            }
            if (backupHint) backupHint.textContent = 'Подключите Dropbox для автоматических бэкапов';
        } else {
            textEl.textContent = 'Dropbox: настройте APP_KEY и APP_SECRET в .env';
            if (actionsEl) actionsEl.innerHTML = '';
            if (backupBtn) {
                backupBtn.textContent = 'Настроить Dropbox';
                backupBtn.disabled = true;
                backupBtn.className = 'btn btn-secondary';
            }
            if (backupHint) backupHint.textContent = 'Добавьте DROPBOX_APP_KEY и DROPBOX_APP_SECRET в .env';
        }
    } catch (e) {
        textEl.textContent = 'Dropbox: ошибка проверки статуса';
        if (actionsEl) actionsEl.innerHTML = '';
    }
}

async function connectDropbox() {
    try {
        const resp = await fetch('/api/dropbox/auth');
        const data = await resp.json();
        if (data.auth_url) {
            window.location.href = data.auth_url;
        } else if (data.error) {
            alert(data.error);
        }
    } catch (e) {
        alert('Не удалось начать авторизацию');
    }
}

async function disconnectDropbox() {
    if (!confirm('Отключить Dropbox? Бэкапы прекратятся.')) return;
    try {
        await fetch('/api/dropbox/disconnect', { method: 'POST' });
        loadDropboxStatus();
    } catch (e) {
        alert('Ошибка отключения');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchInput.closest('form').submit();
            }
        });
    }

    loadDropboxStatus();

    const params = new URLSearchParams(window.location.search);
    if (params.get('dropbox_connected') === '1') {
        window.history.replaceState({}, '', '/');
        const statusEl = document.getElementById('backup-status');
        if (statusEl) {
            statusEl.className = 'success';
            statusEl.style.display = 'block';
            statusEl.textContent = 'Dropbox успешно подключён!';
            setTimeout(() => { statusEl.style.display = 'none'; }, 3000);
        }
    }
    if (params.get('dropbox_error')) {
        window.history.replaceState({}, '', '/');
        const statusEl = document.getElementById('backup-status');
        if (statusEl) {
            statusEl.className = 'error';
            statusEl.style.display = 'block';
            statusEl.textContent = 'Ошибка подключения Dropbox. Попробуйте ещё раз.';
        }
    }
});
