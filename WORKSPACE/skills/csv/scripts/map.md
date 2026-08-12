---
name: map 
description: >
    This file maps the scripts available for reuse and specific instruction sets.
---


## SCRIPTS

**inspect_csv_metadata.py** -> extracts metadata (row/col count, size, columns) from a CSV. Use this instead of reading massive files directly. 
```python
Usage: python skills/user/csv/scripts/inspect_csv.py <path_to_csv> 
```

**csv_scaling.py** -> provides MinMax and Standard scaling functions for CSV data, including inverse transformations via CLI flags.

Scaling: `python skills/user/csv/scripts/csv_scaling.py --scale <path_to_csv> [--method minmax|standard]`
Inverse Scaling: `python skills/user/csv/scripts/csv_scaling.py --Inverse_scale <path_to_csv> [--inv_params <params_json>]`