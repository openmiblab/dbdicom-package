# Coded version of DICOM file 'C:\Users\steve\Dropbox\Software\QIB-Sheffield\dbdicom\tests\data\UltrasoundPaletteColor-dicom_viewer_0020\0020.DCM'
# Produced by pydicom codify utility script
import numpy as np

import pydicom
from pydicom.dataset import FileMetaDataset
from pydicom.sequence import Sequence


def default(ds):

    # File meta info data elements
    ds.file_meta = FileMetaDataset()
    ds.file_meta.FileMetaInformationGroupLength = 138
    ds.file_meta.FileMetaInformationVersion = b'\x00\x01'
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.3.1'
    ds.file_meta.MediaStorageSOPInstanceUID = '999.999.133.1996.1.1800.1.6.29'
    ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.5'
    ds.file_meta.ImplementationClassUID = '999.999.332346'

    ds.is_implicit_VR = False
    ds.is_little_endian = True

    # Main data elements
    ds.add_new((0x0008, 0x0000), 'UL', 226)
    ds.ImageType = ''
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.3.1'
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.StudyDate = '19940323'
    ds.StudyTime = '115104.0'
    ds.AccessionNumber = ''
    ds.Modality = 'US'
    ds.Manufacturer = ''
    ds.ReferringPhysicianName = '------------------'
    ds.StudyDescription = 'Echocardiogram'
    ds.SeriesDescription = 'IAS FEN2'
    ds.add_new((0x0010, 0x0000), 'UL', 70)
    ds.PatientName = 'Rubo DEMO'
    ds.PatientID = pydicom.uid.generate_uid()
    ds.PatientBirthDate = '19231016'
    ds.PatientSex = 'F'
    ds.add_new((0x0018, 0x0000), 'UL', 18)
    ds.FrameTime = '62.727272'
    ds.add_new((0x0020, 0x0000), 'UL', 120)
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyID = '027893462'
    ds.SeriesNumber = '5829'
    ds.InstanceNumber = '28'
    ds.PatientOrientation = ''
    ds.ImageComments = 'IAS FEN2'
    ds.add_new((0x0028, 0x0000), 'UL', 1754)
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'PALETTE COLOR'
    ds.NumberOfFrames = '11'
    ds.FrameIncrementPointer = (0x0018, 0x1063)
    ds.Rows = 430
    ds.Columns = 600
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.RedPaletteColorLookupTableDescriptor = [256, 0, 16]
    ds.GreenPaletteColorLookupTableDescriptor = [256, 0, 16]
    ds.BluePaletteColorLookupTableDescriptor = [256, 0, 16]
    ds.PaletteColorLookupTableUID = '999.999.389972238'
    ds.RedPaletteColorLookupTableData = np.arange(256, dtype=np.uint16)
    ds.GreenPaletteColorLookupTableData = np.arange(256, dtype=np.uint16)
    ds.BluePaletteColorLookupTableData = np.arange(256, dtype=np.uint16)
    ds.PixelData = np.arange(ds.Rows*ds.Columns, dtype=np.uint16)

