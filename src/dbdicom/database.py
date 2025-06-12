import os
from tqdm import tqdm

import numpy as np
import pandas as pd
import pydicom

import dbdicom.utils.dcm4che as dcm4che
import dbdicom.utils.files as filetools
import dbdicom.dataset as dbdataset


COLUMNS = [   
    # Identifiers (unique)
    'PatientID', 
    'StudyInstanceUID', 
    'SeriesInstanceUID', 
    'SOPInstanceUID', 
    # Human-readable identifiers (not unique)
    'PatientName', 
    'StudyDescription', 
    'StudyDate', 
    'SeriesDescription', 
    'SeriesNumber', 
    'InstanceNumber', 
]

def read(path):
    files = filetools.all_files(path)
    tags = COLUMNS + ['NumberOfFrames'] # + ['SOPClassUID']
    array = []
    dicom_files = []
    for i, file in tqdm(enumerate(files), total=len(files), desc='Reading DICOM folder'):
        try:
            ds = pydicom.dcmread(file, force=True, specific_tags=tags+['Rows'])
        except:
            pass
        else:
            if isinstance(ds, pydicom.dataset.FileDataset):
                if 'TransferSyntaxUID' in ds.file_meta:
                    if not 'Rows' in ds: # Image only
                        continue
                    row = dbdataset.get_values(ds, tags)
                    array.append(row)
                    index = os.path.relpath(file, path)
                    dicom_files.append(index) 
    df = pd.DataFrame(array, index = dicom_files, columns = tags)
    df = _multiframe_to_singleframe(path, df)
    dbtree = _tree(df)
    return dbtree


def _multiframe_to_singleframe(path, df):
    """Converts all multiframe files in the folder into single-frame files.
    
    Reads all the multi-frame files in the folder,
    converts them to singleframe files, and delete the original multiframe file.
    """
    singleframe = df.NumberOfFrames.isnull() 
    multiframe = singleframe == False
    nr_multiframe = multiframe.sum()
    if nr_multiframe != 0: 
        for relpath in tqdm(df[multiframe].index.values, desc="Converting multiframe file " + relpath):
            filepath = os.path.join(path, relpath)
            singleframe_files = dcm4che.split_multiframe(filepath) 
            if singleframe_files != []:            
                # add the single frame files to the dataframe
                dfnew = read(singleframe_files, df.columns, path)
                df = pd.concat([df, dfnew])
                # delete the original multiframe 
                os.remove(filepath)
            # drop the file also if the conversion has failed
            df.drop(index=relpath, inplace=True)
    df.drop('NumberOfFrames', axis=1, inplace=True)
    return df


def _tree(df):
    # A human-readable summary tree

    df.sort_values(['PatientID','StudyInstanceUID','SeriesNumber'], inplace=True)
    df = df.fillna('None')
    summary = []

    for uid_patient in df.PatientID.unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        patient = {
            'PatientName': patient_name,
            'PatientID': uid_patient,
            'studies': [],
        }
        summary.append(patient)
        for uid_study in df_patient.StudyInstanceUID.unique():
            df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
            study_desc = df_study.StudyDescription.values[0]
            study_date = df_study.StudyDate.values[0]
            study = {
                'StudyDescription': study_desc,
                'StudyDate': study_date,
                'StudyInstanceUID': uid_study,
                'series': [],
            }
            patient['studies'].append(study)
            for uid_sery in df_study.SeriesInstanceUID.unique():
                df_series = df_study[df_study.SeriesInstanceUID == uid_sery]
                series_desc = df_series.SeriesDescription.values[0]
                series_nr = int(df_series.SeriesNumber.values[0])
                series = {
                    'SeriesNumber': series_nr,
                    'SeriesDescription': series_desc,
                    'SeriesInstanceUID': uid_sery,
                    'instances': {},
                }
                study['series'].append(series)
                for uid_instance in df_series.SOPInstanceUID.unique():
                    df_instance = df_series[df_series.SOPInstanceUID == uid_instance]
                    instance_nr = int(df_instance.InstanceNumber.values[0])
                    relpath = df_instance.index[0]
                    series['instances'][instance_nr]=relpath

    return summary