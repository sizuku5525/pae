// メインJavaScriptファイル

// ページ読み込み完了時の処理
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips の初期化
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// ローディング表示
function showLoading() {
    const loadingHtml = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">処理中...</p>
        </div>
    `;
    return loadingHtml;
}

// エラー処理
function handleError(error) {
    console.error('Error:', error);
    let message = 'エラーが発生しました';
    if (error.responseJSON && error.responseJSON.error) {
        message = error.responseJSON.error;
    }
    return message;
}