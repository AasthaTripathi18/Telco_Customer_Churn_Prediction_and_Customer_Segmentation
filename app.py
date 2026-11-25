from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Customer Churn Analysis", layout="wide")

st.title("Customer Churn and Segmentation")
st.write(
    "An interactive presentation of customer patterns, churn, and segmentation."
)

# Show the charts already saved in the repository
charts = sorted(Path(".").glob("*.png"))

if charts:
    st.subheader("Project visualizations")
    columns = st.columns(2)

    for index, chart in enumerate(charts):
        with columns[index % 2]:
            st.image(str(chart), caption=chart.stem, use_container_width=True)
else:
    st.info("No PNG charts found in the app folder.")

# Show the workbook
workbook = Path("Telco_customer_churn.xlsx")

if workbook.exists():
    st.subheader("Customer data")
    excel_file = pd.ExcelFile(workbook)
    sheet = st.selectbox("Choose a worksheet", excel_file.sheet_names)
    data = pd.read_excel(workbook, sheet_name=sheet)

    st.write(f"{len(data):,} rows · {len(data.columns)} columns")
    st.dataframe(data.head(100), use_container_width=True)
else:
    st.info("The Excel workbook was not found.")
