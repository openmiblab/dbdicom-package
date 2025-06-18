import os


def add_instance(dbtree:list, instance, rel_path):
    
    # Get patient and create if needed
    pts = [pt for pt in dbtree if pt['PatientID']==instance['PatientID']]
    if pts==[]:
        pt = {
            'PatientName': instance['PatientName'],
            'PatientID': instance['PatientID'],
            'studies': [],
        }
        dbtree.append(pt)
    else:
        pt = pts[0]
    
    # Get study and create if needed
    sts = [st for st in pt['studies'] if st['StudyInstanceUID']==instance['StudyInstanceUID']]
    if sts==[]:
        st = {
            'StudyDescription': instance['StudyDescription'],
            'StudyDate': instance['StudyDate'],
            'StudyID': instance['StudyID'],
            'StudyInstanceUID': instance['StudyInstanceUID'],
            'series': [],
        }
        pt['studies'].append(st)
    else:
        st = sts[0]

    # Get series and create if needed
    srs = [sr for sr in st['series'] if sr['SeriesInstanceUID']==instance['SeriesInstanceUID']]
    if srs==[]:
        sr = {
            'SeriesNumber': instance['SeriesNumber'],
            'SeriesDescription': instance['SeriesDescription'],
            'SeriesInstanceUID': instance['SeriesInstanceUID'],
            'instances': {},
        }
        st['series'].append(sr)
    else:
        sr = srs[0]

    # Add instance
    sr['instances'][instance['InstanceNumber']] = rel_path

    return dbtree


def files(dbtree, entity):
    # Raises an error if the entity does not exist or has no files
    relpath = index(dbtree, entity)
    if relpath==[]:
        raise ValueError(f'No files in entity {entity}')
    if isinstance(entity, str):
        return [os.path.join(entity, f) for f in relpath]
    else:
        return [os.path.join(entity[0], f) for f in relpath]
    

def index(dbtree, entity):
    if isinstance(entity, str):
        idx = []
        for pt in dbtree:
            for st in pt['studies']:
                for sr in st['series']:
                    idx += list(sr['instances'].values())
        return idx
    elif len(entity)==2:
        patient_id = uid(dbtree, entity)
        idx = []
        for pt in dbtree:
            if pt['PatientID'] == patient_id:
                for st in pt['studies']:
                    for sr in st['series']:
                        idx += list(sr['instances'].values())
                return idx
    elif len(entity)==3:
        study_uid = uid(dbtree, entity)
        idx = []
        for pt in dbtree:
            for st in pt['studies']:
                if st['StudyInstanceUID'] == study_uid:
                    for sr in st['series']:
                        idx += list(sr['instances'].values())
                    return idx
    elif len(entity)==4:
        series_uid = uid(dbtree, entity)
        for pt in dbtree:
            for st in pt['studies']:
                for sr in st['series']:
                    if sr['SeriesInstanceUID'] == series_uid:
                        return list(sr['instances'].values())
                    

def drop(dbtree, relpaths):
    for pt in dbtree[:]:
        for st in pt['studies'][:]:
            for sr in st['series'][:]:
                for nr, relpath in list(sr['instances'].items()):
                    if relpath in relpaths:
                        del sr['instances'][nr]
                if sr['instances'] == []:
                    st['series'].remove(sr)
            if st['series'] == []:
                pt['studies'].remove(st)
    return dbtree


# def entity(df, path, uid):# information entity from uid
#     dbtree = tree(df)
#     patient_idx = {}
#     for pt in dbtree:
#         patient_name = pt['PatientName']
#         uid_patient = pt['PatientID']
#         if patient_name in patient_idx:
#             patient_idx[patient_name] += 1
#         else:
#             patient_idx[patient_name] = 0
#         patient_desc = (patient_name, patient_idx[patient_name])
#         if uid == uid_patient:
#             return [path, patient_desc]
        
#         else:

#             study_idx = {}
#             for st in pt['studies']:
#                 study_name = st['StudyDescription']
#                 uid_study = st['StudyInstanceUID']
#                 if study_name in study_idx:
#                     study_idx[study_name] += 1
#                 else:
#                     study_idx[study_name] = 0
#                 study_desc = (study_name, study_idx[study_name])
#                 if uid == uid_study:
#                     return [path, patient_desc, study_desc]
                
#                 else:

#                     series_idx = {}
#                     for sr in st['series']:
#                         series_name = sr['SeriesDescription']
#                         uid_series = sr['SeriesInstanceUID']
#                         if series_name in series_idx:
#                             series_idx[series_name] += 1
#                         else:
#                             series_idx[series_name] = 0
#                         series_desc = (series_name, series_idx[series_name])
#                         if uid == uid_series:
#                             return [path, patient_desc, study_desc, series_desc]
                        
#     raise ValueError(f"No information entity with UID {uid} was found.")


def uid(dbtree, entity): # uid from entity
    if len(entity)==2:
        return _patient_uid(dbtree, entity)
    if len(entity)==3:
        return _study_uid(dbtree, entity)
    if len(entity)==4:
        return _series_uid(dbtree, entity)


def _patient_uid(dbtree, patient):
    patient = patient[1]
    patients = {}
    patient_idx = {}
    for pt in dbtree:
        patient_name = pt['PatientName']
        uid_patient = pt['PatientID']
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
    
    

def _study_uid(dbtree, study):
    uid_patient = _patient_uid(dbtree, study[:-1])
    patient, study = study[1], study[2]
    for pt in dbtree:
        if pt['PatientID'] == uid_patient:
            studies = {}
            study_idx = {}
            for st in pt['studies']:
                study_desc = st['StudyDescription']
                uid_study = st['StudyInstanceUID']
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


def _series_uid(dbtree, series): # absolute path to series
    uid_study = _study_uid(dbtree, series[:-1])
    study, sery = series[2], series[3]
    for pt in dbtree:
        for st in pt['studies']:
            if st['StudyInstanceUID'] == uid_study:
                series = {}
                series_idx = {}
                for sr in st['series']:
                    series_desc = sr['SeriesDescription']
                    uid_series = sr['SeriesInstanceUID']
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


def patients(dbtree, database, name=None, contains=None, isin=None):
    simplified_patients = []
    patients = []
    patient_idx = {}
    for pt in dbtree:
        patient_name = pt['PatientName']
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
        return [[database, p] for p in patients_result]
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


def studies(dbtree, pat, name=None, contains=None, isin=None):
    database, patient = pat[0], pat[1]
    patient_as_str = isinstance(patient, str)
    if patient_as_str:
        patient = (patient, 0)
    simplified_studies = []
    patient_idx = {}
    for pt in dbtree:
        patient_name = pt['PatientName']
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
            for st in pt['studies']:
                study_desc = st['StudyDescription']
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



def series(dbtree, stdy, name=None, contains=None, isin=None):
    database, patient, study = stdy[0], stdy[1], stdy[2]
    patient_as_str = isinstance(patient, str)
    if patient_as_str:
        patient = (patient, 0)
    study_as_str = isinstance(study, str)
    if study_as_str:
        study = (study, 0)
    simplified_series = []
    patient_idx = {}
    for pt in dbtree:
        patient_name = pt['PatientName']
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
            for st in pt['studies']:
                study_desc = st['StudyDescription']
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
                    for sr in st['series']:
                        series_desc = sr['SeriesDescription']
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
    



def append(dbtree, parent, child_name): 
    if len(parent) == 1:
        return _new_patient(dbtree, parent, child_name)
    elif len(parent) == 2:
        return _new_study(dbtree, parent, child_name)
    elif len(parent) == 3:
        return _new_series(dbtree, parent, child_name)

def _new_patient(dbtree, database, patient_name):
    # Count the number of series with the same description
    desc = patient_name if isinstance(patient_name, str) else patient_name[0]
    patients_in_db = patients(dbtree, database, name=desc)
    cnt = len(patients_in_db)
    if cnt==0:
        return [database, desc]
    else:
        return [database, (desc, cnt+1)]
    
def _new_study(dbtree, patient, study_name): #len(patient)=2
    # Count the number of series with the same description
    desc = study_name if isinstance(study_name, str) else study_name[0]
    studies_in_patient = studies(dbtree, patient, name=desc)
    cnt = len(studies_in_patient)
    if cnt==0:
        return patient + [desc]
    else:
        return patient + [(desc, cnt+1)]
    
def _new_series(dbtree, study, series_name): #len(study)=3
    # Count the number of series with the same description
    desc = series_name if isinstance(series_name, str) else series_name[0]
    series_in_study = series(dbtree, study, name=desc)
    cnt = len(series_in_study)
    if cnt==0:
        return study + [desc]
    else:
        return study + [(desc, cnt+1)]


# def uid_tree(df, path, depth=3):

#     dbtree = summary(df)
    
#     database = {'uid': path}
#     database['patients'] = []
#     for pat in dbtree:
#         patient = {'uid': pat['PatientID']}
#         database['patients'].append(patient)
#         if depth >= 1:
#             df_patient = df[df.PatientID == pat['PatientID']]
#             patient['key'] = df_patient.index[0] 
#             patient['studies'] = []
#             for stdy in pat['studies']:
#                 study = {'uid': stdy['StudyInstanceUID']}
#                 patient['studies'].append(study)
#                 if depth >= 2:
#                     df_study = df_patient[df_patient.StudyInstanceUID == stdy['StudyInstanceUID']]
#                     study['key'] = df_study.index[0]
#                     study['series'] = []
#                     for sery in stdy['series']:
#                         series = {'uid': sery['SeriesInstanceUID']}
#                         study['series'].append(series)
#                         if depth == 3:
#                             df_series = df_study[df_study.SeriesInstanceUID == sery['SeriesInstanceUID']]
#                             series['key'] = df_series.index[0]
#     return database


def print_tree(dbtree):
    tree = summary(dbtree)
    for patient, studies in tree.items():
        print(f"Patient: ({patient[0]}, {patient[1]})")
        for study, series in studies.items():
            print(f"  Study: ({study[0]}, {study[1]})")
            for s in series:
                print(f"    Series: ({s[0]}, {s[1]})")


# def summary(df):
#     # A human-readable summary tree

#     df = _prep(df)
#     summary = {}

#     patient_idx = {}
#     for uid_patient in df.PatientID.dropna().unique():
#         df_patient = df[df.PatientID == uid_patient]
#         patient_name = df_patient.PatientName.values[0]
#         if patient_name in patient_idx:
#             patient_idx[patient_name] += 1
#         else:
#             patient_idx[patient_name] = 0
#         summary[patient_name, patient_idx[patient_name]] = {}

#         study_idx = {}
#         for uid_study in df_patient.StudyInstanceUID.dropna().unique():
#             df_study = df_patient[df_patient.StudyInstanceUID == uid_study]
#             study_desc = df_study.StudyDescription.values[0]
#             if study_desc in study_idx:
#                 study_idx[study_desc] += 1
#             else:
#                 study_idx[study_desc] = 0
#             summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]] = []

#             series_idx = {}
#             for uid_sery in df_study.SeriesInstanceUID.dropna().unique():
#                 df_series = df_study[df_study.SeriesInstanceUID == uid_sery]
#                 series_desc = df_series.SeriesDescription.values[0]
#                 if series_desc in series_idx:
#                     series_idx[series_desc] += 1
#                 else:
#                     series_idx[series_desc] = 0
#                 summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]].append((series_desc, series_idx[series_desc]))
    
#     return summary


def summary(dbtree):
    # A human-readable summary tree

    summary = {}

    patient_idx = {}
    for patient in dbtree:
        patient_name = patient['PatientName']
        if patient_name in patient_idx:
            patient_idx[patient_name] += 1
        else:
            patient_idx[patient_name] = 0
        summary[patient_name, patient_idx[patient_name]] = {}

        study_idx = {}
        for study in patient['studies']:
            study_desc = study['StudyDescription']
            if study_desc in study_idx:
                study_idx[study_desc] += 1
            else:
                study_idx[study_desc] = 0
            summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]] = []

            series_idx = {}
            for series in study['series']:
                series_desc = series['SeriesDescription']
                if series_desc in series_idx:
                    series_idx[series_desc] += 1
                else:
                    series_idx[series_desc] = 0
                summary[patient_name, patient_idx[patient_name]][study_desc, study_idx[study_desc]].append((series_desc, series_idx[series_desc]))
    
    return summary


