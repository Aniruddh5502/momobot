import pandas as pd
import numpy as np
import json
import os
import argparse

def scale_dataset(input_path, output_path, params_path, method='minmax', columns=None):
    """
    Scales specified columns of a CSV dataset and saves scaling parameters.
    """
    try:
        df = pd.read_csv(input_path)
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        scaling_params = {}
        scaled_df = df.copy()
        
        for col in columns:
            col_data = df[col]
            
            if method == 'minmax':
                c_min = float(col_data.min())
                c_max = float(col_data.max())
                scaling_params[col] = {'min': c_min, 'max': c_max}
                
                if c_max - c_min == 0:
                    scaled_df[col] = 0.0
                else:
                    scaled_df[col] = (col_data - c_min) / (c_max - c_min)
                    
            elif method == 'standard':
                c_mean = float(col_data.mean())
                c_std = float(col_data.std())
                scaling_params[col] = {'mean': c_mean, 'std': c_std}
                
                if c_std == 0:
                    scaled_df[col] = 0.0
                else:
                    scaled_df[col] = (col_data - c_mean) / c_std
            else:
                raise ValueError(f"Unsupported scaling method: {method}")

        scaled_df.to_csv(output_path, index=False)
        
        with open(params_path, 'w') as f:
            json.dump({'method': method, 'params': scaling_params}, f, indent=4)
            
        print(f"Successfully scaled {len(columns)} columns using {method} method.")
        print(f"Data saved to: {output_path}")
        print(f"Params saved to: {params_path}")

    except Exception as e:
        print(f"Error during scaling: {e}")

def inverse_scale(input_path, params_path, output_path):
    """
    Reverses the scaling process using saved parameters.
    """
    try:
        df = pd.read_csv(input_path)
        with open(params_path, 'r') as f:
            meta = json.load(f)
        
        method = meta['method']
        params = meta['params']
        inv_df = df.copy()
        
        for col, p in params.items():
            if col in df.columns:
                if method == 'minmax':
                    inv_df[col] = df[col] * (p['max'] - p['min']) + p['min']
                elif method == 'standard':
                    inv_df[col] = df[col] * p['std'] + p['mean']
        
        inv_df.to_csv(output_path, index=False)
        print(f"Successfully inverted scaling. Saved to: {output_path}")

    except Exception as e:
        print(f"Error during inverse scaling: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CSV Scaling and Inverse Scaling Tool. By default, all output files (scaled CSV, restored CSV, and params JSON) are saved in the same directory as the input file."
    )
    
    parser.add_argument('--scale', type=str, help="Path to the input CSV for scaling")
    parser.add_argument('--method', type=str, choices=['minmax', 'standard'], default='minmax', help="Scaling method (default: minmax)")
    parser.add_argument('--output', type=str, help="Custom output path for scaled CSV. If omitted, saves as <input>_scaled.csv in the same folder.")
    parser.add_argument('--params', type=str, help="Custom output path for scaling parameters JSON. If omitted, saves as <input>_params.json in the same folder.")
    
    parser.add_argument('--Inverse_scale', type=str, help="Path to the scaled CSV for inverse scaling")
    parser.add_argument('--inv_params', type=str, help="Path to the scaling parameters JSON. If omitted, looks for <input>_params.json in the same folder.")
    parser.add_argument('--inv_output', type=str, help="Custom output path for restored CSV. If omitted, saves as <input>_restored.csv in the same folder.")

    args = parser.parse_args()

    if args.scale:
        # Automatic pathing: Save in the same directory as the input file
        base_dir = os.path.dirname(args.scale)
        file_name = os.path.basename(args.scale)
        name_no_ext = os.path.splitext(file_name)[0]
        
        out = args.output if args.output else os.path.join(base_dir, f"{name_no_ext}_scaled.csv")
        prm = args.params if args.params else os.path.join(base_dir, f"{name_no_ext}_params.json")
        
        scale_dataset(args.scale, out, prm, method=args.method)
    
    elif args.Inverse_scale:
        # Automatic pathing: Save in the same directory as the input file
        base_dir = os.path.dirname(args.Inverse_scale)
        file_name = os.path.basename(args.Inverse_scale)
        name_no_ext = os.path.splitext(file_name)[0]
        
        prm = args.inv_params if args.inv_params else os.path.join(base_dir, f"{name_no_ext.replace('_scaled', '')}_params.json")
        out = args.inv_output if args.inv_output else os.path.join(base_dir, f"{name_no_ext.replace('_scaled', '')}_restored.csv")
        
        if not os.path.exists(prm):
            print(f"Error: Params file {prm} not found. Please provide --inv_params.")
        else:
            inverse_scale(args.Inverse_scale, prm, out)
    else:
        parser.print_help()
