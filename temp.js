
        (function() {
            const originalWarn = console.warn;
            console.warn = function(...args) {
                const msg = args.join(' ');
                if (msg.includes('cdn.tailwindcss.com') && msg.includes('production')) return;
                if (msg.includes('SES Removing unpermitted intrinsics')) return;
                originalWarn.apply(console, args);
            };
            const originalLog = console.log;
            console.log = function(...args) {
                const msg = args.join(' ');
                if (msg.includes('lockdown-install.js') && msg.includes('SES')) return;
                originalLog.apply(console, args);
            };
        })();
    