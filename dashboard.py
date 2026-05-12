import streamlit as st
import pandas as pd
import altair as alt
import ast

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Microscopy Acquisition Dashboard",
    layout="wide"
)

st.title("🔬 Microscopy Acquisition Dashboard")

# Column labels (presentation only)
COLUMN_LABELS = {
    "Dose": "Dose (e/Å²)",
    "DoseOnCamera": "Dose on Camera (e/px/s)",
    "DosePerFrame": "Dose per Frame (e/Å²)",
    "PixelSpacing": "Pixel Spacing (Å)",
    "BeamSize": "Beam Size (µm)",
    "HoleSize": "Hole Size (µm)"
}

# Numeric columns to enforce
NUMERIC_COLS = [
    "PixelSpacing",
    "Dose",
    "DoseOnCamera",
    "DosePerFrame",
    "BeamSize",
    "HoleSize",
    "Magnification"
]

# ─────────────────────────────────────────────────────────────
# File upload
# ─────────────────────────────────────────────────────────────
file = st.file_uploader("Upload CSV file", type=["csv"])
if file is None:
    st.stop()

df = pd.read_csv(file)

# Normalize UNKNOWN → NA
df = df.replace("UNKNOWN", pd.NA)

# Enforce numeric types
for col in NUMERIC_COLS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Parse datetime
df["StartDateTime"] = pd.to_datetime(
    df["StartDateTime"],
    utc=True,
    errors="coerce"
)

# Drop invalid timestamps
df = df.dropna(subset=["StartDateTime"])

# ─────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# Date range filter (must use Python `date`)
min_date = df["StartDateTime"].dt.date.min()
max_date = df["StartDateTime"].dt.date.max()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date)
)

df = df[
    (df["StartDateTime"].dt.date >= date_range[0]) &
    (df["StartDateTime"].dt.date <= date_range[1])
]

# Microscope ID filter
microscopes = sorted(df["MicroscopeID"].dropna().unique())
selected_scopes = st.sidebar.multiselect(
    "Microscope ID",
    microscopes,
    default=microscopes
)

df = df[df["MicroscopeID"].isin(selected_scopes)]

# Detector filter
detectors = sorted(df["Detector"].dropna().unique())
selected_cameras = st.sidebar.multiselect(
    "Detector",
    detectors,
    default=detectors
)

df = df[df["Detector"].isin(selected_cameras)]

# ─────────────────────────────────────────────────────────────
# Helper plot functions
# ─────────────────────────────────────────────────────────────
def pie_chart(data, column):
    return (
        alt.Chart(data)
        .mark_arc()
        .encode(
            theta=alt.Theta("count():Q"),
            color=alt.Color(f"{column}:N", title=column),
            tooltip=[column, "count()"]
        )
        .properties(title=column)
    )

def hist_chart(data, column, bins=40):
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{column}:Q",
                bin=alt.Bin(maxbins=bins),
                title=COLUMN_LABELS.get(column, column)
            ),
            y=alt.Y("count():Q", title="Count"),
            tooltip=["count()"]
        )
        .properties(title=COLUMN_LABELS.get(column, column))
    )

# ─────────────────────────────────────────────────────────────
# Pie charts
# ─────────────────────────────────────────────────────────────
st.header("Pie Charts")

pie_columns = [
    "Mode",
    "Binning",
    "Number of exposures",
    "DoseFractionsOutputFormat",
    "ClusteringRadius",
    "SpotSize",
    "Magnification"
]

pie_cols = st.columns(3)

for i, col in enumerate(pie_columns):
    if col in df.columns:
        with pie_cols[i % 3]:
            st.altair_chart(
                pie_chart(df, col),
                width="stretch"
            )

# ─────────────────────────────────────────────────────────────
# Histograms
# ─────────────────────────────────────────────────────────────
st.header("Histograms")

hist_columns = [
    "PixelSpacing",
    "Dose",
    "DoseOnCamera",
    "DosePerFrame",
    "NumSubFrames",
    "BeamSize",
    "HoleSize"
]

hist_cols = st.columns(3)

for i, col in enumerate(hist_columns):
    if col in df.columns:
        with hist_cols[i % 3]:
            st.altair_chart(
                hist_chart(df, col),
                width="stretch"
            )

# ─────────────────────────────────────────────────────────────
# Defocus list histogram (flattened)
# ─────────────────────────────────────────────────────────────
st.header("Defocus Distribution")

defocus_values = []

for v in df["Defocus list"].dropna():
    try:
        parsed = ast.literal_eval(v)
        if isinstance(parsed, list):
            defocus_values.extend(parsed)
    except Exception:
        continue

if defocus_values:
    defocus_df = pd.DataFrame({"Defocus (µm)": defocus_values})

    defocus_chart = (
        alt.Chart(defocus_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Defocus (µm):Q",
                bin=alt.Bin(maxbins=50),
                title="Defocus (µm)"
            ),
            y=alt.Y("count():Q", title="Count"),
            tooltip=["count()"]
        )
    )

    st.altair_chart(defocus_chart, width="stretch")
else:
    st.info("No valid defocus data available.")

# ─────────────────────────────────────────────────────────────
# Data preview
# ─────────────────────────────────────────────────────────────
with st.expander("Preview filtered data"):
    st.dataframe(df.head(50))
    st.write("Total rows (sessions):", len(df))
