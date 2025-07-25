# main.py

import os
import argparse
import pandas as pd
from tqdm import tqdm

# Import our custom modules
from dose import perform_summation
from data import extract_dicom_info


def process_patient_directories(root_dir: str, output_excel_path: str):
    """
    Main function to orchestrate DICOM processing tasks.
    """
    try:
        patient_dirs = [d.path for d in os.scandir(root_dir) if d.is_dir()]
    except FileNotFoundError:
        print(f"Error: Root directory not found at '{root_dir}'")
        return

    if not patient_dirs:
        print(f"No patient directories found in '{root_dir}'.")
        return

    print(f"Found {len(patient_dirs)} patient directories. Starting processing...")

    all_patient_data = []

    for patient_dir in tqdm(patient_dirs, desc="Processing Patients", unit="patient"):
        patient_id = os.path.basename(patient_dir)
        tqdm.write(f"\n--- Processing Patient: {patient_id} ---")

        # 1. Extract DICOM information and get a list of RTDose files
        patient_data, rtdose_files = extract_dicom_info(patient_dir)
        all_patient_data.append(patient_data)

        # 2. Perform dose summation if more than one RTDose file is found
        if len(rtdose_files) > 1:
            # Pass the list of files and the patient ID to the summation script
            perform_summation(rtdose_files, patient_id)
        else:
            tqdm.write(" -> Skipping summation: Single or no RTDose file found.")

    # 3. Save all collected data to an Excel spreadsheet
    if all_patient_data:
        print("\n-------------------------------------------------")
        print(f"Saving extracted data to {output_excel_path}...")
        df = pd.DataFrame(all_patient_data)

        column_order = [
            'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID',
            'ManufacturersModelName', 'TreatmentSites',
            'RTStruct_SOPInstanceUID', 'RTDose_SOPInstanceUIDs'
        ]
        df = df[column_order]

        df.to_excel(output_excel_path, index=False, engine='openpyxl')
        print(f" Processing complete. Report saved to {output_excel_path}")
    else:
        print("No data was extracted.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A toolkit for processing DICOM RT data. It extracts metadata to Excel and performs dose summation."
    )
    parser.add_argument(
        "root_dir",
        type=str,
        help="The root directory containing patient folders (e.g., S:\\ProKnow)."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="dicom_summary.xlsx",
        help="Path for the output Excel file. Default: dicom_summary.xlsx"
    )

    args = parser.parse_args()

    process_patient_directories(args.root_dir, args.output)