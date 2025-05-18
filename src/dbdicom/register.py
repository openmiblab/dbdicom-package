import os
import pandas as pd


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


def index(df:pd.DataFrame, entity):
    if isinstance(entity, str):
        rows = (df.removed==False)
    elif len(entity)==2:
        patient_id = uid(df, entity)
        rows = (df.PatientID==patient_id) & (df.removed==False)
    elif len(entity)==3:
        study_uid = uid(df, entity)
        rows = (df.StudyInstanceUID==study_uid) & (df.removed==False)
    elif len(entity)==4:
        series_uid = uid(df, entity)
        rows = (df.SeriesInstanceUID==series_uid) & (df.removed==False)
    return df.index[rows].tolist()


def files(df:pd.DataFrame, entity):
    # Raises an error if the entity does not exist or has no files
    df.sort_values(['PatientID', 'StudyInstanceUID', 'SeriesNumber', 'InstanceNumber'], inplace=True)
    relpath = index(df, entity)
    if relpath==[]:
        raise ValueError(f'No files in entity {entity}')
    if isinstance(entity, str):
        return [os.path.join(entity, f) for f in relpath]
    else:
        return [os.path.join(entity[0], f) for f in relpath]


def _prep(df:pd.DataFrame):
    df = df[df.removed == False]
    df.sort_values(['PatientID','StudyInstanceUID','SeriesNumber'], inplace=True)
    return df


def entity(df, path, uid):# information entity from uid
    df = _prep(df)

    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        patient_desc = (patient_name, patient_idx[patient_name])
        if uid == uid_patient:
            return [path, patient_desc]
        
        else:

            study_idx = {}
            for uid_study in df_patient.StudyInstanceUID.dropna().unique():
                df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
                study_name = df_study.StudyDescription.values[0]
                if study_name in study_idx:
                    study_idx[study_name] += 1
                else:
                    study_idx[study_name] = 0
                study_desc = (study_name, study_idx[study_name])
                if uid == uid_study:
                    return [path, patient_desc, study_desc]
                
                else:

                    series_idx = {}
                    for uid_series in df_study.SeriesInstanceUID.dropna().unique():
                        df_series = df_study[df_study.SeriesInstanceUID == uid_series]
                        series_name = df_series.SeriesDescription.values[0]
                        if series_name in series_idx:
                            series_idx[series_name] += 1
                        else:
                            series_idx[series_name] = 0
                        series_desc = (series_name, series_idx[series_name])
                        if uid == uid_series:
                            return [path, patient_desc, study_desc, series_desc]
                        
    raise ValueError(f"No information entity with UID {uid} was found.")


def uid(df, entity): # uid from entity
    df = df[df.removed == False]
    if len(entity)==2:
        return _patient_uid(df, entity)
    if len(entity)==3:
        return _study_uid(df, entity)
    if len(entity)==4:
        return _series_uid(df, entity)


def _patient_uid(df, patient):
    patient = patient[1]
    df = df[df.removed == False]
    patients = {}
    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        patient_desc = (patient_name, patient_idx[patient_name])
        if patient == patient_desc:
            return uid_patient
        patients[patient_desc] = uid_patient
    if isinstance(patient, str):
        patient_list = [p for p in patients.keys() if p[0]==patient]
        if len(patient_list) == 1:
            return patients[(patient, 0)]
        elif len(patient_list) > 1:
            raise ValueError(
                f"Multiple patients with name {patient}."
                f"Please specify the index in the call to patient_uid(). "
                f"For instance ({patient}, {len(patients)-1})'. "
            )
    raise ValueError(f"Patient {patient} not found in database.")
    

def _study_uid(df, study):
    uid_patient = _patient_uid(df, study[:-1])
    patient, study = study[1], study[2]
    df = df[df.removed == False] # TODO_manager must do this before passing df
    df_patient = df[df.PatientID == uid_patient]
    studies = {}
    study_idx = {}
    for uid_study in df_patient.StudyInstanceUID.dropna().unique():
        df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
        study_desc = df_study.StudyDescription.values[0]
        if study_desc in study_idx:
            study_idx[study_desc] += 1
        else:
            study_idx[study_desc] = 0
        study_desc = (study_desc, study_idx[study_desc])
        if study == study_desc:
            return uid_study
        studies[study_desc] = uid_study
    if isinstance(study, str):
        studies_list = [s for s in studies.keys() if s[0]==study]
        if len(studies_list) == 1:
            return studies[(study, 0)]
        elif len(studies_list) > 1:
            raise ValueError(
                f"Multiple studies with name {study}."
                f"Please specify the index in the call to study_uid(). "
                f"For instance ({study}, {len(studies)-1})'. "
            )
    raise ValueError(f"Study {study} not found in patient {patient}.")


def _series_uid(df, series): # absolute path to series
    uid_study = _study_uid(df, series[:-1])
    study, sery = series[2], series[3]
    df = df[df.removed == False]
    df_study = df[df.StudyInstanceUID == uid_study]
    series = {}
    series_idx = {}
    for uid_series in df_study.SeriesInstanceUID.dropna().unique():
        df_series = df_study[df_study.SeriesInstanceUID == uid_series]
        series_desc = df_series.SeriesDescription.values[0]
        if series_desc in series_idx:
            series_idx[series_desc] += 1
        else:
            series_idx[series_desc] = 0
        series_desc = (series_desc, series_idx[series_desc])
        if sery == series_desc:
            return uid_series
        series[series_desc] = uid_series
    if isinstance(sery, str):
        series_list = [s for s in series.keys() if s[0]==sery]
        if len(series_list) == 1:
            return series[(sery, 0)]
        elif len(series_list) > 1:
            raise ValueError(
                f"Multiple series with name {sery}."
                f"Please specify the index in the call to series_uid(). "
                f"For instance ({sery}, {len(series)-1})'. "
            )
    raise ValueError(f"Series {sery} not found in study {study}.")


def patients(df, database, name=None, contains=None, isin=None):
    df = _prep(df)
    simplified_patients = []
    patients = []
    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        patients.append((patient_name, patient_idx[patient_name]))
    for patient in patients:
        if patient_idx[patient[0]] == 0:
            simplified_patients.append(patient[0])
        else:
            simplified_patients.append(patient)
    if name is not None:
        patients_result = []
        for s in simplified_patients:
            if isinstance(s, str):
                if s == name:
                    patients_result.append(s)
            elif s[0] == name: 
                patients_result.append(s)
        return [[path, p] for p in patients_result]
    elif contains is not None:
        patients_result = []
        for s in simplified_patients:
            if isinstance(s, str):
                if contains in s:
                    patients_result.append(s)
            elif contains in s[0]: 
                patients_result.append(s)
        return [[database, p] for p in patients_result]
    elif isin is not None:
        patients_result = []
        for s in simplified_patients:
            if isinstance(s, str):
                if s in isin:
                    patients_result.append(s)
            elif s[0] in isin: 
                patients_result.append(s)
        return [[database, p] for p in patients_result]
    else:
        return [[database, p] for p in simplified_patients]


def studies(df, pat, name=None, contains=None, isin=None):
    database, patient = pat[0], pat[1]
    patient_as_str = isinstance(patient, str)
    if patient_as_str:
        patient = (patient, 0)
    df = _prep(df)
    simplified_studies = []
    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        if patient[0] == patient_name:
            if patient_as_str:
                if patient_idx[patient_name] > 0:
                    raise ValueError(
                        f"Multiple patients named {patient_name}. "
                        "Please provide an index along with the patient name."
                    )
        if patient == (patient_name, patient_idx[patient_name]):
            studies = []
            study_idx = {}
            for uid_study in df_patient.StudyInstanceUID.dropna().unique():
                df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
                study_desc = df_study.StudyDescription.values[0]
                if study_desc in study_idx:
                    study_idx[study_desc] += 1
                else:
                    study_idx[study_desc] = 0
                studies.append((study_desc, study_idx[study_desc]))
            for study in studies:
                if study_idx[study[0]] == 0:
                    simplified_studies.append(study[0])
                else:
                    simplified_studies.append(study)
            if not patient_as_str:
                break
    if name is not None:    
        studies_result = []
        for s in simplified_studies:
            if isinstance(s, str):
                if s == name:
                    studies_result.append(s)
            elif s[0] == name: 
                studies_result.append(s)
        return [[database, patient, study] for study in studies_result]
    elif contains is not None:
        studies_result = []
        for s in simplified_studies:
            if isinstance(s, str):
                if contains in s:
                    studies_result.append(s)
            elif contains in s[0]: 
                studies_result.append(s)
        return [[database, patient, study] for study in studies_result]
    elif isin is not None:
        studies_result = []
        for s in simplified_studies:
            if isinstance(s, str):
                if s in isin:
                    studies_result.append(s)
            elif s[0] in isin: 
                studies_result.append(s)
        return [[database, patient, study] for study in studies_result]
    else:
        return [[database, patient, study] for study in simplified_studies]



def series(df, stdy, name=None, contains=None, isin=None):
    database, patient, study = stdy[0], stdy[1], stdy[2]
    patient_as_str = isinstance(patient, str)
    if patient_as_str:
        patient = (patient, 0)
    study_as_str = isinstance(study, str)
    if study_as_str:
        study = (study, 0)
    df = _prep(df)
    simplified_series = []
    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        if patient[0] == patient_name:
            if patient_as_str:
                if patient_idx[patient_name] > 0:
                    raise ValueError(
                        f"Multiple patients named {patient_name}. Please provide an index along with the patient name."
                    )
        if patient == (patient_name, patient_idx[patient_name]):
            study_idx = {}
            for uid_study in df_patient.StudyInstanceUID.dropna().unique():
                df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
                study_desc = df_study.StudyDescription.values[0]
                if study_desc in study_idx:
                    study_idx[study_desc] += 1
                else:
                    study_idx[study_desc] = 0
                if study[0] == study_desc:
                    if study_as_str:
                        if study_idx[study_desc] > 0:
                            raise ValueError(
                                f"Multiple studies named {study_desc} in patient {patient_name}. Please provide an index along with the study description."
                            )
                if study == (study_desc, study_idx[study_desc]):
                    series = []
                    series_idx = {}
                    for uid_sery in df_study.SeriesInstanceUID.dropna().unique():
                        df_series = df_study[df_study.SeriesInstanceUID == uid_sery]
                        series_desc = df_series.SeriesDescription.values[0]
                        if series_desc in series_idx:
                            series_idx[series_desc] += 1
                        else:
                            series_idx[series_desc] = 0
                        series.append((series_desc, series_idx[series_desc]))
                    for sery in series:
                        if series_idx[sery[0]] == 0:
                            simplified_series.append(sery[0])
                        else:
                            simplified_series.append(sery)
                    if not (patient_as_str or study_as_str):
                        break
    if name is not None:    
        series_result = []
        for s in simplified_series:
            if isinstance(s, str):
                if s == name:
                    series_result.append(s)
            elif s[0] == name: 
                series_result.append(s)
        return [[database, patient, study, series] for series in series_result]
    elif contains is not None:    
        series_result = []
        for s in simplified_series:
            if isinstance(s, str):
                if contains in s:
                    series_result.append(s)
            elif contains in s[0]: 
                series_result.append(s)
        return [[database, patient, study, series] for series in series_result]
    elif isin is not None:    
        series_result = []
        for s in simplified_series:
            if isinstance(s, str):
                if s in isin:
                    series_result.append(s)
            elif s[0] in isin: 
                series_result.append(s)
        return [[database, patient, study, series] for series in series_result]
    else:
        return [[database, patient, study, series] for series in simplified_series] 
    

def print_tree(df):
    tree = summary(df)
    for patient, studies in tree.items():
        print(f"Patient: ({patient[0]}, {patient[1]})")
        for study, series in studies.items():
            print(f"  Study: ({study[0]}, {study[1]})")
            for s in series:
                print(f"    Series: ({s[0]}, {s[1]})")

def append(df, parent, child_name): 
    if len(parent) == 1:
        return _new_patient(df, parent, child_name)
    elif len(parent) == 2:
        return _new_study(df, parent, child_name)
    elif len(parent) == 3:
        return _new_series(df, parent, child_name)

def _new_patient(df, database, patient_name):
    # Count the number of series with the same description
    desc = patient_name if isinstance(patient_name, str) else patient_name[0]
    patients_in_db = patients(df, database, name=desc)
    cnt = len(patients_in_db)
    if cnt==0:
        return [database, desc]
    else:
        return [database, (desc, cnt+1)]
    
def _new_study(df, patient, study_name): #len(patient)=2
    # Count the number of series with the same description
    desc = study_name if isinstance(study_name, str) else study_name[0]
    studies_in_patient = studies(df, patient, name=desc)
    cnt = len(studies_in_patient)
    if cnt==0:
        return patient + [desc]
    else:
        return patient + [(desc, cnt+1)]
    
def _new_series(df, study, series_name): #len(study)=3
    # Count the number of series with the same description
    desc = series_name if isinstance(series_name, str) else series_name[0]
    series_in_study = series(df, study, name=desc)
    cnt = len(series_in_study)
    if cnt==0:
        return study + [desc]
    else:
        return study + [(desc, cnt+1)]


def uid_tree(df, path, depth=3):

    if df is None:
        raise ValueError('Cannot build tree - no database open')
    df = df[df.removed == False]
    df.sort_values(['PatientName','StudyDate','SeriesNumber','InstanceNumber'], inplace=True)
    
    database = {'uid': path}
    database['patients'] = []
    for uid_patient in df.PatientID.dropna().unique():
        patient = {'uid': uid_patient}
        database['patients'].append(patient)
        if depth >= 1:
            df_patient = df[df.PatientID == uid_patient]
            patient['key'] = df_patient.index[0]
            patient['studies'] = []
            for uid_study in df_patient.StudyInstanceUID.dropna().unique():
                study = {'uid': uid_study}
                patient['studies'].append(study)
                if depth >= 2:
                    df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
                    study['key'] = df_study.index[0]
                    study['series'] = []
                    for uid_sery in df_study.SeriesInstanceUID.dropna().unique():
                        series = {'uid': uid_sery}
                        study['series'].append(series)
                        if depth == 3:
                            df_series = df_study[df_study.SeriesInstanceUID == uid_sery]
                            series['key'] = df_series.index[0]
    return database
    


def summary(df):
    # A human-readable summary tree

    df = _prep(df)
    summary = {}

    patient_idx = {}
    for uid_patient in df.PatientID.dropna().unique():
        df_patient = df[df.PatientID == uid_patient]
        patient_name = df_patient.PatientName.values[0]
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        summary[patient_name, patient_idx[patient_name]] = {}

        study_idx = {}
        for uid_study in df_patient.StudyInstanceUID.dropna().unique():
            df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
            study_desc = df_study.StudyDescription.values[0]
            if study_desc in study_idx:
                study_idx[study_desc] += 1
            else:
                study_idx[study_desc] = 0
            summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]] = []

            series_idx = {}
            for uid_sery in df_study.SeriesInstanceUID.dropna().unique():
                df_series = df_study[df_study.SeriesInstanceUID == uid_sery]
                series_desc = df_series.SeriesDescription.values[0]
                if series_desc in series_idx:
                    series_idx[series_desc] += 1
                else:
                    series_idx[series_desc] = 0
                summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]].append((series_desc, series_idx[series_desc]))
    
    return summary