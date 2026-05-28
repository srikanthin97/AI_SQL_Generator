import os
import sys
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure local source directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Load environment variables
load_dotenv()

from database.connection import DatabaseConnectionManager, SQLiteConfig, PostgreSQLConfig
from database.schema import DatabaseSchemaExtractor
from database.history import QueryHistoryManager
from llm.provider import get_llm_provider
from sql_engine.translator import NLToSQLTranslator
from sql_engine.explainer import SQLExplainer
from sql_engine.executor import SQLExecutor
from visualization.recommender import ChartRecommender
from analytics.agent import AIDataAnalystAgent
from utils.logging_config import setup_logging

# Setup logging framework on startup
setup_logging()

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="SmartSQL | AI Query Assistant & Analyst",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design Aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background-color: #0f172a;
        color: #f1f5f9;
    }
    
    .stAppHeader {
        background: rgba(15, 23, 42, 0.6);
    }
    
    /* Elegant Title and Badges */
    .title-text {
        font-weight: 700;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    .subtitle-text {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }
    
    /* Card Layouts */
    .dashboard-card {
        background: #1e293b;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        margin-bottom: 20px;
    }
    
    .metric-container {
        display: flex;
        gap: 15px;
        margin-bottom: 15px;
    }
    
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 20px;
        flex: 1;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #38bdf8;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Custom Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #0f172a;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Variables
if "connection_manager" not in st.session_state:
    st.session_state.connection_manager = None
if "schema_context" not in st.session_state:
    st.session_state.schema_context = ""
if "schema_info" not in st.session_state:
    st.session_state.schema_info = {}
if "db_connected" not in st.session_state:
    st.session_state.db_connected = False
if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = ""
if "active_prompt" not in st.session_state:
    st.session_state.active_prompt = ""
if "query_explanation" not in st.session_state:
    st.session_state.query_explanation = ""
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None
if "analyst_report" not in st.session_state:
    st.session_state.analyst_report = ""
if "analyst_steps" not in st.session_state:
    st.session_state.analyst_steps = []

# Initialize local history manager
history_manager = QueryHistoryManager()

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.markdown("<h2 style='color:#38bdf8;'>⚙️ Connections & Config</h2>", unsafe_allow_html=True)

# LLM Configuration Selection
st.sidebar.markdown("### 🧠 LLM Settings")
llm_provider_choice = st.sidebar.selectbox("LLM Provider", ["OpenAI", "Ollama", "Gemini"], index=0)

if llm_provider_choice == "OpenAI":
    api_key_env = os.getenv("OPENAI_API_KEY", "")
    openai_key = st.sidebar.text_input("OpenAI API Key", value=api_key_env, type="password")
    openai_model = st.sidebar.text_input("Model", value="gpt-4o")
    llm_kwargs = {"api_key": openai_key, "model": openai_model}
elif llm_provider_choice == "Ollama":
    ollama_url = st.sidebar.text_input("Ollama Endpoint", value="http://localhost:11434")
    ollama_model = st.sidebar.text_input("Model", value="llama3")
    llm_kwargs = {"base_url": ollama_url, "model": ollama_model}
else:
    gemini_key_env = os.getenv("GEMINI_API_KEY", "")
    gemini_key = st.sidebar.text_input("Gemini API Key", value=gemini_key_env, type="password")
    gemini_model = st.sidebar.text_input("Model", value="gemini-2.5-flash")
    llm_kwargs = {"api_key": gemini_key, "model": gemini_model}

# Database Connection Method Choice
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ Database Settings")
db_type = st.sidebar.selectbox("Database Type", ["SQLite (File Upload)", "PostgreSQL"], index=0)

db_configured = False
config = None

if db_type == "SQLite (File Upload)":
    # Let user upload a file or use the sample database
    uploaded_file = st.sidebar.file_uploader("Upload SQLite Database (.db, .sqlite)", type=["db", "sqlite"])
    
    if uploaded_file is not None:
        # Write uploaded file to a temporary location inside project folder
        temp_db_path = f"sample_data/temp_uploaded_{uploaded_file.name}"
        os.makedirs("sample_data", exist_ok=True)
        with open(temp_db_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        config = SQLiteConfig(db_path=temp_db_path)
        db_configured = True
    else:
        # Check if default ecommerce.db exists
        default_path = "sample_data/ecommerce.db"
        if os.path.exists(default_path):
            st.sidebar.info(f"Using default sample database: `{default_path}`")
            config = SQLiteConfig(db_path=default_path)
            db_configured = True
        else:
            st.sidebar.warning("Upload an SQLite database to begin, or generate the default in Phase 1.")
else:
    # PostgreSQL Configuration
    pg_host = st.sidebar.text_input("Host", value=os.getenv("DB_HOST", "localhost"))
    pg_port = st.sidebar.number_input("Port", min_value=1, max_value=65535, value=int(os.getenv("DB_PORT", 5432)))
    pg_user = st.sidebar.text_input("Username", value=os.getenv("DB_USER", "postgres"))
    pg_password = st.sidebar.text_input("Password", value=os.getenv("DB_PASSWORD", ""), type="password")
    pg_name = st.sidebar.text_input("Database Name", value=os.getenv("DB_NAME", "postgres"))
    
    if pg_user and pg_name:
        config = PostgreSQLConfig(
            host=pg_host,
            port=pg_port,
            user=pg_user,
            password=pg_password,
            database=pg_name
        )
        db_configured = True

# Connect Database Button
if db_configured:
    if st.sidebar.button("🔌 Connect Database", use_container_width=True):
        try:
            conn_mgr = DatabaseConnectionManager(config)
            if conn_mgr.test_connection():
                st.session_state.connection_manager = conn_mgr
                st.session_state.db_connected = True
                
                # Fetch schema details immediately
                engine = conn_mgr.connect()
                extractor = DatabaseSchemaExtractor(engine)
                st.session_state.schema_info = extractor.extract_schema()
                st.session_state.schema_context = extractor.generate_llm_prompt_context(st.session_state.schema_info)
                
                st.sidebar.success("Successfully Connected!")
            else:
                st.sidebar.error("Failed to connect: Connection test failed.")
                st.session_state.db_connected = False
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
            st.session_state.db_connected = False

# Database Schema Navigator
if st.session_state.db_connected and st.session_state.schema_info:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Database Schema Navigator")
    
    tables_dict = st.session_state.schema_info.get("tables", {})
    search_query = st.sidebar.text_input("Search tables/columns", "").lower()
    
    for table_name, details in tables_dict.items():
        # Check if table matches search query
        table_matches = search_query in table_name.lower()
        matching_columns = [col for col in details["columns"] if search_query in col["name"].lower()]
        
        if search_query and not table_matches and not matching_columns:
            continue
            
        with st.sidebar.expander(f"📋 {table_name}"):
            st.markdown(f"**Primary Key(s):** {', '.join(details['primary_keys'])}")
            
            # Show columns
            st.markdown("**Columns:**")
            for col in details["columns"]:
                pk_marker = " 🔑" if col["name"] in details["primary_keys"] else ""
                col_name = col["name"]
                col_type = col["type"]
                # highlight matched search
                if search_query and search_query in col_name.lower():
                    st.markdown(f"- **{col_name}** ({col_type}){pk_marker}")
                else:
                    st.markdown(f"- {col_name} ({col_type}){pk_marker}")
            
            # Show foreign keys
            fks = details.get("foreign_keys", [])
            if fks:
                st.markdown("**Foreign Keys:**")
                for fk in fks:
                    local = ", ".join(fk["constrained_columns"])
                    ref_tbl = fk["referred_table"]
                    ref_cols = ", ".join(fk["referred_columns"])
                    st.markdown(f"- `{local} ➡️ {ref_tbl}({ref_cols})`")

# ==========================================
# MAIN DASHBOARD PANEL
# ==========================================

st.markdown("<h1 class='title-text'>🧠 SmartSQL AI Query Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>Open-source Enterprise AI SQL query generator & business metrics dashboard.</p>", unsafe_allow_html=True)

# Require Database Connection to proceed
if not st.session_state.db_connected:
    st.warning("⚠️ Please connect to a database in the sidebar to begin generating and running queries.")
    st.stop()

# Layout main application tabs
tab_ask, tab_history, tab_saved = st.tabs(["💬 Ask AI Analyst", "📜 Query History Logs", "⭐ Saved Queries"])

# ------------------------------------------
# TAB 1: ASK AI ANALYST
# ------------------------------------------
with tab_ask:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("### Ask a Question in Plain English")
    
    user_question = st.text_area(
        "Describe the data you want to retrieve:",
        placeholder="e.g., Show me the top 3 customers by total purchase volume and their signup date.",
        key="nl_input_box"
    )
    
    analyst_mode = st.checkbox(
        "Enable Autonomous AI Analyst Mode (Multi-step agent reasoning via LangGraph)", 
        value=False,
        help="Routes complex analytical questions to an autonomous workflow executing multiple queries."
    )
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        btn_label = "🧠 Run Analysis" if analyst_mode else "🔮 Generate SQL"
        generate_btn = st.button(btn_label, type="primary", use_container_width=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Generate SQL / Run Analyst logic
    if generate_btn and user_question:
        try:
            provider = get_llm_provider(llm_provider_choice, **llm_kwargs)
            
            if analyst_mode:
                with st.spinner("Initializing Autonomous Analyst workflow..."):
                    engine = st.session_state.connection_manager.connect()
                    agent = AIDataAnalystAgent(provider, engine)
                    
                    st.session_state.active_prompt = user_question
                    result = agent.run_analysis(user_question, st.session_state.schema_context)
                    
                    st.session_state.analyst_report = result.get("final_report", "")
                    st.session_state.analyst_steps = result.get("execution_results", [])
                    
                    # Reset basic generation parameters
                    st.session_state.generated_sql = ""
                    st.session_state.query_explanation = ""
                    st.session_state.execution_result = None
            else:
                with st.spinner("Analyzing schema and generating SQL query..."):
                    dialect = "postgresql" if db_type == "PostgreSQL" else "sqlite"
                    translator = NLToSQLTranslator(provider, dialect=dialect)
                    
                    st.session_state.active_prompt = user_question
                    st.session_state.generated_sql = translator.translate(
                        user_question, 
                        st.session_state.schema_context
                    )
                    
                    # Reset analyst parameters
                    st.session_state.analyst_report = ""
                    st.session_state.analyst_steps = []
                    st.session_state.query_explanation = ""
                    st.session_state.execution_result = None
                
        except Exception as e:
            st.error(f"Error executing analysis: {e}")

    # Display Generated SQL and Controls if present
    if st.session_state.generated_sql:
        st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
        st.markdown("### Generated SQL Query")
        st.code(st.session_state.generated_sql, language="sql")
        
        # Action controls for generated SQL
        btn_explain, btn_run, btn_save_fav = st.columns([2, 2, 8])
        
        with btn_explain:
            explain_trigger = st.button("📖 Explain Query", use_container_width=True)
        with btn_run:
            run_trigger = st.button("⚡ Execute Query", type="primary", use_container_width=True)
        with btn_save_fav:
            save_fav_trigger = st.button("⭐ Save Favorite", use_container_width=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Save Favorite Modal / logic
        if save_fav_trigger:
            # Simple text input prompt
            fav_name = st.text_input("Name this query:", value=f"Query for: {st.session_state.active_prompt[:30]}...")
            if st.button("Confirm Save"):
                if fav_name:
                    history_manager.save_favorite(fav_name, st.session_state.active_prompt, st.session_state.generated_sql)
                    st.success(f"Saved query '{fav_name}' to favorites!")
                else:
                    st.error("Please provide a name.")

        # Explain Query Logic
        if explain_trigger:
            try:
                with st.spinner("Generating step-by-step query explanation..."):
                    provider = get_llm_provider(llm_provider_choice, **llm_kwargs)
                    explainer = SQLExplainer(provider)
                    st.session_state.query_explanation = explainer.explain(
                        st.session_state.generated_sql,
                        st.session_state.schema_context
                    )
            except Exception as e:
                st.error(f"Error explaining query: {e}")

        # Display Explanation if exists
        if st.session_state.query_explanation:
            st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
            st.markdown("### 📘 Query Explanation")
            st.markdown(st.session_state.query_explanation)
            st.markdown("</div>", unsafe_allow_html=True)

        # Run Query Logic
        if run_trigger:
            try:
                with st.spinner("Verifying query safety and running..."):
                    engine = st.session_state.connection_manager.connect()
                    executor = SQLExecutor(engine)
                    res = executor.execute(st.session_state.generated_sql)
                    st.session_state.execution_result = res
                    
                    # Log run to history database
                    history_manager.log_query(
                        prompt=st.session_state.active_prompt,
                        sql_query=st.session_state.generated_sql,
                        success=res.success,
                        execution_time_ms=res.execution_time_ms,
                        row_count=res.row_count,
                        error_message=res.error_message
                    )
            except Exception as e:
                st.error(f"Execution system error: {e}")

        # Display Run Results if exists
        if st.session_state.execution_result is not None:
            res = st.session_state.execution_result
            
            st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
            st.markdown("### Query Execution Results")
            
            # Metric header
            st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
            
            # Success metric
            status_color = "#10b981" if res.success else "#ef4444"
            status_text = "SUCCESS" if res.success else "FAILED"
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value' style='color:{status_color};'>{status_text}</div>
                <div class='metric-label'>Status</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Latency metric
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{res.execution_time_ms} ms</div>
                <div class='metric-label'>Execution Time</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Row count metric
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{res.row_count}</div>
                <div class='metric-label'>Rows Returned</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

            if not res.success:
                st.error(f"Execution Error: {res.error_message}")
            else:
                if res.row_count == 0:
                    st.info("The query was executed successfully but returned 0 rows.")
                else:
                    df = res.data
                    
                    # Layout grid for Data Table and Chart side-by-side or stacked
                    st.markdown("#### Tabular Output")
                    st.dataframe(df, use_container_width=True)
                    
                    # CSV Export Widget
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Results CSV",
                        data=csv_data,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
                    
                    # Automated Visualization Card
                    st.markdown("---")
                    st.markdown("### 📊 Automated Visualizations")
                    
                    recommender = ChartRecommender()
                    chart_type, fig, alts = recommender.recommend_and_create_chart(df)
                    
                    if chart_type and fig:
                        st.info(f"Recommended Chart: **{chart_type.upper()}**")
                        
                        # Handle alternative visualization selection overrides
                        if alts:
                            selected_chart = st.selectbox(
                                "Override Visualization:",
                                [chart_type] + alts
                            )
                            if selected_chart != chart_type:
                                # Re-generate with alternate parameters
                                num_cols, temp_cols, cat_cols = recommender.identify_column_types(df)
                                if selected_chart == "bar" and len(df.columns) > 1:
                                    fig = px.bar(df, x=df.columns[0], y=df.columns[1], template="plotly_white")
                                elif selected_chart == "pie" and len(df.columns) > 1:
                                    fig = px.pie(df, names=df.columns[0], values=df.columns[1], template="plotly_white")
                                elif selected_chart == "line" and len(df.columns) > 1:
                                    fig = px.line(df, x=df.columns[0], y=df.columns[1], template="plotly_white")
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No visualizations could be generated automatically for this result structure (requires numeric data).")
                        
            st.markdown("</div>", unsafe_allow_html=True)

    # Display Autonomous Analyst Results if present
    if st.session_state.analyst_report:
        st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 Autonomous Analyst Executive Report")
        st.markdown(st.session_state.analyst_report)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.analyst_steps:
            with st.expander("🛠️ Show Agent Query Execution Trace"):
                for step in st.session_state.analyst_steps:
                    st.markdown(f"#### Step {step['step_number']}: {step['description']}")
                    st.code(step["sql_query"], language="sql")
                    if step.get("success"):
                        st.markdown(f"**Rows returned:** {step['row_count']}")
                        st.markdown(step["data_summary"])
                    else:
                        st.error(f"Execution Error: {step.get('error_message')}")

# ------------------------------------------
# TAB 2: QUERY HISTORY LOGS
# ------------------------------------------
with tab_history:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("### Query Execution Logs")
    
    if st.button("🧹 Clear History Logs"):
        history_manager.clear_history()
        st.success("History cleared.")
        
    history_logs = history_manager.get_recent_history(limit=30)
    
    if not history_logs:
        st.info("No query logs recorded yet.")
    else:
        for item in history_logs:
            status_symbol = "✅" if item["success"] == 1 else "❌"
            status_text = "Success" if item["success"] == 1 else "Failed"
            
            with st.expander(f"{status_symbol} {item['timestamp']} - {item['prompt'][:50]}..."):
                st.markdown(f"**Original User Prompt:** {item['prompt']}")
                st.markdown("**Generated SQL:**")
                st.code(item["sql_query"], language="sql")
                st.markdown(f"- **Status:** {status_text}")
                st.markdown(f"- **Execution Time:** {item['execution_time_ms']} ms")
                st.markdown(f"- **Rows Returned:** {item['row_count']}")
                if item["error_message"]:
                    st.markdown(f"- **Error details:** `{item['error_message']}`")
                
                # Load back to session triggers
                if st.button("Load Query to Workspace", key=f"hist_load_{item['id']}"):
                    st.session_state.active_prompt = item["prompt"]
                    st.session_state.generated_sql = item["sql_query"]
                    st.session_state.query_explanation = ""
                    st.session_state.execution_result = None
                    st.success("Loaded query back to Workspace. Switch to 'Ask AI Analyst' to view and run.")
                    
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------
# TAB 3: SAVED QUERIES
# ------------------------------------------
with tab_saved:
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("### Favorite Saved Queries")
    
    favorites = history_manager.get_favorites()
    
    if not favorites:
        st.info("No favorite queries saved yet. Generate a query and click 'Save Favorite' to store it here.")
    else:
        for fav in favorites:
            with st.expander(f"⭐ {fav['name']}"):
                st.markdown(f"**User Prompt:** {fav['prompt']}")
                st.markdown("**SQL Statement:**")
                st.code(fav["sql_query"], language="sql")
                
                btn_fav_load, btn_fav_del = st.columns([2, 10])
                with btn_fav_load:
                    if st.button("Load Workspace", key=f"fav_load_{fav['id']}"):
                        st.session_state.active_prompt = fav["prompt"]
                        st.session_state.generated_sql = fav["sql_query"]
                        st.session_state.query_explanation = ""
                        st.session_state.execution_result = None
                        st.success("Loaded query back to Workspace.")
                with btn_fav_del:
                    if st.button("Delete Favorite", key=f"fav_del_{fav['id']}"):
                        history_manager.delete_favorite(fav["id"])
                        st.success("Deleted from favorites.")
                        st.rerun()
                        
    st.markdown("</div>", unsafe_allow_html=True)
