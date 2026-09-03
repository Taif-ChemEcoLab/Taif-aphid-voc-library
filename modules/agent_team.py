"""Ask the Research Team — Multi-Agent Chat Interface (cloud-safe)."""

import streamlit as st
import time
import os
import sys
import traceback

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


def render():
    st.markdown("<div class='section-head'>🤝 Ask the Research Team</div>", unsafe_allow_html=True)

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
                <div style='color:#a8d5b5;font-weight:700;font-size:0.9rem'>Dr. Taghreed Alsufyan</div>
                <div style='color:#6b8f74;font-size:0.78rem'>Organic Chemist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Molecular structure · LogP · Volatility · Fingerprints</div>
            </div>
            <div style='background:rgba(180,83,9,0.15);border:1px solid #b45309;
                        border-radius:10px;padding:12px 16px;flex:1;min-width:160px'>
                <div style='font-size:1.4rem'>🦟</div>
                <div style='color:#fcd34d;font-weight:700;font-size:0.9rem'>Dr. Noura Alotaibi</div>
                <div style='color:#9a7031;font-size:0.78rem'>Entomologist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Bioassays · Insect biology · Host plants · Natural enemies</div>
            </div>
            <div style='background:rgba(67,56,202,0.15);border:1px solid #4338ca;
                        border-radius:10px;padding:12px 16px;flex:1;min-width:160px'>
                <div style='font-size:1.4rem'>💻</div>
                <div style='color:#a5b4fc;font-weight:700;font-size:0.9rem'>Dr. Taufia Hussain</div>
                <div style='color:#5b5ea6;font-size:0.78rem'>Computational Biologist</div>
                <div style='color:#8b949e;font-size:0.74rem;margin-top:4px'>
                    Statistics · Structural similarity · Evidence strength · Patterns</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
                st.code(f"Key loaded: {api_key[:8]}...{api_key[-4:]}")
            else:
                st.warning("Add your API key to activate the agents")
                st.error("❌ No API key found")

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        use_all = st.checkbox("Always use all 3 agents", value=False)
        show_agent_thinking = st.checkbox("Show agent reasoning", value=True)
        show_tools = st.checkbox("Show tools used", value=False)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "agent_details" not in st.session_state:
        st.session_state.agent_details = {}

    if "team_question" not in st.session_state:
        st.session_state.team_question = ""

    st.markdown("**Try an example question:**")
    cols = st.columns(4)

    for i, q in enumerate(EXAMPLE_QUESTIONS):
        with cols[i % 4]:
            if st.button(
                q[:42] + ("…" if len(q) > 42 else ""),
                key=f"ex_{i}",
                use_container_width=True,
            ):
                st.session_state.team_question = q
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    for i, turn in enumerate(st.session_state.chat_history):
        st.markdown(f"""
        <div style='display:flex;justify-content:flex-end;margin-bottom:12px'>
            <div style='background:#1a3a2a;color:#a8d5b5;border-radius:16px 16px 4px 16px;
                        padding:12px 18px;max-width:75%;font-size:0.95rem;
                        border:1px solid #2d6a4f'>{turn["question"]}</div>
        </div>
        """, unsafe_allow_html=True)

        if show_agent_thinking and i in st.session_state.agent_details:
            details = st.session_state.agent_details[i]
            agents_used = details.get("agents_used", [])

            with st.expander(f"🔬 Agent reasoning — {len(agents_used)} specialist(s) consulted"):
                for r in details.get("agent_results", []):
                    ag = r["agent"]
                    response_text = r.get("response", "").replace(chr(10), "<br>")

                    st.markdown(f"""
                    <div style='background:{ag["bg"]};border:1px solid {ag["border"]};
                                border-radius:10px;padding:14px 18px;margin-bottom:12px'>
                        <div style='font-weight:700;color:{ag["color"]};font-size:0.9rem;
                                    margin-bottom:6px'>
                            {ag["emoji"]} {ag["name"]} · {ag["title"]}
                        </div>
                        <div style='font-size:0.85rem;color:#374151;line-height:1.6'>
                            {response_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if show_tools and r.get("tools_used"):
                        pills = " ".join(
                            f'<code style="background:#f3f4f6;padding:2px 6px;'
                            f'border-radius:4px;font-size:0.72rem">{t["tool"]}</code>'
                            for t in r["tools_used"]
                        )
                        st.markdown(f"**Tools used:** {pills}", unsafe_allow_html=True)

        answer_text = turn["answer"].replace(chr(10), "<br>")

        st.markdown(f"""
        <div style='background:#f8fafb;border:1px solid #d1fae5;border-left:4px solid #22c55e;
                    border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:20px'>
            <div style='font-size:0.72rem;color:#4a7c59;font-weight:700;
                        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px'>
                🤝 Research Team · Synthesised Answer
            </div>
            <div style='font-size:0.92rem;color:#1f2937;line-height:1.7'>
                {answer_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    with st.form("chat_form", clear_on_submit=False):
        st.text_area(
            "Ask the research team",
            key="team_question",
            placeholder="e.g. Which compounds from betel leaf repel Thrips palmi?",
            height=80,
            label_visibility="collapsed",
        )

        col_submit, col_clear = st.columns([3, 1])

        with col_submit:
            submitted = st.form_submit_button(
                "🔬 Ask the Team",
                type="primary",
                use_container_width=True,
            )

        with col_clear:
            cleared = st.form_submit_button(
                "🗑️ Clear Chat",
                use_container_width=True,
            )

    if cleared:
        st.session_state.chat_history = []
        st.session_state.agent_details = {}
        st.session_state.team_question = ""
        st.rerun()

    question = st.session_state.team_question.strip()

    if submitted and question:
        if not api_key:
            st.error(
                "❌ No OpenAI API key found. Add it in the sidebar or set "
                "OPENAI_API_KEY in your .env file."
            )
            st.stop()

        try:
            from openai import OpenAI
            test_client = OpenAI(api_key=api_key)
            test_client.models.list()
        except Exception as e:
            st.error(f"❌ OpenAI API key error: {str(e)}")
            st.info("Check that your key starts with 'sk-' and has not expired.")
            st.stop()

        try:
            from utils.multi_agent import ask_research_team, AGENTS
        except ImportError as e:
            st.error(f"❌ Could not load agent module: {e}")
            st.stop()

        with st.status("🔬 Research team is working...", expanded=True) as status:
            st.write("📋 Routing question to relevant specialists...")
            time.sleep(0.3)

            result = None
            error_detail = None
            error_traceback = None

            try:
                result = ask_research_team(
                    question=question,
                    api_key=api_key,
                    use_all_agents=use_all,
                )
            except Exception as e:
                error_detail = str(e)
                error_traceback = traceback.format_exc()

            if error_detail:
                status.update(label="❌ Agent error", state="error")
                st.error(f"Agent failed: {error_detail}")

                with st.expander("Full traceback"):
                    st.code(error_traceback)

                st.stop()

            if not isinstance(result, dict):
                status.update(label="❌ Invalid agent result", state="error")
                st.error("Agent returned an invalid result.")
                st.stop()

            agents_used = result.get("agents_used", [])
            agent_results = result.get("agent_results", [])

            agent_names = [
                AGENTS[a]["emoji"] + " " + AGENTS[a]["name"]
                for a in agents_used
                if a in AGENTS
            ]

            if agent_names:
                st.write(f"✅ Consulting: {' · '.join(agent_names)}")
            else:
                st.warning("No specialist agents were selected.")

            for r in agent_results:
                ag = r.get("agent", {})
                tools = r.get("tools_used", [])

                if tools:
                    st.write(
                        f"  {ag.get('emoji', '🤖')} {ag.get('name', 'Agent')}: called "
                        f"`{'`, `'.join(t.get('tool', 'tool') for t in tools)}`"
                    )

                if not r.get("response") or r.get("response") == "(No response generated)":
                    st.warning(
                        f"⚠️ {ag.get('name', 'Agent')} returned no response — "
                        f"tool calls: {len(tools)}"
                    )

            if not result.get("synthesis"):
                status.update(label="⚠️ Synthesis empty", state="error")
                st.error("Orchestrator returned empty synthesis.")
                st.stop()

            st.write("🧩 Synthesising findings...")
            status.update(label="✅ Team response ready!", state="complete")

        turn_idx = len(st.session_state.chat_history)

        st.session_state.chat_history.append({
            "question": question,
            "answer": result["synthesis"],
        })

        st.session_state.agent_details[turn_idx] = result

        st.session_state.team_question = ""
        st.rerun()