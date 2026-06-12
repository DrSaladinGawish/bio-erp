/*
 * Co-Pilot Smart Panel — Floating AI Assistant
 * Injects into any ERP form for contextual suggestions.
 * Fully offline, self-contained.
 *
 * Usage:
 *   <script src="/static/js/copilot-panel.js"></script>
 *   <script>initCoPilotPanel('event', 42);</script>
 */

(function() {
    'use strict';

    let panelState = {
        open: false,
        formType: 'dashboard',
        entityId: null,
        apiBase: window.COPILOT_API_BASE || '/api/v1/copilot',
        session: [],
    };

    // ── DOM Injection ──────────────────────────────────────────────────────

    function injectPanel() {
        if (document.getElementById('copilot-panel-root')) return;
        const div = document.createElement('div');
        div.id = 'copilot-panel-root';
        div.innerHTML = `
            <div id="copilot-panel" class="copilot-panel">
                <div class="copilot-header" id="copilotHeader">
                    <div class="copilot-header-left">
                        <span class="copilot-icon">🧠</span>
                        <span class="copilot-title">Co-Pilot</span>
                        <span class="copilot-status-dot" id="copilotStatusDot"></span>
                    </div>
                    <div class="copilot-header-right">
                        <span class="copilot-context-label" id="copilotContextLabel">Dashboard</span>
                        <button class="copilot-close-btn" id="copilotCloseBtn" title="Close">✕</button>
                    </div>
                </div>
                <div class="copilot-body" id="copilotBody">
                    <div class="copilot-loading" id="copilotLoading">Analyzing...</div>
                    <div class="copilot-content" id="copilotContent"></div>
                </div>
                <div class="copilot-footer">
                    <div class="copilot-summary" id="copilotSummary"></div>
                    <div class="copilot-input-row">
                        <input type="text" class="copilot-input" id="copilotInput"
                               placeholder="Ask Co-Pilot..." />
                        <button class="copilot-send-btn" id="copilotSendBtn">➤</button>
                    </div>
                </div>
            </div>
            <button class="copilot-fab" id="copilotFab" title="Open Co-Pilot">🧠</button>
        `;
        document.body.appendChild(div);
        attachEvents();
        applyStyles();
    }

    // ── CSS Injection ──────────────────────────────────────────────────────

    function applyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .copilot-panel {
                position: fixed; bottom: 90px; right: 24px; width: 380px;
                max-height: 560px; background: #1a1a2e; border-radius: 14px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05);
                display: none; flex-direction: column; z-index: 10000;
                font-family: 'Segoe UI', system-ui, sans-serif;
                animation: copilotSlideIn 0.3s ease;
                overflow: hidden;
            }
            .copilot-panel.open { display: flex; }
            @keyframes copilotSlideIn {
                from { opacity: 0; transform: translateY(12px) scale(0.96); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }
            .copilot-header {
                padding: 12px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex; justify-content: space-between; align-items: center;
                cursor: move; user-select: none;
            }
            .copilot-header-left { display: flex; align-items: center; gap: 8px; }
            .copilot-icon { font-size: 18px; }
            .copilot-title { font-weight: 700; font-size: 14px; color: #fff; }
            .copilot-status-dot {
                width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
                display: inline-block; animation: copilotPulse 2s infinite;
            }
            @keyframes copilotPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
            .copilot-header-right { display: flex; align-items: center; gap: 8px; }
            .copilot-context-label {
                font-size: 11px; color: rgba(255,255,255,0.7); font-weight: 500;
                background: rgba(255,255,255,0.1); padding: 2px 10px; border-radius: 10px;
            }
            .copilot-close-btn {
                background: none; border: none; color: rgba(255,255,255,0.6);
                font-size: 16px; cursor: pointer; padding: 2px 6px; border-radius: 4px;
                line-height: 1;
            }
            .copilot-close-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
            .copilot-body {
                flex: 1; overflow-y: auto; padding: 12px 16px;
                background: #1a1a2e; color: #e0e0e0;
                max-height: 340px;
            }
            .copilot-loading {
                text-align: center; color: #94a3b8; padding: 20px;
                font-size: 13px;
            }
            .copilot-content { display: flex; flex-direction: column; gap: 10px; }
            .copilot-card {
                background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px; padding: 10px 12px; font-size: 13px;
            }
            .copilot-card-title { font-weight: 600; font-size: 12px; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
            .copilot-card-desc { color: #94a3b8; font-size: 12px; line-height: 1.4; }
            .copilot-card-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
            .copilot-action-btn {
                padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);
                background: rgba(255,255,255,0.06); color: #cbd5e1; font-size: 11px;
                cursor: pointer; transition: all 0.2s;
            }
            .copilot-action-btn:hover {
                background: rgba(102,126,234,0.2); border-color: #667eea; color: #fff;
            }
            .copilot-quick-actions {
                display: flex; gap: 8px; flex-wrap: wrap;
            }
            .copilot-quick-btn {
                padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(102,126,234,0.3);
                background: rgba(102,126,234,0.08); color: #cbd5e1; font-size: 12px;
                cursor: pointer; transition: all 0.2s; font-weight: 500;
            }
            .copilot-quick-btn:hover {
                background: rgba(102,126,234,0.2); border-color: #667eea; color: #fff;
            }
            .copilot-footer {
                padding: 8px 12px 10px; border-top: 1px solid rgba(255,255,255,0.06);
            }
            .copilot-summary {
                font-size: 11px; color: #64748b; margin-bottom: 6px;
                padding: 0 4px;
            }
            .copilot-input-row {
                display: flex; gap: 6px;
            }
            .copilot-input {
                flex: 1; padding: 8px 12px; border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04);
                color: #e0e0e0; font-size: 12px; outline: none; font-family: inherit;
            }
            .copilot-input:focus { border-color: #667eea; }
            .copilot-input::placeholder { color: #64748b; }
            .copilot-send-btn {
                padding: 8px 14px; border-radius: 8px; border: none;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: #fff; cursor: pointer; font-size: 14px;
            }
            .copilot-send-btn:hover { opacity: 0.9; }
            .copilot-fab {
                position: fixed; bottom: 24px; right: 24px; width: 56px; height: 56px;
                border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2);
                border: none; color: #fff; font-size: 24px; cursor: pointer;
                box-shadow: 0 4px 20px rgba(102,126,234,0.4); z-index: 10000;
                transition: all 0.2s;
            }
            .copilot-fab:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(102,126,234,0.5); }
            .copilot-fab.open { transform: rotate(90deg); }
            ::-webkit-scrollbar { width: 4px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        `;
        document.head.appendChild(style);
    }

    // ── Event Binding ──────────────────────────────────────────────────────

    function attachEvents() {
        document.getElementById('copilotFab').addEventListener('click', togglePanel);
        document.getElementById('copilotCloseBtn').addEventListener('click', togglePanel);
        document.getElementById('copilotSendBtn').addEventListener('click', sendQuestion);
        document.getElementById('copilotInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') sendQuestion();
        });
    }

    function togglePanel() {
        panelState.open = !panelState.open;
        const panel = document.getElementById('copilot-panel');
        const fab = document.getElementById('copilotFab');
        panel.classList.toggle('open', panelState.open);
        fab.classList.toggle('open', panelState.open);
        if (panelState.open) {
            loadPanelContent();
            document.getElementById('copilotInput').focus();
        }
    }

    // ── API Calls ──────────────────────────────────────────────────────────

    async function fetchJSON(url, body) {
        const resp = await fetch(panelState.apiBase + url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
    }

    async function loadPanelContent() {
        const loading = document.getElementById('copilotLoading');
        const content = document.getElementById('copilotContent');
        const summary = document.getElementById('copilotSummary');
        const label = document.getElementById('copilotContextLabel');

        loading.style.display = 'block';
        content.innerHTML = '';

        try {
            const data = await fetchJSON('/panel', {
                form_type: panelState.formType,
                form_data: null,
                entity_id: panelState.entityId,
            });

            label.textContent = data.context_title || panelState.formType;
            summary.textContent = data.summary || '';

            let html = '';

            // Quick actions
            if (data.quick_actions && data.quick_actions.length) {
                html += '<div class="copilot-quick-actions">';
                data.quick_actions.forEach(a => {
                    html += `<button class="copilot-quick-btn" data-action="${a.action}">${a.label}</button>`;
                });
                html += '</div>';
            }

            // Suggestions
            if (data.suggestions && data.suggestions.length) {
                data.suggestions.forEach(s => {
                    const icon = s.type === 'error' || s.type === 'red' ? '🔴' :
                                s.type === 'warning' || s.type === 'yellow' ? '🟡' :
                                s.type === 'success' || s.type === 'green' ? '🟢' : '💡';
                    html += `<div class="copilot-card">
                        <div class="copilot-card-title">${icon} ${s.title}</div>
                        <div class="copilot-card-desc">${s.description}</div>
                        ${s.action ? `<div class="copilot-card-actions"><button class="copilot-action-btn" onclick="alert('Action: ${s.action}')">${s.action}</button></div>` : ''}
                    </div>`;
                });
            }

            if (!html) html = '<div class="copilot-card"><div class="copilot-card-title">💡 No suggestions</div><div class="copilot-card-desc">Fill in the form to get AI-powered suggestions.</div></div>';
            content.innerHTML = html;

            // Bind quick action buttons
            content.querySelectorAll('.copilot-quick-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    handleQuickAction(this.dataset.action);
                });
            });

            loading.style.display = 'none';
        } catch (err) {
            loading.style.display = 'none';
            content.innerHTML = `<div class="copilot-card"><div class="copilot-card-title">⚠️ Error</div><div class="copilot-card-desc">${err.message}</div></div>`;
        }
    }

    function handleQuickAction(action) {
        switch (action) {
            case 'suggest_budget':
            case 'suggest_vendors':
            case 'auto_generate':
            case 'check_duplicates':
            case 'optimize_supplier':
            case 'auto_match':
            case 'view_patterns':
            case 'view_pnl':
            case 'view_cashflow':
            case 'run_analysis':
            case 'view_notifications':
                showToast(`Co-Pilot: ${action.replace(/_/g, ' ')}`, 'info');
                break;
            default:
                showToast(`Action: ${action}`, 'info');
        }
    }

    async function sendQuestion() {
        const input = document.getElementById('copilotInput');
        const text = input.value.trim();
        if (!text) return;
        input.value = '';

        const content = document.getElementById('copilotContent');
        content.innerHTML += `<div class="copilot-card" style="background:rgba(102,126,234,0.1);border-color:rgba(102,126,234,0.2);">
            <div class="copilot-card-title">👤 You</div>
            <div class="copilot-card-desc">${text}</div>
        </div>`;

        try {
            const data = await fetchJSON('/ask', {
                question: text,
                context: { form_type: panelState.formType },
            });
            content.innerHTML += `<div class="copilot-card">
                <div class="copilot-card-title">🧠 Co-Pilot <span style="font-size:10px;color:#64748b;">(${data.confidence.label})</span></div>
                <div class="copilot-card-desc">${data.answer}</div>
            </div>`;
        } catch (err) {
            content.innerHTML += `<div class="copilot-card"><div class="copilot-card-title">⚠️ Error</div><div class="copilot-card-desc">${err.message}</div></div>`;
        }

        content.scrollTop = content.scrollHeight;
    }

    function showToast(msg, type) {
        const t = document.createElement('div');
        t.style.cssText = 'position:fixed;bottom:100px;right:24px;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:500;z-index:10001;background:' +
            (type === 'info' ? 'rgba(102,126,234,0.9)' : 'rgba(239,68,68,0.9)') +
            ';color:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.3);animation:copilotSlideIn 0.2s ease;';
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(() => t.remove(), 300); }, 3000);
    }

    // ── Public API ─────────────────────────────────────────────────────────

    window.initCoPilotPanel = function(formType, entityId) {
        panelState.formType = formType || 'dashboard';
        panelState.entityId = entityId || null;
        injectPanel();
        if (panelState.open) loadPanelContent();
    };

    window.openCoPilot = function() {
        if (!panelState.open) togglePanel();
    };

    window.closeCoPilot = function() {
        if (panelState.open) togglePanel();
    };

    window.getCoPilotState = function() {
        return { ...panelState };
    };

    // Auto-init if data attributes present on <body>
    document.addEventListener('DOMContentLoaded', function() {
        const body = document.body;
        const formType = body.dataset.formType || 'dashboard';
        const entityId = body.dataset.entityId || null;
        initCoPilotPanel(formType, entityId);
    });

})();
