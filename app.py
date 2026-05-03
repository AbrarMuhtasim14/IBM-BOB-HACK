# -*- coding: utf-8 -*-
"""
SmartShift - AI Warehouse Workforce Optimizer
Main Streamlit application for the SmartShift system.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="SmartShift - AI Workforce Optimizer",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .recommendation-card {
        background-color: #e8f4f8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
    .diagnostics-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_system():
    """Initialize the SmartShift system components."""
    if 'initialized' not in st.session_state:
        with st.spinner("⚙️ Initializing SmartShift system..."):
            try:
                from config.settings import get_settings
                from data.loader import WorkerDataLoader
                from embeddings.skill_embedder import get_embedder
                from rag.vector_store import get_vector_store
                from rag.retriever import WorkerRetriever
                from rag.query_builder import QueryBuilder
                from agents.crew_setup import create_smartshift_crew
                from api.service import SmartShiftService

                # Load settings
                settings = get_settings()

                # Initialize data loader
                data_loader = WorkerDataLoader(settings.workers_csv_path)
                workers = data_loader.load_workers()

                # Initialize embedder
                embedder = get_embedder(settings.embedding_model)

                # Generate embeddings
                worker_profiles = embedder.embed_worker_profiles(workers)

                # Initialize vector store
                vector_store = get_vector_store(
                    settings.faiss_persist_dir,
                    settings.faiss_collection_name
                )

                # Index workers
                vector_store.index_workers(worker_profiles)

                # Initialize retriever
                retriever = WorkerRetriever(vector_store, embedder)

                # Initialize query builder
                query_builder = QueryBuilder()

                # Initialize crew
                crew = create_smartshift_crew(retriever, data_loader, embedder)

                # Initialize service
                service = SmartShiftService(data_loader, crew, query_builder)

                # Store in session state
                st.session_state.service = service
                st.session_state.data_loader = data_loader
                st.session_state.initialized = True

                logger.info("SmartShift system initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Error initializing system: {e}")
                st.error(f"❌ Failed to initialize system: {str(e)}")
                return False

    return True


def display_header():
    """Display the application header."""
    st.markdown(
        '<div class="main-header">🏭 SmartShift - AI Workforce Optimizer</div>',
        unsafe_allow_html=True
    )

    # Check if LLM is configured
    try:
        from config.settings import get_settings
        settings = get_settings()
        if not settings.validate_watsonx_credentials():
            st.warning(
                "⚠️ **IBM watsonx.ai LLM not configured.** "
                "The system is running in rule-based mode. "
                "Configure WATSONX_API_KEY and WATSONX_PROJECT_ID "
                "in .env for full AI capabilities.",
                icon="⚠️"
            )
            st.markdown("**Running in Rule-Based Mode** (Limited AI features)")
        else:
            st.success(
                "✅ IBM watsonx.ai connected - "
                "Full AI capabilities enabled"
            )
            st.markdown(
                "**Intelligent shift recommendations powered by "
                "IBM Granite AI**"
            )
    except Exception:
        st.markdown(
            "**Intelligent shift recommendations powered by IBM Granite AI**"
        )

    st.markdown("---")


def display_worker_registry():
    """Display the current worker registry."""
    st.markdown(
        '<div class="sub-header">📋 Current Worker Registry</div>',
        unsafe_allow_html=True
    )

    try:
        service = st.session_state.service
        workers = service.get_all_workers()

        if workers:
            # Convert to DataFrame
            df = pd.DataFrame(workers)

            # Reorder columns
            columns = [
                'worker_id', 'name', 'primary_skill',
                'current_zone', 'shift', 'load_status', 'available'
            ]
            df = df[columns]

            # Rename columns for display
            df.columns = [
                'ID', 'Name', 'Primary Skill',
                'Zone', 'Shift', 'Load', 'Available'
            ]

            # Color code load status
            def color_load(val):
                if val == 'Low':
                    return 'background-color: #d4edda'
                elif val == 'Medium':
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'

            styled_df = df.style.map(color_load, subset=['Load'])
            st.dataframe(styled_df, use_container_width=True, height=400)

            # Display zone statistics
            col1, col2, col3, col4 = st.columns(4)
            zone_stats = service.get_zone_statistics()

            for col, (zone, stats) in zip(
                [col1, col2, col3, col4], zone_stats.items()
            ):
                with col:
                    st.metric(
                        label=zone,
                        value=f"{stats['total_workers']} workers",
                        delta=f"{stats['average_load']}% avg load"
                    )
        else:
            st.warning("No workers found in the system.")

    except Exception as e:
        logger.error(f"Error displaying worker registry: {e}")
        st.error(f"Error loading worker data: {str(e)}")


def display_overload_input():
    """Display the overload situation input form."""
    st.markdown(
        '<div class="sub-header">🚨 Report Overload Situation</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    Describe the overload situation in natural language. Include:
    - Which zone is overloaded
    - What skill is needed
    - (Optional) Shift timing

    **Examples:**
    - "Zone A dispatch is overloaded, need forklift help"
    - "Zone C needs packing specialist for afternoon shift"
    - "Urgent: Zone B quality control overloaded"
    """)

    # Input form
    with st.form("overload_form"):
        description = st.text_area(
            "Describe the situation:",
            placeholder="e.g., Zone A forklift station is overloaded, need help",
            height=100
        )

        submitted = st.form_submit_button(
            "🔍 Get AI Recommendation",
            use_container_width=True
        )

        if submitted and description:
            with st.spinner("🤖 AI is analyzing the situation..."):
                try:
                    service = st.session_state.service
                    result = service.process_overload_request(description)

                    # Store result in session state
                    st.session_state.last_result = result
                    st.rerun()

                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    st.error(f"Error: {str(e)}")


def display_diagnostics(result: dict):
    """
    Display diagnostics panel showing which components were used.

    Args:
        result: The result dictionary from process_overload_request
    """
    diag = result.get('diagnostics')
    if not diag:
        return

    with st.expander("🔍 System Diagnostics - What ran this query?"):

        st.markdown("##### Component Status for This Query")

        col1, col2 = st.columns(2)

        with col1:
            # LLM Status
            st.markdown("**🤖 LLM (watsonx.ai)**")
            if diag.get('llm_used'):
                st.success(f"✅ Called: `{diag.get('llm_model', 'unknown')}`")
            else:
                st.warning("⚠️ Not used — running in fallback mode")

            # Execution path
            st.markdown("**⚙️ Execution Path**")
            path = diag.get('execution_path', 'unknown')
            if path == 'crewai':
                st.success("✅ CrewAI + IBM Granite LLM")
            else:
                st.info("ℹ️ Rule-based fallback (no LLM)")

            # watsonx credentials
            st.markdown("**🔑 watsonx.ai Credentials**")
            if diag.get('watsonx_configured'):
                st.success("✅ Configured in .env")
            else:
                st.warning(
                    "⚠️ Not configured → add WATSONX_API_KEY "
                    "and WATSONX_PROJECT_ID to .env"
                )

        with col2:
            # Vector Store
            st.markdown("**🗄️ Vector Store (FAISS)**")
            if diag.get('vector_store_used'):
                backend = diag.get('vector_store_backend', 'unknown')
                workers_indexed = diag.get('vector_store_workers_indexed', 0)
                st.success(f"✅ Used — backend: `{backend}`")
                st.caption(f"Workers indexed: **{workers_indexed}**")
            else:
                st.error("❌ Vector store not used")

            # Embedding Model
            st.markdown("**📐 Embedding Model**")
            embed_model = diag.get('embedding_model', 'unknown')
            st.success(f"✅ Active: `{embed_model}`")

        # Parsed query section
        st.markdown("---")
        st.markdown("**📝 Parsed Query (what the system understood)**")
        parsed = result.get('parsed_query', {})
        if parsed:
            pcol1, pcol2, pcol3 = st.columns(3)
            with pcol1:
                st.metric("Zone Detected", parsed.get('zone') or 'None')
            with pcol2:
                st.metric("Skill Detected", parsed.get('skill') or 'None')
            with pcol3:
                st.metric("Shift Detected", parsed.get('shift') or 'Any')


def display_recommendation():
    """Display the AI recommendation."""
    if 'last_result' not in st.session_state:
        return

    result = st.session_state.last_result

    st.markdown(
        '<div class="sub-header">💡 AI Recommendation</div>',
        unsafe_allow_html=True
    )

    if result.get('success'):
        recommendation = result.get('recommendation')

        if recommendation:
            st.markdown(
                '<div class="recommendation-card">',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### 👤 {recommendation['worker_name']}")
                st.markdown(f"**Worker ID:** {recommendation['worker_id']}")
                st.markdown(
                    f"**Move:** {recommendation['from_zone']} → "
                    f"{recommendation['to_zone']}"
                )
                st.markdown(
                    f"**Skill Match:** {recommendation['skill_match']} "
                    f"({recommendation['match_type']})"
                )
                st.markdown(
                    f"**Confidence:** "
                    f"{recommendation['confidence_score']:.0%}"
                )

            with col2:
                if st.button(
                    "✅ Confirm Shift",
                    use_container_width=True,
                    type="primary"
                ):
                    confirm_shift(recommendation)

            st.markdown("---")
            st.markdown("**🧠 AI Reasoning:**")
            st.markdown(result.get('reasoning', 'No reasoning provided'))

            # Load impact
            if 'load_impact' in recommendation:
                st.markdown("---")
                st.markdown("**📊 Load Impact Analysis:**")
                impact = recommendation['load_impact']

                lcol1, lcol2 = st.columns(2)
                with lcol1:
                    st.metric(
                        label=impact.get('from_zone', 'Source Zone'),
                        value=f"{impact.get('from_zone_new_load', 0)}%",
                        delta=f"{impact.get('from_zone_change', 0):+.1f}%"
                    )
                with lcol2:
                    st.metric(
                        label=impact.get('to_zone', 'Target Zone'),
                        value=f"{impact.get('to_zone_new_load', 0)}%",
                        delta=f"{impact.get('to_zone_change', 0):+.1f}%"
                    )

            st.markdown('</div>', unsafe_allow_html=True)

            # Alternative candidates
            if result.get('all_candidates'):
                with st.expander("👥 View Alternative Candidates"):
                    for i, candidate in enumerate(
                        result['all_candidates'][:3], 1
                    ):
                        st.markdown(
                            f"**{i}. {candidate['name']}** "
                            f"({candidate['worker_id']})"
                        )
                        st.markdown(
                            f"&nbsp;&nbsp;- Zone: {candidate['current_zone']}"
                            f", Load: {candidate['load_status']}"
                        )
                        st.markdown(
                            f"&nbsp;&nbsp;- Match Score: "
                            f"{candidate.get('match_score', 0):.2f}"
                        )

            # ── DIAGNOSTICS PANEL ─────────────────────────────────────
            display_diagnostics(result)
            # ─────────────────────────────────────────────────────────

    else:
        st.markdown(
            '<div class="error-message">',
            unsafe_allow_html=True
        )
        st.markdown(f"**❌ Error:** {result.get('error', 'Unknown error')}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Still show diagnostics even on error
        display_diagnostics(result)


def confirm_shift(recommendation):
    """Confirm and execute a shift change."""
    try:
        service = st.session_state.service
        result = service.confirm_shift_change(
            worker_id=recommendation['worker_id'],
            from_zone=recommendation['from_zone'],
            to_zone=recommendation['to_zone'],
            confirmed_by="Manager"
        )

        if result['success']:
            st.success(f"✅ {result['message']}")
            del st.session_state.last_result
            st.rerun()
        else:
            st.error(f"❌ {result['message']}")

    except Exception as e:
        logger.error(f"Error confirming shift: {e}")
        st.error(f"Error: {str(e)}")


def display_sidebar():
    """Display the sidebar with system information."""
    with st.sidebar:
        st.markdown("### 🖥️ System Information")

        try:
            service = st.session_state.service
            health = service.get_health_status()

            status_color = "🟢" if health['status'] == 'healthy' else "🟡"
            st.markdown(
                f"{status_color} **Status:** {health['status'].title()}"
            )
            st.markdown(f"**Version:** {health['version']}")

            st.markdown("---")
            st.markdown("### 🔧 Components")
            for component, status in health['components'].items():
                icon = "✅" if status == 'healthy' else "⚠️"
                st.markdown(
                    f"{icon} {component.replace('_', ' ').title()}: "
                    f"{status}"
                )

            st.markdown("---")
            st.markdown("### ℹ️ About")
            st.markdown("""
SmartShift uses AI to optimize warehouse workforce
allocation in real-time.

**Powered by:**
- IBM Granite LLM (watsonx.ai)
- CrewAI Agents
- FAISS Vector Search
- Sentence Transformers
            """)

            st.markdown("---")
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        except Exception as e:
            st.error(f"Error loading system info: {str(e)}")


def main():
    """Main application function."""
    # Initialize system
    if not initialize_system():
        st.stop()

    # Display sidebar
    display_sidebar()

    # Display main content
    display_header()

    # Worker registry
    display_worker_registry()

    st.markdown("---")

    # Overload input
    display_overload_input()

    # Recommendation (if available)
    display_recommendation()

    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #7f8c8d; padding: 1rem;">'
        '❤️ Built with IBM Bob IDE | IBM Dev Day Hackathon 2026'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

# Made with Bob