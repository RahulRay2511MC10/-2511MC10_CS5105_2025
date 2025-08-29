import streamlit as st
import pandas as pd
import math
from pathlib import Path


# File Handling Utilities

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def save_csv(df: pd.DataFrame, filename: str) -> bytes:
    """
    Save a DataFrame both to disk and return a downloadable CSV in memory.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        filename (str): Desired output file name.

    Returns:
        bytes: Encoded CSV content for Streamlit download button.
    """
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False)
    return df.to_csv(index=False).encode("utf-8")



#  Grouping Functions

def export_branchwise(df: pd.DataFrame):
    """
    Export students into separate CSV files grouped by branch.

    Args:
        df (pd.DataFrame): Input dataset containing a 'Roll' column.

    Returns:
        dict: Mapping of filenames → CSV bytes for download.
        None: Placeholder since no stats are generated here.
    """
    cleaned = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    cleaned["branch"] = cleaned["Roll"].astype(str).str[4:6]


    results = {}
    for branch, block in cleaned.groupby("branch"):
        fname = f"branch_{branch}.csv"
        results[fname] = save_csv(block, fname)
    return results, None


def distribute_round_robin(df: pd.DataFrame, groups: int):
    """
    Interleave students from each department into a fixed number of groups.

    Logic:
        - Each department list is traversed in order.
        - Students are assigned in a round-robin fashion.
        - Groups are filled until desired size is reached.

    Args:
        df (pd.DataFrame): Input dataset with Roll numbers.
        groups (int): Number of groups to generate.

    Returns:
        dict: Generated group CSVs.
        tuple: (stats filename, stats CSV bytes, stats DataFrame)
    """
    base = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    base["dept"] = base["Roll"].astype(str).str[4:6]

    # Split into pools by department
    sequence = list(dict.fromkeys(base["dept"]))
    pools = {d: base[base["dept"] == d].reset_index(drop=True) for d in sequence}
    positions = {d: 0 for d in sequence}

    group_size = math.ceil(len(base) / groups)
    containers = [[] for _ in range(groups)]

    for g in range(groups):
        while len(containers[g]) < group_size:
            inserted = False
            for d in sequence:
                if positions[d] < len(pools[d]):
                    containers[g].append(pools[d].iloc[positions[d]].to_dict())
                    positions[d] += 1
                    inserted = True
                    if len(containers[g]) >= group_size:
                        break
            if not inserted:
                break

    # Build DataFrames for each group
    final = [pd.DataFrame(chunk) for chunk in containers if chunk]

    files = {}
    for i, gdf in enumerate(final, 1):
        fname = f"mix_group_{i}.csv"
        files[fname] = save_csv(gdf, fname)

    # Create department count stats
    summary = []
    for i, gdf in enumerate(final, 1):
        counts = gdf["dept"].value_counts().to_dict()
        counts["Group"] = f"G{i}"
        summary.append(counts)

    stats = pd.DataFrame(summary).fillna(0).set_index("Group")
    stats["Total"] = stats.sum(axis=1)

    stats_name = "round_robin_stats.csv"
    stats_bytes = save_csv(stats.reset_index(), stats_name)
    return files, (stats_name, stats_bytes, stats)


def balanced_split(df: pd.DataFrame, groups: int):
    """
    Distribute students across groups such that sizes are as balanced as possible.

    Method:
        - Sort departments by size.
        - Allocate slices of each department to groups sequentially.
        - Ensure remainder distribution keeps groups balanced.

    Args:
        df (pd.DataFrame): Dataset with Roll numbers.
        groups (int): Number of groups.

    Returns:
        dict: Generated CSVs for each group.
        tuple: (stats filename, stats CSV bytes, stats DataFrame)
    """
    data = df.drop(columns=["Unnamed: 3", "Unique"], errors="ignore")
    data["dept"] = data["Roll"].astype(str).str[4:6]

    # Organize departments
    counts = data["dept"].value_counts().to_dict()
    ordered = sorted(counts, key=counts.get, reverse=True)
    pools = {d: data[data["dept"] == d].reset_index(drop=True) for d in ordered}
    pointers = {d: 0 for d in ordered}

    # Pre-compute group sizes
    q, r = divmod(len(data), groups)
    group_sizes = [q + (1 if i < r else 0) for i in range(groups)]
    groups_data = [[] for _ in range(groups)]

    idx = 0
    for dept in ordered:
        while pointers[dept] < len(pools[dept]):
            available = group_sizes[idx] - len(groups_data[idx])
            remain = len(pools[dept]) - pointers[dept]
            take = min(available, remain)

            slice_df = pools[dept].iloc[pointers[dept]: pointers[dept] + take]
            groups_data[idx].extend(slice_df.to_dict(orient="records"))
            pointers[dept] += take

            if len(groups_data[idx]) == group_sizes[idx]:
                idx += 1
                if idx == groups:
                    break
        if idx == groups:
            break

    final = [pd.DataFrame(chunk) for chunk in groups_data]

    files = {}
    for i, gdf in enumerate(final, 1):
        fname = f"balanced_group_{i}.csv"
        files[fname] = save_csv(gdf, fname)

    # Build stats summary
    dept_list = data["dept"].unique().tolist()
    stats_table = pd.DataFrame(0, index=[f"G{i}" for i in range(1, groups + 1)], columns=dept_list)

    for i, gdf in enumerate(final, 1):
        counts = gdf["dept"].value_counts()
        stats_table.loc[f"G{i}", counts.index] = counts.values

    stats_table["Total"] = stats_table.sum(axis=1)

    stats_name = "balanced_stats.csv"
    stats_bytes = save_csv(stats_table.reset_index(), stats_name)
    return files, (stats_name, stats_bytes, stats_table)


# =============================
# 🚀 Streamlit Interface
# =============================
st.title("🎓 Student Grouping Tool (Refactored)")

file = st.file_uploader("Upload your CSV/Excel file", type=["csv", "xlsx"])

if file:
    # Load dataset preview
    df = pd.read_csv(file) if file.name.endswith("csv") else pd.read_excel(file)
    st.subheader("Preview")
    st.dataframe(df.head())

    # User choice of grouping method
    option = st.radio(
        "Select grouping mode:",
        ("Branch Export", "Round Robin Mix", "Balanced Split")
    )

    groups = None
    if option in ["Round Robin Mix", "Balanced Split"]:
        groups = st.number_input("Number of groups", min_value=1, step=1)

    if st.button("Generate Groups"):
        if option == "Branch Export":
            files, stats = export_branchwise(df)
        elif option == "Round Robin Mix":
            files, stats = distribute_round_robin(df, int(groups))
        else:
            files, stats = balanced_split(df, int(groups))

        # File download section
        st.subheader("📥 Download Files")
        for fname, content in files.items():
            st.download_button(
                label=f"Download {fname}",
                data=content,
                file_name=fname,
                mime="text/csv"
            )

        # Stats download section
        if stats:
            sname, sdata, sdf = stats
            st.subheader("📊 Group Statistics")
            st.dataframe(sdf)
            st.download_button(
                label=f"Download {sname}",
                data=sdata,
                file_name=sname,
                mime="text/csv"
            )
