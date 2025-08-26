#imorting pandas for handling file and os for directory
#importing emojis for printing
import pandas as pd
import os


#reading excel
df=pd.read_excel('input_Make Groups.xlsx')

#drop unknown columns
df=df.drop(columns="Unnamed: 3")
df=df.drop(columns="Unique")
#seeing the structure
df.head(7)

#extracting branch name from roll no and creating a new column Branch with their respective branch
df["Branch"]=df["Roll"].str[4:6]


#directory where i want to save the csv files
directory = "/home/rahul/Desktop/New Drive/DAA assignment/a1Solution_2511MC10_RahulRay/BranchWiseFullList" 

#saving branch wise csv file using groupby
for name,group in df.groupby("Branch"):
  filename=f"Group{name}.csv"
  file_path = os.path.join(directory, filename)
  print(f"Group{name}.csv is created.🔥")
 
  group.to_csv(file_path)
  

 
