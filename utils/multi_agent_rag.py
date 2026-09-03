"""
multi_agent.py  —  Multi-Agent Orchestration Engine (RAG-enhanced)
───────────────────────────────────────────────────────────────────
Changes from v1:
  • search_literature() tool added to every agent's tool list
  • execute_tool() routes "search_literature" to the RAG module
  • run_agent() passes api_key into RAG tool calls
  • Everything else is unchanged — drop-in replacement.
"""

import json
import os
from openai import OpenAI

from utils.agent_tools import (
    CHEMIST_TOOLS, ENTOMOLOGIST_TOOLS, COMPUTATIONAL_TOOLS, execute_tool,
)
from utils.literature_rag import (
    SEARCH_LITERATURE_TOOL, search_literature, get_collection_stats,
)

#  Attach the literature tool to every agent 

def _with_rag(tool_list: list) -> list:
    """Append the RAG search tool to an existing tool list."""
    return tool_list + [SEARCH_LITERATURE_TOOL]


AGENTS = {
    "chemist": {
        "id": "chemist", "name": "Dr. Taghreed Alsufyani", "title": "Chemist",
        "emoji": "🧪", "color": "#4a7c59", "bg": "#f0fdf4",
        "border": "#86efac",
        "tools": _with_rag(CHEMIST_TOOLS),
        "system_prompt": """You are Dr. Taghreed Alsufyani, an expert organic chemist specialising
in plant volatile organic compounds (VOCs) and chemical ecology.
Analyse CHEMICAL properties: structure, formula, SMILES, MW, LogP, TPSA, volatility,
chemical class, structure-activity relationships, and structural similarity.
Always use your tools to retrieve actual data. Be precise and cite compound IDs.
You also have access to search_literature — use it when you need mechanistic
explanations, receptor interactions, or comparative structure-activity data
from the published literature that is not in the structured database.
Keep your response focused on chemistry — 3 to 5 sentences maximum.
End with a one-line "Chemical Assessment:" summary.""",
    },
    "entomologist": {
        "id": "entomologist", "name": "Dr. Noura Alotaibi",
        "title": "Chemical Ecologist & Entomologist",
        "emoji": "🦟", "color": "#b45309", "bg": "#fffbeb",
        "border": "#fcd34d",
        "tools": _with_rag(ENTOMOLOGIST_TOOLS),
        "system_prompt": """You are Dr. Noura Alotaibi, a field entomologist specialising
in aphid and thrips biology, host plant associations, and insect behavioural responses.
Interpret BIOLOGICAL and ECOLOGICAL significance: insect biology, bioassay results,
natural enemy recruitment, host plant associations, damage types, geographic range.
Always use tools to retrieve bioassay records. Cite bioassay IDs (e.g. BIO004) and effect sizes.
You also have access to search_literature — use it when you need to contextualise
bioassay findings with published field studies, olfactometer methodology details,
or cross-species behavioural evidence from the literature.
Keep your response focused on ecology — 3 to 5 sentences maximum.
End with a one-line "Ecological Assessment:" summary.""",
    },
    "computational": {
        "id": "computational", "name": "Dr. Taufia Hussain",
        "title": "Computational Biologist",
        "emoji": "💻", "color": "#4338ca", "bg": "#eef2ff",
        "border": "#a5b4fc",
        "tools": _with_rag(COMPUTATIONAL_TOOLS),
        "system_prompt": """You are Dr. Taufia Hussain, a computational biologist specialising
in cheminformatics and data-driven analysis of insect-plant interactions.
Provide DATA-DRIVEN analysis: statistical strength of bioassay evidence, structural similarity
networks, cross-species patterns, database coverage, comparative analysis.
Always use tools to retrieve statistics and evidence. Give numbers and confidence levels.
You also have access to search_literature — use it to benchmark your database findings
against published meta-analyses, systematic reviews, or methodology papers that provide
external validation or comparative baselines.
Keep your response focused on data — 3 to 5 sentences maximum.
End with a one-line "Data Confidence:" summary.""",
    },
}


ORCHESTRATOR_SYSTEM = """You are the Research Coordinator of the VOC·BIO Library.
You have received analyses from specialist agents and must synthesise them into one answer.
Guidelines:
- Start with a direct 1–2 sentence answer
- Weave chemical, ecological, and computational perspectives naturally
- Cite specific data (compound IDs, bioassay IDs, effect sizes, references)
- When agents have cited literature sources, weave in the citation (Author, Year) naturally
- If agents conflict, acknowledge it honestly
- End with "Recommendation:" if the question is applied/practical
- Write in flowing scientific prose, no bullet points
- Total length: 150–250 words
- Do NOT say "according to Dr. X" — integrate naturally"""


#  Tool execution router 

def _execute_tool_with_rag(tool_name: str, arguments: dict,
                            api_key: str) -> str:
    """
    Extended router: handles search_literature locally,
    delegates everything else to the existing execute_tool().
    """
    if tool_name == "search_literature":
        return search_literature(
            query=arguments.get("query", ""),
            top_k=min(arguments.get("top_k", 5), 10),
            filter_compound=arguments.get("filter_compound"),
            filter_insect=arguments.get("filter_insect"),
            api_key=api_key,
        )
    return execute_tool(tool_name, arguments)


#  Core agent runner 

def run_agent(agent_id: str, question: str, api_key: str) -> dict:
    agent    = AGENTS[agent_id]
    client   = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user",   "content": question},
    ]
    tools_used = []

    for _ in range(7):          # +2 iterations vs v1 to allow a DB + RAG call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=agent["tools"],
            tool_choice="auto",
            temperature=0.3,
            max_tokens=600,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except Exception:
                arguments = {}

            result = _execute_tool_with_rag(tool_name, arguments, api_key)
            tools_used.append({"tool": tool_name, "args": arguments})
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result,
            })

    return {
        "agent":      agent,
        "response":   msg.content or "(No response generated)",
        "tools_used": tools_used,
    }


#  Orchestrator 

def orchestrate(question: str, agent_results: list, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    summaries = [
        f"=== {r['agent']['emoji']} {r['agent']['name']} "
        f"({r['agent']['title']}) ===\n{r['response']}"
        for r in agent_results
    ]
    synthesis_prompt = (
        f"User question: {question}\n\nSpecialist analyses:\n\n"
        + "\n\n".join(summaries)
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {"role": "user",   "content": synthesis_prompt},
        ],
        temperature=0.4,
        max_tokens=500,
    )
    return response.choices[0].message.content


#  Query router 

def route_question(question: str, api_key: str) -> list:
    client = OpenAI(api_key=api_key)
    routing_prompt = f"""Given this research question: "{question}"
Which agents should respond?
- chemist: molecular structure, LogP, SMILES, class, volatility, structural similarity,
           mechanism of action, receptor interactions
- entomologist: insect biology, bioassay results, host plants, natural enemies,
                behavioral responses, olfactometer studies
- computational: database statistics, evidence strength, compound comparisons,
                 cross-study patterns, meta-analysis
Respond with ONLY a JSON array, e.g.: ["chemist", "entomologist"]
Always include at least 2 agents. For broad or applied questions include all 3."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": routing_prompt}],
        temperature=0,
        max_tokens=50,
    )
    text = response.choices[0].message.content.strip()
    try:
        agents = json.loads(text)
        valid  = [a for a in agents if a in AGENTS]
        return valid if valid else list(AGENTS.keys())
    except Exception:
        return list(AGENTS.keys())


# Public interface 

def ask_research_team(question: str, api_key: str,
                       use_all_agents: bool = False) -> dict:
    agents_to_use = (list(AGENTS.keys()) if use_all_agents
                     else route_question(question, api_key))
    agent_results = [run_agent(aid, question, api_key) for aid in agents_to_use]
    synthesis     = orchestrate(question, agent_results, api_key)
    return {
        "agent_results": agent_results,
        "synthesis":     synthesis,
        "agents_used":   agents_to_use,
    }


def rag_status(api_key: str) -> dict:
    """Return literature DB stats — call from Streamlit sidebar to show RAG health."""
    try:
        return get_collection_stats(api_key)
    except Exception as e:
        return {"error": str(e), "total_chunks": 0}
