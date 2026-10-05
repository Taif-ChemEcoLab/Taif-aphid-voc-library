"""VOC·BIO Library — Main entry point. Run: streamlit run app.py"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()   # reads .env locally; Streamlit Cloud uses Secrets Manager instead

st.set_page_config(
    page_title="VOC·BIO Library",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: #0d1117 !important; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.4rem; color: #1a3a2a; line-height: 1.1; margin: 0;
}
.hero-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem; color: #4a7c59;
    letter-spacing: 0.12em; text-transform: uppercase; margin-top: 8px;
}
.stat-card {
    background: linear-gradient(135deg, #f0f9f4 0%, #e6f3ec 100%);
    border: 1px solid #b7dfc9; border-radius: 12px;
    padding: 20px 24px; text-align: center;
}
.stat-number {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem; color: #1a3a2a; line-height: 1;
}
.stat-label {
    font-size: 0.78rem; color: #4a7c59;
    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px;
}
.section-head {
    font-family: 'DM Serif Display', serif;
    font-size: 1.8rem; color: #1a3a2a;
    border-bottom: 2px solid #b7dfc9;
    padding-bottom: 8px; margin-bottom: 20px;
}
.smiles-box {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem; background: #f6f8fa;
    border: 1px solid #d0d7de; border-radius: 6px;
    padding: 6px 10px; word-break: break-all; color: #24292f;
}
.info-box {
    background: #f0fdf4; border-left: 4px solid #22c55e;
    border-radius: 0 8px 8px 0; padding: 12px 16px;
    font-size: 0.88rem; color: #166534; margin: 12px 0;
}
.footer {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: #8b949e; text-align: center;
    margin-top: 40px; padding-top: 20px; border-top: 1px solid #e6f3ec;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🌿 VOC·BIO Library")
    st.markdown("---")
    route_names = [
        "Dashboard", "Published GC-MS Features", "Chemical Structure Explorer",
        "Biological & Sample Contexts", "Published Feature Statistics", "Evidence Explorer",
        "Docking Predictions", "Feature-Context Network", "Structural Similarity Explorer",
        "References / Data Sources", "Research Team Assistant",
    ]
    query_page = st.query_params.get("page")
    if query_page in route_names and "main_navigation" not in st.session_state:
        st.session_state["main_navigation"] = query_page
    if "route_override" in st.session_state:
        st.session_state["main_navigation"] = st.session_state.pop("route_override")
    page = st.radio(
        "Navigate",
        route_names,
        label_visibility="collapsed",
        key="main_navigation",
    )
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#8b949e; line-height:1.6;'>
    Built with <b>Streamlit</b> + <b>RDKit</b><br>
    Cheminformatics-enhanced<br>
    insect–VOC–plant library<br><br>
    <i>Taif University ×<br>Collaboration Project</i>
    </div>
    """, unsafe_allow_html=True)

if   page == "Dashboard":                       from modules.phase5c3_dashboard      import render
elif page == "Published GC-MS Features":        from modules.phase5c3_feature_library import render
elif page == "Chemical Structure Explorer":     from modules.phase5c3_molecule_explorer import render
elif page == "Biological & Sample Contexts":    from modules.phase5c3_contexts       import render
elif page == "Published Feature Statistics":    from modules.v1_statistics          import render
elif page == "Evidence Explorer":                from modules.phase5c3_evidence       import render
elif page == "Docking Predictions":              from modules.v1_docking_explorer    import render
elif page == "Feature-Context Network":         from modules.v1_network             import render
elif page == "Structural Similarity Explorer":  from modules.phase5c3_similarity    import render
elif page == "References / Data Sources":       from modules.phase5c3_references    import render
elif page == "Research Team Assistant":         from modules.v1_agent_guide         import render

render()
