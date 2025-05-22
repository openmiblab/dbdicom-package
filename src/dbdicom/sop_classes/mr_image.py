# Coded version of DICOM file 
# 'RIDER Neuro MRI-3369019796\03-21-1904-BRAINRESEARCH-00598\14.000000-sag 3d gre c-04769\1-010.dcm'
# Produced by pydicom codify utility script
import os
import struct
import numpy as np
import pydicom
from pydicom.dataset import FileMetaDataset, Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    ExplicitVRLittleEndian,
    generate_uid,
    MRImageStorage,
)

from datetime import datetime
import tempfile

import dbdicom.utils.image as image


def pixel_data(ds):
    """Read the pixel array from an MR image"""

    #array = ds.pixel_array.astype(np.float64)
    #array = ds.pixel_array
    #array = np.frombuffer(ds.PixelData, dtype=np.uint16).reshape(ds.Rows, ds.Columns)
    #array = array.astype(np.float32)

    array = ds.pixel_array
    array = array.astype(np.float32)
    if [0x2005, 0x100E] in ds: # 'Philips Rescale Slope'
        slope = ds[(0x2005, 0x100E)].value
        intercept = ds[(0x2005, 0x100D)].value
        array -= intercept
        array /= slope
    else:
        slope = float(getattr(ds, 'RescaleSlope', 1)) 
        intercept = float(getattr(ds, 'RescaleIntercept', 0)) 
        array *= slope
        array += intercept
    return np.transpose(array)


def set_pixel_data(ds, array):

    if (0x2005, 0x100E) in ds: 
        del ds[0x2005, 0x100E]  # Delete 'Philips Rescale Slope'
    if (0x2005, 0x100D) in ds: 
        del ds[0x2005, 0x100D]

    # clipping may slow down a lot
    array = image.clip(array.astype(np.float32))
    array, slope, intercept = image.scale_to_range(array, ds.BitsAllocated)
    array = np.transpose(array)

    ds.PixelRepresentation = 0
    ds.RescaleSlope = 1 / slope
    ds.RescaleIntercept = - intercept / slope
#        ds.WindowCenter = (maximum + minimum) / 2
#        ds.WindowWidth = maximum - minimum
    ds.Rows = array.shape[0]
    ds.Columns = array.shape[1]
    ds.PixelData = array.tobytes()



def chat_gpt_3d(num_frames=10, rows=256, columns=256):

    # File meta info
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Create FileDataset in memory
    ds = FileDataset(
        filename_or_obj=None,
        dataset=Dataset(),
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    # Transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    now = datetime.now()

    # Required fields
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PatientName = "Multi^Frame"
    ds.PatientID = "999999"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "MR"
    ds.Manufacturer = "PythonPACS"
    ds.StudyID = "1"
    ds.SeriesNumber = "1"
    ds.InstanceNumber = "1"

    # Image geometry
    ds.Rows = rows
    ds.Columns = columns
    ds.PixelSpacing = [1.0, 1.0]
    ds.ImagePositionPatient = [0.0, 0.0, 0.0]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    ds.FrameOfReferenceUID = generate_uid()
    ds.PositionReferenceIndicator = ""

    # Multi-frame specific
    ds.NumberOfFrames = str(num_frames)
    ds.InstanceNumber = "1"

    # Pixel data requirements
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0  # unsigned

    # Create dummy image data (e.g., black frames)
    pixel_array = np.zeros((num_frames, rows, columns), dtype=np.uint16)
    ds.PixelData = pixel_array.tobytes()

    return ds



def chat_gpt_2d():
    # Basic identifiers
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()

    # Create the main dataset
    ds = FileDataset(
        filename_or_obj=None,
        dataset=Dataset(),
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    # Set transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Required DICOM tags for MR Image Storage
    now = datetime.now()
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PatientName = "Anonymous^Patient"
    ds.PatientID = "123456"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "MR"
    ds.Manufacturer = "PythonPACS"
    ds.StudyID = "1"
    ds.SeriesNumber = "1"
    ds.InstanceNumber = "1"
    ds.ImagePositionPatient = [0.0, 0.0, 0.0]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    ds.FrameOfReferenceUID = generate_uid()
    ds.PositionReferenceIndicator = ""
    ds.Rows = 256
    ds.Columns = 256
    ds.PixelSpacing = [1.0, 1.0]
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0  # unsigned
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = (b"\0" * (ds.Rows * ds.Columns * 2))  # Dummy black image

    return ds


def default(): # from the RIDER dataset

    # File meta info data elements
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 190
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
    file_meta.MediaStorageSOPInstanceUID = '1.3.6.1.4.1.9328.50.16.175333593952805976694548436931998383940'
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'
    file_meta.ImplementationClassUID = '1.2.40.0.13.1.1'
    file_meta.ImplementationVersionName = 'dcm4che-1.4.27'

    # Create the main dataset
    ds = FileDataset(
        filename_or_obj=None,
        dataset=Dataset(),
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    ds.is_implicit_VR = True
    ds.is_little_endian = True

    # Main data elements
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'M', 'ND', 'NORM']
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.4'
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.StudyDate = '19040321'
    ds.ContentDate = '19040321'
    ds.StudyTime = ''
    ds.AcquisitionTime = '075649.057496'
    ds.ContentTime = ''
    ds.AccessionNumber = '2819497684894126'
    ds.Modality = 'MR'
    ds.Manufacturer = 'SIEMENS'
    ds.ReferringPhysicianName = ''
    ds.StationName = ''
    ds.StudyDescription = 'BRAIN^RESEARCH'
    ds.SeriesDescription = 'sag 3d gre +c'
    ds.ManufacturerModelName = ''
    ds.ReferencedSOPClassUID = '1.3.6.1.4.1.9328.50.16.295504506656781074046411123909869020125'
    ds.ReferencedSOPInstanceUID = '1.3.6.1.4.1.9328.50.16.303143938897288157958328401346374476407'
    ds.PatientName = '281949'
    ds.PatientID = pydicom.uid.generate_uid()
    ds.PatientBirthDate = ''
    ds.PatientSex = ''
    ds.PatientIdentityRemoved = 'YES'
    ds.DeidentificationMethod = 'CTP:NBIA Default w/ extra date removal:20100323:172722'
    ds.ContrastBolusAgent = 'Magnevist'
    ds.BodyPartExamined = 'FAKE'
    ds.ScanningSequence = 'GR'
    ds.SequenceVariant = 'SP'
    ds.ScanOptions = ''
    ds.MRAcquisitionType = '3D'
    ds.SequenceName = '*fl3d1'
    ds.AngioFlag = 'N'
    ds.SliceThickness = '1.0'
    ds.RepetitionTime = '8.6'
    ds.EchoTime = '4.11'
    ds.NumberOfAverages = '1.0'
    ds.ImagingFrequency = '63.676701'
    ds.ImagedNucleus = '1H'
    ds.EchoNumbers = '0'
    ds.MagneticFieldStrength = '1.4939999580383'
    ds.NumberOfPhaseEncodingSteps = '224'
    ds.EchoTrainLength = '1'
    ds.PercentSampling = '100.0'
    ds.PercentPhaseFieldOfView = '100.0'
    ds.PixelBandwidth = '150.0'
    ds.DeviceSerialNumber = '25445'
    ds.SoftwareVersions = 'syngo MR 2004V 4VB11D'
    ds.ProtocolName = 'sag 3d gre +c'
    ds.ContrastBolusVolume = '20.0'
    ds.DateOfLastCalibration = '19031229'
    ds.TimeOfLastCalibration = '155156.000000'
    ds.TransmitCoilName = 'Body'
    ds.InPlanePhaseEncodingDirection = 'ROW'
    ds.FlipAngle = '20.0'
    ds.VariableFlipAngleFlag = 'N'
    ds.SAR = '0.09494107961655'
    ds.dBdt = '0.0'
    ds.PatientPosition = 'HFS'
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyID = ''
    ds.SeriesNumber = '14'
    ds.AcquisitionNumber = '1'
    ds.InstanceNumber = '1'
    ds.ImagePositionPatient = [0, 0, 0]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.FrameOfReferenceUID = '1.3.6.1.4.1.9328.50.16.22344679587635360510174487884943834158'
    ds.PositionReferenceIndicator = ''
    ds.SliceLocation = '0.0'
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.Rows = 64
    ds.Columns = 64
    ds.PixelSpacing = [1, 1]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SmallestImagePixelValue = 0
    ds.LargestImagePixelValue = 913
    ds.WindowCenter = '136.0'
    ds.WindowWidth = '380.0'
    ds.RescaleIntercept = '0.0'
    ds.RescaleSlope = '1.0'
    ds.RescaleType = 'PIXELVALUE'
    ds.WindowCenterWidthExplanation = 'Algo1'
    ds.RequestedProcedureDescription = 'MRI BRAIN W/WO ENHANCEMENT'
    ds.ScheduledProcedureStepDescription = 'MRI BRAIN W/WO ENHANCEMENT'
    ds.ScheduledProcedureStepID = '5133240'
    ds.PerformedProcedureStepStartDate = '19040611'
    ds.PerformedProcedureStepDescription = 'MRI BRAIN W/WO ENHANCEMENT'
    ds.RequestAttributesSequence = Sequence()
    ds.RequestedProcedureID = '5133240'
    ds.StorageMediaFileSetUID = '1.3.6.1.4.1.9328.50.16.162890465625511526068665093825399871205'
    pixel_values = np.arange(ds.Rows*ds.Columns)*ds.LargestImagePixelValue/(ds.Rows*ds.Columns)
    ds.PixelData = pixel_values.astype(np.uint16).tobytes()

    return ds





if __name__ == '__main__':
    file = os.path.join(os.getcwd(), 'chat_gpt_mri.dcm')
    chat_gpt_3d().save_as(file)
    file = os.path.join(os.getcwd(), 'default_mri.dcm')
    default().save_as(file)
    print(file)



