import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
import datetime


def create_binary_segmentation_dicom(rows=128, cols=128):
    # Create file metadata
    meta = Dataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.66.4'  # Segmentation Storage
    meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    meta.ImplementationClassUID = pydicom.uid.generate_uid()

    # Create the FileDataset (in memory)
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Required general attributes
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.Modality = 'SEG'
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()
    ds.PatientName = 'Seg^Test'
    ds.PatientID = 'SEG001'

    # Set content date/time
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    ds.ContentTime = dt.strftime('%H%M%S.%f')[:13]

    # Segmentation-specific
    ds.SegmentationType = 'BINARY'
    ds.ContentLabel = 'MASK'
    ds.ContentDescription = 'Binary segmentation mask'
    ds.ContentCreatorName = 'AutoGen'

    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = 1
    ds.BitsStored = 1
    ds.HighBit = 0
    ds.PixelRepresentation = 0
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.NumberOfFrames = 1
    ds.BurnedInAnnotation = 'NO'
    ds.ImageType = ['DERIVED', 'PRIMARY']

    # Create a dummy mask (circle in center)
    Y, X = np.ogrid[:rows, :cols]
    mask = ((X - cols // 2)**2 + (Y - rows // 2)**2) < (min(rows, cols) // 4)**2
    binary_frame = np.packbits(mask.astype(np.uint8).flatten())

    # Assign Pixel Data
    ds.PixelData = binary_frame.tobytes()

    # SegmentSequence: define what the mask means
    segment = Dataset()
    segment.SegmentNumber = 1
    segment.SegmentLabel = 'Kidney'
    segment.SegmentAlgorithmType = 'MANUAL'
    segment.SegmentAlgorithmName = 'ManualDraw'

    segment.SegmentedPropertyCategoryCodeSequence = Sequence([Dataset()])
    segment.SegmentedPropertyCategoryCodeSequence[0].CodeValue = 'T-D0050'
    segment.SegmentedPropertyCategoryCodeSequence[0].CodingSchemeDesignator = 'SRT'
    segment.SegmentedPropertyCategoryCodeSequence[0].CodeMeaning = 'Tissue'

    segment.SegmentedPropertyTypeCodeSequence = Sequence([Dataset()])
    segment.SegmentedPropertyTypeCodeSequence[0].CodeValue = 'T-71000'
    segment.SegmentedPropertyTypeCodeSequence[0].CodingSchemeDesignator = 'SRT'
    segment.SegmentedPropertyTypeCodeSequence[0].CodeMeaning = 'Kidney'

    ds.SegmentSequence = Sequence([segment])

    # Functional groups (Plane Position)
    fg = Dataset()
    pp = Dataset()
    pp.ImagePositionPatient = [0.0, 0.0, 0.0]
    fg.PlanePositionSequence = Sequence([pp])
    ds.PerFrameFunctionalGroupsSequence = Sequence([fg])

    return ds




def create_multi_segment_segmentation_dicom(masks_dict, spacing=(1.0, 1.0), origin=(0.0, 0.0, 0.0)):
    """
    Create a multi-segment binary DICOM Segmentation object.

    Parameters:
    - masks_dict: dict of {label: binary 2D NumPy array}
    - spacing: (row_spacing, col_spacing)
    - origin: (x, y, z) ImagePositionPatient

    Returns:
    - pydicom FileDataset object
    """

    labels = list(masks_dict.keys())
    first_mask = next(iter(masks_dict.values()))
    rows, cols = first_mask.shape

    # Create metadata
    meta = Dataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.66.4'
    meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    meta.ImplementationClassUID = pydicom.uid.generate_uid()

    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Required general attributes
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.Modality = 'SEG'
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()
    ds.PatientName = 'Seg^Multi'
    ds.PatientID = 'MULTISEG001'
    ds.ContentDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.ContentTime = datetime.datetime.now().strftime('%H%M%S.%f')[:13]

    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = 1
    ds.BitsStored = 1
    ds.HighBit = 0
    ds.PixelRepresentation = 0
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.SegmentationType = 'BINARY'
    ds.BurnedInAnnotation = 'NO'
    ds.ImageType = ['DERIVED', 'PRIMARY']
    ds.ContentLabel = 'MULTI_SEG'
    ds.ContentCreatorName = 'AutoGen'

    # SegmentSequence
    segment_sequence = []
    pixel_data_bytes = b''
    fg_sequence = []

    for i, label in enumerate(labels):
        segment = Dataset()
        segment.SegmentNumber = i + 1
        segment.SegmentLabel = label
        segment.SegmentAlgorithmType = 'MANUAL'
        segment.SegmentAlgorithmName = 'ManualDraw'

        # Use generic SRT codes for tissue/organ
        segment.SegmentedPropertyCategoryCodeSequence = Sequence([Dataset()])
        segment.SegmentedPropertyCategoryCodeSequence[0].CodeValue = 'T-D0050'
        segment.SegmentedPropertyCategoryCodeSequence[0].CodingSchemeDesignator = 'SRT'
        segment.SegmentedPropertyCategoryCodeSequence[0].CodeMeaning = 'Tissue'

        segment.SegmentedPropertyTypeCodeSequence = Sequence([Dataset()])
        segment.SegmentedPropertyTypeCodeSequence[0].CodeValue = 'T-00000'
        segment.SegmentedPropertyTypeCodeSequence[0].CodingSchemeDesignator = '99LOCAL'
        segment.SegmentedPropertyTypeCodeSequence[0].CodeMeaning = label

        segment_sequence.append(segment)

        # Mask -> 1-bit packed frame
        mask = masks_dict[label]
        assert mask.shape == (rows, cols), f"Shape mismatch for label '{label}'"
        packed = np.packbits(mask.astype(np.uint8).flatten())
        pixel_data_bytes += packed.tobytes()

        # Per-frame functional group (Plane Position and Segment Identification)
        fg = Dataset()

        # Plane Position
        pp = Dataset()
        pp.ImagePositionPatient = [float(origin[0]), float(origin[1]), float(origin[2] + i)]
        fg.PlanePositionSequence = Sequence([pp])

        # Segment Identification
        si = Dataset()
        si.ReferencedSegmentNumber = i + 1
        fg.SegmentIdentificationSequence = Sequence([si])

        fg_sequence.append(fg)



def create_multiframe_segmentation(masks_dict, pixel_spacing=(1.0, 1.0), slice_thickness=1.0, origin=(0.0, 0.0, 0.0)):
    """
    Create a DICOM Segmentation object with multiple frames per segment (e.g., 3D masks).
    
    Parameters:
        masks_dict: dict {label: 3D numpy array (Z, Y, X)}
        pixel_spacing: tuple of (row_spacing, col_spacing)
        slice_thickness: float
        origin: tuple of (x, y, z)
    """
    labels = list(masks_dict.keys())
    first_volume = next(iter(masks_dict.values()))
    num_slices, rows, cols = first_volume.shape

    meta = Dataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.66.4'
    meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    meta.ImplementationClassUID = pydicom.uid.generate_uid()

    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.Modality = 'SEG'
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()
    ds.PatientName = 'Seg^3D'
    ds.PatientID = 'SEG3D001'
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    ds.ContentTime = dt.strftime('%H%M%S.%f')[:13]

    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = 1
    ds.BitsStored = 1
    ds.HighBit = 0
    ds.PixelRepresentation = 0
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.SegmentationType = 'BINARY'
    ds.BurnedInAnnotation = 'NO'
    ds.ImageType = ['DERIVED', 'PRIMARY']
    ds.ContentLabel = 'MULTIFRAME_SEG'
    ds.ContentCreatorName = 'AutoGen'

    ds.NumberOfFrames = num_slices * len(labels)

    pixel_data_bytes = b''
    segment_sequence = []
    per_frame_sequence = []

    for seg_index, label in enumerate(labels):
        vol = masks_dict[label]
        assert vol.shape == (num_slices, rows, cols)

        segment = Dataset()
        segment.SegmentNumber = seg_index + 1
        segment.SegmentLabel = label
        segment.SegmentAlgorithmType = 'MANUAL'
        segment.SegmentAlgorithmName = 'ManualDraw'

        segment.SegmentedPropertyCategoryCodeSequence = Sequence([Dataset()])
        segment.SegmentedPropertyCategoryCodeSequence[0].CodeValue = 'T-D0050'
        segment.SegmentedPropertyCategoryCodeSequence[0].CodingSchemeDesignator = 'SRT'
        segment.SegmentedPropertyCategoryCodeSequence[0].CodeMeaning = 'Tissue'

        segment.SegmentedPropertyTypeCodeSequence = Sequence([Dataset()])
        segment.SegmentedPropertyTypeCodeSequence[0].CodeValue = 'T-00000'
        segment.SegmentedPropertyTypeCodeSequence[0].CodingSchemeDesignator = '99LOCAL'
        segment.SegmentedPropertyTypeCodeSequence[0].CodeMeaning = label

        segment_sequence.append(segment)

        for z in range(num_slices):
            # Pack each slice (frame)
            frame = np.packbits(vol[z].astype(np.uint8).flatten())
            pixel_data_bytes += frame.tobytes()

            # Functional Group for this frame
            fg = Dataset()

            # Position
            pos = list(origin)
            pos[2] += z * slice_thickness
            plane = Dataset()
            plane.ImagePositionPatient = [str(v) for v in pos]
            fg.PlanePositionSequence = Sequence([plane])

            # Segment reference
            seg_id = Dataset()
            seg_id.ReferencedSegmentNumber = seg_index + 1
            fg.SegmentIdentificationSequence = Sequence([seg_id])

            per_frame_sequence.append(fg)

    ds.SegmentSequence = Sequence(segment_sequence)
    ds.PixelData = pixel_data_bytes
    ds.PerFrameFunctionalGroupsSequence = Sequence(per_frame_sequence)

    # Shared functional groups
    shared = Dataset()
    geom = Dataset()
    geom.PixelSpacing = [str(pixel_spacing[0]), str(pixel_spacing[1])]
    geom.SliceThickness = str(slice_thickness)
    geom.ImageOrientationPatient = ['1', '0', '0', '0', '1', '0']
    shared.PixelMeasuresSequence = Sequence([geom])
    ds.SharedFunctionalGroupsSequence = Sequence([shared])

    return ds



