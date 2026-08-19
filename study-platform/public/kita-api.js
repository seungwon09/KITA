(function () {
    const configuredBase = String(window.KITA_API_BASE || '').replace(/\/$/, '');
    const sameOrigin = location.origin;
    const apiBase = configuredBase || sameOrigin;
    const originalFetch = window.fetch.bind(window);

    window.kitaApiBase = apiBase;
    window.kitaApiUrl = function (path) {
        const value = String(path || '');
        if (/^https?:\/\//i.test(value)) return value;
        if (!value.startsWith('/api/')) return value;
        return `${apiBase}${value}`;
    };

    window.fetch = function (input, init) {
        if (typeof input === 'string') return originalFetch(window.kitaApiUrl(input), init);
        return originalFetch(input, init);
    };
})();

