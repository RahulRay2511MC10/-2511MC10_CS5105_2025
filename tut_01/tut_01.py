def BranchWiseFullList():
    #imorting pandas for handling file and os for directory
#importing emojis for printing
 import pandas as pd
 import os


#reading excel
 df=pd.read_excel('/home/rahul/Desktop/New Drive/DAA assignment/tut_01/input/input_Make Groups.xlsx')

#drop unknown columns
 df=df.drop(columns="Unnamed: 3")
 df=df.drop(columns="Unique")
#seeing the structure
 df.head(7)

#extracting branch name from roll no and creating a new column Branch with their respective branch
 df["Branch"]=df["Roll"].str[4:6]


#directory where i want to save the csv files
 directory = "/home/rahul/Desktop/New Drive/DAA assignment/tut_01/output" 

#saving branch wise csv file using groupby
 for name,group in df.groupby("Branch"):
   filename=f"Group{name}.csv"
   file_path = os.path.join(directory, filename)
   print(f"Group{name}.csv is created.🔥")
 
   group.to_csv(file_path)
  

 

def BranchWiseMix():
  import pandas as pd
  import os
  import math

# --- Load input sheet ---
  data = pd.read_excel("/home/rahul/Desktop/New Drive/DAA assignment/tut_01/input/input_Make Groups.xlsx")


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
  save_dir = "/home/rahul/Desktop/New Drive/DAA assignment/tut_01/output"
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
  stats_path = os.path.join(save_dir, "BranchMixstats.csv")
  stats.to_csv(stats_path)
  print(f"📊 Stats file created: {stats_path}")


def UniformMix():
   import pandas as pd
   import os

# === Load Data ===
   
   students = pd.read_excel("/home/rahul/Desktop/New Drive/DAA assignment/tut_01/input/input_Make Groups.xlsx")

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
   save_path = "/home/rahul/Desktop/New Drive/DAA assignment/tut_01/output"


   for i, grp in enumerate(final_groups, start=1):
    out_file = os.path.join(save_path, f"group_UNI{i}.csv")
    grp.to_csv(out_file, index=False)
    print(f"✅ Group_UNI {i} saved with {len(grp)} students")

  

# === Stats Summary ===
   dept_sequence = students["Dept"].unique().tolist()
   stats_table = pd.DataFrame(0, index=[f"Group_{i}" for i in range(1, groups_count + 1)], columns=dept_sequence)

   for i, grp in enumerate(final_groups, start=1):
    counts = grp["Dept"].value_counts()
    stats_table.loc[f"Group_{i}", counts.index] = counts.values

   stats_table["Total"] = stats_table.sum(axis=1)

# Save stats.csv
   stats_out = os.path.join(save_path, "statsUNI.csv")
   stats_table.to_csv(stats_out)
   print(f"📊 Stats written to {stats_out}")

   


print("Which function you want to execute:")
print("type 1 for BranchWiseFullList")
print("type 2 for BranchWiseMixList")
print("type 3 for UniformMixList")
print("Enter the number: ")
a=int(input())

if(a==1):
   BranchWiseFullList()
elif(a==2):
   BranchWiseMix()
elif(a==3):
   UniformMix()      