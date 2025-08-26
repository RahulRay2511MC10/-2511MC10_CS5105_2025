import pandas as pd
import os
import math

# --- Load input sheet ---
data = pd.read_excel("input_Make Groups.xlsx")


#drop unknown columns
data=data.drop(columns="Unnamed: 3")
data=data.drop(columns="Unique")

# Extract branch code (5th–6th character of Roll)
data["Dept"] = data["Roll"].astype(str).str[4:6]

# Preserve the branch sequence as it first appeared
dept_sequence = list(dict.fromkeys(data["Dept"]))

# Create separate DataFrames per branch
dept_frames = {d: data[data["Dept"] == d].reset_index(drop=True) for d in dept_sequence}

# Ask user for number of groups
num_groups = int(input("Enter number of groups: "))

# Approximate rows per group
rows_each = math.ceil(len(data) / num_groups)

# Track how many rows used from each branch
ptr = {d: 0 for d in dept_sequence}

# Initialize groups
grouped = [[] for _ in range(num_groups)]

# Distribute students across groups
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
        if not inserted:   # no students left in any branch
            break

# Convert to DataFrames
final_groups = [pd.DataFrame(g) for g in grouped if g]

# --- Save grouped CSVs ---
save_dir = "/home/rahul/Desktop/New Drive/DAA assignment/a1Solution_2511MC10_RahulRay/BranchWiseMix"
os.makedirs(save_dir, exist_ok=True)

for i, grp in enumerate(final_groups, start=1):
    out = os.path.join(save_dir, f"group_{i}.csv")
    grp.to_csv(out, index=False)
    print(f"✅ File saved: {out} with {len(grp)} students")

# --- Collect group statistics ---
summary = []
for i, grp in enumerate(final_groups, start=1):
    counts = grp["Dept"].value_counts().to_dict()
    counts["Group"] = f"Group {i}"
    summary.append(counts)

# Create stats DataFrame
stats = pd.DataFrame(summary).fillna(0).set_index("Group")
stats["Total"] = stats.sum(axis=1)

# Save statistics
stats_path = os.path.join(save_dir, "stats.csv")
stats.to_csv(stats_path)
print(f"📊 Stats file created: {stats_path}")
