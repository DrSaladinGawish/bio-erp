# 🏢 Incentive House ERP - Production Frontend

## Overview

Production-ready ERP frontend interface for **Incentive House** with full transaction management, company branding, and comprehensive CRUD operations.

## ✨ Features

### 🎨 Corporate Branding
- **Company Logo**: SVG logo embedded in header (replace with your own)
- **Header**: Company name, tagline, user info, notifications, settings
- **Footer**: Copyright, version info, support links, system status indicator
- **Color Scheme**: Professional blue/gold theme matching corporate identity

### 📝 Transaction Management
- **Journal Voucher Entry**: Full form with header and line items
- **Line Items Table**: Dynamic add/remove with account codes, descriptions, debit/credit
- **Auto-Balance Check**: Real-time validation of debit/credit totals
- **Status Tracking**: Draft → Posted → Void workflow

### 🔘 Action Buttons
| Button | Action | Description |
|--------|--------|-------------|
| **Post** | `btn-post` | Finalize and post transaction (irreversible) |
| **Save Draft** | `btn-save` | Save as draft for later editing |
| **New** | `btn-new` | Reset form for new entry |
| **Print** | `btn-print` | Print-friendly layout with company header |
| **Void** | `btn-void` | Cancel/void existing transaction |

### 📊 Dashboard
- Statistics cards (Total, Posted, Draft, Void counts)
- Quick action shortcuts
- Recent activity feed
- System status monitoring

### 🔍 Transaction History
- Search by reference, description, type
- Filter by status and date range
- Sortable data table
- View/Edit/Void actions per row

## 📁 File Structure

```
erp-frontend/
├── index.html              # Dashboard page
├── transactions.html       # Transaction entry & listing
├── css/
│   └── erp-theme.css      # Complete theme & branding
├── js/
│   ├── erp-core.js         # API client, UI utilities, common functions
│   └── transactions.js     # Transaction-specific logic
└── images/
    └── (place your logo here)
```

## 🔧 FastAPI Integration

### 1. Mount Static Files

Add to your `main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Incentive House ERP")

# Mount static files
frontend_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Serve index.html at root
@app.get("/", response_class=FileResponse)
async def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Catch-all for SPA routing
@app.get("/{catchall:path}", response_class=FileResponse)
async def read_spa(request):
    file_path = os.path.join(frontend_path, request.path_params["catchall"])
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_path, "index.html"))
```

### 2. CORS Configuration (if needed)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. API Endpoints Required

The frontend expects these endpoints:

```
GET    /api/v1/transactions          # List all transactions
POST   /api/v1/transactions          # Create new transaction
PUT    /api/v1/transactions/{id}    # Update transaction
PATCH  /api/v1/transactions/{id}/void # Void transaction
```

### 4. Directory Placement

Copy the `erp-frontend` contents to your FastAPI static directory:

```bash
# Windows
copy /Y erp-frontend\* D:\ERP System\BIO_ERP\app\static\

# Or manually copy:
# - index.html → static/index.html
# - css/ → static/css/
# - js/ → static/js/
```

## 🎨 Customization

### Replace Logo
1. Create your logo file (PNG/SVG recommended, 48x48px)
2. Save to `images/logo.png`
3. Update `index.html` and `transactions.html`:
   ```html
   <div class="company-logo">
       <img src="images/logo.png" alt="Incentive House">
   </div>
   ```

### Change Colors
Edit `css/erp-theme.css` root variables:
```css
:root {
    --primary: #1a3a5c;      /* Your primary color */
    --accent: #c9a227;       /* Your accent color */
}
```

### Update Company Info
Edit `js/erp-core.js`:
```javascript
const ERP_CONFIG = {
    COMPANY_NAME: 'Your Company',
    COMPANY_TAGLINE: 'Your Tagline',
    // ...
};
```

## 🚀 Production Deployment

### Docker (Multi-stage)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY erp-frontend/ ./app/static/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```env
API_BASE_URL=http://localhost:8000/api/v1
COMPANY_NAME=Incentive House
DEBUG=false
```

## 📱 Responsive Design

- **Desktop**: Full sidebar + main content layout
- **Tablet**: Collapsible sidebar
- **Mobile**: Hidden sidebar with toggle button

## 🖨 Print Support

Print-friendly styles included:
- Hides navigation, buttons, filters
- Shows company header with logo
- Clean transaction form layout
- Use browser Print or `Ctrl+P`

## 🔒 Security Notes

- All API calls use standard fetch with JSON
- Implement authentication middleware on backend
- Use HTTPS in production
- Validate all inputs server-side

## 📞 Support

For issues or questions:
- Check browser console for errors
- Verify API endpoints are accessible
- Ensure CORS is properly configured
- Review FastAPI logs

---

**Incentive House ERP** v2.0.0 | Production Ready
