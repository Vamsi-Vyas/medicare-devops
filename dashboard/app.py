import json
import os
import secrets
import shutil
import subprocess
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, Response, render_template_string

app = Flask(__name__)
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
KUBECONFIG = os.environ.get("KUBECONFIG", "/home/ec2-user/.kube/config")
NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")
SERVICE = "medicare-service"
PROJECT_CANDIDATES = [
    Path("/home/ec2-user/medicare-devops"),
    Path("/var/lib/jenkins/workspace/medicare-ci-cd"),
]

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediCare DevOps Dashboard</title><style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#121d30;--line:#263752;--text:#e8eef8;--muted:#9aabc4;--ok:#6ee7b7;--warn:#fbbf24;--bad:#f87171}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#0b1220,#14243b);color:var(--text);font:15px system-ui,Segoe UI,Arial}
header{padding:26px max(20px,calc((100vw - 1100px)/2));border-bottom:1px solid var(--line);background:#0b1220cc}h1{margin:0;font-size:clamp(24px,4vw,34px)}header p{margin:7px 0 0;color:var(--muted)}
main{max-width:1100px;margin:24px auto;padding:0 18px 40px}.toolbar,.actions{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
button{border:1px solid #3b526f;background:#1a2a42;color:var(--text);padding:10px 14px;border-radius:9px;cursor:pointer;font-weight:650}button:hover{border-color:var(--ok)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:18px;box-shadow:0 10px 35px #0002}h2{font-size:18px;margin:0 0 14px}.muted,.small{color:var(--muted)}.small{font-size:12px}
.row{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid #26375280}.status{font-weight:700}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#09111e;border:1px solid var(--line);padding:12px;border-radius:9px;max-height:330px;overflow:auto;font-size:12px}.wide{grid-column:1/-1}
</style></head><body><header><h1>🩺 MediCare DevOps Control Center</h1><p>Live status · Jenkins · Docker · Kubernetes · Trivy</p></header>
<main><div class="toolbar"><button onclick="refreshAll()">↻ Refresh status</button><button onclick="loadSecurity()">Run Trivy configuration scan</button><a href="http://98.93.100.162:8080" target="_blank" rel="noreferrer" style="color:#9bd4ff;align-self:center">Open Jenkins ↗</a></div>
<p id="notice" class="muted">Loading live checks…</p><div class="grid">
<section class="card"><h2>1 · Platform health</h2><div id="services">Loading…</div></section>
<section class="card"><h2>2 · Kubernetes</h2><div id="kube">Loading…</div></section>
<section class="card"><h2>3 · Blue-Green traffic</h2><div id="bg">Loading…</div><div class="actions"><button onclick="switchVersion('blue')">Route to Blue</button><button onclick="switchVersion('green')">Route to Green</button></div><p class="small">Switches the Service selector after checking target readiness; it does not build or publish an image.</p></section>
<section class="card wide"><h2>4 · Trivy security scan</h2><p class="muted">Displays actual scanner output. Errors and missing source files are not treated as clean results.</p><div id="security">Select “Run Trivy configuration scan”.</div></section>
</div></main><script>
async function api(url,options={}){const r=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});const d=await r.json().catch(()=>({error:'Response was not JSON'}));if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
function row(k,v,cls=''){return '<div class="row"><span>'+safe(k)+'</span><span class="status '+cls+'">'+safe(v)+'</span></div>'}
function safe(s){return String(s??'—').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function refreshAll(){document.querySelector('#notice').textContent='Refreshing live status…';try{const d=await api('/api/health');
document.querySelector('#services').innerHTML=Object.entries(d.services||{}).map(([k,v])=>row(k,v,v==='active'?'ok':'bad')).join('');
document.querySelector('#kube').innerHTML=row('Node status',d.node_status,d.node_status==='Ready'?'ok':'bad')+row('Deployments',d.deployments_ready)+row('Pods',d.pods_summary)+row('NodePort test',d.local_http,String(d.local_http).includes('200')?'ok':'bad');
document.querySelector('#bg').innerHTML=row('Active selector',d.selector)+row('Service endpoints',d.endpoints)+row('App version',d.app_version);
document.querySelector('#notice').textContent='Last refreshed: '+new Date().toLocaleTimeString()+' · live command results'}catch(e){document.querySelector('#notice').textContent='Health check failed: '+e.message}}
async function switchVersion(v){if(!confirm('Switch MediCare traffic to '+v.toUpperCase()+'?'))return;document.querySelector('#notice').textContent='Switching traffic…';try{const d=await api('/api/switch/'+v,{method:'POST'});document.querySelector('#notice').textContent=d.message;await refreshAll()}catch(e){document.querySelector('#notice').textContent='Switch failed: '+e.message}}
async function loadSecurity(){document.querySelector('#security').textContent='Running Trivy…';try{const d=await api('/api/trivy',{method:'POST'});const s=d.summary||{};document.querySelector('#security').innerHTML=row('Scan target',d.target)+row('Scanner',d.scanner)+row('Result',d.status,d.status==='completed'?'ok':'warn')+row('HIGH findings',s.HIGH??'not reported')+row('CRITICAL findings',s.CRITICAL??'not reported')+'<pre>'+safe(d.output||d.error||'No output returned')+'</pre>'}catch(e){document.querySelector('#security').innerHTML='<p class="bad">Scan error: '+safe(e.message)+'</p>'}}
refreshAll();
</script></body></html>"""

def cmd(args, timeout=15):
    env = os.environ.copy()
    env["KUBECONFIG"] = KUBECONFIG
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "Command not found: " + args[0]
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"

def result(rc, out, err):
    return out if rc == 0 else (err or out or "command failed")

def auth_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        auth = request.authorization
        if not PASSWORD:
            return jsonify(error="DASHBOARD_PASSWORD is not configured"), 503
        if not auth or auth.username != "admin" or not secrets.compare_digest(auth.password or "", PASSWORD):
            return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="MediCare DevOps Dashboard"'})
        return fn(*args, **kwargs)
    return inner

@app.get("/")
@auth_required
def home():
    return render_template_string(PAGE)

@app.get("/api/health")
@auth_required
def health():
    services = {name: result(*cmd(["systemctl", "is-active", name])) for name in ("jenkins", "docker", "k3s")}
    rc, raw, err = cmd(["kubectl", "get", "nodes", "-o", "json"])
    node_status = "unknown"
    try:
        nodes = json.loads(raw).get("items", [])
        node_status = ", ".join(next(("Ready" if c.get("status") == "True" else "NotReady" for c in n.get("status", {}).get("conditions", []) if c.get("type") == "Ready"), "NotReady") for n in nodes) or "no nodes"
    except Exception: node_status = result(rc, raw, err)
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "get", "deployments", "-o", "json"])
    try:
        deployments = json.loads(raw).get("items", [])
        dep_summary = ", ".join(f'{d["metadata"]["name"]}: {d.get("status",{}).get("readyReplicas",0)}/{d.get("spec",{}).get("replicas",1)} ready' for d in deployments) or "no deployments"
    except Exception: dep_summary = result(rc, raw, err)
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "get", "pods", "-o", "json"])
    try:
        pods = json.loads(raw).get("items", [])
        pod_summary = ", ".join(f'{p["metadata"]["name"]}: {sum(1 for c in p.get("status",{}).get("containerStatuses",[]) if c.get("ready"))}/{len(p.get("status",{}).get("containerStatuses",[]))} ready' for p in pods[:8]) or "no pods"
    except Exception: pod_summary = result(rc, raw, err)
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "get", "service", SERVICE, "-o", "json"])
    try: selector = json.dumps(json.loads(raw).get("spec", {}).get("selector", {}))
    except Exception: selector = result(rc, raw, err)
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "get", "endpoints", SERVICE, "-o", "json"])
    try:
        eps = json.loads(raw)
        endpoint_summary = ", ".join(a.get("ip","") for s in eps.get("subsets",[]) for a in s.get("addresses",[])) or "no ready endpoints"
    except Exception: endpoint_summary = result(rc, raw, err)
    rc, raw, err = cmd(["curl", "-sS", "--max-time", "4", "-o", "/dev/null", "-w", "HTTP %{http_code}", "http://127.0.0.1:30080/"], 6)
    local_http = result(rc, raw, err)
    rc, raw, err = cmd(["curl", "-sS", "--max-time", "4", "http://127.0.0.1:30080/"], 6)
    version = "unavailable"
    if rc == 0:
        import re
        match = re.search(r'<p[^>]*id=["\']version["\'][^>]*>\s*([^<]+)', raw, re.I)
        version = match.group(1).strip() if match else "page loaded; version label not found"
    else: version = result(rc, raw, err)
    return jsonify(services=services, node_status=node_status, deployments_ready=dep_summary, pods_summary=pod_summary, selector=selector, endpoints=endpoint_summary, local_http=local_http, app_version=version)

@app.post("/api/switch/<version>")
@auth_required
def switch(version):
    if version not in ("blue", "green"):
        return jsonify(error="Version must be blue or green"), 400
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "get", "deployment", "medicare-" + version, "-o", "json"])
    if rc: return jsonify(error=result(rc, raw, err)), 409
    try:
        dep = json.loads(raw)
        desired = dep.get("spec", {}).get("replicas", 1)
        ready = dep.get("status", {}).get("readyReplicas", 0)
        if ready < desired: return jsonify(error=f"Refusing switch: medicare-{version} has {ready}/{desired} replicas ready"), 409
    except Exception: return jsonify(error="Could not verify target readiness; traffic was not switched"), 409
    patch = json.dumps({"spec":{"selector":{"app":"medicare","version":version}})
    rc, raw, err = cmd(["kubectl", "-n", NAMESPACE, "patch", "service", SERVICE, "--type=merge", "-p", patch])
    if rc: return jsonify(error=result(rc, raw, err)), 500
    return jsonify(message=f"Service selector switched to {version}. Refresh status to verify endpoints and served version.")

@app.post("/api/trivy")
@auth_required
def trivy():
    if not shutil.which("trivy"): return jsonify(error="Trivy is not installed or not on PATH; no scan was run"), 503
    target = next((p for p in PROJECT_CANDIDATES if p.is_dir() and (p / "Dockerfile").exists()), None)
    if target is None: return jsonify(error="No verified project directory containing Dockerfile found. Configure PROJECT_CANDIDATES in dashboard/app.py; no scan was run."), 404
    rc, raw, err = cmd(["trivy", "config", "--severity", "HIGH,CRITICAL", "--format", "json", str(target)], 120)
    if rc: return jsonify(status="error", scanner="Trivy config", target=str(target), error=result(rc, raw, err), output=raw[:12000]), 500
    try:
        report = json.loads(raw or "{}")
        counts = {"HIGH":0, "CRITICAL":0}
        for item in report.get("Results", []) or []:
            for mis in item.get("Misconfigurations", []) or []:
                sev = (mis.get("Severity") or "").upper()
                if sev in counts and (mis.get("Status") or "FAIL").upper() == "FAIL": counts[sev] += 1
        summary = counts
        shown = json.dumps(report, indent=2)[:12000]
    except Exception:
        summary, shown = {}, raw[:12000]
    return jsonify(status="completed", scanner="Trivy config", target=str(target), summary=summary, output=shown)

if __name__ == "__main__":
    # Loopback only: use an SSH tunnel; do not expose port 5000 publicly.
    app.run(host="127.0.0.1", port=5000, debug=False)
