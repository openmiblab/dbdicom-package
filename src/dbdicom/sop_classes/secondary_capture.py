import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import SecondaryCaptureImageStorage, generate_uid, ExplicitVRLittleEndian
from datetime import datetime
from pydicom.sequence import Sequence



def create_3d_secondary_capture_dataset_with_dimensions(depth=16, rows=256, cols=256, pixel_volume=None):
    now = datetime.now()

    # File Meta
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Dataset
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Patient & Study Info
    ds.PatientName = "SC^ThreeD"
    ds.PatientID = "3D123456"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "OT"
    ds.Manufacturer = "PythonSC"

    ds.SeriesNumber = 1
    ds.InstanceNumber = 1

    # Image Attributes
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.NumberOfFrames = str(depth)
    ds.ImageType = ["DERIVED", "SECONDARY"]

    # Pixel Data
    if pixel_volume is None:
        pixel_volume = np.random.randint(0, 4095, size=(depth, rows, cols), dtype=np.uint16)
    ds.PixelData = pixel_volume.tobytes()

    # === DIMENSIONS ===
    dim_uid = generate_uid()

    ds.DimensionOrganizationSequence = Sequence([
        Dataset()
    ])
    ds.DimensionOrganizationSequence[0].DimensionOrganizationUID = dim_uid

    # Define 1 dimension: slice index (z-dimension)
    dim_index = Dataset()
    dim_index.DimensionOrganizationUID = dim_uid
    dim_index.DimensionIndexPointer = 0x00200032  # ImagePositionPatient
    dim_index.FunctionalGroupPointer = 0x00209113  # PlanePositionSequence

    ds.DimensionIndexSequence = Sequence([dim_index])

    # Per-Frame Functional Groups
    ds.PerFrameFunctionalGroupsSequence = Sequence()

    for z in range(depth):
        frame = Dataset()

        # Plane position sequence with slice position
        pos = Dataset()
        pos.ImagePositionPatient = [0.0, 0.0, float(z)]  # Simple linear z spacing
        frame.PlanePositionSequence = Sequence([pos])

        ds.PerFrameFunctionalGroupsSequence.append(frame)

    return ds



def create_3d_secondary_capture_dataset(depth=16, rows=256, cols=256, pixel_volume=None):
    now = datetime.now()
    total_frames = depth

    # File Meta
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # FileDataset
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Basic metadata
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PatientName = "SC^ThreeD"
    ds.PatientID = "3D123456"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "OT"
    ds.Manufacturer = "PythonGenerator"

    ds.SeriesNumber = 1
    ds.InstanceNumber = 1

    # Image attributes
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.NumberOfFrames = str(total_frames)
    ds.ImageType = ["DERIVED", "SECONDARY"]

    # Dummy or real 3D pixel data
    if pixel_volume is None:
        pixel_volume = np.random.randint(0, 4095, size=(depth, rows, cols), dtype=np.uint16)

    ds.PixelData = pixel_volume.tobytes()

    return ds

