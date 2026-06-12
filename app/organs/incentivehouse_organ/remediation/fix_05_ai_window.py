#!/usr/bin/env python3
"""FIX 5 (P0): Inject AI smart window into base.html"""

import sys
import pathlib

BASE = pathlib.Path(r"D:\ERP System\BIO_ERP")
IH = BASE / "app" / "organs" / "incentivehouse_organ"
DRY = "--dry-run" in sys.argv
p_ih = IH / "templates" / "base.html"
p_bio = BASE / "app" / "templates" / "base.html"

print("FIX 5: Inject AI smart window (id=ai-smart-window) into base.html")

AI_HTML = """
<!-- AUTO-INJECTED by audit fix 7.1 - AI smart window -->
<div id="ai-smart-window" class="ai-smart-window" data-audit-fix="7.1"
     style="position:fixed;bottom:90px;right:20px;width:360px;max-height:480px;
            background:#fff;border:2px solid #D4A017;border-radius:12px;
            box-shadow:0 8px 32px rgba(0,0,0,0.2);display:none;flex-direction:column;z-index:9999;">
  <div style="background:#D4A017;color:#fff;padding:12px;border-radius:10px 10px 0 0;font-weight:600;display:flex;justify-content:space-between;">
    <span>AI Smart Assistant</span>
    <button onclick="document.getElementById('ai-smart-window').style.display='none'"
            style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;">&times;</button>
  </div>
  <div id="ai-chat-messages" style="flex:1;overflow-y:auto;padding:12px;font-size:13px;"></div>
  <div style="display:flex;border-top:1px solid #eee;padding:8px;">
    <input id="ai-chat-input" type="text" placeholder="Ask AI..."
           style="flex:1;border:1px solid #ddd;border-radius:6px;padding:6px 10px;font-size:13px;">
    <button onclick="window.__aiSend&&window.__aiSend()"
            style="background:#D4A017;color:#fff;border:none;border-radius:6px;padding:6px 12px;margin-left:6px;cursor:pointer;">Send</button>
  </div>
</div>
<button id="ai-smart-toggle" data-audit-fix="7.1"
        onclick="var w=document.getElementById('ai-smart-window');w.style.display=w.style.display==='none'?'flex':'none'"
        style="position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;
               background:#D4A017;color:#fff;border:none;font-size:20px;cursor:pointer;z-index:9998;
               box-shadow:0 4px 16px rgba(0,0,0,0.3);">AI</button>
<script>
document.addEventListener('focusin',function(e){
  if(e.target&&(e.target.name||e.target.id))window.__aiLastField=e.target.name||e.target.id;
});
window.__aiSend=function(){
  var i=document.getElementById('ai-chat-input'),b=document.getElementById('ai-chat-messages');
  if(!i.value.trim())return;
  b.innerHTML+='<div style="text-align:right;margin:6px 0;color:#1E90FF;">'+i.value+'</div>';
  var c=window.__aiLastField||'general';
  b.innerHTML+='<div style="text-align:left;margin:6px 0;color:#333;">AI: working on <b>'+c+'</b></div>';
  i.value='';b.scrollTop=b.scrollHeight;
};
</script>
<!-- END AI smart window -->
"""

target = p_ih if p_ih.exists() else p_bio
if not target.exists():
    print("  [SKIP] base.html not found in IH or BIO templates")
    sys.exit(0)
src = target.read_text(encoding="utf-8", errors="ignore")
if "ai-smart-window" in src:
    print(f"  [OK]  ai-smart-window already present in {target.name}")
    sys.exit(0)
if "</body>" in src.lower():
    idx = src.lower().rfind("</body>")
    new_src = src[:idx] + AI_HTML + src[idx:]
else:
    new_src = src + AI_HTML
if DRY:
    print(f"  [DRY] would inject into {target.name}")
else:
    target.write_text(new_src, encoding="utf-8")
    print(f"  [FIX] injected AI smart window into {target.name}")
print("  Done.")
