# Coded version of DICOM file 'C:\Users\steve\Dropbox\Software\QIB-Sheffield\dbdicom\tests\data\VPH-Pelvis-CT\vhf.1000.dcm'
# Produced by pydicom codify utility script
import numpy as np
import pydicom
from pydicom.dataset import FileMetaDataset
from pydicom.sequence import Sequence


def default(ds): #VPH

    # File meta info data elements
    ds.file_meta = FileMetaDataset()
    ds.file_meta.FileMetaInformationGroupLength = 194
    ds.file_meta.FileMetaInformationVersion = b'\x00\x01'
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.file_meta.MediaStorageSOPInstanceUID = '1.2.826.0.1.3680043.2.1125.1.75064541463040.2005072610414630768'
    ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    ds.file_meta.ImplementationClassUID = '1.2.840.10008.5.1.4.1.1.7'
    ds.file_meta.SourceApplicationEntityTitle = 'GDCM'

    ds.is_implicit_VR = False
    ds.is_little_endian = True

    # Main data elements
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'AXIAL']
    ds.InstanceCreationDate = '20050726'
    ds.InstanceCreationTime = '104146'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.StudyDate = '20050101'
    ds.StudyTime = '010100.000000'
    ds.AccessionNumber = '1'
    ds.Modality = 'CT'
    ds.Manufacturer = 'GDCM'
    ds.InstitutionName = 'National Library of Medicine'
    ds.InstitutionAddress = 'http://www-creatis.insa-lyon.fr/Public/Gdcm'
    ds.ReferringPhysicianName = 'Unknown'
    ds.StudyDescription = 'Visible Human Female'
    ds.SeriesDescription = 'Resampled to 1mm voxels'
    ds.PatientName = 'Eve'
    ds.PatientID = pydicom.uid.generate_uid()
    ds.PatientBirthDate = '20050101'
    ds.PatientBirthTime = '010100.000000'
    ds.PatientSex = 'F'
    ds.SliceThickness = '1.0'
    ds.PatientPosition = 'HFS'
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyID = '1'
    ds.SeriesNumber = '1'
    ds.InstanceNumber = '1000'
    ds.ImagePositionPatient = [0, 0, 999]
    ds.ImageOrientationPatient = [1.000000, 0.000000, 0.000000, 0.000000, 1.000000, 0.000000]
    ds.FrameOfReferenceUID = '1.2.826.0.1.3680043.2.1125.1.75064541463040.2005072610384286419'
    ds.PositionReferenceIndicator = 'SN'
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.Rows = 512
    ds.Columns = 512
    ds.PixelSpacing = [1.000000, 1.000000]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.RescaleIntercept = '-1024.0'
    ds.RescaleSlope = '1.0'
    ds.add_new((0x7fe0, 0x0000), 'UL', 524300)
    ds.PixelData = np.arange(ds.Rows*ds.Columns, dtype=np.uint16)

    return ds