import json
import re
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from llm.provider import BaseLLMProvider
from sql_engine.executor import SQLExecutor
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger("ai_sql_generator.analytics")

class AnalystState(TypedDict):
    question: str
    schema_context: str
    plan: List[Dict[str, Any]]
    execution_results: List[Dict[str, Any]]
    final_report: str
    error: Optional[str]

class AIDataAnalystAgent:
    """Autonomous agent powered by LangGraph to plan, execute, and analyze multi-step SQL queries."""

    def __init__(self, llm_provider: BaseLLMProvider, db_engine: Engine):
        self.llm_provider = llm_provider
        self.executor = SQLExecutor(db_engine)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Constructs the LangGraph state machine workflow."""
        workflow = StateGraph(AnalystState)
        
        # Define nodes
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("synthesizer", self.synthesizer_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Define transitions
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", "synthesizer")
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()

    def planner_node(self, state: AnalystState) -> Dict[str, Any]:
        """Node: Parses the user request and drafts a multi-step query plan in JSON format."""
        logger.info("Starting planning node...")
        question = state["question"]
        schema = state["schema_context"]
        
        prompt = f"""You are an expert Data Strategist. The user has asked a complex analysis question: "{question}".
Analyze the database schema below and create a multi-step SQL query plan to answer this question.
You should break the question down into 1 to 3 logical SQL query steps. For example, if asked "Why did sales drop?", first fetch sales over time, then check order volumes by product category.

{schema}

You MUST output your response strictly as a JSON list of query step dictionaries. No other text.
JSON Structure:
[
  {{
    "step_number": 1,
    "description": "Short explanation of what this step retrieves",
    "sql_query": "SELECT ... "
  }}
]
"""
        try:
            response = self.llm_provider.generate(prompt, temperature=0.0)
            
            # Clean JSON out of markdown blocks if any
            clean_json = response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            plan = json.loads(clean_json)
            return {"plan": plan, "error": None}
        except Exception as e:
            logger.error(f"Planner Node Failure: {e}")
            # Fallback simple single step query planning
            fallback_plan = [{
                "step_number": 1,
                "description": f"Direct single-step retrieval for: {question}",
                "sql_query": f"-- Fallback query placeholder for: {question}"
            }]
            return {"plan": fallback_plan, "error": f"Failed to generate structured plan: {e}"}

    def executor_node(self, state: AnalystState) -> Dict[str, Any]:
        """Node: Runs each query from the plan securely and logs results."""
        logger.info("Starting execution node...")
        plan = state.get("plan", [])
        results = []
        
        for step in plan:
            desc = step.get("description", "")
            sql = step.get("sql_query", "")
            step_num = step.get("step_number", 1)
            
            logger.info(f"Executing step {step_num}: {desc}")
            
            # Execute query safely
            exec_result = self.executor.execute(sql)
            
            if exec_result.success and exec_result.data is not None:
                # Convert DataFrame to Markdown table for LLM parsing in synthesis
                df = exec_result.data
                # Limit row output size to avoid flooding LLM context
                md_table = df.head(15).to_markdown(index=False)
                results.append({
                    "step_number": step_num,
                    "description": desc,
                    "sql_query": sql,
                    "success": True,
                    "row_count": exec_result.row_count,
                    "data_summary": md_table
                })
            else:
                results.append({
                    "step_number": step_num,
                    "description": desc,
                    "sql_query": sql,
                    "success": False,
                    "error_message": exec_result.error_message or "Unknown execution error"
                })
                
        return {"execution_results": results}

    def synthesizer_node(self, state: AnalystState) -> Dict[str, Any]:
        """Node: Examines raw table outputs and writes a detailed markdown insights summary report."""
        logger.info("Starting synthesis node...")
        question = state["question"]
        results = state.get("execution_results", [])
        
        # Compile execution outputs
        data_narrative = []
        for res in results:
            data_narrative.append(f"### Step {res['step_number']}: {res['description']}")
            data_narrative.append(f"**SQL Executed:**\n```sql\n{res['sql_query']}\n```")
            if res.get("success"):
                data_narrative.append(f"**Rows Returned:** {res['row_count']}")
                data_narrative.append(f"**Data Sample:**\n{res['data_summary']}\n")
            else:
                data_narrative.append(f"❌ **Execution Failed:** {res.get('error_message')}\n")
                
        runs_summary = "\n".join(data_narrative)
        
        prompt = f"""You are a Principal AI Data Analyst. You have run a sequence of queries to answer this question: "{question}".

Below are the details and outputs of the query steps:
{runs_summary}

Please synthesize these findings into a professional Data Analyst Executive Report.
Your report MUST cover:
1. **Executive Summary**: Core answer to the question.
2. **Detailed Analysis**: Breakdown of what the tables represent, highlighting key trends, numbers, and correlations.
3. **Data Insight/Recommendation**: Actionable recommendations based on the data findings.

Write in a clear, persuasive, business-consulting style. Use markdown headers, lists, and tables. Keep it concise but highly valuable.
"""
        try:
            report = self.llm_provider.generate(prompt, temperature=0.2)
            return {"final_report": report}
        except Exception as e:
            logger.error(f"Synthesizer Node Failure: {e}")
            return {"final_report": f"### Synthesis Error\nFailed to compile analyst report: {e}"}

    def run_analysis(self, question: str, schema_context: str) -> Dict[str, Any]:
        """Runs the compiled LangGraph workflow."""
        initial_state: AnalystState = {
            "question": question,
            "schema_context": schema_context,
            "plan": [],
            "execution_results": [],
            "final_report": "",
            "error": None
        }
        return self.workflow.invoke(initial_state)
