# Coded version of DICOM file 'C:\Users\steve\Dropbox\Software\QIB-Sheffield\dbdicom\tests\data\MULTIFRAME\IM_0010'
# Produced by pydicom codify utility script
from datetime import datetime
from datetime import timedelta

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    generate_uid,
    MRImageStorage,
    EnhancedMRImageStorage,
    ExplicitVRLittleEndian
)


from dbdicom.utils import image


import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, EnhancedMRImageStorage, generate_uid
from datetime import datetime, timedelta


def create_5d_enhanced_mr_dataset(
    time_points=20, flip_angles=10, slices=4, rows=128, cols=192
):
    total_frames = time_points * flip_angles * slices
    now = datetime.now()

    # File Meta Info
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = EnhancedMRImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Create FileDataset
    ds = FileDataset(
        filename_or_obj=None,
        dataset=Dataset(),
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Identification
    ds.SOPClassUID = EnhancedMRImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PatientName = "FiveD^Phantom"
    ds.PatientID = "555555"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "MR"
    ds.Manufacturer = "PythonPACS"
    ds.StudyID = "1"
    ds.SeriesNumber = "1"
    ds.InstanceNumber = "1"

    # Image Dimensions
    ds.Rows = rows
    ds.Columns = cols
    ds.NumberOfFrames = str(total_frames)
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.PixelSpacing = [1.0, 1.0]
    ds.SliceThickness = 1.0
    ds.FrameOfReferenceUID = generate_uid()

    # Dummy pixel data
    pixel_array = np.zeros((total_frames, rows, cols), dtype=np.uint16)
    ds.PixelData = pixel_array.tobytes()

    # Shared Functional Groups
    shared_fg = Dataset()
    pix_meas = Dataset()
    pix_meas.PixelSpacing = ds.PixelSpacing
    pix_meas.SliceThickness = ds.SliceThickness
    shared_fg.PixelMeasuresSequence = [pix_meas]
    ds.SharedFunctionalGroupsSequence = [shared_fg]

    # Dimension Organization
    dim_org_uid = generate_uid()
    ds.DimensionOrganizationSequence = Sequence([
        Dataset()
    ])
    ds.DimensionOrganizationSequence[0].DimensionOrganizationUID = dim_org_uid

    ds.DimensionIndexSequence = Sequence()

    # Time dimension
    temporal = Dataset()
    temporal.DimensionOrganizationUID = dim_org_uid
    temporal.DimensionIndexPointer = 0x00209164  # TemporalPositionIndex
    temporal.FunctionalGroupPointer = 0x00209113  # TemporalPositionSequence
    ds.DimensionIndexSequence.append(temporal)

    # Flip angle dimension
    flip = Dataset()
    flip.DimensionOrganizationUID = dim_org_uid
    flip.DimensionIndexPointer = 0x00181314  # FlipAngle
    flip.FunctionalGroupPointer = 0x00189105  # MRImagingModifierSequence
    ds.DimensionIndexSequence.append(flip)

    # Slice position
    slice_dim = Dataset()
    slice_dim.DimensionOrganizationUID = dim_org_uid
    slice_dim.DimensionIndexPointer = 0x00200032  # ImagePositionPatient
    slice_dim.FunctionalGroupPointer = 0x00209113  # PlanePositionSequence
    ds.DimensionIndexSequence.append(slice_dim)

    # Per-Frame Functional Groups
    per_frame_seq = []

    base_time = now
    flip_angle_values = np.linspace(5, 50, flip_angles)  # Example flip angles

    for t in range(time_points):
        for f in range(flip_angles):
            for z in range(slices):
                frame = Dataset()

                # Frame content
                fc = Dataset()
                fc.FrameAcquisitionNumber = len(per_frame_seq)
                fc.AcquisitionTime = (base_time + timedelta(seconds=t)).strftime("%H%M%S.%f")[:13]
                frame.FrameContentSequence = [fc]

                # Temporal position
                tp = Dataset()
                tp.TemporalPositionIndex = t + 1
                frame.TemporalPositionSequence = [tp]

                # Flip angle
                fa = Dataset()
                fa.FlipAngle = float(flip_angle_values[f])
                frame.MRImagingModifierSequence = [fa]

                # Slice position
                pos = Dataset()
                pos.ImagePositionPatient = [0.0, 0.0, float(z)]
                frame.PlanePositionSequence = [pos]

                per_frame_seq.append(frame)

    ds.PerFrameFunctionalGroupsSequence = Sequence(per_frame_seq)

    return ds






def default(): # UKRIN-MAPS


    ds = Dataset()

    # File meta info data elements
    ds.file_meta = FileMetaDataset()
    ds.file_meta.FileMetaInformationGroupLength = 204
    ds.file_meta.FileMetaInformationVersion = b'\x00\x01'
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.file_meta.MediaStorageSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611151582180'
    ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'
    ds.file_meta.ImplementationClassUID = '1.3.46.670589.11.0.0.51.4.56.1'
    ds.file_meta.ImplementationVersionName = 'Philips MR 56.1'
    
    ds.is_implicit_VR = False
    ds.is_little_endian = True

    # Main data elements
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'T1', 'NONE']
    ds.InstanceCreationDate = '20210616'
    ds.InstanceCreationTime = '152058.057'
    ds.InstanceCreatorUID = '1.3.46.670589.11.89.5'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.SOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611151582180'
    ds.StudyDate = '20210616'
    ds.SeriesDate = '20210616'
    ds.ContentDate = '20210616'
    ds.AcquisitionDateTime = '20210616111515.81000'
    ds.StudyTime = '105739'
    ds.SeriesTime = '111515.81000'
    ds.ContentTime = '111515.81000'
    ds.Modality = 'MR'
    ds.ConversionType = ''
    ds.Manufacturer = 'Philips Medical Systems'
    ds.InstitutionName = 'Nottingham University'
    ds.InstitutionAddress = 'University Park'
    ds.ReferringPhysicianName = ''
    ds.CodeValue = ''
    ds.CodingSchemeDesignator = ''
    ds.CodeMeaning = ''
    ds.StationName = 'HOST-2ADB2S6FDM'
    ds.StudyDescription = '14407_002'
    ds.SeriesDescription = 'Ax_localiser_BH'
    ds.InstitutionalDepartmentName = 'SPMIC'
    ds.PerformingPhysicianName = 'CB'
    ds.OperatorsName = ''
    ds.AdmittingDiagnosesDescription = ''
    ds.ManufacturerModelName = 'Ingenia'
    ds.ReferencedPerformedProcedureStepSequence = Sequence([Dataset()])
    ds.ReferencedPerformedProcedureStepSequence[0].InstanceCreationDate = '20210616'
    ds.ReferencedPerformedProcedureStepSequence[0].InstanceCreationTime = '105739.631'
    ds.ReferencedPerformedProcedureStepSequence[0].InstanceCreatorUID = '1.3.46.670589.11.89.5'
    ds.ReferencedPerformedProcedureStepSequence[0].ReferencedSOPClassUID = '1.2.840.10008.3.1.2.3.3'
    ds.ReferencedPerformedProcedureStepSequence[0].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.0.16828.2021061610573963005'
    ds.ReferencedPerformedProcedureStepSequence[0].InstanceNumber = '0'
    ds.ReferencedImageEvidenceSequence = Sequence([Dataset() for _ in range(3)])
    ds.ReferencedImageEvidenceSequence[0].ReferencedSeriesSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[0].ReferencedSeriesSequence[0].ReferencedSOPSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[0].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageEvidenceSequence[0].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[0].ReferencedSeriesSequence[0].SeriesInstanceUID = '1.3.46.670589.11.71459.5.0.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[0].StudyInstanceUID = '1.3.46.670589.11.71459.5.0.16828.2021061610573962004'
    ds.ReferencedImageEvidenceSequence[1].ReferencedSeriesSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[1].ReferencedSeriesSequence[0].ReferencedSOPSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[1].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageEvidenceSequence[1].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[1].ReferencedSeriesSequence[0].SeriesInstanceUID = '1.3.46.670589.11.71459.5.0.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[1].StudyInstanceUID = '1.3.46.670589.11.71459.5.0.16828.2021061610573962004'
    ds.ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence[0].ReferencedSOPSequence = Sequence([Dataset()])
    ds.ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[2].ReferencedSeriesSequence[0].SeriesInstanceUID = '1.3.46.670589.11.71459.5.0.4024.2021061611103722062'
    ds.ReferencedImageEvidenceSequence[2].StudyInstanceUID = '1.3.46.670589.11.71459.5.0.16828.2021061610573962004'
    ds.CreatorVersionUID = '1.3.46.670589.11'
    ds.PixelPresentation = 'MONOCHROME'
    ds.VolumetricProperties = 'VOLUME'
    ds.VolumeBasedCalculationTechnique = 'NONE'
    ds.ComplexImageComponent = 'MAGNITUDE'
    ds.AcquisitionContrast = 'T1'
    ds.PatientName = 'travelkidney21'
    ds.PatientID = 'UKRIN_SPMIC_001'
    ds.PatientSex = 'M'
    ds.PatientWeight = '65.0'
    ds.PatientComments = ''
    ds.DeidentificationMethod = 'CR common deidentification v001'
    ds.DeidentificationMethodCodeSequence = Sequence([Dataset()])
    ds.DeidentificationMethodCodeSequence[0].CodeValue = '34'
    ds.DeidentificationMethodCodeSequence[0].CodingSchemeDesignator = 'XNAT'
    ds.DeidentificationMethodCodeSequence[0].CodingSchemeVersion = '1.0'
    ds.DeidentificationMethodCodeSequence[0].CodeMeaning = 'XNAT DicomEdit 4 Script'
    ds.BodyPartExamined = 'KIDNEY'
    ds.ScanOptions = 'RG'
    ds.MRAcquisitionType = '2D'
    ds.InversionTime = '0.0'
    ds.MagneticFieldStrength = '3.0'
    ds.NumberOfPhaseEncodingSteps = '227'
    ds.EchoTrainLength = '76'
    ds.PercentSampling = '114.0'
    ds.PercentPhaseFieldOfView = '100.0'
    ds.PixelBandwidth = '992.0'
    ds.DeviceSerialNumber = '71459'
    ds.SecondaryCaptureDeviceID = ''
    ds.SecondaryCaptureDeviceManufacturer = ''
    ds.SecondaryCaptureDeviceManufacturerModelName = ''
    ds.SecondaryCaptureDeviceSoftwareVersions = ''
    ds.SoftwareVersions = ['5.6.1', '5.6.1.0']
    ds.VideoImageFormatAcquired = ''
    ds.DigitalImageFormatAcquired = ''
    ds.ProtocolName = 'WIP Ax_localiser_BH'
    ds.B1rms = 2.0383660793304443
    ds.PatientPosition = 'FFS'
    ds.ContentQualification = 'RESEARCH'
    ds.PulseSequenceName = 'B-TFE'
    ds.EchoPulseSequence = 'GRADIENT'
    ds.MultiPlanarExcitation = 'NO'
    ds.PhaseContrast = 'NO'
    ds.TimeOfFlightContrast = 'NO'
    ds.Spoiling = 'NONE'
    ds.SteadyStatePulseSequence = 'FREE_PRECESSION'
    ds.EchoPlanarPulseSequence = 'NO'
    ds.TagAngleFirstAxis = 7.23e+75
    ds.MagnetizationTransfer = 'NONE'
    ds.T2Preparation = 'NO'
    ds.BloodSignalNulling = 'NO'
    ds.SaturationRecovery = 'NO'
    ds.SpectrallySelectedSuppression = 'NONE'
    ds.SpectrallySelectedExcitation = 'NONE'
    ds.SpatialPresaturation = 'NONE'
    ds.Tagging = 'NONE'
    ds.OversamplingPhase = '2D'
    ds.TagSpacingFirstDimension = 7.23e+75
    ds.GeometryOfKSpaceTraversal = 'RECTILINEAR'
    ds.SegmentedKSpaceTraversal = 'PARTIAL'
    ds.RectilinearPhaseEncodeReordering = 'UNKNOWN'
    ds.TagThickness = 0.0
    ds.PartialFourierDirection = ''
    ds.CardiacSynchronizationTechnique = 'NONE'
    ds.TransmitCoilManufacturerName = ''
    ds.TransmitCoilType = 'SURFACE'
    ds.ChemicalShiftReference = [4.68, 4.68]
    ds.MRAcquisitionFrequencyEncodingSteps = 200
    ds.Decoupling = 'NO'
    ds.DecoupledNucleus = ''
    ds.DecouplingMethod = ''
    ds.KSpaceFiltering = 'RIESZ'
    ds.TimeDomainFiltering = ''
    ds.ParallelReductionFactorInPlane = 3.0
    ds.AcquisitionDuration = 11.148174285888672
    ds.ParallelAcquisition = 'YES'
    ds.ParallelAcquisitionTechnique = 'SENSE'
    ds.PartialFourier = 'NO'
    ds.VelocityEncodingDirection = [0.0, 0.0, 0.0]
    ds.VelocityEncodingMinimumValue = 0.0
    ds.NumberOfKSpaceTrajectories = 1
    ds.ResonantNucleus = '1H'
    ds.FrequencyCorrection = 'NO'
    ds.ParallelReductionFactorOutOfPlane = 1.0
    ds.ParallelReductionFactorSecondInPlane = 1.0
    ds.RespiratoryMotionCompensationTechnique = 'BREATH_HOLD'
    ds.RespiratorySignalSource = 'NONE'
    ds.BulkMotionCompensationTechnique = 'NONE'
    ds.ApplicableSafetyStandardAgency = 'IEC'
    ds.SpecificAbsorptionRateDefinition = 'IEC_WHOLE_BODY'
    ds.GradientOutputType = 'DB_DT'
    ds.SpecificAbsorptionRateValue = 2.69488263130188
    ds.GradientOutput = 49.73076629638672
    ds.FlowCompensationDirection = ''
    ds.WaterReferencedPhaseCorrection = 'NO'
    ds.MRSpectroscopyAcquisitionType = ''
    ds.MRAcquisitionPhaseEncodingStepsInPlane = 227
    ds.RFEchoTrainLength = 0
    ds.GradientEchoTrainLength = 76
    ds.StudyInstanceUID = '1.3.46.670589.11.71459.5.0.16828.2021061610573962004'
    ds.SeriesInstanceUID = '1.3.46.670589.11.71459.5.0.4024.2021061611151582180'
    ds.StudyID = '663674259'
    ds.SeriesNumber = '401'
    ds.AcquisitionNumber = '4'
    ds.InstanceNumber = '1'
    ds.FrameOfReferenceUID = '1.3.46.670589.11.71459.5.0.19740.2021061611091352001'
    ds.PositionReferenceIndicator = ''
    ds.FrameLaterality = 'U'
    ds.DimensionOrganizationSequence = Sequence([Dataset()])
    ds.DimensionOrganizationSequence[0].DimensionOrganizationUID = '1.3.46.670589.11.71459.5.0.1860.2021061615205802000'
    ds.DimensionIndexSequence = Sequence([Dataset() for _ in range(2)])
    ds.DimensionIndexSequence[0].DimensionOrganizationUID = '1.3.46.670589.11.71459.5.0.1860.2021061615205802000'
    ds.DimensionIndexSequence[0].DimensionIndexPointer = (0x0020, 0x9056)
    ds.DimensionIndexSequence[0].FunctionalGroupPointer = (0x0020, 0x9111)
    ds.DimensionIndexSequence[0].DimensionDescriptionLabel = 'Stack ID'
    ds.DimensionIndexSequence[1].DimensionOrganizationUID = '1.3.46.670589.11.71459.5.0.1860.2021061615205802000'
    ds.DimensionIndexSequence[1].DimensionIndexPointer = (0x0020, 0x9057)
    ds.DimensionIndexSequence[1].FunctionalGroupPointer = (0x0020, 0x9111)
    ds.DimensionIndexSequence[1].DimensionDescriptionLabel = 'In-Stack Position Number'
    ds.RespiratoryIntervalTime = 0.0
    ds.NominalRespiratoryTriggerDelayTime = 0.0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.NumberOfFrames = '5'
    ds.Rows = 128
    ds.Columns = 128
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.BurnedInAnnotation = 'NO'
    ds.LossyImageCompression = '00'
    ds.DataPointRows = 1
    ds.DataPointColumns = 0
    ds.SignalDomainColumns = ''
    ds.DataRepresentation = ''
    ds.RequestingPhysician = ''
    ds.RequestingService = ''
    ds.RequestedProcedureDescription = ''
    ds.RequestedContrastAgent = ''
    ds.StudyComments = ''
    ds.SpecialNeeds = ''
    ds.ScheduledPerformingPhysicianName = 'CB'
    ds.PerformedStationAETitle = 'Ingenia3T'
    ds.PerformedStationName = ''
    ds.PerformedLocation = ''
    ds.PerformedProcedureStepStartDate = '20210616'
    ds.PerformedProcedureStepStartTime = '105739'
    ds.PerformedProcedureStepEndDate = '20210616'
    ds.PerformedProcedureStepEndTime = '105739'
    ds.PerformedProcedureStepStatus = ''
    ds.PerformedProcedureStepID = '663674259'
    ds.PerformedProcedureStepDescription = 'FMHS36122002'
    ds.PerformedProcedureTypeDescription = ''
    ds.PerformedProtocolCodeSequence = Sequence([Dataset()])
    ds.PerformedProtocolCodeSequence[0] = Dataset()
    ds.PerformedProtocolCodeSequence[0].CodeValue = 'UNDEFINED'
    ds.PerformedProtocolCodeSequence[0].CodingSchemeDesignator = 'UNDEFINED'
    ds.PerformedProtocolCodeSequence[0].CodeMeaning = 'UNDEFINED'
    ds.PerformedProtocolCodeSequence[0].ContextGroupExtensionFlag = 'N'
    ds.CommentsOnThePerformedProcedureStep = ''
    ds.AcquisitionContextSequence = Sequence()
    ds.RequestedProcedureID = ''
    ds.ReasonForTheRequestedProcedure = ''
    ds.RequestedProcedurePriority = ''
    ds.PatientTransportArrangements = ''
    ds.RequestedProcedureLocation = ''
    ds.ReasonForTheImagingServiceRequest = ''
    ds.IssueDateOfImagingServiceRequest = '20210616'
    ds.IssueTimeOfImagingServiceRequest = '105739.627'
    ds.OrderEntererLocation = ''
    ds.OrderCallbackPhoneNumber = ''
    ds.ImagingServiceRequestComments = ''
    ds.LUTLabel = 'Philips'
    ds.PresentationLUTShape = 'IDENTITY'
    ds.SharedFunctionalGroupsSequence = ukrin_maps_shared_functional_groups_sequence()
    ds.PerFrameFunctionalGroupsSequence = ukrin_maps_per_frame_functional_groups_sequence()
    ds.PixelData = np.arange(ds.Rows*ds.Columns*ds.NumberOfFrames, dtype=np.uint16)

    return ds


def ukrin_maps_shared_functional_groups_sequence():

    fg = ukrin_maps_shared_functional_group()
    return Sequence([fg])


def ukrin_maps_shared_functional_group():

    ds = Dataset()

    ds.ReferencedImageSequence = Sequence([Dataset() for _ in range(3)])
    ds.ReferencedImageSequence[0].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageSequence[0].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageSequence[0].ReferencedFrameNumber = '10'
    ds.ReferencedImageSequence[0].PurposeOfReferenceCodeSequence = Sequence([Dataset()])
    ds.ReferencedImageSequence[0].PurposeOfReferenceCodeSequence[0].CodeValue = '121311'
    ds.ReferencedImageSequence[0].PurposeOfReferenceCodeSequence[0].CodingSchemeDesignator = 'DCM'
    ds.ReferencedImageSequence[0].PurposeOfReferenceCodeSequence[0].CodeMeaning = 'Localizer'
    ds.ReferencedImageSequence[0].PurposeOfReferenceCodeSequence[0].ContextUID = '1.2.840.10008.6.1.508'
    ds.ReferencedImageSequence[1].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageSequence[1].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageSequence[1].ReferencedFrameNumber = '41'
    ds.ReferencedImageSequence[1].PurposeOfReferenceCodeSequence = Sequence([Dataset()])
    ds.ReferencedImageSequence[1].PurposeOfReferenceCodeSequence[0].CodeValue = '121311'
    ds.ReferencedImageSequence[1].PurposeOfReferenceCodeSequence[0].CodingSchemeDesignator = 'DCM'
    ds.ReferencedImageSequence[1].PurposeOfReferenceCodeSequence[0].CodeMeaning = 'Localizer'
    ds.ReferencedImageSequence[1].PurposeOfReferenceCodeSequence[0].ContextUID = '1.2.840.10008.6.1.508'
    ds.ReferencedImageSequence[2].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.4.1'
    ds.ReferencedImageSequence[2].ReferencedSOPInstanceUID = '1.3.46.670589.11.71459.5.20.1.1.4024.2021061611103722062'
    ds.ReferencedImageSequence[2].ReferencedFrameNumber = '49'
    ds.ReferencedImageSequence[2].PurposeOfReferenceCodeSequence = Sequence([Dataset()])
    ds.ReferencedImageSequence[2].PurposeOfReferenceCodeSequence[0].CodeValue = '121311'
    ds.ReferencedImageSequence[2].PurposeOfReferenceCodeSequence[0].CodingSchemeDesignator = 'DCM'
    ds.ReferencedImageSequence[2].PurposeOfReferenceCodeSequence[0].CodeMeaning = 'Localizer'
    ds.ReferencedImageSequence[2].PurposeOfReferenceCodeSequence[0].ContextUID = '1.2.840.10008.6.1.508'

    ds.MRImagingModifierSequence = Sequence([Dataset()])
    ds.MRImagingModifierSequence[0].PixelBandwidth = '992.0634765625'
    ds.MRImagingModifierSequence[0].MagnetizationTransfer = 'NONE'
    ds.MRImagingModifierSequence[0].BloodSignalNulling = 'NO'
    ds.MRImagingModifierSequence[0].Tagging = 'NONE'
    ds.MRImagingModifierSequence[0].TransmitterFrequency = 127.749096

    ds.MRReceiveCoilSequence = Sequence([Dataset()])
    ds.MRReceiveCoilSequence[0].ReceiveCoilName = 'MULTI COIL'
    ds.MRReceiveCoilSequence[0].ReceiveCoilManufacturerName = ''
    ds.MRReceiveCoilSequence[0].ReceiveCoilType = 'MULTICOIL'
    ds.MRReceiveCoilSequence[0].QuadratureReceiveCoil = 'NO'
    ds.MRReceiveCoilSequence[0].MultiCoilDefinitionSequence = Sequence([Dataset()])
    ds.MRReceiveCoilSequence[0].MultiCoilDefinitionSequence[0].MultiCoilElementName = 'MULTI ELEMENT'
    ds.MRReceiveCoilSequence[0].MultiCoilDefinitionSequence[0].MultiCoilElementUsed = 'YES'

    ds.MRTransmitCoilSequence = Sequence([Dataset()])
    ds.MRTransmitCoilSequence[0].TransmitCoilName = 'S'
    ds.MRTransmitCoilSequence[0].TransmitCoilManufacturerName = ''
    ds.MRTransmitCoilSequence[0].TransmitCoilType = 'SURFACE'

    ds.MRTimingAndRelatedParametersSequence = Sequence([Dataset()])
    ds.MRTimingAndRelatedParametersSequence[0].RepetitionTime = '3.06139993667602'
    ds.MRTimingAndRelatedParametersSequence[0].EchoTrainLength = '76'
    ds.MRTimingAndRelatedParametersSequence[0].FlipAngle = '50.0'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence = Sequence([Dataset() for _ in range(3)])
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[0].OperatingModeType = 'STATIC FIELD'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[0].OperatingMode = 'IEC_FIRST_LEVEL'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[1].OperatingModeType = 'RF'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[1].OperatingMode = 'IEC_FIRST_LEVEL'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[2].OperatingModeType = 'GRADIENT'
    ds.MRTimingAndRelatedParametersSequence[0].OperatingModeSequence[2].OperatingMode = 'IEC_NORMAL'
    ds.MRTimingAndRelatedParametersSequence[0].GradientOutputType = 'DB_DT'
    ds.MRTimingAndRelatedParametersSequence[0].GradientOutput = 49.73076629638672
    ds.MRTimingAndRelatedParametersSequence[0].SpecificAbsorptionRateSequence = Sequence([Dataset()])
    ds.MRTimingAndRelatedParametersSequence[0].SpecificAbsorptionRateSequence[0].SpecificAbsorptionRateDefinition = 'IEC_WHOLE_BODY'
    ds.MRTimingAndRelatedParametersSequence[0].SpecificAbsorptionRateSequence[0].SpecificAbsorptionRateValue = 2.69488263130188
    ds.MRTimingAndRelatedParametersSequence[0].RFEchoTrainLength = 0
    ds.MRTimingAndRelatedParametersSequence[0].GradientEchoTrainLength = 76

    ds.MRModifierSequence = Sequence([Dataset()])
    ds.MRModifierSequence[0].InversionRecovery = 'NO'
    ds.MRModifierSequence[0].FlowCompensation = 'NONE'
    ds.MRModifierSequence[0].Spoiling = 'NONE'
    ds.MRModifierSequence[0].T2Preparation = 'NO'
    ds.MRModifierSequence[0].SpectrallySelectedExcitation = 'NONE'
    ds.MRModifierSequence[0].SpatialPresaturation = 'NONE'
    ds.MRModifierSequence[0].ParallelReductionFactorInPlane = 3.0
    ds.MRModifierSequence[0].ParallelAcquisition = 'YES'
    ds.MRModifierSequence[0].ParallelAcquisitionTechnique = 'SENSE'
    ds.MRModifierSequence[0].PartialFourier = 'NO'
    ds.MRModifierSequence[0].ParallelReductionFactorOutOfPlane = 1.0
    ds.MRModifierSequence[0].ParallelReductionFactorSecondInPlane = 1.0

    ds.MRAveragesSequence = Sequence([Dataset()])
    ds.MRAveragesSequence[0].NumberOfAverages = '1.0'

    ds.MRFOVGeometrySequence = Sequence([Dataset()])
    ds.MRFOVGeometrySequence[0].PercentSampling = '114.0'
    ds.MRFOVGeometrySequence[0].PercentPhaseFieldOfView = '100.0'
    ds.MRFOVGeometrySequence[0].InPlanePhaseEncodingDirection = 'ROW'
    ds.MRFOVGeometrySequence[0].MRAcquisitionFrequencyEncodingSteps = 200
    ds.MRFOVGeometrySequence[0].MRAcquisitionPhaseEncodingStepsInPlane = 227
    ds.MRFOVGeometrySequence[0].MRAcquisitionPhaseEncodingStepsOutOfPlane = 1

    ds.FrameAnatomySequence = Sequence([Dataset()])
    ds.FrameAnatomySequence[0].AnatomicRegionSequence = Sequence([Dataset()])
    ds.FrameAnatomySequence[0].AnatomicRegionSequence[0].CodeValue = 'T-71000'
    ds.FrameAnatomySequence[0].AnatomicRegionSequence[0].CodingSchemeDesignator = 'SRT'
    ds.FrameAnatomySequence[0].AnatomicRegionSequence[0].CodeMeaning = 'Kidney'
    ds.FrameAnatomySequence[0].AnatomicRegionSequence[0].ContextUID = '1.2.840.10008.6.1.307'
    ds.FrameAnatomySequence[0].FrameLaterality = 'U'

    return ds


def ukrin_maps_per_frame_functional_groups_sequence():

    NumberOfFrames = 5

    fg = []
    for _ in range(NumberOfFrames):
        fg.append(ukrin_maps_per_frame_functional_group())

    fg[0].FrameContentSequence[0].InStackPositionNumber = 1
    fg[0].FrameContentSequence[0].DimensionIndexValues = [1, 1]
    fg[0].PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -77.157058715820]
    fg[0].FrameVOILUTSequence[0].WindowCenter = '1070.0'
    fg[0].FrameVOILUTSequence[0].WindowWidth = '1860.0' 
       
    fg[1].FrameContentSequence[0].InStackPositionNumber = 2
    fg[1].FrameContentSequence[0].DimensionIndexValues = [1, 2]
    fg[1].PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -70.157058715820]
    fg[1].FrameVOILUTSequence[0].WindowCenter = '1089.0'
    fg[1].FrameVOILUTSequence[0].WindowWidth = '1893.0'
    
    fg[2].FrameContentSequence[0].InStackPositionNumber = 3
    fg[2].FrameContentSequence[0].DimensionIndexValues = [1, 3]
    fg[2].PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -63.157058715820]
    fg[2].FrameVOILUTSequence[0].WindowCenter = '1107.0'
    fg[2].FrameVOILUTSequence[0].WindowWidth = '1924.0'
    
    fg[3].FrameContentSequence[0].InStackPositionNumber = 4
    fg[3].FrameContentSequence[0].DimensionIndexValues = [1, 4]
    fg[3].PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -56.157058715820]
    fg[3].FrameVOILUTSequence[0].WindowCenter = '1135.0'
    fg[3].FrameVOILUTSequence[0].WindowWidth = '1974.0'
    
    fg[4].FrameContentSequence[0].InStackPositionNumber = 5
    fg[4].FrameContentSequence[0].DimensionIndexValues = [1, 5]
    fg[4].PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -49.157058715820]
    fg[4].FrameVOILUTSequence[0].WindowCenter = '1094.0'
    fg[4].FrameVOILUTSequence[0].WindowWidth = '1902.0'

    return Sequence(fg)


def ukrin_maps_per_frame_functional_group():

    ds = Dataset()
    
    ds.MREchoSequence = Sequence([Dataset()])
    ds.MREchoSequence[0].EffectiveEchoTime = 1.531

    ds.MRMetaboliteMapSequence = Sequence([Dataset()])
    ds.MRMetaboliteMapSequence[0].MetaboliteMapDescription = 'WATER'

    ds.MRImageFrameTypeSequence = Sequence([Dataset()])
    ds.MRImageFrameTypeSequence[0].FrameType = ['ORIGINAL', 'PRIMARY', 'T1', 'NONE']
    ds.MRImageFrameTypeSequence[0].PixelPresentation = 'MONOCHROME'
    ds.MRImageFrameTypeSequence[0].VolumetricProperties = 'VOLUME'
    ds.MRImageFrameTypeSequence[0].VolumeBasedCalculationTechnique = 'NONE'
    ds.MRImageFrameTypeSequence[0].ComplexImageComponent = 'MAGNITUDE'
    ds.MRImageFrameTypeSequence[0].AcquisitionContrast = 'T1'

    ds.FrameContentSequence = Sequence([Dataset()])
    ds.FrameContentSequence[0].FrameAcquisitionDateTime = '20210616111544.65'
    ds.FrameContentSequence[0].FrameReferenceDateTime = '20210616111515.81000'
    ds.FrameContentSequence[0].FrameAcquisitionDuration = 11148.174285888672
    ds.FrameContentSequence[0].StackID = '1'
    ds.FrameContentSequence[0].InStackPositionNumber = 1
    ds.FrameContentSequence[0].TemporalPositionIndex = 1
    ds.FrameContentSequence[0].DimensionIndexValues = [1, 1]

    ds.PlanePositionSequence = Sequence([Dataset()])
    ds.PlanePositionSequence[0].ImagePositionPatient = [-194.70974302291, -149.94026184082, -77.157058715820]

    ds.PlaneOrientationSequence = Sequence([Dataset()])
    ds.PlaneOrientationSequence[0].ImageOrientationPatient = [1, 0, 0, 0, 1, 0]

    ds.PixelMeasuresSequence = Sequence([Dataset()])
    ds.PixelMeasuresSequence[0].SliceThickness = '7.0'
    ds.PixelMeasuresSequence[0].SpacingBetweenSlices = '7.0'
    ds.PixelMeasuresSequence[0].PixelSpacing = [1.5625, 1.5625]

    ds.FrameVOILUTSequence = Sequence([Dataset()])
    ds.FrameVOILUTSequence[0].WindowCenter = '1070.0'
    ds.FrameVOILUTSequence[0].WindowWidth = '1860.0'

    ds.PixelValueTransformationSequence = Sequence([Dataset()])
    ds.PixelValueTransformationSequence[0].RescaleIntercept = '0.0'
    ds.PixelValueTransformationSequence[0].RescaleSlope = '2.15579975579975'
    ds.PixelValueTransformationSequence[0].RescaleType = 'US'

    return ds

def get_window(ds):
    """Centre and width of the pixel data after applying rescale slope and intercept.
    
    In this case retrieve the centre and width values of the first frame
    NOT In USE
    """

    centre = ds.PerFrameFunctionalGroupsSequence[0].FrameVOILUTSequence[0].WindowCenter 
    width = ds.PerFrameFunctionalGroupsSequence[0].FrameVOILUTSequence[0].WindowWidth
    if centre is None or width is None:
        array = ds.get_pixel_array()
    if centre is None: 
        centre = np.median(array)
    if width is None: 
        p = np.percentile(array, [25, 75])
        width = p[1] - p[0]
    
    return centre, width

def get_pixel_array(ds):

    array = ds.pixel_array.astype(np.float32)
    frames = ds.PerFrameFunctionalGroupsSequence
    for index, frame in enumerate(frames):
        slice = np.squeeze(array[index, ...])
        if [0x2005, 0x100E] in ds: # 'Philips Rescale Slope'
            slope = ds[(0x2005, 0x100E)].value
            intercept = ds[(0x2005, 0x100D)].value
            slice = (slice - intercept) / slope
        else:
            transform = frame.PixelValueTransformationSequence[0]
            slope = float(getattr(transform, 'RescaleSlope', 1)) 
            intercept = float(getattr(transform, 'RescaleIntercept', 0)) 
            slice = slice * slope + intercept
        array[index, ...] = np.transpose(slice)
    
    return array


def set_pixel_array(ds, array, value_range=None):

    if (0x2005, 0x100E) in ds: 
        del ds[0x2005, 0x100E]  # Delete 'Philips Rescale Slope'
    if (0x2005, 0x100D) in ds: 
        del ds[0x2005, 0x100D]

    array = image.clip(array, value_range=value_range)
    array, slope, intercept = image.scale_to_range(array, ds.BitsAllocated)
    array = np.transpose(array, (0, 2, 1))

    maximum = np.amax(array)
    minimum = np.amin(array)
    shape = np.shape(array)

    ds.NumberOfFrames = np.shape(array)[0]
    del ds.PerFrameFunctionalGroupsSequence[ds.NumberOfFrames:]

    ds.PixelRepresentation = 0
    ds.SmallestImagePixelValue = int(maximum)
    ds.LargestImagePixelValue = int(minimum)
    ds.RescaleSlope = 1 / slope
    ds.RescaleIntercept = - intercept / slope
    ds.WindowCenter = (maximum + minimum) / 2
    ds.WindowWidth = maximum - minimum
    ds.Rows = shape[0]
    ds.Columns = shape[1]
    ds.PixelData = array.tobytes()


def image_type(ds):
    """Determine if a dataset is Magnitude, Phase, Real or Imaginary"""

    image_type = []
    for slice in ds.PerFrameFunctionalGroupsSequence:
        sequence = slice.MRImageFrameTypeSequence[0]

        if hasattr(sequence, 'FrameType'):
            type = set(sequence.FrameType)
            if set(['M', 'MAGNITUDE']).intersection(type):
                image_type.append('MAGNITUDE')
            elif set(['P', 'PHASE']).intersection(type):
                image_type.append('PHASE')
            elif set(['R', 'REAL']).intersection(type):
                image_type.append('REAL')
            elif set(['I', 'IMAGINARY']).intersection(type):
                image_type.append('IMAGINARY')
        elif hasattr(sequence, 'ComplexImageComponent'):
            type = set(sequence.ComplexImageComponent)
            if set(['M', 'MAGNITUDE']).intersection(type):
                image_type.append('MAGNITUDE')
            elif set(['P', 'PHASE']).intersection(type):
                image_type.append('PHASE')
            elif set(['R', 'REAL']).intersection(type):
                image_type.append('REAL')
            elif set(['I', 'IMAGINARY']).intersection(type):
                image_type.append('IMAGINARY')
        else:
            image_type.append('UNKNOWN')

    return image_type


def signal_type(ds):
    """Determine if an image is Water, Fat, In-Phase, Out-phase image or None"""

    signal_type = []
    for slice in ds.PerFrameFunctionalGroupsSequence:
        sequence = slice.MRImageFrameTypeSequence[0]

        if hasattr(sequence, 'FrameType'):
            type = set(sequence.FrameType)
            if set(['W', 'WATER']).intersection(type):
                signal_type.append('WATER')
            elif set(['F', 'FAT']).intersection(type):
                signal_type.append('FAT')
            elif set(['IP', 'IN_PHASE']).intersection(type):
                signal_type.append('IN-PHASE')
            elif set(['OP', 'OUT_PHASE']).intersection(type):
                signal_type.append('OP-PHASE')
        else:
            signal_type.append('UNKNOWN')

    return signal_type

def get_affine_matrix(ds):
    """Affine transformation matrix for all images in a multiframe image"""

    affineList = []
    for frame in ds.PerFrameFunctionalGroupsSequence:
        affine = image.affine_matrix(
            frame.PlaneOrientationSequence[0].ImageOrientationPatient, 
            frame.PlanePositionSequence[0].ImagePositionPatient, 
            frame.PixelMeasuresSequence[0].PixelSpacing, 
            frame.PixelMeasuresSequence[0].SliceThickness)
        affineList.append(affine)
    return np.squeeze(np.array(affineList))