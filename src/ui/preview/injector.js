(function () {
    // Web View Error Injector for Gaia
    // Captures errors and sends them to the Python backend

    function sendToGaia(type, message, source, lineno, colno, stack) {
        if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.gaia) {
            window.webkit.messageHandlers.gaia.postMessage({
                "type": type,
                "message": message,
                "source": source,
                "lineno": lineno,
                "colno": colno,
                "stack": stack || ""
            });
        }
    }

    // 1. Capture Global Errors
    window.onerror = function (message, source, lineno, colno, error) {
        sendToGaia("error", message, source, lineno, colno, error ? error.stack : "");
        // Don't swallow the error, let it print to console context too if needed
        return false;
    };

    // 2. Capture Unhandled Promise Rejections
    window.onunhandledrejection = function (event) {
        sendToGaia("unhandled_rejection", event.reason ? event.reason.toString() : "Unknown Promise Error", "", 0, 0, "");
    };

    // 3. Hook console.error
    var originalConsoleError = console.error;
    console.error = function () {
        var message = Array.from(arguments).join(" ");
        sendToGaia("console_error", message, "", 0, 0, "");
        originalConsoleError.apply(console, arguments);
    };

    // 4. Hook console.log (for debug visibility)
    var originalConsoleLog = console.log;
    console.log = function () {
        var message = Array.from(arguments).join(" ");
        // Send logs as 'log' type
        sendToGaia("log", message, "", 0, 0, "");
        originalConsoleLog.apply(console, arguments);
    };

    console.log("[Gaia] Error listener injected.");
})();
