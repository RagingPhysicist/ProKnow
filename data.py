import os
import pydicom
from pydicom.errors import InvalidDicomError
from typing import Tuple, Dict, List


def extract_dicom_info(patient_dir: str) -> Tuple[Dict, List[str]]:
    """
    Finds all DICOM files, extracts specified metadata for a spreadsheet,
    and returns the full list of file paths.

    Args:
        patient_dir (str): The path to the patient's main folder.

    Returns:
        A tuple containing:
        - dict: A dictionary with the extracted metadata.
        - list: A list of full paths to ALL DICOM files found.
    """
    all_dicom_files = []
    categorized_files = {'RTPLAN': [], 'RTSTRUCT': [], 'RTDOSE': []}

    # Find and categorize all DICOM files in one pass
    for root, _, filenames in os.walk(patient_dir):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            try:
                dcm = pydicom.dcmread(filepath, stop_before_pixels=True)
                all_dicom_files.append(filepath)  # Add to the master list
                modality = dcm.get("Modality", "").upper()
                if modality in categorized_files:
                    categorized_files[modality].append(filepath)
            except (InvalidDicomError, AttributeError, IsADirectoryError):
                continue

    patient_id = os.path.basename(os.path.normpath(patient_dir))
    data = {
        'PatientID': patient_id, 'StudyInstanceUID': 'N/A', 'SeriesInstanceUID': 'N/A',
        'ManufacturersModelName': 'N/A', 'TreatmentSites': 'N/A',
        'RTStruct_SOPInstanceUID': 'N/A', 'RTDose_SOPInstanceUIDs': 'N/A',
    }

    # Extract metadata from the categorized files
    if categorized_files['RTPLAN']:
        plan_path = categorized_files['RTPLAN'][0]
        try:
            plan_dcm = pydicom.dcmread(plan_path)
            data['StudyInstanceUID'] = plan_dcm.get("StudyInstanceUID", "N/A")
            data['SeriesInstanceUID'] = plan_dcm.get("SeriesInstanceUID", "N/A")
            data['ManufacturersModelName'] = plan_dcm.get("ManufacturerModelName", "N/A")
            accessory_code = plan_dcm.get("AccessoryCode", "N/A")
            if accessory_code != "N/A":
                data['TreatmentSites'] = ', '.join(map(str, accessory_code)) if isinstance(accessory_code,
                                                                                           pydicom.multival.MultiValue) else str(
                    accessory_code)
        except Exception as e:
            print(f"  -> Error processing RTPlan for {patient_id}: {e}")

    if categorized_files['RTSTRUCT']:
        struct_path = categorized_files['RTSTRUCT'][0]
        try:
            data['RTStruct_SOPInstanceUID'] = pydicom.dcmread(struct_path, stop_before_pixels=True).get(
                "SOPInstanceUID", "N/A")
        except Exception as e:
            print(f"  -> Error processing RTStruct for {patient_id}: {e}")

    if categorized_files['RTDOSE']:
        dose_uids = [pydicom.dcmread(p, stop_before_pixels=True).get("SOPInstanceUID", "N/A") for p in
                     categorized_files['RTDOSE']]
        data['RTDose_SOPInstanceUIDs'] = ', '.join(filter(None, dose_uids))

    # Return the extracted data AND the complete list of all files
    return data, all_dicom_files, categorized_files['RTDOSE']