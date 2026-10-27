import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PAGE = "AI API Diagnosis Assistant"
st.set_page_config(page_title=PAGE, page_icon="🛠", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:1.5rem;max-width:1400px}.hero{padding:1.35rem 1.6rem;border-radius:18px;background:linear-gradient(120deg,#102a43,#165d7a 58%,#37a3a3);color:white;margin-bottom:1rem}.hero h1{font-size:2rem;margin:0}.hero p{margin:.35rem 0 0;color:#e2f6f5}.metric-card{padding:1rem;border:1px solid #e6edf3;border-radius:14px;background:#fff}.warning{padding:.8rem 1rem;border-radius:10px;background:#fff4d6;color:#664d03;border:1px solid #ffdf87}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>AI-Based API Error Diagnosis Assistant</h1><p>Sanitized, evidence-led API incident analysis — keep secrets out of logs and prompts.</p></div>', unsafe_allow_html=True)
st.warning("Never share API keys, access tokens, passwords, cookies, private keys, or other secrets. Automatic masking is best-effort; review the sanitized preview before submitting.")


def api(method, path, **kwargs):
    try:
        response = requests.request(method, API + path, timeout=20, **kwargs)
        if response.ok:
            return response
        st.error(f"Backend returned {response.status_code}: {response.text[:500]}")
    except requests.RequestException:
        st.error(f"Cannot reach the FastAPI backend at {API}. Start it in a separate terminal.")
    return None


def redact_preview(text: str) -> str:
    # UI preview is only advisory; authoritative masking is repeated in the backend.
    import re
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+\-/]+=*", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|token|cookie|client[_-]?secret)\b\s*[\"']?\s*[:=]\s*[\"']?)[^\s,\"';&}]+", r"\1[REDACTED]", text)
    return text


def fetch_incidents(params=None):
    r = api("GET", "/incidents", params=params or {"limit": 100})
    return r.json() if r else {"items": [], "total": 0}


def render_dashboard():
    payload = fetch_incidents({"limit": 100})
    items = payload.get("items", [])
    docs_r = api("GET", "/documents")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total incidents", payload.get("total", 0))
    c2.metric("Open", sum(x["status"] == "open" for x in items))
    c3.metric("Investigating", sum(x["status"] == "investigating" for x in items))
    c4.metric("Resolved", sum(x["status"] == "resolved" for x in items))
    st.subheader("API reliability overview")
    left,right=st.columns([1.15,1])
    with left:
        st.markdown("#### Recent incidents")
        if items:
            df=pd.DataFrame(items)
            st.dataframe(df[["id","title","api_name","status_code","category","status","created_at"]], use_container_width=True, hide_index=True)
        else: st.info("No incidents yet. Create your first incident from **New Incident**.")
    with right:
        st.markdown("#### Errors by category")
        if items:
            counts=pd.Series([x.get("category","Unknown / other") for x in items]).value_counts()
            st.bar_chart(counts)
        else: st.caption("Category chart appears after incidents are recorded.")
    st.markdown("#### Status code distribution")
    codes=[str(x["status_code"]) for x in items if x.get("status_code")]
    if codes: st.bar_chart(pd.Series(codes).value_counts().sort_index())
    else: st.caption("No HTTP status codes recorded yet.")
    st.markdown("#### Common API failure patterns")
    if items:
        cats=pd.Series([x.get("category", "Unknown") for x in items]).value_counts()
        st.write(" · ".join(f"{k}: {v}" for k,v in cats.head(4).items()))
    st.caption(f"Indexed documentation files: {len(docs_r.json().get('items', [])) if docs_r else 0}")


def render_new_incident():
    st.subheader("Create a new incident")
    st.caption("Incident data is sanitized again before it is stored. Provide patterns rather than real identifiers where possible.")
    with st.form("incident_form"):
        a,b=st.columns(2)
        title=a.text_input("Incident title*", placeholder="Checkout API returns 422")
        api_name=b.text_input("API name or service*", placeholder="payments-service")
        c,d=st.columns(2)
        method=c.selectbox("HTTP method", ["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS","OTHER"])
        endpoint=d.text_input("Sanitized endpoint pattern", placeholder="/v1/orders/{order_id}")
        e,f=st.columns(2)
        status=e.number_input("HTTP response status", min_value=100, max_value=599, value=500)
        duration=f.number_input("Request duration (ms)", min_value=0.0, value=0.0)
        error=st.text_area("Error message", height=75)
        headers=st.text_area("Selected headers (JSON)", value="{}", height=80)
        g,h=st.columns(2)
        req=g.text_area("Sanitized request sample", height=100)
        resp=h.text_area("Sanitized response sample", height=100)
        metadata=st.text_area("Request / response metadata (JSON)", value='{"request": {}, "response": {}}', height=80)
        logs=st.text_area("Logs or stack trace", height=150)
        submitted=st.form_submit_button("Review sanitized data", type="primary", use_container_width=True)
    if submitted:
        try:
            hdr=json.loads(headers or "{}")
            meta=json.loads(metadata or "{}")
            if not isinstance(hdr,dict) or not isinstance(meta,dict): raise ValueError("Headers and metadata must be JSON objects")
            data={"title":title,"api_name":api_name,"method":method,"endpoint":endpoint,"status_code":int(status),"error_message":error,"headers":hdr,"request_metadata":meta.get("request",{}),"response_metadata":meta.get("response",{}),"request_sample":req,"response_sample":resp,"duration_ms":duration,"timestamp":datetime.now().astimezone().isoformat(),"logs":logs}
            if not title.strip() or not api_name.strip(): raise ValueError("Incident title and API name are required")
            safe=json.loads(redact_preview(json.dumps(data)))
            st.session_state["pending_incident"]=safe
        except (json.JSONDecodeError, ValueError) as ex: st.error(f"Please check the form: {ex}")
    if st.session_state.get("pending_incident"):
        st.markdown("### Sanitized content preview")
        st.json(st.session_state["pending_incident"])
        st.caption("Masking is not perfect. Inspect every field before analysis.")
        if st.button("Submit sanitized incident", type="primary"):
            r=api("POST","/incidents",json=st.session_state["pending_incident"])
            if r:
                st.success(f"Incident saved: {r.json()['id']}")
                st.session_state.pop("pending_incident",None)
                st.session_state["selected_incident"]=r.json()["id"]


def render_diagnose():
    st.subheader("Diagnose an incident")
    items=fetch_incidents({"limit":100}).get("items",[])
    if not items: st.info("Create an incident first."); return
    options={f"{x['title']} · {x['id'][:8]} · {x.get('category','')}":x["id"] for x in items}
    keys=list(options)
    default=next((i for i,k in enumerate(keys) if options[k]==st.session_state.get("selected_incident")),0)
    selected=options[st.selectbox("Incident",keys,index=default)]
    if st.button("Run diagnosis",type="primary"):
        with st.spinner("Analyzing sanitized incident and retrieving local documentation…"):
            r=api("POST",f"/incidents/{selected}/diagnose")
        if r: st.session_state["diagnosis_result"]=r.json()
    result=st.session_state.get("diagnosis_result")
    if result:
        st.info(result.get("provider_status",""))
        cl=result.get("classification",{})
        st.markdown(f"### {result.get('summary','Diagnosis')}")
        st.metric("Classification",cl.get("category","Unknown"),f"Confidence {cl.get('confidence',0):.0%}"+ (" · uncertain" if cl.get("uncertain") else ""))
        facts,hyps=st.columns(2)
        with facts:
            st.markdown("#### Observed facts")
            for x in result.get("observed_facts",[]): st.write(f"- {x['fact']} · *{x['source']}*")
            st.markdown("#### Supporting evidence")
            for x in result.get("supporting_evidence",[]): st.write(f"- {x}")
        with hyps:
            st.markdown("#### Likely causes (hypotheses)")
            for x in result.get("likely_causes",[]): st.write(f"- {x}")
            st.markdown("#### Alternative explanations")
            for x in result.get("alternative_explanations",[]): st.write(f"- {x}")
        st.caption("Uncertainty and limitations: "+result.get("uncertainty",""))
        st.markdown("#### Ordered troubleshooting steps")
        for i,step in enumerate(result.get("troubleshooting_steps",[]),1): st.write(f"{i}. {step}")
        st.markdown("#### Safe validation tests")
        for x in result.get("safe_validation_tests",[]): st.write(f"- {x}")
        st.markdown("#### Documentation references")
        refs=result.get("documentation_references",[])
        if refs:
            for r in refs: st.write(f"**{r['filename']} · {r['reference']}** — {r['passage']}")
        else: st.caption("No matching local documents. Diagnosis uses incident data and built-in rules only.")


def render_history():
    st.subheader("Incident history")
    c1,c2,c3=st.columns(3)
    search=c1.text_input("Search ID, API, or title")
    status=c2.selectbox("Status",["All","open","investigating","resolved"])
    category=c3.selectbox("Category",["All","Authentication","Authorization","Validation","Rate limit","Timeout","Server error","Unknown / other"])
    params={"limit":100,"search":search}
    if status!="All": params["status"]=status
    if category!="All": params["category"]=category
    items=fetch_incidents(params).get("items",[])
    if not items: st.info("No matching incidents."); return
    st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
    ids=[x["id"] for x in items]
    selected=st.selectbox("Open incident detail",ids,format_func=lambda x: next((i["title"]+" · "+x for i in items if i["id"]==x),x))
    detail=api("GET",f"/incidents/{selected}")
    if detail:
        item=detail.json()
        with st.expander("Sanitized incident detail",expanded=True): st.json(item)
        current=item.get("status","open")
        new_status=st.selectbox("Update status",["open","investigating","resolved"],index=["open","investigating","resolved"].index(current),key="status_"+selected)
        if st.button("Save status",key="save_status_"+selected):
            r=api("PATCH",f"/incidents/{selected}/status",json={"status":new_status})
            if r: st.success("Status updated.")
        with st.form("fix_"+selected):
            note=st.text_area("Record attempted fix")
            outcome=st.selectbox("Outcome",["pending","successful","unsuccessful","inconclusive"])
            if st.form_submit_button("Add fix attempt"):
                r=api("POST",f"/incidents/{selected}/fix-attempts",json={"notes":note,"outcome":outcome})
                if r: st.success("Fix attempt recorded.")


def render_docs():
    st.subheader("Documentation library")
    st.write("Add approved local API docs or schemas. Uploaded files are treated as untrusted text, never executed. Supported formats: TXT, Markdown, JSON, YAML; max size is controlled by backend configuration.")
    files=st.file_uploader("Upload documentation",type=["txt","md","json","yaml","yml"],accept_multiple_files=True)
    if files and st.button("Index selected files",type="primary"):
        for file in files:
            r=api("POST","/documents/upload",files={"file":(file.name,file.getvalue(),file.type or "text/plain")})
            if r: st.success(f"Indexed {file.name}: {r.json()['passages_indexed']} passages")
    r=api("GET","/documents")
    if r:
        items=r.json().get("items",[])
        if items: st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
        else: st.info("No documents indexed yet. Try docs/sample_api_spec.json.")


def render_scenarios():
    st.subheader("Test scenarios")
    items=fetch_incidents({"limit":100}).get("items",[])
    if not items: st.info("Create an incident first."); return
    options={f"{x['title']} · {x['id'][:8]}":x["id"] for x in items}
    label=st.selectbox("Incident",list(options)); iid=options[label]
    with st.form("scenario_form"):
        name=st.text_input("Scenario name", "Sanitized regression case")
        a,b=st.columns(2); expected=a.number_input("Expected status",100,599,200); observed=b.number_input("Observed status",100,599,500)
        sample=st.text_area("Sanitized test input (mock/non-production only)")
        result=st.selectbox("Result",["not_run","pass","fail"])
        notes=st.text_area("Notes")
        if st.form_submit_button("Save test scenario"):
            r=api("POST",f"/incidents/{iid}/test-scenarios",json={"name":name,"expected_status":int(expected),"observed_status":int(observed),"input_sample":sample,"result":result,"notes":notes})
            if r: st.success("Scenario saved. The app does not call production endpoints.")
    d=api("GET",f"/incidents/{iid}")
    if d:
        rows=d.json().get("test_scenarios",[])
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else: st.caption("No scenarios recorded for this incident.")


def render_reports():
    st.subheader("Reports and export")
    items=fetch_incidents({"limit":100}).get("items",[])
    if not items: st.info("No incidents available for export."); return
    options={f"{x['title']} · {x['id'][:8]}":x["id"] for x in items}
    selected=options[st.selectbox("Incident",list(options))]
    for fmt in ["json","csv"]:
        r=api("GET",f"/incidents/{selected}/export",params={"format":fmt})
        if r:
            st.download_button(f"Download sanitized {fmt.upper()}",r.content,file_name=f"incident-{selected}.{fmt}",mime=r.headers.get("content-type","application/octet-stream"),key="download_"+fmt)


def render_help():
    st.subheader("Settings and help")
    st.markdown(f"**Backend:** `{API}`")
    st.write("Diagnosis works offline with deterministic rules. Optional AI uses environment variables LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL. No production API requests are ever made by diagnosis or scenarios.")
    st.markdown("#### Privacy and limitations")
    st.write("Masking is best-effort, not perfect. Sanitize identifiers and review previews. Local SQLite and uploaded document contents are not encrypted and this app does not include user authentication; run only on a trusted machine/network. Treat diagnosis causes as hypotheses and verify against authorized logs and documentation.")
    st.markdown("#### Useful links")
    st.markdown("- [FastAPI interactive API docs](http://127.0.0.1:8000/docs)\n- [Health check](http://127.0.0.1:8000/health)")

with st.sidebar:
    st.markdown("### Navigation")
    page=st.radio("Go to",["Dashboard","New Incident","Diagnose Error","Documentation Library","Incident History","Test Scenarios","Reports and Export","Settings and Help"],label_visibility="collapsed")
    st.caption("Local developer tool · Rule-based fallback available")

{
 "Dashboard":render_dashboard,"New Incident":render_new_incident,"Diagnose Error":render_diagnose,
 "Documentation Library":render_docs,"Incident History":render_history,"Test Scenarios":render_scenarios,
 "Reports and Export":render_reports,"Settings and Help":render_help
}[page]()
