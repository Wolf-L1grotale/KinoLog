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
            statusEl.textContent = 'Бэкап пропущен: токен Dropbox не настроен';
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

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchInput.closest('form').submit();
            }
        });
    }
});
