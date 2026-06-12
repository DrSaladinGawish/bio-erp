/**
 * Co-Pilot Panel — Floating Smart Assistant for IncentiveHouse ERP
 * 
 * Embeds on every form. Provides:
 * - Contextual insights and tips
 * - Quick action buttons
 * - Smart recommendations
 * - Real-time alerts
 * 
 * Usage: Include this script on any page. Call initCoPilotPanel(formType, entityId)
 */

(function() {
    'use strict';

    // ── Configuration ──────────────────────────────────────────────────
    const CONFIG = {
        apiBase: window.COPILOT_API_BASE || '/api/v1/copilot',
        refreshInterval: 30000,  // 30 seconds
        panelPosition: 'bottom-right',  // bottom-right, bottom-left, top-right, top-left
        theme: 'dark',  // dark, light
    };

    // ── State ──────────────────────────────────────────────────────────
    let panelElement = null;
    let currentFormType = 'dashboard';
    let currentEntityId = null;
    let refreshTimer = null;

    // ── Icons (SVG) ─────────────────────────────────────────────────────
    const ICONS = {
        robot: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><circle cx="8" cy="14" r="1" fill="currentColor"/><circle cx="16" cy="14" r="1" fill="currentColor"/></svg>',
        lightbulb: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-7 7c0 2 2 3 2 6h10c0-3 2-4 2-6a7 7 0 0 0-7-7z"/></svg>',
        alert: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        check: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        arrow: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
        close: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        expand: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>',
        collapse: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>',
    };

    // ── CSS Injection ──────────────────────────────────────────────────
    function injectStyles() {
        if (document.getElementById('copilot-panel-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'copilot-panel-styles';
        styles.textContent = `
            .copilot-panel {
                position: fixed;
                z-index: 9999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 13px;
                line-height: 1.5;
                transition: all 0.3s ease;
            }
            .copilot-panel.bottom-right { bottom: 20px; right: 20px; }
            .copilot-panel.bottom-left { bottom: 20px; left: 20px; }
            .copilot-panel.top-right { top: 20px; right: 20px; }
            .copilot-panel.top-left { top: 20px; left: 20px; }

            .copilot-panel.minimized .copilot-body { display: none; }
            .copilot-panel.minimized { width: auto; }

            .copilot-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 10px 14px;
                border-radius: 12px 12px 0 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                cursor: pointer;
                user-select: none;
            }
            .copilot-panel.minimized .copilot-header {
                border-radius: 12px;
            }

            .copilot-header-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
                font-size: 14px;
            }

            .copilot-header-actions {
                display: flex;
                gap: 6px;
            }

            .copilot-header-btn {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            .copilot-header-btn:hover { background: rgba(255,255,255,0.3); }

            .copilot-body {
                background: #1a1a2e;
                color: #e0e0e0;
                width: 360px;
                max-height: 500px;
                overflow-y: auto;
                border-radius: 0 0 12px 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }

            .copilot-section {
                padding: 12px 14px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            .copilot-section:last-child { border-bottom: none; }

            .copilot-section-title {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #8892b0;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .copilot-insight {
                background: rgba(102, 126, 234, 0.1);
                border-left: 3px solid #667eea;
                padding: 8px 10px;
                border-radius: 0 6px 6px 0;
                margin-bottom: 6px;
                font-size: 12px;
            }

            .copilot-alert {
                background: rgba(239, 68, 68, 0.1);
                border-left: 3px solid #ef4444;
                padding: 8px 10px;
                border-radius: 0 6px 6px 0;
                margin-bottom: 6px;
                font-size: 12px;
            }

            .copilot-tip {
                background: rgba(34, 197, 94, 0.1);
                border-left: 3px solid #22c55e;
                padding: 8px 10px;
                border-radius: 0 6px 6px 0;
                margin-bottom: 6px;
                font-size: 12px;
            }

            .copilot-action-btn {
                display: flex;
                align-items: center;
                justify-content: space-between;
                width: 100%;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                color: #e0e0e0;
                padding: 8px 12px;
                border-radius: 8px;
                margin-bottom: 6px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 12px;
                text-decoration: none;
            }
            .copilot-action-btn:hover {
                background: rgba(102, 126, 234, 0.2);
                border-color: #667eea;
            }

            .copilot-shortcut {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                background: rgba(255,255,255,0.08);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                color: #8892b0;
                text-decoration: none;
                margin-right: 6px;
                margin-bottom: 6px;
                transition: all 0.2s;
            }
            .copilot-shortcut:hover {
                background: rgba(102, 126, 234, 0.2);
                color: #e0e0e0;
            }

            .copilot-loading {
                text-align: center;
                padding: 20px;
                color: #8892b0;
            }

            .copilot-error {
                background: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                padding: 10px;
                border-radius: 6px;
                margin: 10px;
                font-size: 12px;
            }

            .copilot-badge {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 600;
            }
            .copilot-badge.high { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
            .copilot-badge.medium { background: rgba(234, 179, 8, 0.2); color: #eab308; }
            .copilot-badge.low { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

            /* Scrollbar */
            .copilot-body::-webkit-scrollbar { width: 6px; }
            .copilot-body::-webkit-scrollbar-track { background: transparent; }
            .copilot-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
            .copilot-body::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

            /* Pulse animation for new alerts */
            @keyframes copilot-pulse {
                0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
            }
            .copilot-panel.has-alert .copilot-header {
                animation: copilot-pulse 2s infinite;
            }
        `;
        document.head.appendChild(styles);
    }

    // ── Panel Creation ─────────────────────────────────────────────────
    function createPanel() {
        if (panelElement) return;

        injectStyles();

        panelElement = document.createElement('div');
        panelElement.className = `copilot-panel ${CONFIG.panelPosition}`;
        panelElement.innerHTML = `
            <div class="copilot-header" onclick="copilotToggle()">
                <div class="copilot-header-title">
                    ${ICONS.robot}
                    <span>Co-Pilot</span>
                </div>
                <div class="copilot-header-actions">
                    <button class="copilot-header-btn" onclick="event.stopPropagation(); copilotToggle()" title="Toggle">
                        ${ICONS.collapse}
                    </button>
                </div>
            </div>
            <div class="copilot-body">
                <div class="copilot-loading">Loading insights...</div>
            </div>
        `;

        document.body.appendChild(panelElement);

        // Make functions global for onclick handlers
        window.copilotToggle = togglePanel;
        window.copilotRefresh = refreshPanel;
        window.copilotAction = handleAction;
    }

    // ── Panel Toggle ────────────────────────────────────────────────────
    function togglePanel() {
        if (!panelElement) return;
        panelElement.classList.toggle('minimized');

        // Update icon
        const btn = panelElement.querySelector('.copilot-header-btn');
        if (btn) {
            const isMinimized = panelElement.classList.contains('minimized');
            btn.innerHTML = isMinimized ? ICONS.expand : ICONS.collapse;
        }

        // If expanding, refresh data
        if (!panelElement.classList.contains('minimized')) {
            refreshPanel();
        }
    }

    // ── Data Fetching ────────────────────────────────────────────────────
    async function fetchPanelData() {
        try {
            const response = await fetch(`${CONFIG.apiBase}/panel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    form_type: currentFormType,
                    entity_id: currentEntityId,
                    user_role: window.CURRENT_USER_ROLE || 'user',
                    current_form_data: getFormData(),
                }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Co-Pilot fetch error:', error);
            return null;
        }
    }

    function getFormData() {
        // Extract data from current form if available
        const forms = document.querySelectorAll('form');
        if (forms.length === 0) return null;

        const data = {};
        const form = forms[0];
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.name) {
                data[input.name] = input.value;
            }
        });
        return data;
    }

    // ── Panel Rendering ────────────────────────────────────────────────
    async function refreshPanel() {
        if (!panelElement || panelElement.classList.contains('minimized')) return;

        const body = panelElement.querySelector('.copilot-body');
        body.innerHTML = '<div class="copilot-loading">Loading insights...</div>';

        const data = await fetchPanelData();

        if (!data || !data.success) {
            body.innerHTML = `
                <div class="copilot-error">
                    ${ICONS.alert} Unable to load insights. 
                    <button onclick="copilotRefresh()" style="background:none;border:none;color:#667eea;cursor:pointer;text-decoration:underline;">Retry</button>
                </div>
            `;
            return;
        }

        // Check for alerts
        const hasAlerts = data.alerts && data.alerts.length > 0;
        panelElement.classList.toggle('has-alert', hasAlerts);

        let html = '';

        // Alerts section
        if (data.alerts && data.alerts.length > 0) {
            html += `
                <div class="copilot-section">
                    <div class="copilot-section-title">${ICONS.alert} Alerts</div>
                    ${data.alerts.map(a => `<div class="copilot-alert">${a}</div>`).join('')}
                </div>
            `;
        }

        // Insights section
        if (data.insights && data.insights.length > 0) {
            html += `
                <div class="copilot-section">
                    <div class="copilot-section-title">${ICONS.lightbulb} Insights</div>
                    ${data.insights.map(i => `<div class="copilot-insight">${i}</div>`).join('')}
                </div>
            `;
        }

        // Tips section
        if (data.tips && data.tips.length > 0) {
            html += `
                <div class="copilot-section">
                    <div class="copilot-section-title">${ICONS.check} Tips</div>
                    ${data.tips.map(t => `<div class="copilot-tip">${t}</div>`).join('')}
                </div>
            `;
        }

        // Actions section
        if (data.contextual_actions && data.contextual_actions.length > 0) {
            html += `
                <div class="copilot-section">
                    <div class="copilot-section-title">⚡ Quick Actions</div>
                    ${data.contextual_actions.map(a => `
                        <button class="copilot-action-btn" onclick="copilotAction('${a.endpoint}', '${a.method}')">
                            <span>${a.label}</span>
                            ${ICONS.arrow}
                        </button>
                    `).join('')}
                </div>
            `;
        }

        // Shortcuts section
        if (data.shortcuts && data.shortcuts.length > 0) {
            html += `
                <div class="copilot-section">
                    <div class="copilot-section-title">🔗 Shortcuts</div>
                    <div>
                        ${data.shortcuts.map(s => `
                            <a href="${s.url}" class="copilot-shortcut">${s.label}</a>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Footer
        html += `
            <div class="copilot-section" style="text-align:center;color:#8892b0;font-size:11px;padding:8px;">
                Local AI • ${data.processing_time_ms ? data.processing_time_ms.toFixed(0) + 'ms' : 'cached'}
            </div>
        `;

        body.innerHTML = html;
    }

    // ── Action Handler ─────────────────────────────────────────────────
    async function handleAction(endpoint, method) {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };

            // For POST requests, include current context
            if (method === 'POST') {
                options.body = JSON.stringify({
                    event_id: currentEntityId,
                    form_type: currentFormType,
                });
            }

            const response = await fetch(`${CONFIG.apiBase}${endpoint}`, options);
            const result = await response.json();

            if (result.success) {
                // Show success notification
                showNotification('✅ Action completed successfully', 'success');
                refreshPanel();
            } else {
                showNotification('❌ ' + (result.message || 'Action failed'), 'error');
            }
        } catch (error) {
            showNotification('❌ Network error', 'error');
        }
    }

    function showNotification(message, type) {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            background: ${type === 'success' ? '#22c55e' : '#ef4444'};
        `;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ── Auto-Refresh ────────────────────────────────────────────────────
    function startAutoRefresh() {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(refreshPanel, CONFIG.refreshInterval);
    }

    // ── Public API ──────────────────────────────────────────────────────
    window.initCoPilotPanel = function(formType, entityId) {
        currentFormType = formType || 'dashboard';
        currentEntityId = entityId || null;

        createPanel();
        refreshPanel();
        startAutoRefresh();

        console.log(`🤖 Co-Pilot initialized for ${formType}`);
    };

    window.destroyCoPilotPanel = function() {
        if (refreshTimer) clearInterval(refreshTimer);
        if (panelElement) {
            panelElement.remove();
            panelElement = null;
        }
    };

    // ── Auto-init on page load ──────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            // Auto-detect form type from URL or data attribute
            const formType = document.body.dataset.formType || 'dashboard';
            const entityId = document.body.dataset.entityId || null;
            window.initCoPilotPanel(formType, entityId);
        });
    } else {
        const formType = document.body.dataset.formType || 'dashboard';
        const entityId = document.body.dataset.entityId || null;
        window.initCoPilotPanel(formType, entityId);
    }

})();
