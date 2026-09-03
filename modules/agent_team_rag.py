"""Ask the Research Team — Multi-Agent Chat Interface (RAG-enhanced)."""

import streamlit as st
import time
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

EXAMPLE_QUESTIONS = [
    "Which compounds from betel leaf repel Thrips palmi?",
    "What natural enemies can be recruited against Myzus persicae?",
    "Compare eugenol and linalool — which is a better repellent?",
    "What are the most volatile compounds in the library?",
    "Which VOCs show the strongest statistical evidence in bioassays?",
    "Design a natural pest management strategy for Piper betle.",
    "What sesquiterpenes are known attractants for natural enemies?",
    "How similar is β-caryophyllene to other compounds in the library?",
]


def _rag_status_badge(total_chunks: int) -> tuple[str, str]:
    """Return (colour hex, label) for the RAG status indicator."""
    if total_chunks == 0:
        return "#ef4444", "Empty — run ingest_literature.py"
    if total_chunks < 20:
        return "#f59e0b", f"{total_chunks} chunks (partial)"
    return "#22c55e", f"{total_chunks} chunks ready"


def render():
    st.markdown("<div class='section-head'>🤝 Ask the Research Team</div>",
                unsafe_allow_html=True)

    st.markdown("""
    <div style='background:linear-gradient(135deg,#0d1117 0%,#1a3a2a 100%);
                border-radius:14px;padding:24px 28px;margin-bottom:24px;
                border:1px solid #2d6a4f'>
        <div style='font-family:"DM Serif Display",serif;font-size:1.4rem;
                    color:#a8d5b5;margin-bottom:8px'>Your AI Research Collaborators</div>
        <div style='display:flex;gap:20px;flex-wrap:wrap;margin-top:14px'>
            <div style='background:rgba(74,124,89,0.2);border:1px solid #4a7c59;
                        border-radius:10px;padding:12px 16px;flex:1;min-width:160px'>
                <div style='font-size:1.4rem'>🧪</div>
                <div style='color:#a8d5b5;font-weight:700;font-size:0.9rem'>Dr. Taghreed Alsufyani</div>
                <div style='color:#6b8f74;font-size:0.78rem'>Organic Chemist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Molecular structure · LogP · Volatility · Fingerprints · Literature mechanisms</div>
            </div>
            <div style='background:rgba(180,83,9,0.15);border:1px solid #b45309;
                        border-radius:10px;padding:12px 16px;flex:1;min-width:160px'>
                <div style='font-size:1.4rem'>🦟</div>
                <div style='color:#fcd34d;font-weight:700;font-size:0.9rem'>Dr. Noura Alotaibi</div>
                <div style='color:#9a7031;font-size:0.78rem'>Entomologist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Bioassays · Insect biology · Host plants · Field study context</div>
            </div>
            <div style='background:rgba(67,56,202,0.15);border:1px solid #4338ca;
                        border-radius:10px;padding:12px 16px;flex:1;min-width:160px'>
                <div style='font-size:1.4rem'>💻</div>
                <div style='color:#a5b4fc;font-weight:700;font-size:0.9rem'>Dr. Taufia Hussain</div>
                <div style='color:#5b5ea6;font-size:0.78rem'>Computational Biologist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Statistics · Structural similarity · Evidence strength · Meta-analysis</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── API key ───────────────────────────────────────────────────────────────
    api_key = os.getenv("OPENAI_API_KEY", "")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔑 OpenAI API Key")
        if api_key:
            st.success("API key loaded from secrets ✓")
        else:
            api_key = st.text_input(
                "Enter your OpenAI API key",
                type="password",
                placeholder="sk-...",
                help="Your key is used only for this session and never stored.",
            )
            if api_key:
                st.success("API key set ✓")
            else:
                st.warning("Add your API key to activate the agents")
            
            if api_key:
                st.code(f"Key loaded: {api_key[:8]}...{api_key[-4:]}")
            else:
                st.error("❌ No API key found")

        # ── RAG status panel ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📚 Literature Knowledge Base")

        if api_key:
            if st.button("🔄 Check RAG Status", use_container_width=True):
                try:
                    from utils.multi_agent_rag import rag_status
                    st.session_state["rag_stats"] = rag_status(api_key)
                except Exception as e:
                    st.session_state["rag_stats"] = {"error": str(e), "total_chunks": 0}

            stats = st.session_state.get("rag_stats")
            if stats:
                if "error" in stats and stats["total_chunks"] == 0:
                    st.error(f"RAG unavailable: {stats['error']}")
                else:
                    total   = stats.get("total_chunks", 0)
                    colour, label = _rag_status_badge(total)
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid {colour};"
                        f"border-radius:8px;padding:10px 14px;margin-top:6px'>"
                        f"<div style='color:{colour};font-weight:700;font-size:0.8rem'>"
                        f"● {label}</div>"
                        f"<div style='color:#8b949e;font-size:0.72rem;margin-top:4px'>"
                        f"Collection: {stats.get('collection','—')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Click above to check literature DB status.")

            with st.expander("📥 Ingest a PDF"):
                uploaded_pdf = st.file_uploader(
                    "Upload a research paper (PDF)",
                    type=["pdf"],
                    key="pdf_uploader",
                )
                if uploaded_pdf:
                    col_t, col_a = st.columns(2)
                    with col_t:
                        pdf_title   = st.text_input("Title",   key="pdf_title")
                        pdf_authors = st.text_input("Authors", key="pdf_authors")
                        pdf_year    = st.text_input("Year",    key="pdf_year")
                    with col_a:
                        pdf_journal  = st.text_input("Journal",        key="pdf_journal")
                        pdf_doi      = st.text_input("DOI",            key="pdf_doi")
                        pdf_compound = st.text_input("Compound focus", key="pdf_compound",
                                                     placeholder="e.g. eugenol")
                        pdf_insect   = st.text_input("Insect focus",   key="pdf_insect",
                                                     placeholder="e.g. Thrips_palmi")
                    if st.button("📥 Ingest PDF", type="primary",
                                 use_container_width=True):
                        if not pdf_title:
                            st.error("Title is required.")
                        else:
                            import tempfile, pathlib
                            from utils.literature_rag import ingest_pdf
                            with tempfile.NamedTemporaryFile(
                                suffix=".pdf", delete=False
                            ) as tmp:
                                tmp.write(uploaded_pdf.read())
                                tmp_path = tmp.name
                            with st.spinner("Ingesting…"):
                                n = ingest_pdf(
                                    tmp_path,
                                    {
                                        "title":          pdf_title,
                                        "authors":        pdf_authors,
                                        "year":           pdf_year,
                                        "journal":        pdf_journal,
                                        "doi":            pdf_doi,
                                        "compound_focus": pdf_compound or "general_VOCs",
                                        "insect_focus":   pdf_insect   or "general_insects",
                                        "paper_type":     "research_article",
                                    },
                                    api_key,
                                )
                                pathlib.Path(tmp_path).unlink(missing_ok=True)
                            st.success(f"✅ Ingested {n} chunks from '{pdf_title}'")
        else:
            st.caption("Add your API key to manage the literature KB.")

        # ── Agent settings ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        use_all             = st.checkbox("Always use all 3 agents", value=False)
        show_agent_thinking = st.checkbox("Show agent reasoning",    value=True)
        show_tools          = st.checkbox("Show tools used",         value=False)

    # ── Session state ─────────────────────────────────────────────────────────
    if "chat_history"  not in st.session_state: st.session_state.chat_history  = []
    if "agent_details" not in st.session_state: st.session_state.agent_details = {}

    # ── Example buttons ───────────────────────────────────────────────────────
    st.markdown("**Try an example question:**")
    cols = st.columns(4)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        with cols[i % 4]:
            if st.button(q[:42] + ("…" if len(q) > 42 else ""),
                         key=f"ex_{i}", use_container_width=True):
                st.session_state["pending_question"] = q

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    for i, turn in enumerate(st.session_state.chat_history):
        st.markdown(f"""
        <div style='display:flex;justify-content:flex-end;margin-bottom:12px'>
            <div style='background:#1a3a2a;color:#a8d5b5;border-radius:16px 16px 4px 16px;
                        padding:12px 18px;max-width:75%;font-size:0.95rem;
                        border:1px solid #2d6a4f'>{turn["question"]}</div>
        </div>
        """, unsafe_allow_html=True)

        if show_agent_thinking and i in st.session_state.agent_details:
            details     = st.session_state.agent_details[i]
            agents_used = details.get("agents_used", [])
            with st.expander(
                f"🔬 Agent reasoning — {len(agents_used)} specialist(s) consulted"
            ):
                for r in details.get("agent_results", []):
                    ag = r["agent"]

                    # Separate DB tools from RAG tool calls for display
                    db_tools  = [t for t in r.get("tools_used", [])
                                 if t["tool"] != "search_literature"]
                    rag_calls = [t for t in r.get("tools_used", [])
                                 if t["tool"] == "search_literature"]

                    st.markdown(f"""
                    <div style='background:{ag["bg"]};border:1px solid {ag["border"]};
                                border-radius:10px;padding:14px 18px;margin-bottom:12px'>
                        <div style='font-weight:700;color:{ag["color"]};font-size:0.9rem;
                                    margin-bottom:6px'>
                            {ag["emoji"]} {ag["name"]} · {ag["title"]}
                        </div>
                        <div style='font-size:0.85rem;color:#374151;line-height:1.6'>
                            {r["response"].replace(chr(10), "<br>")}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if show_tools:
                        if db_tools:
                            pills = " ".join(
                                f'<code style="background:#f3f4f6;padding:2px 6px;'
                                f'border-radius:4px;font-size:0.72rem">{t["tool"]}</code>'
                                for t in db_tools
                            )
                            st.markdown(f"**DB tools:** {pills}",
                                        unsafe_allow_html=True)
                        if rag_calls:
                            for rc in rag_calls:
                                q_text = rc["args"].get("query", "")
                                st.markdown(
                                    f'📚 **Literature search:** '
                                    f'<code style="font-size:0.72rem">{q_text}</code>',
                                    unsafe_allow_html=True,
                                )

        st.markdown(f"""
        <div style='background:#f8fafb;border:1px solid #d1fae5;
                    border-left:4px solid #22c55e;border-radius:0 12px 12px 0;
                    padding:16px 20px;margin-bottom:20px'>
            <div style='font-size:0.72rem;color:#4a7c59;font-weight:700;
                        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px'>
                🤝 Research Team · Synthesised Answer
            </div>
            <div style='font-size:0.92rem;color:#1f2937;line-height:1.7'>
                {turn["answer"].replace(chr(10), "<br>")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Input form ────────────────────────────────────────────────────────────
    st.markdown("---")
    default_q = st.session_state.pop("pending_question", "")

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Ask the research team",
            value=default_q,
            placeholder="e.g. Why does eugenol repel Thrips palmi at the receptor level?",
            height=80,
            label_visibility="collapsed",
        )
        col_submit, col_clear = st.columns([3, 1])
        with col_submit:
            submitted = st.form_submit_button(
                "🔬 Ask the Team", type="primary", use_container_width=True
            )
        with col_clear:
            cleared = st.form_submit_button("🗑️ Clear Chat", use_container_width=True)

    if cleared:
        st.session_state.chat_history  = []
        st.session_state.agent_details = {}
        st.rerun()

    # ── Replace the existing "if submitted and user_input.strip():" block ──────
    # ── with this version in your modules/agent_team.py ──────────────────────

    if submitted and user_input.strip():

        # ── 1. API key guard ──────────────────────────────────────────────────
        if not api_key:
            st.error("❌ No OpenAI API key found. Add it in the sidebar or set "
                     "OPENAI_API_KEY in your .env file.")
            st.stop()

        # ── 2. Quick connectivity test before calling agents ──────────────────
        try:
            from openai import OpenAI
            test_client = OpenAI(api_key=api_key)
            test_client.models.list()          # lightweight call — just checks auth
        except Exception as e:
            st.error(f"❌ OpenAI API key error: {str(e)}")
            st.info("Check that your key starts with 'sk-' and has not expired.")
            st.stop()

        # ── 3. Load agent module ──────────────────────────────────────────────
        try:
            from utils.multi_agent import ask_research_team, AGENTS
        except ImportError as e:
            st.error(f"❌ Could not load agent module: {e}")
            st.stop()

        # ── 4. Run agents with full error visibility ──────────────────────────
        question = user_input.strip()

        with st.status("🔬 Research team is working...", expanded=True) as status:
            st.write("📋 Routing question to relevant specialists...")
            time.sleep(0.3)

            result = None
            error_detail = None

            try:
                result = ask_research_team(
                    question=question,
                    api_key=api_key,
                    use_all_agents=use_all,
                )
            except Exception as e:
                error_detail = str(e)

            if error_detail:
                status.update(label="❌ Agent error", state="error")
                st.error(f"Agent failed: {error_detail}")
                # Show full traceback in an expander for debugging
                import traceback
                with st.expander("Full traceback"):
                    st.code(traceback.format_exc())
                st.stop()

            agents_used  = result["agents_used"]
            agent_names  = [AGENTS[a]["emoji"] + " " + AGENTS[a]["name"]
                            for a in agents_used]
            st.write(f"✅ Consulting: {' · '.join(agent_names)}")

            for r in result["agent_results"]:
                ag    = r["agent"]
                tools = r.get("tools_used", [])
                if tools:
                    st.write(f"  {ag['emoji']} {ag['name']}: called "
                             f"`{'`, `'.join(t['tool'] for t in tools)}`")
                # Warn if an agent returned no content
                if not r.get("response") or r["response"] == "(No response generated)":
                    st.warning(f"⚠️ {ag['name']} returned no response — "
                               f"tool calls: {len(tools)}")

            if not result.get("synthesis"):
                status.update(label="⚠️ Synthesis empty", state="error")
                st.error("Orchestrator returned empty synthesis.")
                st.stop()

            st.write("🧩 Synthesising findings...")
            status.update(label="✅ Team response ready!", state="complete")

        # ── 5. Save to chat history ───────────────────────────────────────────
        turn_idx = len(st.session_state.chat_history)
        st.session_state.chat_history.append({
            "question": question,
            "answer":   result["synthesis"],
        })
        st.session_state.agent_details[turn_idx] = result
        st.rerun()
