"""
P5 Integration Snippets — for reference/copy-paste only.

Step 1 — Register in EventCore main.py
----------------------------------------
Add to imports (near line 15):
    from backend.app.routers import prescriptions_htmx

Add near other include_router calls (after line 83):
    app.include_router(prescriptions_htmx.router)


Step 2 — Add to job detail template (templates/jobs/detail.html)
-----------------------------------------------------------------
Paste inside the job detail view, where you want prescriptions to appear:

    <div style="margin-top:20px;">
        <h3 style="font-size:16px;color:#1f2937;margin-bottom:10px;">
            Doctor's Prescriptions
        </h3>
        <div id="prescriptions-container"
             hx-get="/api/v1/prescriptions/htmx/job/{{ job.id }}"
             hx-trigger="load"
             hx-swap="innerHTML">
            <div style="padding:20px;text-align:center;color:#9ca3af;">
                Loading prescriptions...
            </div>
        </div>
    </div>


Step 3 — Add badge to job listing rows
----------------------------------------
Inside each job row in the list template:

    <span hx-get="/api/v1/prescriptions/htmx/badge/{{ job.id }}"
          hx-trigger="load"
          hx-swap="outerHTML"></span>
"""
