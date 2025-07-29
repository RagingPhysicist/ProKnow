import os
import pydicom
from tqdm import tqdm
from pynetdicom import AE
from pynetdicom.sop_class import (
    CTImageStorage,
    MRImageStorage,
    RTDoseStorage,
    RTPlanStorage,
    RTStructureSetStorage
)

def send_patient_files(file_list: list, dest_ip: str, dest_port: int, dest_aet: str, calling_aet: str):
    """
    Sends a list of DICOM files to a specified destination using C-STORE.

    Args:
        file_list (list): A list of paths to the DICOM files to send.
        dest_ip (str): The IP address of the DICOM destination.
        dest_port (int): The port number of the DICOM destination.
        dest_aet (str): The Application Entity Title (AET) of the destination.
        calling_aet (str): The AET for this script.
    """
    if not file_list:
        print(" -> No files to send.")
        return

    # Set up our Application Entity
    ae = AE(ae_title=calling_aet)

    # Add required storage presentation contexts
    sop_classes = [
        CTImageStorage,
        MRImageStorage,
        RTDoseStorage,
        RTPlanStorage,
        RTStructureSetStorage
    ]

    for sop_class in sop_classes:
        ae.add_requested_context(sop_class)

    print(f"\nAttempting to send {len(file_list)} files to {dest_aet} at {dest_ip}:{dest_port}...")

    # Associate with the remote AE
    assoc = ae.associate(dest_ip, dest_port, ae_title=dest_aet)

    if assoc.is_established:
        print("Association successful.")

        for filepath in tqdm(file_list, desc="Sending Files", unit="file", leave=False):
            try:
                dataset = pydicom.dcmread(filepath)
                status = assoc.send_c_store(dataset)

                if status and status.Status != 0x0000:
                    tqdm.write(f"Failed to send {os.path.basename(filepath)}. Status: 0x{status.Status:04x}")

            except Exception as e:
                tqdm.write(f"Could not read or send {filepath}: {e}")

        assoc.release()
        print(" -> Send process complete. Association released.")
    else:
        print("Association with the destination failed. Please check IP, port, and AET.")