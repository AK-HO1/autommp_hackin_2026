"""Streamlit UI for the CE Consolidation Pipeline."""
import streamlit as st
import subprocess, sys, os, tempfile, shutil, time
import pandas as pd

st.set_page_config(page_title="AutoMMP — CE Pipeline", page_icon="🔄", layout="wide")

# ── Styling ──
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .big-number { font-size: 2.4rem; font-weight: 700; color: #1a73e8; }
    .status-card { background: #f8f9fa; border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0; border-left: 4px solid #1a73e8; }
    .success-card { background: #e8f5e9; border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0; border-left: 4px solid #2e7d32; }
</style>
""", unsafe_allow_html=True)

CE_PIPELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ce_pipeline")

def run_pipeline(feed_path, city, out_dir, do_assort):
    """Run the CE pipeline as a subprocess and yield log lines."""
    cmd = [
        sys.executable, os.path.join(CE_PIPELINE, "run.py"),
        "--city", city,
        "--input", feed_path,
        "--out", out_dir,
        "--ce-list", os.path.join(CE_PIPELINE, "skills", "collection-builder", "sample_data_ce_list_global.csv"),
        "--inputs-dir", os.path.join(CE_PIPELINE, "inputs"),
    ]
    if do_assort:
        cmd += ["--assort", "--review-xlsx"]

    env = os.environ.copy()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, env=env, cwd=CE_PIPELINE)
    for line in proc.stdout:
        yield line.strip()
    proc.wait()
    if proc.returncode != 0:
        yield f"ERROR: pipeline exited with code {proc.returncode}"


# ── Session state ──
if "stage" not in st.session_state:
    st.session_state.stage = "upload"  # upload | processing | results
if "results" not in st.session_state:
    st.session_state.results = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 1: Upload
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if st.session_state.stage == "upload":
    st.title("🔄 AutoMMP — CE Consolidation Pipeline")
    st.markdown("Upload a supplier listings CSV and the pipeline will **categorize** experiences "
                "into Combined Entities, **assort** each CE with ranked experiences/variants, "
                "and produce an **ExperienceOS upload CSV**.")

    st.divider()

    # API key
    api_key = st.text_input("OpenAI API Key", type="password",
                            value=os.environ.get("OPENAI_API_KEY", ""),
                            help="Required for categorization (embeddings + LLM gate) and assortment")

    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", placeholder="e.g. Kyoto, Hong Kong, Singapore",
                             help="Filter the feed to this city and scope CE matching")
    with col2:
        do_assort = st.checkbox("Run assortment (LLM)", value=True,
                                help="If unchecked, stops after categorization only")

    st.divider()

    # File upload
    st.subheader("Upload Supplier Feed CSV")
    st.markdown("""
    **Required columns** (case-insensitive, aliases accepted):

    | Column | Aliases | Description |
    |--------|---------|-------------|
    | `Product ID` | `experience_id` | Unique supplier product identifier |
    | `Name` | `experience_name`, `Product Name`, `title` | Product display name |
    | `City` | `city` | City name (used for filtering) |
    | `Link` | `link` | Product URL (optional) |
    """)

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded:
        preview = pd.read_csv(uploaded)
        uploaded.seek(0)
        st.markdown(f"**Preview** — {len(preview)} rows, {len(preview.columns)} columns")
        st.dataframe(preview.head(10), use_container_width=True, height=300)

    st.divider()

    if st.button("🚀 Run Pipeline", type="primary", disabled=not uploaded or not city):
        if not api_key:
            st.error("OpenAI API key is required.")
        else:
            os.environ["OPENAI_API_KEY"] = api_key
            # Save uploaded file
            tmp_dir = tempfile.mkdtemp(prefix="ce_pipeline_")
            feed_path = os.path.join(tmp_dir, "feed.csv")
            with open(feed_path, "wb") as f:
                f.write(uploaded.read())
            st.session_state.feed_path = feed_path
            st.session_state.out_dir = os.path.join(tmp_dir, "out")
            st.session_state.city = city
            st.session_state.do_assort = do_assort
            st.session_state.stage = "processing"
            st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 2: Processing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
elif st.session_state.stage == "processing":
    st.title("⏳ Pipeline Running...")
    st.markdown(f"**City:** {st.session_state.city} &nbsp; | &nbsp; "
                f"**Assortment:** {'Yes' if st.session_state.do_assort else 'No'}")
    st.divider()

    progress_bar = st.progress(0, text="Starting pipeline...")
    log_container = st.container()
    log_lines = []

    steps = {
        "[ingest]": (10, "Ingesting and normalizing listings..."),
        "[categorize]": (50, "Categorizing experiences into CEs (LLM + embeddings)..."),
        "[group]": (65, "Grouping experiences into Combined Entities..."),
        "[assort]": (80, "Running assortment per CE (LLM)..."),
        "[output]": (95, "Writing output files..."),
    }

    for line in run_pipeline(st.session_state.feed_path, st.session_state.city,
                             st.session_state.out_dir, st.session_state.do_assort):
        log_lines.append(line)
        for tag, (pct, msg) in steps.items():
            if tag in line:
                progress_bar.progress(pct / 100, text=msg)
                break
        with log_container:
            st.code("\n".join(log_lines), language="text")

    if any("ERROR" in l for l in log_lines):
        progress_bar.progress(1.0, text="Pipeline failed.")
        st.error("Pipeline encountered an error. Check the logs above.")
        if st.button("← Back to Upload"):
            st.session_state.stage = "upload"
            st.rerun()
    else:
        progress_bar.progress(1.0, text="Done!")
        # Load results
        out = st.session_state.out_dir
        results = {}
        for fname in ["experienceos_upload.csv", "review_queue.csv", "decisions.csv",
                       "categorized_collections.csv"]:
            p = os.path.join(out, fname)
            if os.path.exists(p):
                results[fname] = pd.read_csv(p)
        xlsx_path = os.path.join(out, "assortment_review.xlsx")
        if os.path.exists(xlsx_path):
            results["_xlsx_path"] = xlsx_path

        st.session_state.results = results
        st.session_state.stage = "results"
        time.sleep(1)
        st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 3: Results
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
elif st.session_state.stage == "results":
    st.title("✅ Pipeline Results")
    st.markdown(f"**City:** {st.session_state.city}")
    st.divider()

    results = st.session_state.results

    # Summary metrics
    decisions = results.get("decisions.csv")
    upload = results.get("experienceos_upload.csv")
    review = results.get("review_queue.csv")
    grouping = results.get("categorized_collections.csv")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total = len(decisions) if decisions is not None else 0
        st.metric("Total Listings", total)
    with c2:
        if decisions is not None:
            n_ces = decisions["collection_id"].nunique() if "collection_id" in decisions.columns else 0
            st.metric("Combined Entities", n_ces)
    with c3:
        if upload is not None:
            st.metric("Auto-Listed CEs", upload["ce_name"].nunique() if "ce_name" in upload.columns else len(upload))
        else:
            st.metric("Auto-Listed CEs", 0)
    with c4:
        if review is not None:
            st.metric("Needs Review", review["ce_name"].nunique() if "ce_name" in review.columns else len(review))
        else:
            st.metric("Needs Review", 0)

    st.divider()

    # Tabs for each output
    tab_names = []
    tab_data = []

    if upload is not None and not upload.empty:
        tab_names.append("📤 ExperienceOS Upload")
        tab_data.append(("experienceos_upload.csv", upload))
    if review is not None and not review.empty:
        tab_names.append("🔍 Review Queue")
        tab_data.append(("review_queue.csv", review))
    if decisions is not None and not decisions.empty:
        tab_names.append("📋 Decisions")
        tab_data.append(("decisions.csv", decisions))
    if grouping is not None and not grouping.empty:
        tab_names.append("🗂 CE Groupings")
        tab_data.append(("categorized_collections.csv", grouping))

    if tab_names:
        tabs = st.tabs(tab_names)
        for tab, (fname, df) in zip(tabs, tab_data):
            with tab:
                st.dataframe(df, use_container_width=True, height=500)
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(f"Download {fname}", csv_data, fname, "text/csv")

    # Excel download
    if "_xlsx_path" in results:
        with open(results["_xlsx_path"], "rb") as f:
            st.download_button("📊 Download Assortment Review (Excel)",
                               f.read(), "assortment_review.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()
    if st.button("🔄 Run Another"):
        st.session_state.stage = "upload"
        st.session_state.results = {}
        st.rerun()
