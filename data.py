# data_retriever.py

import os
import pydicom
from pydicom.errors import InvalidDicomError
from typing import Tuple, Dict, List  # <-- ADD THIS IMPORT


def get_all_dicom_files(patient_dir: str) -> Dict[str, List[str]]:
    """Recursively finds all RTPlan, RTStruct, and RTDose files within a patient directory."""
    files = {'RTPLAN': [], 'RTSTRUCT': [], 'RTDOSE': []}
    for root, _, filenames in os.walk(patient_dir):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            try:
                dcm = pydicom.dcmread(filepath, stop_before_pixels=True)
                modality = dcm.get("Modality", "").upper()
                if modality in files:
                    files[modality].append(filepath)
            except (InvalidDicomError, AttributeError, IsADirectoryError):
                continue
    return files


def extract_dicom_info(patient_dir: str) -> Tuple[dict, list]:  # <-- CHANGE THIS LINE
    """Extracts specified UIDs and other info from DICOM files for one patient."""
    dicom_files = get_all_dicom_files(patient_dir)
    patient_id = os.path.basename(os.path.normpath(patient_dir))

    data = {
        'PatientID': patient_id,
        'StudyInstanceUID': 'N/A',
        'SeriesInstanceUID': 'N/A',
        'ManufacturersModelName': 'N/A',
        'TreatmentSites': 'N/A',
        'RTStruct_SOPInstanceUID': 'N/A',
        'RTPlan_SOPInstanceUID' : 'N/A',
        'RTDose_SOPInstanceUIDs': 'N/A',
    }

    if dicom_files['RTPLAN']:
        plan_path = dicom_files['RTPLAN'][0]
        try:
            plan_dcm = pydicom.dcmread(plan_path)
            data['StudyInstanceUID'] = plan_dcm.get("StudyInstanceUID", "N/A")
            data['SeriesInstanceUID'] = plan_dcm.get("SeriesInstanceUID", "N/A")
            data['ManufacturersModelName'] = plan_dcm.get("ManufacturerModelName", "N/A")
            data['TreatmentSites'] = plan_dcm.get("TreatmentSites", "N/A")
            data['RTPlan_SOPInstanceUID'] = plan_dcm.get("SOPInstanceUID", "N/A")

        except Exception as e:
            print(f"  -> Error processing RTPlan for {patient_id}: {e}")

    if dicom_files['RTSTRUCT']:
        struct_path = dicom_files['RTSTRUCT'][0]
        try:
            struct_dcm = pydicom.dcmread(struct_path, stop_before_pixels=True)
            data['RTStruct_SOPInstanceUID'] = struct_dcm.get("SOPInstanceUID", "N/A")
        except Exception as e:
            print(f"  -> Error processing RTStruct for {patient_id}: {e}")

    if dicom_files['RTDOSE']:
        dose_uids = []
        for dose_path in dicom_files['RTDOSE']:
            try:
                dose_dcm = pydicom.dcmread(dose_path, stop_before_pixels=True)
                dose_uids.append(dose_dcm.get("SOPInstanceUID", "N/A"))
            except Exception as e:
                print(f"  -> Error processing RTDose file {dose_path}: {e}")
        if dose_uids:
            data['RTDose_SOPInstanceUIDs'] = ', '.join(dose_uids)

    return data, dicom_files['RTDOSE']