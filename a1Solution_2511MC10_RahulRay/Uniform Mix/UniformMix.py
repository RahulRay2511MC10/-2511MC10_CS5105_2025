import pandas as pd
import os

# === Load Data ===
input_file = "input_Make Groups.xlsx"
students = pd.read_excel(input_file)

# Extract department code from Roll (5th–6th chars)
students["Dept"] = students["Roll"].astype(str).str[4:6]

# Count size of each department, sort by descending frequency
dept_sizes = students["Dept"].value_counts().to_dict()
dept_order = sorted(dept_sizes, key=lambda d: dept_sizes[d], reverse=True)

# Make department-wise sub-dataframes
dept_frames = {d: students[students["Dept"] == d].reset_index(drop=True) for d in dept_order}

# Number of groups to create
groups_count = int(input("Enter how many groups to generate: "))

# Compute fair split sizes
quotient, remainder = divmod(len(students), groups_count)
group_sizes = [quotient + (1 if i < remainder else 0) for i in range(groups_count)]

# Prepare containers
final_groups = [[] for _ in range(groups_count)]
dept_pos = {d: 0 for d in dept_order}

# === Distribution ===
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

# Convert to DataFrames
final_groups = [pd.DataFrame(g) for g in final_groups]

# === Save Groups ===
save_path = "/home/rahul/Desktop/New Drive/DAA assignment/a1Solution_2511MC10_RahulRay/Uniform Mix"


for i, grp in enumerate(final_groups, start=1):
    out_file = os.path.join(save_path, f"group_{i}.csv")
    grp.to_csv(out_file, index=False)
    print(f"✅ Group {i} saved with {len(grp)} students")

print("🎉 Groups created successfully!")

# === Stats Summary ===
dept_sequence = students["Dept"].unique().tolist()
stats_table = pd.DataFrame(0, index=[f"Group_{i}" for i in range(1, groups_count + 1)], columns=dept_sequence)

for i, grp in enumerate(final_groups, start=1):
    counts = grp["Dept"].value_counts()
    stats_table.loc[f"Group_{i}", counts.index] = counts.values

stats_table["Total"] = stats_table.sum(axis=1)

# Save stats.csv
stats_out = os.path.join(save_path, "stats.csv")
stats_table.to_csv(stats_out)
print(f"📊 Stats written to {stats_out}")
