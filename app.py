from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Telco Churn & Segmentation", page_icon="📊", layout="wide")

ROOT = Path(__file__).resolve().parent


@st.cache_data(show_spinner="Loading customer data…")
def load_workbook(path: str, modified: float) -> pd.DataFrame:
    # `modified` is included in the cache key so a replaced workbook is reloaded.
    del modified
    return pd.read_excel(path)


def find_workbook() -> Path | None:
    candidates = sorted(ROOT.glob("*.xlsx"))
    preferred = [p for p in candidates if "telco_customer_churn" in p.name.lower()]
    return (preferred or candidates or [None])[0]


def churn_mask(data: pd.DataFrame) -> pd.Series | None:
    if "Churn Label" in data:
        return data["Churn Label"].astype(str).str.strip().str.lower().eq("yes")
    if "Churn Value" in data:
        return pd.to_numeric(data["Churn Value"], errors="coerce").eq(1)
    return None


def money(value: float) -> str:
    return f"${value:,.0f}"


st.title("Telco Customer Churn & Segmentation")
st.caption("Explore churn patterns, compare customer groups, and inspect the project dataset.")

workbook = find_workbook()
if workbook is None:
    st.error("No Excel workbook was found. Place the project .xlsx dataset beside app.py and redeploy.")
    st.stop()

try:
    data = load_workbook(str(workbook), workbook.stat().st_mtime)
except Exception as exc:
    st.error(f"Could not load {workbook.name}. Check that openpyxl is installed and the workbook is valid.")
    st.exception(exc)
    st.stop()

if data.empty:
    st.error("The workbook loaded, but it contains no customer rows.")
    st.stop()

label = "Churn Label" if "Churn Label" in data else "Churn Value" if "Churn Value" in data else None
if label is None:
    st.warning("The dataset has no recognized churn column. Showing the data without churn metrics.")
else:
    if label == "Churn Value":
        data["Churn status"] = pd.to_numeric(data[label], errors="coerce").map({1: "Yes", 0: "No"})
    else:
        data["Churn status"] = data[label].astype(str)

with st.sidebar:
    st.header("Filters")
    filtered = data.copy()
    for col, title in [("Contract", "Contract"), ("Internet Service", "Internet service"), ("Payment Method", "Payment method")]:
        if col in filtered:
            options = sorted(filtered[col].dropna().astype(str).unique().tolist())
            selected = st.multiselect(title, options, default=options, key=f"filter_{col}")
            filtered = filtered[filtered[col].astype(str).isin(selected)]

if filtered.empty:
    st.warning("No customers match the selected filters.")
    st.stop()

tabs = st.tabs(["Overview", "Churn patterns", "Customer data"])

with tabs[0]:
    mask = churn_mask(filtered)
    churned = int(mask.sum()) if mask is not None else None
    total_customers = len(filtered)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Customers", f"{total_customers:,}")
    metric_cols[1].metric("Churned", f"{churned:,}" if churned is not None else "N/A")
    metric_cols[2].metric("Churn rate", f"{mask.mean():.1%}" if mask is not None and total_customers else "N/A")
    if "Monthly Charges" in filtered:
        metric_cols[3].metric("Average monthly charge", money(pd.to_numeric(filtered["Monthly Charges"], errors="coerce").mean()))
    else:
        metric_cols[3].metric("Average monthly charge", "N/A")

    left, right = st.columns(2)
    if label and "Churn status" in filtered:
        with left:
            counts = filtered["Churn status"].value_counts(dropna=False).rename_axis("Status").reset_index(name="Customers")
            fig = px.pie(counts, names="Status", values="Customers", hole=0.55, title="Customer churn")
            st.plotly_chart(fig, use_container_width=True)
    if "Contract" in filtered and mask is not None:
        with right:
            contract_rates = filtered.assign(_churn=mask).groupby("Contract", dropna=False, as_index=False)["_churn"].mean()
            contract_rates["Churn rate"] = contract_rates["_churn"] * 100
            fig = px.bar(contract_rates, x="Contract", y="Churn rate", title="Churn rate by contract", labels={"Churn rate": "Churn rate (%)"})
            st.plotly_chart(fig, use_container_width=True)

    if "CustomerID" in filtered:
        st.caption(f"Source workbook: {workbook.name} · {len(data):,} rows in total")
    if "Customer Segment" in filtered:
        st.subheader("Customer segments")
        segments = filtered["Customer Segment"].value_counts().rename_axis("Segment").reset_index(name="Customers")
        st.plotly_chart(px.bar(segments, x="Segment", y="Customers", title="Customers by segment"), use_container_width=True)
    else:
        st.info("The workbook does not contain a saved cluster label. Segmentation charts from the notebook are available below as project visuals.")
        segment_charts = [p for p in ROOT.glob("*.png") if "segmentation" in p.name.lower()]
        for chart in segment_charts:
            st.image(str(chart), caption=chart.stem, use_container_width=True)

with tabs[1]:
    st.subheader("How churn varies across customers")
    categorical = [c for c in ["Contract", "Internet Service", "Payment Method", "Tech Support", "Online Security"] if c in filtered.columns]
    numeric = [c for c in ["Tenure Months", "Monthly Charges", "Total Charges", "CLTV"] if c in filtered.columns]
    if mask is None:
        st.info("Add a 'Churn Label' or 'Churn Value' column to the workbook to see churn comparisons.")
    else:
        cols = st.columns(2)
        for index, feature in enumerate(categorical[:4]):
            rate_data = filtered.assign(_churn=mask).groupby(feature, dropna=False, as_index=False)["_churn"].mean()
            rate_data["Churn rate"] = rate_data["_churn"] * 100
            with cols[index % 2]:
                fig = px.bar(rate_data, x=feature, y="Churn rate", title=f"Churn rate by {feature.lower()}", labels={"Churn rate": "Churn rate (%)"})
                st.plotly_chart(fig, use_container_width=True)
        if numeric:
            feature = st.selectbox("Compare churn by numeric measure", numeric)
            plot_data = filtered[[feature, "Churn status"]].copy()
            plot_data[feature] = pd.to_numeric(plot_data[feature], errors="coerce")
            plot_data = plot_data.dropna()
            fig = px.box(plot_data, x="Churn status", y=feature, color="Churn status", points="outliers", title=f"{feature} by churn status")
            st.plotly_chart(fig, use_container_width=True)

    image_files = sorted(p for p in ROOT.glob("*.png") if "segmentation" not in p.name.lower())
    if image_files:
        with st.expander("Notebook charts"):
            for start in range(0, len(image_files), 2):
                cols = st.columns(2)
                for offset, chart in enumerate(image_files[start:start + 2]):
                    with cols[offset]:
                        st.image(str(chart), caption=chart.stem, use_container_width=True)

with tabs[2]:
    st.subheader("Filtered customer records")
    st.caption(f"Showing {len(filtered):,} of {len(data):,} rows. The full dataset is available to download.")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered data as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="telco_customers_filtered.csv",
        mime="text/csv",
    )
