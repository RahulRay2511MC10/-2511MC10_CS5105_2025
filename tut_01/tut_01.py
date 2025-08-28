import streamlit as st
import pandas as pd
import os
import math
from io import BytesIO

import streamlit as st
import webbrowser
import threading

def open_browser():
    webbrowser.open_new("http://localhost:8501")

if __name__ == "__main__":
    st.set_page_config(page_title="Student Grouping Tool")



# ========== FUNCTIONS ==========
def BranchWiseFullList(df):
    df = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    df["Branch"] = df["Roll"].astype(str).str[4:6]

    files = {}
    for name, group in df.groupby("Branch"):
        filename = f"Group{name}.csv"
        files[filename] = group.to_csv(index=False).encode("utf-8")
    return files, None


def BranchWiseMix(df, num_groups):
    df = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    df["Dept"] = df["Roll"].astype(str).str[4:6]

    dept_sequence = list(dict.fromkeys(df["Dept"]))
    dept_frames = {d: df[df["Dept"] == d].reset_index(drop=True) for d in dept_sequence}

    rows_each = math.ceil(len(df) / num_groups)
    ptr = {d: 0 for d in dept_sequence}
    grouped = [[] for _ in range(num_groups)]

    for gid in range(num_groups):
        while len(grouped[gid]) < rows_each:
            inserted = False
            for d in dept_sequence:
                if ptr[d] < len(dept_frames[d]):
                    grouped[gid].append(dept_frames[d].iloc[ptr[d]].to_dict())
                    ptr[d] += 1
                    inserted = True
                    if len(grouped[gid]) >= rows_each:
                        break
            if not inserted:
                break

    final_groups = [pd.DataFrame(g) for g in grouped if g]

    files = {}
    for i, grp in enumerate(final_groups, start=1):
        files[f"group_{i}.csv"] = grp.to_csv(index=False).encode("utf-8")

    summary = []
    for i, grp in enumerate(final_groups, start=1):
        counts = grp["Dept"].value_counts().to_dict()
        counts["Group"] = f"Group {i}"
        summary.append(counts)

    stats = pd.DataFrame(summary).fillna(0).set_index("Group")
    stats["Total"] = stats.sum(axis=1)
    stats_file = stats.to_csv().encode("utf-8")

    return files, ("BranchMixstats.csv", stats_file, stats)


def UniformMix(df, groups_count):
    df = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    df["Dept"] = df["Roll"].astype(str).str[4:6]

    dept_sizes = df["Dept"].value_counts().to_dict()
    dept_order = sorted(dept_sizes, key=lambda d: dept_sizes[d], reverse=True)
    dept_frames = {d: df[df["Dept"] == d].reset_index(drop=True) for d in dept_order}

    quotient, remainder = divmod(len(df), groups_count)
    group_sizes = [quotient + (1 if i < remainder else 0) for i in range(groups_count)]
    final_groups = [[] for _ in range(groups_count)]
    dept_pos = {d: 0 for d in dept_order}

    curr = 0
    for dept in dept_order:
        while dept_pos[dept] < len(dept_frames[dept]):
            room_left = group_sizes[curr] - len(final_groups[curr])
            remaining = len(dept_frames[dept]) - dept_pos[dept]
            take_now = min(room_left, remaining)

            slice_df = dept_frames[dept].iloc[dept_pos[dept]: dept_pos[dept] + take_now]
            final_groups[curr].extend(slice_df.to_dict(orient="records"))
            dept_pos[dept] += take_now

            if len(final_groups[curr]) == group_sizes[curr]:
                curr += 1
                if curr == groups_count:
                    break
        if curr == groups_count:
            break

    final_groups = [pd.DataFrame(g) for g in final_groups]

    files = {}
    for i, grp in enumerate(final_groups, start=1):
        files[f"group_UNI{i}.csv"] = grp.to_csv(index=False).encode("utf-8")

    dept_sequence = df["Dept"].unique().tolist()
    stats_table = pd.DataFrame(0, index=[f"Group_{i}" for i in range(1, groups_count + 1)], columns=dept_sequence)

    for i, grp in enumerate(final_groups, start=1):
        counts = grp["Dept"].value_counts()
        stats_table.loc[f"Group_{i}", counts.index] = counts.values

    stats_table["Total"] = stats_table.sum(axis=1)
    stats_file = stats_table.to_csv().encode("utf-8")

    return files, ("statsUNI.csv", stats_file, stats_table)


# ========== STREAMLIT APP ==========
st.title("🎓 Student Grouping Tool")

uploaded_file = st.file_uploader("Upload Excel/CSV file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Preview of uploaded file")
    st.dataframe(df.head())

    choice = st.radio(
        "Choose grouping method:",
        ("BranchWiseFullList", "BranchWiseMixList", "UniformMixList")
    )

    num_groups = None
    if choice in ["BranchWiseMixList", "UniformMixList"]:
        num_groups = st.number_input("Enter number of groups:", min_value=1, step=1)

    if st.button("Process"):
        if choice == "BranchWiseFullList":
            files, stats = BranchWiseFullList(df)
        elif choice == "BranchWiseMixList":
            files, stats = BranchWiseMix(df, int(num_groups))
        else:
            files, stats = UniformMix(df, int(num_groups))

        st.subheader("📥 Download Generated Files")
        for fname, fdata in files.items():
            st.download_button(
                label=f"Download {fname}",
                data=fdata,
                file_name=fname,
                mime="text/csv"
            )

        if stats:
            stats_name, stats_file, stats_df = stats
            st.subheader("📊 Statistics")
            st.dataframe(stats_df)
            st.download_button(
                label=f"Download {stats_name}",
                data=stats_file,
                file_name=stats_name,
                mime="text/csv"
            )
