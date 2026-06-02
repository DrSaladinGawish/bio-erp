let currentSuggestionId = null;
let lastProtocolResult = null;

document.addEventListener('DOMContentLoaded', function () {
    loadDocuments();
    loadSuggestions();
    loadPatterns();

    document.getElementById('uploadForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        const input = document.getElementById('fileInput');
        if (!input.files.length) return;

        const progress = document.getElementById('uploadProgress');
        progress.classList.remove('d-none');

        const formData = new FormData();
        formData.append('file', input.files[0]);

        try {
            const resp = await fetch('/api/v1/ai-ingest/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${getToken()}` },
                body: formData,
            });
            const data = await resp.json();
            if (resp.ok) {
                await analyzeDocument(data.id);
            } else {
                alert('Upload failed: ' + (data.detail || 'Unknown error'));
            }
        } catch (err) {
            alert('Upload error: ' + err.message);
        } finally {
            progress.classList.add('d-none');
            input.value = '';
        }
    });
});

function getToken() {
    return localStorage.getItem('access_token') || '';
}

async function loadDocuments() {
    try {
        const resp = await fetch('/api/v1/ai-ingest/documents?limit=20', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!resp.ok) return;
        const docs = await resp.json();
        const tbody = document.getElementById('documentsBody');
        if (!docs.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center">No documents uploaded yet</td></tr>';
            return;
        }
        tbody.innerHTML = docs.map(d => `
            <tr>
                <td>${d.id}</td>
                <td>${d.filename}</td>
                <td><span class="badge bg-${statusBadge(d.status)}">${d.status}</span></td>
                <td>${formatBytes(d.file_size_bytes)}</td>
                <td>${d.created_at ? new Date(d.created_at).toLocaleString() : '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="viewStatus(${d.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-primary" onclick="analyzeDocument(${d.id})">
                        <i class="bi bi-arrow-repeat"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('loadDocuments error:', e);
    }
}

async function loadSuggestions() {
    try {
        const resp = await fetch('/api/v1/ai-ingest/suggestions?limit=20', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!resp.ok) return;
        const suggestions = await resp.json();
        const tbody = document.getElementById('suggestionsBody');
        if (!suggestions.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-muted text-center">No suggestions yet</td></tr>';
            return;
        }
        tbody.innerHTML = suggestions.map(s => `
            <tr>
                <td>${s.id}</td>
                <td>${s.title || '-'}</td>
                <td>${s.transaction_type}</td>
                <td>${s.total_debit.toFixed(2)}</td>
                <td>${(s.confidence_score * 100).toFixed(0)}%</td>
                <td><span class="badge bg-${statusBadge(s.status)}">${s.status}</span></td>
                <td>
                    <span id="orBadge-${s.id}"></span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary" onclick="showSuggestion(${s.id})">
                        <i class="bi bi-search"></i>
                    </button>
                    ${s.status === 'approved' ? `
                        <button class="btn btn-sm btn-outline-success" onclick="postSuggestion(${s.id})">
                            <i class="bi bi-check-circle"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('loadSuggestions error:', e);
    }
}

async function loadPatterns() {
    try {
        const resp = await fetch('/api/v1/ai-ingest/patterns?limit=20', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!resp.ok) return;
        const patterns = await resp.json();
        const tbody = document.getElementById('patternsBody');
        if (!patterns.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No patterns logged yet</td></tr>';
            return;
        }
        tbody.innerHTML = patterns.map(p => `
            <tr>
                <td>${p.id}</td>
                <td>${p.pattern_type}</td>
                <td><code>${p.pattern_key}</code></td>
                <td>${(p.confidence * 100).toFixed(0)}%</td>
                <td>${p.source}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('loadPatterns error:', e);
    }
}

async function analyzeDocument(docId) {
    const formData = new FormData();
    formData.append('full_protocol', 'true');

    try {
        const resp = await fetch(`/api/v1/ai-ingest/${docId}/analyze`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData,
        });
        const data = await resp.json();
        if (resp.ok) {
            lastProtocolResult = data.data || data;
            updateProtocolBadges(lastProtocolResult);
            loadDocuments();
            loadSuggestions();
            loadPatterns();
        } else {
            const detail = data.detail || {};
            if (detail.protocol === 'AI Agent') {
                alert(`Protocol violation [${detail.violation_type}]: ${detail.message}`);
            } else {
                alert('Analysis failed: ' + (data.detail || 'Unknown error'));
            }
        }
    } catch (err) {
        alert('Analysis error: ' + err.message);
    }
}

function updateProtocolBadges(protocolResult) {
    if (!protocolResult || !protocolResult.gate_1_agent) return;

    const g1 = protocolResult.gate_1_agent;
    const g2 = protocolResult.gate_2_or;
    const badgesDiv = document.getElementById('protocolBadges');

    let badges = '';
    if (g1.status === 'passed') {
        badges += '<span class="badge bg-success"><i class="bi bi-shield-check"></i> Agent: PASS</span>';
    } else if (g1.status === 'blocked') {
        badges += `<span class="badge bg-danger" title="${g1.error}"><i class="bi bi-shield-x"></i> Agent: BLOCKED</span>`;
    } else {
        badges += `<span class="badge bg-secondary"><i class="bi bi-shield"></i> Agent: ${g1.status}</span>`;
    }

    if (g2 && g2.status === 'scored') {
        const score = (g2.overall_score * 100).toFixed(1);
        const recClass = g2.recommendation === 'approve' ? 'success' : g2.recommendation === 'amend' ? 'warning text-dark' : g2.recommendation === 'reject' ? 'danger' : 'secondary';
        badges += `<span class="badge bg-info"><i class="bi bi-calculator"></i> OR: ${score}%</span>`;
        badges += `<span class="badge bg-${recClass}"><i class="bi bi-check-circle"></i> ${g2.recommendation}</span>`;
        if (g2.confidence_interval) {
            badges += `<span class="badge bg-secondary">CI: ${(g2.confidence_interval[0]*100).toFixed(0)}%-${(g2.confidence_interval[1]*100).toFixed(0)}%</span>`;
        }
    }

    if (protocolResult.final_status === 'awaiting_user_decision') {
        badges += '<span class="badge bg-warning text-dark"><i class="bi bi-bandaid"></i> Surgery: READY</span>';
    }

    badgesDiv.innerHTML = badges;
}

async function showSuggestion(id) {
    currentSuggestionId = id;
    try {
        const resp = await fetch(`/api/v1/ai-ingest/suggestions/${id}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const s = await resp.json();
        const modalBody = document.getElementById('suggestionModalBody');
        modalBody.innerHTML = `
            <h6>${s.title || 'Untitled'}</h6>
            <p>${s.description || ''}</p>
            <table class="table table-sm">
                <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
                <tbody>
                    ${(s.journal_lines || []).map(l => `
                        <tr>
                            <td>${l.coa_account_name || l.coa_account_id || '?'}</td>
                            <td>${l.debit.toFixed(2)}</td>
                            <td>${l.credit.toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </tbody>
                <tfoot>
                    <tr class="fw-bold">
                        <td>Total</td>
                        <td>${s.total_debit.toFixed(2)}</td>
                        <td>${s.total_credit.toFixed(2)}</td>
                    </tr>
                </tfoot>
            </table>
            <p>Confidence: ${(s.confidence_score * 100).toFixed(1)}% | Status: <strong>${s.status}</strong></p>
            <hr>
            <button class="btn btn-outline-info btn-sm" onclick="showORDetails()">
                <i class="bi bi-bar-chart-line"></i> View OR Score Breakdown
            </button>
        `;

        if (lastProtocolResult && lastProtocolResult.gate_2_or) {
            updateProtocolBadges(lastProtocolResult);
        }

        const modal = new bootstrap.Modal(document.getElementById('suggestionModal'));
        modal.show();
    } catch (e) {
        console.error('showSuggestion error:', e);
    }
}

function showORDetails() {
    if (!lastProtocolResult || !lastProtocolResult.gate_2_or) {
        alert('No OR evaluation data available. Run analysis first.');
        return;
    }
    const orData = lastProtocolResult.gate_2_or;
    const body = document.getElementById('orScoreBody');
    body.innerHTML = `
        <div class="mb-3">
            <h6>Overall Score: <strong class="text-${orData.recommendation === 'approve' ? 'success' : orData.recommendation === 'amend' ? 'warning' : orData.recommendation === 'reject' ? 'danger' : 'secondary'}">
                ${(orData.overall_score * 100).toFixed(1)}%
            </strong></h6>
            <p>Recommendation: <strong>${orData.recommendation.toUpperCase()}</strong></p>
            <p>Confidence Interval: ${(orData.confidence_interval[0] * 100).toFixed(1)}% - ${(orData.confidence_interval[1] * 100).toFixed(1)}%</p>
        </div>
        <table class="table table-sm">
            <thead><tr><th>Criterion</th><th>Score</th></tr></thead>
            <tbody>
                ${Object.entries(orData.criteria_breakdown || {}).map(([k, v]) => `
                    <tr>
                        <td>${k.replace(/_/g, ' ')}</td>
                        <td>${(v * 100).toFixed(1)}%</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div class="mt-2">
            <h6>Reasoning</h6>
            <ul class="small text-muted">
                ${(orData.reasoning || []).map(r => `<li>${r}</li>`).join('')}
            </ul>
        </div>
    `;
    const modal = new bootstrap.Modal(document.getElementById('orScoreModal'));
    modal.show();
}

async function reviewSuggestion(action) {
    if (!currentSuggestionId) return;
    const notes = prompt(`Enter ${action} notes (optional):`);
    try {
        if (action === 'amend') {
            const resp = await fetch(`/api/v1/ai-ingest/suggestions/${currentSuggestionId}/amend-and-post`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action, notes }),
            });
            const data = await resp.json();
            if (resp.ok) {
                alert('Amended & posted via Surgery Protocol!');
            } else {
                alert('Amend failed: ' + (data.detail || 'Unknown error'));
            }
        } else {
            const resp = await fetch(`/api/v1/ai-ingest/suggestions/${currentSuggestionId}/review`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action, notes }),
            });
            const data = await resp.json();
            if (resp.ok && action === 'approve') {
                await postSuggestion(currentSuggestionId);
            } else if (resp.ok) {
                alert(`Suggestion ${action}d`);
            } else {
                alert('Review failed: ' + (data.detail || 'Unknown error'));
            }
        }
        loadSuggestions();
        const modal = bootstrap.Modal.getInstance(document.getElementById('suggestionModal'));
        if (modal) modal.hide();
    } catch (e) {
        alert('Review error: ' + e.message);
    }
}

async function postSuggestion(id) {
    if (!confirm('Post this journal entry via Surgery Protocol?')) return;
    try {
        const resp = await fetch(`/api/v1/ai-ingest/suggestions/${id}/post`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
        });
        const data = await resp.json();
        if (resp.ok) {
            alert('Posted via Surgery Protocol! ' + (data.message || ''));
            loadSuggestions();
            loadDocuments();
        } else {
            alert('Post failed: ' + (data.detail || data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Post error: ' + e.message);
    }
}

async function viewStatus(docId) {
    try {
        const resp = await fetch(`/api/v1/ai-ingest/${docId}/status`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const s = await resp.json();
        alert(`Document #${s.document_id}: ${s.filename}\nUpload: ${s.upload_status}\nAnalysis: ${s.analysis_status || '-'}\nSuggestion: ${s.suggestion_status || '-'}\nJV ID: ${s.posted_jv_id || '-'}`);
    } catch (e) {
        console.error('viewStatus error:', e);
    }
}

function statusBadge(status) {
    const map = {
        'uploaded': 'secondary',
        'analyzed': 'info',
        'posted': 'success',
        'draft': 'secondary',
        'pending_review': 'warning',
        'approved': 'success',
        'amended': 'info',
        'rejected': 'danger',
        'completed': 'success',
        'failed': 'danger',
    };
    return map[status] || 'secondary';
}

function formatBytes(bytes) {
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}
