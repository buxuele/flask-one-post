const Components = {
    renderNavigation(activePage) {
        const nav = document.querySelector('.nav');
        if (!nav) return;

        const pages = [
            { name: '发布', path: '/', key: 'publish' },
            { name: '历史', path: '/history', key: 'history' }
        ];

        const linksHTML = pages.map(page => `
            <li>
                <a href="${page.path}" class="nav-link ${activePage === page.key ? 'active' : ''}">
                    ${page.name}
                </a>
            </li>
        `).join('');

        nav.innerHTML = `
            <a href="/" class="nav-brand">Echo</a>
            <ul class="nav-links">${linksHTML}</ul>
        `;
    },

    createProgressDrawer() {
        const drawer = document.createElement('div');
        drawer.className = 'progress-drawer';
        drawer.id = 'progressDrawer';
        drawer.innerHTML = `
            <div class="progress-drawer-header">
                <div class="progress-title">发布进度</div>
                <button class="progress-close" id="progressClose">
                    <span class="icon" style="width: 20px; height: 20px;">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/>
                        </svg>
                    </span>
                </button>
            </div>
            <div class="progress-list" id="progressList"></div>
            <div class="progress-result" id="progressResult"></div>
            <div class="progress-actions" id="progressActions" style="display: none;">
                <button class="btn btn-outline" id="cancelPublishBtn" style="width: 100%;">
                    <span>取消发布</span>
                </button>
            </div>
        `;
        document.body.appendChild(drawer);

        document.getElementById('progressClose').addEventListener('click', () => {
            drawer.classList.remove('show');
        });

        return drawer;
    },

    createToast() {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.id = 'toast';
        document.body.appendChild(toast);
        return toast;
    }
};

window.Components = Components;
