(function() {
    let images = window.INITIAL_IMAGES || [];
    let isPublishing = false;
    let isAILoading = false;
    
    const contentInput = document.getElementById('contentInput');
    const imageGrid = document.getElementById('imageGrid');
    const fileInput = document.getElementById('fileInput');
    const refineBtn = document.getElementById('refineBtn');
    const refineIcon = document.getElementById('refineIcon');
    const publishBtn = document.getElementById('publishBtn');
    const progressDrawer = document.getElementById('progressDrawer');
    const progressList = document.getElementById('progressList');
    const progressResult = document.getElementById('progressResult');
    const progressClose = document.getElementById('progressClose');
    const charCounter = document.getElementById('charCounter');

    let publishTimer = null;
    let autoCloseTimer = null;
    const CHAR_LIMIT = 140;
    const CHAR_WARNING = 120;
    
    function renderImages() {
        const previewArea = document.querySelector('.image-preview-area');
        imageGrid.innerHTML = images.map((img, index) => `
            <div class="image-item" data-id="${img.id}" data-index="${index}" draggable="true">
                <div class="drag-handle">
                    <span class="icon" style="width: 12px; height: 12px;">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none"/><path d="M11 18c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm-2-8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm6 4c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z" fill="currentColor"/></svg>
                    </span>
                </div>
                <img src="${img.url}" alt="Preview" draggable="false">
                <button class="remove-btn" onclick="event.stopPropagation(); window.removeImage('${img.id}')">
                    <span class="icon" style="width: 10px; height: 10px;">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none"/><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/></svg>
                    </span>
                </button>
            </div>
        `).join('');

        if (images.length > 0) {
            previewArea.classList.add('has-images');
        } else {
            previewArea.classList.remove('has-images');
        }

        setupDragAndDrop();
    }

    // Expose removeImage to global for onclick
    window.removeImage = function(id) {
        images = images.filter(img => img.id !== id);
        renderImages();
    };

    let draggedItem = null;

    function setupDragAndDrop() {
        const items = document.querySelectorAll('.image-item');
        items.forEach(item => {
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragend', handleDragEnd);
            item.addEventListener('dragover', handleDragOver);
            item.addEventListener('drop', handleDrop);
            item.addEventListener('dragenter', handleDragEnter);
            item.addEventListener('dragleave', handleDragLeave);
        });
    }

    function handleDragStart(e) {
        draggedItem = this;
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.dataset.id);
    }

    function handleDragEnd(e) {
        this.classList.remove('dragging');
        draggedItem = null;
        document.querySelectorAll('.image-item').forEach(item => {
            item.classList.remove('drag-over');
        });
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDragEnter(e) {
        e.preventDefault();
        if (this !== draggedItem) {
            this.classList.add('drag-over');
        }
    }

    function handleDragLeave(e) {
        this.classList.remove('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        this.classList.remove('drag-over');

        if (this === draggedItem || !draggedItem) return;

        const draggedId = draggedItem.dataset.id;
        const targetId = this.dataset.id;

        const draggedIndex = images.findIndex(img => img.id === draggedId);
        const targetIndex = images.findIndex(img => img.id === targetId);

        if (draggedIndex !== -1 && targetIndex !== -1) {
            const [movedItem] = images.splice(draggedIndex, 1);
            images.splice(targetIndex, 0, movedItem);
            renderImages();
        }
    }
    
    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length === 0) return;
        fileInput.value = '';

        const formData = new FormData();
        files.forEach(file => formData.append('images', file));

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!data.success) {
                const errorMsg = data.errors ? data.errors.join('\n') : (data.message || '图片上传失败');
                showToast(errorMsg, 'error');
                return;
            }
            images = images.concat(data.images || []);
            renderImages();
            
            if (data.errors && data.errors.length > 0) {
                showToast(data.errors.join('\n'), 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('图片上传失败，请检查网络连接', 'error');
        }
    });
    
    document.querySelectorAll('.platform-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.classList.toggle('active');
        });
    });

    function updateCharCounter() {
        const count = contentInput.value.length;
        charCounter.textContent = `${count}/${CHAR_LIMIT}`;

        charCounter.classList.remove('warning', 'error');
        publishBtn.disabled = count > CHAR_LIMIT;

        if (count > CHAR_LIMIT) {
            charCounter.classList.add('error');
        } else if (count > CHAR_WARNING) {
            charCounter.classList.add('warning');
        }
    }

    contentInput.addEventListener('input', updateCharCounter);
    updateCharCounter();

    progressClose.addEventListener('click', () => {
        progressDrawer.classList.remove('show');
        if (autoCloseTimer) {
            clearTimeout(autoCloseTimer);
            autoCloseTimer = null;
        }
    });

    renderImages();

    refineBtn.addEventListener('click', async () => {
        const content = contentInput.value;
        if (!content || isAILoading) return;

        isAILoading = true;
        refineIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none"/><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/></svg>';
        refineIcon.classList.add('loading');

        try {
            const response = await fetch('/api/suggest-hashtags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            const data = await response.json();

            if (data.hashtags && data.hashtags.length > 0) {
                const hashtagStr = data.hashtags.map(t => `#${t.replace(/^#/, '')}`).join(' ');
                contentInput.value = contentInput.value.trim() + '\n\n' + hashtagStr;
                updateCharCounter();
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('AI 润色失败，请稍后重试', 'error');
        }

        isAILoading = false;
        refineIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none"/><path d="M18.85 8.65l.65.65-.65.65-.65-.65.65-.65M12 4.58l2.5 2.5-2.5 2.5-2.5-2.5 2.5-2.5m9.07 3.07l-1.4-1.4-1.4 1.4 1.4 1.4 1.4-1.4M7.35 15.15l-.65-.65.65-.65.65.65-.65.65M12 19.42l-2.5-2.5 2.5-2.5 2.5 2.5-2.5 2.5m-7.07-3.07l1.4 1.4 1.4-1.4-1.4-1.4-1.4 1.4M18.85 15.35l.65-.65-.65-.65-.65.65.65.65M12 2L9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2z" fill="currentColor"/></svg>';
        refineIcon.classList.remove('loading');
    });
    
    publishBtn.addEventListener('click', async () => {
        const content = contentInput.value;
        if (!content || isPublishing) return;
        
        const platformBtns = document.querySelectorAll('.platform-btn.active');
        const platforms = Array.from(platformBtns).map(btn => btn.dataset.platform);
        
        if (platforms.length === 0) {
            alert('请至少选择一个发布平台');
            return;
        }
        
        isPublishing = true;
        publishBtn.disabled = true;
        publishBtn.innerHTML = '<span>发布中...</span>';
        progressDrawer.classList.add('show');
        progressList.innerHTML = '';
        progressResult.textContent = '';
        progressResult.className = 'progress-result';
        
        try {
            const imagePaths = images.map(img => img.path).filter(Boolean);
            const response = await fetch('/api/publish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, platforms, image_paths: imagePaths })
            });
            const data = await response.json();
            if (!data.success) {
                progressResult.textContent = data.message || '发布失败';
                progressResult.classList.add('error');
                stopPublishing();
                return;
            }

            const jobId = data.job_id;
            if (!jobId) {
                progressResult.textContent = '未获取到任务编号';
                progressResult.classList.add('error');
                stopPublishing();
                return;
            }

            publishTimer = setInterval(() => pollPublishStatus(jobId, content), 1000);
        } catch (error) {
            console.error('Error:', error);
            progressResult.textContent = '发布失败，请检查控制台';
            progressResult.classList.add('error');
            stopPublishing();
        }
    });

    async function pollPublishStatus(jobId, originalContent) {
        try {
            const response = await fetch(`/api/publish/status/${jobId}`);
            const data = await response.json();
            if (!data.success || !data.job) {
                progressResult.textContent = data.message || '任务状态获取失败';
                progressResult.classList.add('error');
                stopPublishing();
                return;
            }

            const job = data.job;
            renderProgress(job.steps || []);

            if (job.status === 'done') {
                progressResult.textContent = job.message || '发布完成';
                progressResult.classList.add(job.success ? 'success' : 'error');
                if (job.success) {
                    contentInput.value = '';
                    images = [];
                    renderImages();
                    updateCharCounter();
                    autoCloseTimer = setTimeout(() => {
                        progressDrawer.classList.remove('show');
                    }, 3000);
                } else if (originalContent) {
                    contentInput.value = originalContent;
                }
                stopPublishing();
                return;
            }

            if (job.status === 'error') {
                progressResult.textContent = job.message || '发布失败';
                progressResult.classList.add('error');
                stopPublishing();
            }
        } catch (error) {
            console.error('Error:', error);
            progressResult.textContent = '发布状态获取失败';
            progressResult.classList.add('error');
            stopPublishing();
        }
    }

    function renderProgress(steps) {
        progressList.innerHTML = steps.map(step => `
            <div class="progress-item">
                <span class="progress-time">${escapeHtml(step.time || '')}</span>
                <span>${escapeHtml(step.message || '')}</span>
            </div>
        `).join('');
        progressList.scrollTop = progressList.scrollHeight;
    }

    function stopPublishing() {
        isPublishing = false;
        publishBtn.disabled = false;
        publishBtn.innerHTML = '<span>立即发布</span>';
        if (publishTimer) {
            clearInterval(publishTimer);
            publishTimer = null;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message, type = 'error') {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = message;
        toast.className = 'toast ' + type;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    const qualityPanel = document.getElementById('qualityPanel');
    let isDraggingPanel = false;
    let panelOffsetX = 0;
    let panelOffsetY = 0;

    if (qualityPanel) {
        qualityPanel.addEventListener('mousedown', (e) => {
            isDraggingPanel = true;
            panelOffsetX = e.clientX - qualityPanel.offsetLeft;
            panelOffsetY = e.clientY - qualityPanel.offsetTop;
            qualityPanel.classList.add('dragging');
        });
    }

    document.addEventListener('mousemove', (e) => {
        if (!isDraggingPanel || !qualityPanel) return;
        e.preventDefault();
        qualityPanel.style.left = (e.clientX - panelOffsetX) + 'px';
        qualityPanel.style.top = (e.clientY - panelOffsetY) + 'px';
    });

    document.addEventListener('mouseup', () => {
        isDraggingPanel = false;
        if (qualityPanel) qualityPanel.classList.remove('dragging');
    });

    // 草稿管理
    let currentDraftId = localStorage.getItem('echo_current_draft_id') || null;
    const draftPanel = document.getElementById('draftPanel');
    const draftList = document.getElementById('draftList');
    const newDraftBtn = document.getElementById('newDraftBtn');
    let autoSaveTimer = null;

    function getDrafts() {
        return JSON.parse(localStorage.getItem('echo_drafts') || '[]');
    }

    function saveDrafts(drafts) {
        localStorage.setItem('echo_drafts', JSON.stringify(drafts));
    }

    function createNewDraft() {
        const drafts = getDrafts();
        const newDraft = {
            id: Date.now().toString(),
            content: '',
            images: [],
            updatedAt: new Date().toISOString()
        };
        drafts.unshift(newDraft);
        saveDrafts(drafts);
        currentDraftId = newDraft.id;
        localStorage.setItem('echo_current_draft_id', currentDraftId);
        loadDraft(newDraft);
        renderDraftList();
        return newDraft;
    }

    function loadDraft(draft) {
        contentInput.value = draft.content || '';
        images = draft.images || [];
        renderImages();
        updateCharCounter();
        currentDraftId = draft.id;
        localStorage.setItem('echo_current_draft_id', currentDraftId);
        renderDraftList();
    }

    function saveCurrentDraft() {
        if (!currentDraftId) {
            if (!contentInput.value.trim() && images.length === 0) return;
            createNewDraft();
            return;
        }

        const drafts = getDrafts();
        const index = drafts.findIndex(d => d.id === currentDraftId);
        if (index !== -1) {
            drafts[index].content = contentInput.value;
            drafts[index].images = images;
            drafts[index].updatedAt = new Date().toISOString();
            saveDrafts(drafts);
            renderDraftList();
        }
    }

    // Expose deleteDraft to global
    window.deleteDraft = function(draftId, event) {
        event.stopPropagation();
        if (!confirm('确定删除此草稿？')) return;
        
        const drafts = getDrafts().filter(d => d.id !== draftId);
        saveDrafts(drafts);
        
        if (currentDraftId === draftId) {
            currentDraftId = null;
            localStorage.removeItem('echo_current_draft_id');
            contentInput.value = '';
            images = [];
            renderImages();
            updateCharCounter();
        }
        renderDraftList();
        showToast('草稿已删除', 'success');
    };

    function renderDraftList() {
        if (!draftList) return;
        const drafts = getDrafts();
        if (drafts.length === 0) {
            draftList.innerHTML = '<div class="draft-empty">暂无草稿</div>';
            return;
        }

        draftList.innerHTML = drafts.map(draft => {
            const isActive = draft.id === currentDraftId;
            const content = draft.content || '(无内容)';
            const date = new Date(draft.updatedAt).toLocaleDateString('zh-CN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            return `
                <div class="draft-item ${isActive ? 'active' : ''}" data-id="${draft.id}">
                    <div class="draft-item-content">${escapeHtml(content.substring(0, 50))}${content.length > 50 ? '...' : ''}</div>
                    <div class="draft-item-meta">
                        <span>${date}</span>
                        <button class="draft-delete-btn" onclick="window.deleteDraft('${draft.id}', event)">删除</button>
                    </div>
                </div>
            `;
        }).join('');

        draftList.querySelectorAll('.draft-item').forEach(item => {
            item.addEventListener('click', () => {
                const draftId = item.dataset.id;
                const draft = getDrafts().find(d => d.id === draftId);
                if (draft) loadDraft(draft);
            });
        });
    }

    // 自动保存
    contentInput.addEventListener('input', () => {
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            saveCurrentDraft();
        }, 2000);
    });

    if (newDraftBtn) newDraftBtn.addEventListener('click', createNewDraft);

    // 加载初始草稿
    const initialDrafts = getDrafts();
    if (currentDraftId) {
        const draft = initialDrafts.find(d => d.id === currentDraftId);
        if (draft) {
            loadDraft(draft);
        } else {
            currentDraftId = null;
            localStorage.removeItem('echo_current_draft_id');
        }
    }
    renderDraftList();

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'Enter':
                    e.preventDefault();
                    publishBtn.click();
                    break;
                case 's':
                    e.preventDefault();
                    saveCurrentDraft();
                    showToast('草稿已保存', 'success');
                    break;
                case 'l':
                    e.preventDefault();
                    refineBtn.click();
                    break;
                case 'p':
                    e.preventDefault();
                    const pBtn = document.getElementById('previewBtn');
                    if (pBtn) pBtn.click();
                    break;
            }
        }
    });

    // 预览功能
    const previewBtn = document.getElementById('previewBtn');
    const previewModal = document.getElementById('previewModal');
    const previewClose = document.getElementById('previewClose');
    const previewText = document.getElementById('previewText');
    const previewImages = document.getElementById('previewImages');
    const previewWarning = document.getElementById('previewWarning');
    const previewTabs = document.querySelectorAll('.preview-tab');
    let currentPreviewPlatform = 'twitter';

    if (previewBtn) {
        previewBtn.addEventListener('click', () => {
            const content = contentInput.value;
            previewText.textContent = content;
            
            previewImages.innerHTML = images.map(img => `
                <img src="${img.url}" class="preview-image" alt="">
            `).join('');

            // 检查字符限制
            const count = content.length;
            if (currentPreviewPlatform === 'twitter' && count > 280) {
                previewWarning.style.display = 'block';
                previewWarning.textContent = `⚠️ X (Twitter) 限制 280 字符，当前 ${count} 字符，超出 ${count - 280} 字符`;
            } else {
                previewWarning.style.display = 'none';
            }

            previewModal.classList.add('show');
        });
    }

    if (previewClose) {
        previewClose.addEventListener('click', () => {
            previewModal.classList.remove('show');
        });
    }

    if (previewModal) {
        previewModal.addEventListener('click', (e) => {
            if (e.target === previewModal) {
                previewModal.classList.remove('show');
            }
        });
    }

    previewTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            previewTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentPreviewPlatform = tab.dataset.platform;
            
            // 重新检查字符限制
            const content = contentInput.value;
            const count = content.length;
            if (currentPreviewPlatform === 'twitter' && count > 280) {
                previewWarning.style.display = 'block';
                previewWarning.textContent = `⚠️ X (Twitter) 限制 280 字符，当前 ${count} 字符，超出 ${count - 280} 字符`;
            } else {
                previewWarning.style.display = 'none';
            }
        });
    });

    // 定时发布
    const scheduleBtn = document.getElementById('scheduleBtn');
    const scheduleModal = document.getElementById('scheduleModal');
    const scheduleClose = document.getElementById('scheduleClose');
    const confirmScheduleBtn = document.getElementById('confirmScheduleBtn');
    const scheduleTimeInput = document.getElementById('scheduleTime');

    if (scheduleBtn) {
        scheduleBtn.addEventListener('click', () => {
            const content = contentInput.value;
            if (!content) {
                showToast('请先输入内容', 'error');
                return;
            }
            
            const platformBtns = document.querySelectorAll('.platform-btn.active');
            if (platformBtns.length === 0) {
                showToast('请至少选择一个发布平台', 'error');
                return;
            }
            
            // 设置默认时间为明天同一时间
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            tomorrow.setMinutes(0);
            scheduleTimeInput.value = tomorrow.toISOString().slice(0, 16);
            
            scheduleModal.classList.add('show');
        });
    }

    if (scheduleClose) {
        scheduleClose.addEventListener('click', () => {
            scheduleModal.classList.remove('show');
        });
    }

    if (scheduleModal) {
        scheduleModal.addEventListener('click', (e) => {
            if (e.target === scheduleModal) {
                scheduleModal.classList.remove('show');
            }
        });
    }

    if (confirmScheduleBtn) {
        confirmScheduleBtn.addEventListener('click', async () => {
            const scheduledTime = scheduleTimeInput.value;
            if (!scheduledTime) {
                showToast('请选择发布时间', 'error');
                return;
            }

            const content = contentInput.value;
            const platformBtns = document.querySelectorAll('.platform-btn.active');
            const platforms = Array.from(platformBtns).map(btn => btn.dataset.platform);
            const imagePathsArr = images.map(img => img.path).filter(Boolean);

            try {
                confirmScheduleBtn.disabled = true;
                confirmScheduleBtn.innerHTML = '<span>创建中...</span>';
                
                const response = await fetch('/api/scheduled', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content,
                        platforms,
                        image_paths: imagePathsArr,
                        scheduled_at: scheduledTime
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast('定时发布已创建', 'success');
                    scheduleModal.classList.remove('show');
                    
                    // 清除当前内容
                    contentInput.value = '';
                    images = [];
                    renderImages();
                    updateCharCounter();
                    
                    // 清除草稿
                    if (currentDraftId) {
                        const drafts = getDrafts().filter(d => d.id !== currentDraftId);
                        saveDrafts(drafts);
                        currentDraftId = null;
                        localStorage.removeItem('echo_current_draft_id');
                        renderDraftList();
                    }
                } else {
                    showToast(data.message || '创建失败', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('创建失败，请检查网络', 'error');
            } finally {
                confirmScheduleBtn.disabled = false;
                confirmScheduleBtn.innerHTML = '<span>确认定时发布</span>';
            }
        });
    }

    // 发布成功后清除当前草稿
    const originalStopPublishing = stopPublishing;
    stopPublishing = function() {
        if (typeof originalStopPublishing === 'function') originalStopPublishing();
        if (progressResult.classList.contains('success')) {
            const drafts = getDrafts().filter(d => d.id !== currentDraftId);
            saveDrafts(drafts);
            currentDraftId = null;
            localStorage.removeItem('echo_current_draft_id');
            renderDraftList();
        }
    };
})();
