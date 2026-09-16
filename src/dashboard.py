import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Network Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📶 Network Performance Dashboard")
st.caption(
    "Skye8 Data Science Project 3 | Lum Precious | Diagnostic Analysis"
)


# Load merged & cleaned dataset
@st.cache_data
def load_data():
    sessions = pd.read_csv("data/raw/sessions.csv")
    sites = pd.read_csv("data/raw/cell_sites.csv")
    complaints = pd.read_csv("data/raw/complaints.csv")

    # Exclude faulty site CS-0077 explicitly
    sessions = sessions[sessions["site_id"] != "CS-0077"].copy()

    # Normalize dropped column
    sessions["dropped"] = (
        sessions["dropped"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
        .astype(int)
    )

    df = sessions.merge(sites, on="site_id", how="left")
    return df, complaints


df, complaints = load_data()

# Global Sidebar Filter (Stage E Requirement)
st.sidebar.header("Controls")
regions = ["All Regions (Aggregate)"] + sorted(df["region"].dropna().unique())
selected_region = st.sidebar.selectbox("Filter by Region:", regions)

if selected_region != "All Regions (Aggregate)":
    filtered_df = df[df["region"] == selected_region]
    st.sidebar.info(f"Viewing individual region: **{selected_region}**")
else:
    filtered_df = df.copy()
    st.sidebar.warning(
        "Viewing **Aggregate Network Data** (5G looks worse due to deployment bias)"
    )

# --- VIEW 1: Drop Rate by Tech (Grouped Bar Chart) ---
st.subheader("1. Call Drop Rate by Technology")
drop_data = (
    filtered_df.groupby("technology")["dropped"].mean() * 100
).reset_index()
fig1 = px.bar(
    drop_data,
    x="technology",
    y="dropped",
    color="technology",
    text_auto=".2f",
    color_discrete_sequence=px.colors.qualitative.Set2,
    labels={"dropped": "Drop Rate (%)", "technology": "Technology"},
    title=f"Drop Rate (%) - {selected_region}",
)
st.plotly_chart(fig1, use_container_width=True)

# --- VIEW 2: Throughput Distribution (Violin Plot for Skewness) ---
st.subheader("2. Throughput Distribution (Mbps)")
fig2 = px.violin(
    filtered_df,
    x="technology",
    y="throughput_mbps",
    color="technology",
    box=True,  # Shows internal boxplot inside the violin
    points=False,
    title="Throughput Density & Distribution Shape",
)
st.plotly_chart(fig2, use_container_width=True)

# --- VIEW 3: Hourly Patterns (Line Chart) ---
st.subheader("3. Hourly Performance Patterns")
if "hour" not in filtered_df.columns:
    filtered_df["started_at"] = pd.to_datetime(
        filtered_df["started_at"], errors="coerce"
    )
    filtered_df["hour"] = filtered_df["started_at"].dt.hour

hourly = (
    filtered_df.groupby(["hour", "technology"])["dropped"].mean() * 100
).reset_index()
fig3 = px.line(
    hourly,
    x="hour",
    y="dropped",
    color="technology",
    markers=True,
    title="Hourly Drop Rate (%) Across 24 Hours",
)
st.plotly_chart(fig3, use_container_width=True)

# --- VIEW 4 & VIEW 5: Side-by-Side Section ---
col1, col2 = st.columns(2)

with col1:
    # --- VIEW 4: Site Ranking (Horizontal Bar Chart) ---
    st.subheader("4. Top 10 Sites by Highest Drop Rate")
    site_rank = (
        filtered_df.groupby(["site_id", "technology"])["dropped"]
        .agg(["mean", "count"])
        .reset_index()
    )
    site_rank["drop_pct"] = site_rank["mean"] * 100
    top_sites = (
        site_rank.sort_values(by="drop_pct", ascending=True)
        .tail(10)  # Tail for horizontal bar ascending layout
    )

    fig4 = px.bar(
        top_sites,
        x="drop_pct",
        y="site_id",
        color="technology",
        orientation="h",
        text_auto=".2f",
        title="Top 10 Worst Performing Sites",
        labels={"drop_pct": "Drop Rate (%)", "site_id": "Site ID"},
    )
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    # --- VIEW 5: Customer Complaints (Donut Chart) ---
    st.subheader("5. Customer Complaints Share")
    complaints_cat = complaints["category"].value_counts().reset_index()
    complaints_cat.columns = ["category", "count"]

    fig5 = px.pie(
        complaints_cat,
        names="category",
        values="count",
        hole=0.4,  # Creates the donut shape
        title="Complaints Share by Category",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    st.plotly_chart(fig5, use_container_width=True)
