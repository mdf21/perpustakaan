function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatRupiah(angka) {
    if (!angka && angka !== 0) return 'Rp 0';
    return 'Rp ' + parseInt(angka).toLocaleString('id-ID');
}

function showNotification(message, type) {
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const html = `<div class="alert ${alertClass} alert-dismissible fade show" role="alert">${escapeHtml(message)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
    const container = document.querySelector('.container-fluid');
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    container.insertBefore(wrapper, container.firstChild);
    setTimeout(() => {
        wrapper.firstElementChild.remove();
    }, 5000);
}
