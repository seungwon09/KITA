(function () {
    const items = [
        ['홈', '/'],
        ['AI 학습', '/ai.html'],
        ['문제 풀이', '/ai.html#solve'],
        ['학습 통계', '/stats.html'],
        ['오답노트', '/wrong.html'],
        ['업그레이드', '/billing.html'],
        ['친구 초대', '/rewards.html']
    ];

    function token() {
        return localStorage.getItem('token');
    }

    function logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('kitaPlan');
        location.href = '/';
    }

    function ensureNav() {
        let topbar = document.querySelector('.topbar');
        if (!topbar) {
            topbar = document.createElement('header');
            topbar.className = 'topbar';
            topbar.innerHTML = '<button class="brand" onclick="location.href=\'/\'">KITA</button><div class="nav-actions"></div>';
            document.body.prepend(topbar);
        }
        const actions = topbar.querySelector('.nav-actions') || topbar.appendChild(document.createElement('div'));
        actions.className = 'nav-actions';
        if (actions.querySelector('[data-kita-menu]')) return;

        const loginBtn = document.createElement('button');
        loginBtn.className = 'btn ghost optional';
        loginBtn.textContent = token() ? '로그아웃' : '로그인';
        loginBtn.onclick = () => token() ? logout() : location.href = '/login.html';
        actions.appendChild(loginBtn);

        const menuBtn = document.createElement('button');
        menuBtn.className = 'hamburger';
        menuBtn.type = 'button';
        menuBtn.setAttribute('aria-label', '더보기');
        menuBtn.dataset.kitaMenu = 'true';
        menuBtn.innerHTML = '<span></span><span></span><span></span>';
        actions.appendChild(menuBtn);

        const panel = document.createElement('div');
        panel.className = 'menu-panel';
        panel.hidden = true;
        panel.innerHTML = items.map(([label, path]) => `<button type="button" data-path="${path}">${label}</button>`).join('')
            + `<button type="button" data-auth>${token() ? '로그아웃' : '로그인'}</button>`;
        document.body.appendChild(panel);
        panel.addEventListener('click', event => {
            const button = event.target.closest('button');
            if (!button) return;
            if (button.dataset.auth !== undefined) return token() ? logout() : location.href = '/login.html';
            location.href = button.dataset.path;
        });
        menuBtn.addEventListener('click', () => panel.hidden = !panel.hidden);
        document.addEventListener('click', event => {
            if (!panel.hidden && !panel.contains(event.target) && !menuBtn.contains(event.target)) panel.hidden = true;
        });
    }

    window.kitaAuthHeaders = function () {
        return token() ? { Authorization: `Bearer ${token()}` } : {};
    };
    window.kitaRequireLogin = function () {
        if (token()) return true;
        location.href = '/login.html';
        return false;
    };
    window.kitaFormatMath = function (value) {
        const escape = String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
        return escape
            .replace(/\\\[([\s\S]*?)\\\]/g, (_, formula) => `<span class="formula">${formatFormula(formula)}</span>`)
            .replace(/\\\(([\s\S]*?)\\\)/g, (_, formula) => `<span class="formula-inline">${formatFormula(formula)}</span>`)
            .replace(/([A-Za-z0-9가-힣)])\^(-?\d+)/g, '$1<sup>$2</sup>')
            .replace(/x²/g, 'x<sup>2</sup>')
            .replace(/x³/g, 'x<sup>3</sup>')
            .replace(/\n/g, '<br>');
    };

    function formatFormula(formula) {
        return String(formula)
            .replace(/\\left|\\right/g, '')
            .replace(/\\Delta/g, 'Δ')
            .replace(/\\mu/g, 'μ')
            .replace(/\\pi/g, 'π')
            .replace(/\\ln/g, 'ln')
            .replace(/\\sqrt\{([^{}]+)\}/g, '√($1)')
            .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '<span class="frac"><span class="top">$1</span><span class="bottom">$2</span></span>')
            .replace(/\\vec\{([^{}]+)\}/g, '<span style="text-decoration:overline;font-style:italic">$1</span>')
            .replace(/\{([^{}]+)\}/g, '$1')
            .replace(/_\{?([A-Za-z0-9]+)\}?/g, '<sub>$1</sub>')
            .replace(/\^\{?(-?[A-Za-z0-9]+)\}?/g, '<sup>$1</sup>');
    }

    ensureNav();
})();
