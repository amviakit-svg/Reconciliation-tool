
        // Safely inject CSS to hide the standalone header if loaded inside the SaaS wrapper iframe
        if (window.self !== window.top) {
            const style = document.createElement('style');
            style.textContent = 'header { display: none !important; } main { padding-top: 1rem !important; padding-bottom: 1rem !important; }';
            document.head.appendChild(style);
        }
    