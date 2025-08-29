
# Student Grouping Tool

This project provides a **Streamlit-based tool** for grouping students from a dataset (CSV/Excel). 
The tool generates groups based on different methods and saves the results in the `output` folder.

## Features
- **BranchWiseFullList** → Splits students into groups by their branch code.
- **BranchWiseMix** → Distributes students from different branches evenly across groups.
- **UniformMix** → Creates uniformly distributed groups across all departments.

Each method also generates CSV output files and statistics (where applicable).

---




---

## How to Run

1. Clone this repository or download the code.
2. ##locate to tut_01 folder first then to download libraries
   ##```bash
   pip install -r requirements.txt
   ```
3. Start the Streamlit app:

```bash
streamlit run tut_01.py
```

4. A browser window will open automatically. If not, go to:
   [http://localhost:8501](http://localhost:8501)

---

## Usage

1. Upload your dataset (CSV/Excel).
   - Make sure the file has a **Roll** column, since groups are based on Roll numbers.
2. Choose the grouping method:
   - `BranchWiseFullList`
   - `BranchWiseMixList` (requires number of groups)
   - `UniformMixList` (requires number of groups)
3. Click **Process**.
4. Download the generated group files and statistics from the app.
5. Output CSV files will also be saved in the `output` folder.

---

## Example File Structure

```
project/
│── tut_01.py
│── requirements.txt
│── README.txt
│── output/
│     ├── GroupXX.csv
│     ├── group_1.csv
│     ├── statsUNI.csv
│     └── BranchMixstats.csv
```

---

## Notes
- Ensure that the `Roll` column contains student roll numbers where branch code is located in positions `[4:6]`.
- The output folder is automatically created if it doesn’t exist.


