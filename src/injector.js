(function() {
    console.log("Automation injector loaded.");

    // State
    window.__automationPaused = false;

    // Helper: Notify python side if binding exists
    function sendEvent(type, details = {}) {
        if (window.notifyPython) {
            window.notifyPython({ type, ...details }).catch(e => console.error(e));
        } else {
            console.log("notifyPython not bound. Event:", type, details);
        }
    }

    // CAPTCHA Detection heuristics
    const CAPTCHA_SELECTORS = [
        'iframe[src*="recaptcha"]',
        '.h-captcha',
        '[data-sitekey]',
        '#cf-challenge',
        '#cf-please-wait',
        '#challenge-running'
    ];

    function checkCaptcha() {
        if (window.__automationPaused) return;

        for (const sel of CAPTCHA_SELECTORS) {
            const el = document.querySelector(sel);
            if (el && el.offsetHeight > 0 && el.offsetWidth > 0) {
                // Ignore invisible recaptcha badges if possible, but basic height/width check helps
                if (el.src && el.src.includes('recaptcha') && el.parentElement && el.parentElement.style.opacity === '0') {
                    continue;
                }
                
                triggerPause("CAPTCHA detected: " + sel);
                return;
            }
        }
    }

    function triggerPause(reason) {
        window.__automationPaused = true;
        sendEvent("paused", { reason });
        showOverlay(reason);
    }

    // Popup/Cookie Banner Dismissal Heuristics
    const DISMISS_SELECTORS = [
        '#onetrust-accept-btn-handler',
        '#onetrust-reject-all-handler',
        '.cc-btn.cc-dismiss',
        '.cookie-btn',
        'button[id*="cookie" i]:not([id*="settings" i])',
        'button[class*="cookie" i]:not([class*="settings" i])',
        '[data-testid="cookie-policy-dialog-accept-button"]',
        '#CybotCookiebotDialogBodyButtonAccept',
        '.fc-button',
        // Common newsletter close buttons
        '.close-popup',
        '.modal-close',
        '[aria-label="Close"]',
        'button.close'
    ];

    function handlePopups() {
        for (const sel of DISMISS_SELECTORS) {
            const btns = document.querySelectorAll(sel);
            for (const btn of btns) {
                if (btn && btn.offsetHeight > 0 && !btn.dataset.autoDismissed) {
                    btn.dataset.autoDismissed = "true";
                    console.log("Auto-dismissing popup using selector:", sel);
                    sendEvent("log", { message: "Auto-dismissing popup: " + sel });
                    try {
                        btn.click();
                    } catch (e) { }
                }
            }
        }
    }

    // Overlay UI
    function showOverlay(reason) {
        if (document.getElementById('automation-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'automation-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); color: white; z-index: 2147483647;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-family: sans-serif;
        `;

        const box = document.createElement('div');
        box.style.cssText = `
            background: #222; padding: 30px; border-radius: 8px; text-align: center;
            max-width: 500px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        `;

        box.innerHTML = `
            <h2 style="color: #ff4444; margin-top: 0;">Automation Paused</h2>
            <p style="font-size: 16px;">${reason}</p>
            <p>Please solve the CAPTCHA in this window, then click Resume.</p>
        `;

        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'margin-top: 20px; display: flex; gap: 10px; justify-content: center;';

        const btnResume = document.createElement('button');
        btnResume.textContent = "I solved it - Resume";
        btnResume.style.cssText = "padding: 10px 20px; background: #4caf50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;";
        btnResume.onclick = () => {
            window.__automationPaused = false;
            overlay.remove();
            sendEvent("resumed");
        };

        const btnDebug = document.createElement('button');
        btnDebug.textContent = "Hide this overlay (Debug)";
        btnDebug.style.cssText = "padding: 10px 20px; background: #666; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;";
        btnDebug.onclick = () => {
            overlay.style.pointerEvents = 'none';
            overlay.style.background = 'transparent';
            box.style.display = 'none';
        };

        btnRow.appendChild(btnResume);
        btnRow.appendChild(btnDebug);
        box.appendChild(btnRow);
        overlay.appendChild(box);
        document.body.appendChild(overlay);
    }

    // Observer to detect dynamically added CAPTCHAs or Popups
    const observer = new MutationObserver((mutations) => {
        handlePopups();
        checkCaptcha();
    });

    // Start observing once body is available
    function init() {
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
            handlePopups();
            checkCaptcha();
        } else {
            setTimeout(init, 100);
        }
    }
    
    init();

})();
