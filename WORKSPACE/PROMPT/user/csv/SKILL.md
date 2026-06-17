---
name: csv
description: >
  Work with csv files in a modular way. This skill lists scripts that make working with csv files easier.
  Use this skill when you need to do csv cleaning, scaling, reversing scale, getting metadata of a csv file etc tasks.
  This skill lists scripts and their uses to process csv files easily. you can get header, dimention, num of rows from this skill.
---

## SCRIPTS

### **inspect_csv_metadata.py**
**inspect_csv_metadata.py** -> extracts metadata (row/col count, size, columns) from a CSV. Use this instead of reading massive files directly. 
```python
Usage: python skills/user/csv/scripts/inspect_csv.py <path_to_csv> 
```

### **csv_scaling.py**
**csv_scaling.py** -> provides MinMax and Standard scaling functions for CSV data, including inverse transformations via CLI flags.
if no output adress is given then normally all the files after processing will be saved in the same folder
Scaling: `python skills/user/csv/scripts/csv_scaling.py --scale <path_to_csv> [--method minmax|standard]`
Inverse Scaling: `python skills/user/csv/scripts/csv_scaling.py --Inverse_scale <path_to_csv> [--inv_params <params_json>]`

EX: Scaling
```bash
python skills/user/csv/scripts/csv_scaling.py --scale obsidian/Thesis/04_SINDy_ROM/dense_surrogate_dataset.csv --method minmax
```

EX: Inverting Scaling
```bash
python skills/user/csv/scripts/csv_scaling.py --Inverse_scale obsidian/Thesis/04_SINDy_ROM/dense_surrogate_dataset_scaled.csv --inv_params obsidian/Thesis/04_SINDy_ROM/dense_surrogate_dataset_params.json
```