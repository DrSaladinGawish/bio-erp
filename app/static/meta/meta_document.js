(function() {
  'use strict';

  class MetaDocument {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.docKey = config.doc_key || container.id || 'docs';
      this.init();
    }

    init() {
      this.addDropZone();
      this.addPreviewOnHover();
      this.loadVersionHistory();
      this.startOCRPolling();
    }

    addDropZone() {
      const zone = document.createElement('div');
      zone.className = 'meta-drop-zone';
      zone.style.cssText = 'border:2px dashed #cbd5e1;border-radius:8px;padding:32px;text-align:center;margin-bottom:16px;transition:all 0.3s;cursor:pointer;';
      zone.innerHTML = '<div style="font-size:2rem;margin-bottom:8px;">\ud83d\udcc1</div><div>Drag & drop files here or click to browse</div>';
      zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.style.borderColor = '#06b6d4';
        zone.style.background = 'rgba(6,182,212,0.05)';
      });
      zone.addEventListener('dragleave', () => {
        zone.style.borderColor = '#cbd5e1';
        zone.style.background = '';
      });
      zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.style.borderColor = '#cbd5e1';
        zone.style.background = '';
        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
      });
      zone.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.addEventListener('change', () => {
          if (input.files) this.uploadFiles(Array.from(input.files));
        });
        input.click();
      });
      this.el.insertBefore(zone, this.el.firstChild);
      this._dropZone = zone;
    }

    uploadFiles(files) {
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      this._dropZone.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Uploading ' + files.length + ' file(s)...';
      fetch('/api/meta/documents/' + this.docKey + '/upload', {
        method: 'POST',
        body: formData
      }).then(r => {
        if (r.ok) {
          this._dropZone.innerHTML = '<div style="font-size:2rem;margin-bottom:8px;">\u2705</div><div>' + files.length + ' file(s) uploaded successfully</div>';
          this.loadVersionHistory();
        } else {
          this._dropZone.innerHTML = '<div style="font-size:2rem;margin-bottom:8px;">\u274c</div><div>Upload failed</div>';
        }
        setTimeout(() => {
          this._dropZone.innerHTML = '<div style="font-size:2rem;margin-bottom:8px;">\ud83d\udcc1</div><div>Drag & drop files here or click to browse</div>';
        }, 3000);
      }).catch(() => {
        this._dropZone.innerHTML = '<div style="font-size:2rem;margin-bottom:8px;">\u274c</div><div>Upload error</div>';
      });
    }

    addPreviewOnHover() {
      this.el.querySelectorAll('[data-file-url]').forEach(el => {
        el.addEventListener('mouseenter', () => {
          const url = el.dataset.fileUrl;
          const type = el.dataset.fileType || '';
          let preview = this.el.querySelector('.meta-file-preview');
          if (!preview) {
            preview = document.createElement('div');
            preview.className = 'meta-file-preview';
            preview.style.cssText = 'position:absolute;z-index:1000;background:#fff;border:1px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);padding:8px;max-width:300px;';
            document.body.appendChild(preview);
          }
          if (type.startsWith('image/')) {
            preview.innerHTML = '<img src="' + url + '" style="max-width:280px;max-height:200px;border-radius:4px;">';
          } else {
            preview.innerHTML = '<div style="text-align:center;padding:16px;"><div style="font-size:3rem;">\ud83d\udcc4</div><div>' + (type || 'File') + '</div></div>';
          }
          const rect = el.getBoundingClientRect();
          preview.style.top = (rect.top - 10) + 'px';
          preview.style.left = (rect.right + 10) + 'px';
          preview.dataset.active = 'true';
        });
        el.addEventListener('mouseleave', () => {
          const preview = document.querySelector('.meta-file-preview[data-active="true"]');
          if (preview) setTimeout(() => { if (preview.dataset.active) preview.remove(); }, 300);
        });
      });
    }

    loadVersionHistory() {
      const container = this.el.querySelector('[data-version-history]');
      if (!container) return;
      fetch('/api/meta/documents/' + this.docKey + '/versions')
        .then(r => r.json())
        .then(data => {
          const versions = Array.isArray(data) ? data : (data.versions || []);
          if (versions.length === 0) {
            container.innerHTML = '<p class="text-muted">No version history</p>';
            return;
          }
          container.innerHTML = '<h6 class="mb-2">Version History</h6>' +
            versions.map(v => '<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f1f5f9;">' +
              '<span><strong>v' + v.version + '</strong> — ' + (v.description || '') + '</span>' +
              '<span class="text-muted" style="font-size:0.8rem;">' + (v.created_at || '') + '</span></div>'
            ).join('');
        })
        .catch(() => {});
    }

    startOCRPolling() {
      this.el.querySelectorAll('[data-ocr-status]').forEach(el => {
        const statusUrl = el.dataset.ocrStatus;
        const poll = () => {
          fetch(statusUrl)
            .then(r => r.json())
            .then(data => {
              el.textContent = data.status || 'unknown';
              el.className = 'badge ' + (
                data.status === 'completed' ? 'bg-success' :
                data.status === 'processing' ? 'bg-warning' :
                data.status === 'error' ? 'bg-danger' : 'bg-secondary'
              );
              if (data.status === 'processing') setTimeout(poll, 2000);
            })
            .catch(() => { el.textContent = 'error'; el.className = 'badge bg-danger'; });
        };
        poll();
      });
    }
  }

  function initDocuments() {
    document.querySelectorAll('[data-meta-documents]').forEach(el => {
      if (el.dataset.metaDocumentsInit) return;
      const url = el.dataset.metaDocuments;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaDocument(el, config);
          el.dataset.metaDocumentsInit = 'true';
        }).catch(e => console.warn('[MetaDocument] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDocuments);
  else initDocuments();
  window.MetaDocument = MetaDocument;
})();
