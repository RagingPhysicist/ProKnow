# dose_summation.py
# sum sequential dose cubes of a treatment course for further use in proknow

import os
import numpy as np
import pydicom
from pydicom.uid import generate_uid
from datetime import datetime
from copy import deepcopy


def load_dose_grid(filepath):
    ds = pydicom.dcmread(filepath)
    if not isinstance(ds, pydicom.dataset.FileDataset):
        raise TypeError(f"Expected a pydicom.dataset.FileDataset, but got {type(ds)} for {filepath}")
    if ds.Modality != 'RTDOSE':
        raise ValueError(f"{filepath} is not an RTDOSE file.")
    if not hasattr(ds, 'pixel_array') or not hasattr(ds, 'DoseGridScaling'):
        raise ValueError(f"Missing required DICOM attributes in {filepath}")

    dose_grid = ds.pixel_array.astype(np.float32) * float(ds.DoseGridScaling)
    return dose_grid, ds


def check_same_geometry(datasets):
    ref = datasets[0]
    for i, ds in enumerate(datasets[1:], 1):
        if (
                ds.Rows != ref.Rows or
                ds.Columns != ref.Columns or
                ds.NumberOfFrames != ref.NumberOfFrames or
                ds.PixelSpacing != ref.PixelSpacing or
                ds.ImageOrientationPatient != ref.ImageOrientationPatient or
                ds.ImagePositionPatient != ref.ImagePositionPatient or
                ds.GridFrameOffsetVector != ref.GridFrameOffsetVector
        ):
            raise ValueError(f"Geometry mismatch in dose file {i + 1} ({ds.filename}).")


def sum_doses(dose_arrays):
    return np.sum(dose_arrays, axis=0)


def create_new_dose_dataset(reference_ds, summed_dose_array, patient_id):
    new_ds = deepcopy(reference_ds)

    # Update required UIDs and description
    new_ds.SOPInstanceUID = generate_uid()
    new_ds.SeriesInstanceUID = generate_uid()  # Each summed dose gets its own series
    new_ds.SeriesDescription = "Summed Dose"
    new_ds.ContentDate = datetime.now().strftime("%Y%m%d")
    new_ds.ContentTime = datetime.now().strftime("%H%M%S")

    max_val = np.max(summed_dose_array)
    if max_val == 0:
        raise ValueError("Summed dose grid is all zeros. Cannot scale.")

    # Use uint32 for better precision if needed, but uint16 is common
    scaled_array = (summed_dose_array / max_val * np.iinfo(np.uint16).max).astype(np.uint16)
    new_ds.DoseGridScaling = max_val / np.iinfo(np.uint16).max

    new_ds.PixelData = scaled_array.tobytes()
    new_ds.Rows, new_ds.Columns = scaled_array.shape[1], scaled_array.shape[2]
    new_ds.NumberOfFrames = scaled_array.shape[0]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"RD_SummedDose_{patient_id}_{timestamp}.dcm"
    return new_ds, filename


def perform_summation(rtdose_files: list, patient_id: str):
    if len(rtdose_files) <= 1:
        # This check is technically redundant as main.py already does it, but it's good practice.
        return

    # Use the directory of the first dose file as the output location
    output_dir = os.path.dirname(rtdose_files[0])

    # Check if a summed file already exists in the folder
    if any("summed" in f.lower() for f in os.listdir(output_dir)):
        print(f" -> Summed dose already exists for patient {patient_id}, skipping.")
        return

    print(f"\nPerforming dose summation for patient: {patient_id}")
    dose_arrays = []
    datasets = []

    for file_path in rtdose_files:
        try:
            dose_array, ds = load_dose_grid(file_path)
            dose_arrays.append(dose_array)
            datasets.append(ds)
        except Exception as e:
            print(f"  -> ERROR: Could not load {os.path.basename(file_path)}: {e}")
            return  # Stop summation for this patient if a file is invalid

    if not datasets:
        print(f"  -> ERROR: No valid RTDOSE files could be loaded for patient {patient_id}.")
        return

    try:
        print(f" -> Checking geometry for {len(datasets)} dose files...")
        check_same_geometry(datasets)

        print(" -> Summing dose grids...")
        summed_array = sum_doses(dose_arrays)

        print(" -> Creating new DICOM dataset for summed dose...")
        new_ds, filename = create_new_dose_dataset(datasets[0], summed_array, patient_id)

        out_path = os.path.join(output_dir, filename)
        new_ds.save_as(out_path)
        print(f" Summed dose saved to: {out_path}")

    except Exception as e:
        print(f"  -> ERROR: Failed to sum doses for patient {patient_id}: {e}")