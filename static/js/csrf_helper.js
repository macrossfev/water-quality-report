// CSRF Protection Helper
// Automatically injects X-CSRFToken header into all fetch requests
(function() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return;
    var token = meta.getAttribute('content');
    if (!token) return;

    var originalFetch = window.fetch;
    window.fetch = function(url, options) {
        options = options || {};
        var headers = options.headers || {};

        if (headers instanceof Headers) {
            if (!headers.has('X-CSRFToken')) {
                headers.set('X-CSRFToken', token);
            }
        } else {
            if (!headers['X-CSRFToken']) {
                headers['X-CSRFToken'] = token;
            }
        }
        options.headers = headers;
        return originalFetch.call(this, url, options);
    };
})();
