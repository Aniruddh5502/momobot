import pandas as pd
import os
import sys

def get_csv_metadata(file_path):
    """
    Extracts metadata from a CSV file without loading the full raw data.
    """
    try:
        # Read only the first row to get column names
        df_head = pd.read_csv(file_path, nrows=0)
        columns = df_head.columns.tolist()
        
        # Get file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Count rows using a fast method (not loading the whole df)
        with open(file_path, 'r', encoding='utf-8') as f:
            row_count = sum(1 for line in f) - 1 # Subtract header
            
        metadata = {
            "File Name": os.path.basename(file_path),
            "Row Count": row_count,
            "Column Count": len(columns),
            "Column Names": columns,
            "File Size (MB)": f"{file_size_mb:.4f}",
            "Data Dimensions": f"{row_count} x {len(columns)}"
        }
        return metadata
    except Exception as e:
        return {"Error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide the path to the CSV file.")
        print("Usage: python inspect_csv_metadata.py <path_to_csv>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found at {csv_path}")
        sys.exit(1)

    meta = get_csv_metadata(csv_path)
    
    print("\n--- Dataset Metadata ---")
    for key, value in meta.items():
        if key != "Column Names":
            print(f"{key}: {value}")
        else:
            print(f"{key}: {', '.join(value)}")
    print("------------------------\n")
