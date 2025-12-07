import streamlit as st
import pandas as pd
import logging
from io import BytesIO

import os
import logging

# Ensure the 'logs' directory exists
log_dir = '/Users/rahulray/Downloads/Mtech1stSem/Algorithm/Assignment and project/btp_allocation_app/logs'
os.makedirs(log_dir, exist_ok=True)  # This will create the folder if it doesn't exist

# Set up logging
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Logging is set up successfully.")

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

st.set_page_config(page_title="BTP/MTP Allocation System", layout="wide")
st.title("🎓 BTP/MTP Faculty Allocation System")

uploaded_file = st.file_uploader("📂 Upload Input CSV (input_btp_mtp_allocation.csv)", type=["csv"])

def process_allocation(input_df):
    try:
        cols = list(input_df.columns)
        cgpa_index = cols.index("CGPA")
        faculty_cols = cols[cgpa_index + 1:]
        n_faculties = len(faculty_cols)
        st.info(f"Detected {n_faculties} faculties: {', '.join(faculty_cols)}")
        students = input_df.sort_values(by="CGPA", ascending=False).reset_index(drop=True)
        allocations = []
        for i, row in students.iterrows():
            cycle_pref_index = i % n_faculties + 1
            allocated_fac = None
            for fac in faculty_cols:
                if row[fac] == cycle_pref_index:
                    allocated_fac = fac
                    break
            if not allocated_fac:
                allocated_fac = faculty_cols[i % n_faculties]
            allocations.append(allocated_fac)
        output_df = students[["Roll", "Name", "Email", "CGPA"]].copy()
        output_df["Allocated"] = allocations
        pref_counts = pd.DataFrame({"Fac": faculty_cols})
        for pref_rank in range(1, n_faculties + 1):
            pref_counts[f"Count Pref {pref_rank}"] = [
                (input_df[fac] == pref_rank).sum() for fac in faculty_cols
            ]
        return output_df, pref_counts
    except Exception as e:
        logger.error("Error during allocation processing", exc_info=True)
        st.error(f"❌ Error during allocation: {e}")
        return None, None

def convert_df_to_csv_bytes(df):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer

if uploaded_file is not None:
    try:
        input_df = pd.read_csv(uploaded_file)
        st.success("✅ File uploaded successfully!")
        output_df, fac_pref_df = process_allocation(input_df)
        if output_df is not None:
            st.subheader("📊 Allocation Preview")
            st.dataframe(output_df.head())
            st.subheader("📈 Faculty Preference Summary")
            st.dataframe(fac_pref_df.head())
            st.download_button(
                label="⬇️ Download Allocation CSV",
                data=convert_df_to_csv_bytes(output_df),
                file_name="output_btp_mtp_allocation.csv",
                mime="text/csv"
            )
            st.download_button(
                label="⬇️ Download Faculty Preference Count CSV",
                data=convert_df_to_csv_bytes(fac_pref_df),
                file_name="fac_preference_count.csv",
                mime="text/csv"
            )
    except Exception as e:
        logger.error("Error while reading uploaded file", exc_info=True)
        st.error(f"❌ Failed to process uploaded file: {e}")
#to run streamlit you can do python3 -m streamlit run app.py
#to stop server control +c
#