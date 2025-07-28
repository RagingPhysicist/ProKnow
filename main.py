# main.py

import os
import argparse
import pandas as pd
from tqdm import tqdm

from dose import perform_summation
from data import extract_dicom_info
from dicom_send import send_patient_files  # <-- IMPORT THE NEW FUNCTION


def process_patient_directories(args):
    """Main function to orchestrate DICOM processing tasks."""
    try:
        patient_dirs = [d.path for d in os.scandir(args.root_dir) if d.is_dir()]
    except FileNotFoundError:
        print(f"Error: Root directory not found at '{args.root_dir}'")
        return

    if not patient_dirs:
        print(f"No patient directories found in '{args.root_dir}'.")
        return

    print(f"Found {len(patient_dirs)} patient directories. Starting processing...")

    all_patient_data = []

    for patient_dir in tqdm(patient_dirs, desc="Processing Patients", unit="patient"):
        patient_id = os.path.basename(patient_dir)
        tqdm.write(f"\n--- Processing Patient: {patient_id} ---")

        # 1. Get metadata, the list of ALL dicom files, and the list of RTDose files
        patient_data, all_files, rtdose_files = extract_dicom_info(patient_dir)
        all_patient_data.append(patient_data)

        # 2. Perform dose summation if applicable
        if len(rtdose_files) > 1:
            summed_dose_path = perform_summation(rtdose_files, patient_id)
            # If a new file was created, add it to the list of files to be sent
            if summed_dose_path:
                all_files.append(summed_dose_path)

        # 3. If the send flag is set, send ALL collected files
        if args.send:
            send_patient_files(
                file_list=all_files,
                dest_ip=args.dest_ip,
                dest_port=args.dest_port,
                dest_aet=args.dest_aet,
                calling_aet=args.calling_aet
            )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A toolkit for processing DICOM RT data. It extracts metadata and performs dose summation and sending."
    )
    # Existing arguments
    parser.add_argument("root_dir", type=str, help="The root directory containing patient folders.")
    parser.add_argument("-o", "--output", type=str, default="dicom_summary.xlsx",
                        help="Path for the output Excel file.")

    # Arguments for DICOM sending
    parser.add_argument("--send", action="store_true",
                        help="Flag to enable sending of new summed dose files to a DICOM destination.")
    parser.add_argument("--dest-ip", type=str, help="Destination IP address.")
    parser.add_argument("--dest-port", type=int, help="Destination port number.")
    parser.add_argument("--dest-aet", type=str, help="Destination Application Entity Title (AET).")
    parser.add_argument("--calling-aet", type=str, default="PY_SENDER", help="This script's AET. Default: PY_SENDER")

    args = parser.parse_args()

    # Check if sending is enabled and all required arguments are provided
    if args.send and not all([args.dest_ip, args.dest_port, args.dest_aet]):
        parser.error("--send requires --dest-ip, --dest-port, and --dest-aet to be set.")

    # This is the corrected function call
    process_patient_directories(args)