// デバッグ用スクリプト
console.log('=== Debug Script Loaded ===');

// MutationObserverで画面の変更を監視
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.target.id === 'gemini-status') {
            console.log('Gemini status changed:', mutation.target.innerHTML);
        }
        if (mutation.type === 'childList' && mutation.target.id === 'openai-status') {
            console.log('OpenAI status changed:', mutation.target.innerHTML);
        }
    });
});

// 監視開始
setTimeout(() => {
    const geminiStatus = document.getElementById('gemini-status');
    const openaiStatus = document.getElementById('openai-status');
    
    if (geminiStatus) {
        observer.observe(geminiStatus, { childList: true, subtree: true });
        console.log('Watching gemini-status');
    }
    
    if (openaiStatus) {
        observer.observe(openaiStatus, { childList: true, subtree: true });
        console.log('Watching openai-status');
    }
}, 1000);