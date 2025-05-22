# Coded version of DICOM file 'C:\Users\steve\Dropbox\Software\QIB-Sheffield\dbdicom\tests\data\XRayAngioUncompressed-dicom_viewer_0015\0015.DCM'
# Produced by pydicom codify utility script
import numpy as np
import pydicom
from pydicom.dataset import FileMetaDataset
from pydicom.sequence import Sequence

def default(ds):

    # File meta info data elements
    ds.file_meta = FileMetaDataset()
    ds.file_meta.FileMetaInformationGroupLength = 202
    ds.file_meta.FileMetaInformationVersion = b'\x00\x01'
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.12.2'
    ds.file_meta.MediaStorageSOPInstanceUID = '1.2.840.113619.2.15.1008000062035011254.825190719.0.31.2.1'
    ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    ds.file_meta.ImplementationClassUID = '1.2.840.113619.6.36'
    ds.file_meta.ImplementationVersionName = '1_2_5'
    ds.file_meta.SourceApplicationEntityTitle = 'ard-demo'

    ds.is_implicit_VR = False
    ds.is_little_endian = True

    # Main data elements
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'SINGLE PLANE']
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.12.2'
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.StudyDate = '19960308'
    ds.SeriesDate = '19960308'
    ds.AcquisitionDate = '19960308'
    ds.ContentDate = '19960308'
    ds.StudyTime = ''
    ds.AcquisitionTime = '105650'
    ds.ContentTime = '105650'
    ds.AccessionNumber = ''
    ds.Modality = 'RF'
    ds.Manufacturer = 'GE MEDICAL SYSTEMS'
    ds.ReferringPhysicianName = ''
    ds.StationName = ''
    ds.StudyDescription = '5'
    ds.SeriesDescription = ''
    ds.PerformingPhysicianName = '00558747^'
    ds.ManufacturerModelName = 'DRS'
    ds.PatientName = 'Rubo DEMO'
    ds.PatientID = pydicom.uid.generate_uid()
    ds.PatientBirthDate = ''
    ds.PatientSex = 'F'
    ds.PatientAge = ''
    ds.KVP = None
    ds.SoftwareVersions = '4.00'
    ds.ExposureTime = None
    ds.XRayTubeCurrent = None
    ds.RadiationSetting = 'GR'
    ds.AcquisitionDeviceProcessingDescription = '10 OUT OF 20. 0=LOW, 20=HIGH CONVOLUTION KERNEL'
    ds.ShutterShape = ['CIRCULAR', 'RECTANGULAR']
    ds.ShutterLeftVerticalEdge = '10'
    ds.ShutterRightVerticalEdge = '950'
    ds.ShutterUpperHorizontalEdge = '10'
    ds.ShutterLowerHorizontalEdge = '950'
    ds.CenterOfCircularShutter = [480, 480]
    ds.RadiusOfCircularShutter = '470'
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyID = ''
    ds.SeriesNumber = '1'
    ds.InstanceNumber = '2'
    ds.PatientOrientation = ''
    ds.ImageComments = 'L1'
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.Rows = 1024
    ds.Columns = 1024
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PixelIntensityRelationship = 'LIN'
    ds.WindowCenter = '127.0'
    ds.WindowWidth = '255.0'
    ds.LossyImageCompression = '00'
    ds.RepresentativeFrameNumber = 1
    ds.FrameNumbersOfInterest = 2
    ds.FrameOfInterestDescription = 'L1'
    ds.PixelData = np.arange(ds.Rows*ds.Columns, dtype=np.uint16)

