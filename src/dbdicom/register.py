import os


class AmbiguousError(Exception):
    pass


def add_instance(dbtree:list, attr, rel_path):
    
    # Get patient and create if needed
    pts = [pt for pt in sorted(dbtree, key=lambda pt: pt['PatientID']) if pt['PatientID']==attr['PatientID']]
    if pts==[]:
        pt = {
            'PatientName': attr['PatientName'],
            'PatientID': attr['PatientID'],
            'studies': [],
        }
        dbtree.append(pt)
    else:
        pt = pts[0]
    
    # Get study and create if needed
    sts = [st for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']) if st['StudyInstanceUID']==attr['StudyInstanceUID']]
    if sts==[]:
        st = {
            'StudyDescription': attr['StudyDescription'],
            'StudyID': attr['StudyID'],
            'StudyInstanceUID': attr['StudyInstanceUID'],
            'series': [],
        }
        pt['studies'].append(st)
    else:
        st = sts[0]

    # Get series and create if needed
    srs = [sr for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']) if sr['SeriesInstanceUID']==attr['SeriesInstanceUID']]
    if srs==[]:
        sr = {
            'SeriesNumber': attr['SeriesNumber'],
            'SeriesDescription': attr['SeriesDescription'],
            'SeriesInstanceUID': attr['SeriesInstanceUID'],
            'instances': {},
        }
        st['series'].append(sr)
    else:
        sr = srs[0]

    # Add instance
    sr['instances'][attr['InstanceNumber']] = rel_path

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
        for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
                    idx += list(sr['instances'].values())
        return idx
    elif len(entity)==2:
        patient_id = entity[1]
        idx = []
        for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
            if pt['PatientID'] == patient_id:
                for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                    for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
                        idx += list(sr['instances'].values())
                return idx
    elif len(entity)==3:
        study_uid = uid(dbtree, entity)
        idx = []
        for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                if st['StudyInstanceUID'] == study_uid:
                    for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
                        idx += list(sr['instances'].values())
                    return idx
    elif len(entity)==4:
        series_uid = uid(dbtree, entity)
        for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
                    if sr['SeriesInstanceUID'] == series_uid:
                        return list(sr['instances'].values())
                    

def drop(dbtree, relpaths):
    for pt in sorted(dbtree[:], key=lambda pt: pt['PatientID']):
        for st in sorted(pt['studies'][:], key=lambda st: st['StudyInstanceUID']):
            for sr in sorted(st['series'][:], key=lambda sr: sr['SeriesNumber']):
                for nr, relpath in list(sr['instances'].items()):
                    if relpath in relpaths:
                        del sr['instances'][nr]
                if sr['instances'] == []:
                    st['series'].remove(sr)
            if st['series'] == []:
                pt['studies'].remove(st)
    return dbtree



def uid(dbtree, entity): # uid from entity
    if len(entity)==2:
        return entity[1]
    if len(entity)==3:
        return study_uid(dbtree, entity)
    if len(entity)==4:
        return series_uid(dbtree, entity)
    

def study_uid(dbtree, study):
    patient_id, study = study[1], study[2]
    for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
        if pt['PatientID'] == patient_id:

            uid_studies = {}
            study_idx = {}
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                study_desc = st['StudyDescription']
                uid_study = st['StudyInstanceUID']
                if study_desc in study_idx:
                    study_idx[study_desc] += 1
                else:
                    study_idx[study_desc] = 0
                study_desc = (study_desc, study_idx[study_desc])
                if study == study_desc:
                    return uid_study
                uid_studies[study_desc] = uid_study

            if isinstance(study, str):
                studies_list = [s for s in uid_studies.keys() if s[0]==study]
                if len(studies_list) == 1:
                    return uid_studies[(study, 0)]
                elif len(studies_list) > 1:
                    raise AmbiguousError(
                        f"Multiple studies with name {study}. "
                        f"Please specify the index along with the description. "
                        f"For instance ({study}, {len(uid_studies)-1})'. "
                    )
            raise ValueError(f"Study {study} not found in patient {patient_id}.")


def series_uid(dbtree, series): # absolute path to series
    uid_study = study_uid(dbtree, series[:-1])
    study, sery = series[2], series[3]
    for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
        for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
            if st['StudyInstanceUID'] == uid_study:

                series = {}
                series_idx = {}
                for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
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
                        raise AmbiguousError(
                            f"Multiple series with name {sery}. "
                            f"Please specify the index along with the description. "
                            f"For instance ({sery}, {len(series)-1})'. "
                        )
                raise ValueError(f"Series {sery} not found in study {study}.")


def patients(dbtree, database, name=None, contains=None, isin=None):

    patients = []
    for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
        patient_name = pt['PatientName']
        append = True
        if name is not None:
            append = append and (patient_name==name)
        if contains is not None:
            append = append and (contains in patient_name)
        if isin is not None:
            append = append and (patient_name in isin)
        if append:
            patients.append(pt['PatientID'])

    return [[database, p] for p in patients]


def studies(dbtree, pat, desc=None, contains=None, isin=None):
    database, patient_id = pat[0], pat[1]
    studies = []
    for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
        if pt['PatientID'] == patient_id:
            study_idx = {}
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                study_desc = st['StudyDescription']
                if study_desc in study_idx:
                    study_idx[study_desc] += 1
                else:
                    study_idx[study_desc] = 0
                studies.append((study_desc, study_idx[study_desc]))

    # Apply filters
    if desc is not None:   
        studies = [s for s in studies if s[0]==desc] 
    if contains is not None:
        studies = [s for s in studies if contains in s[0]]
    if isin is not None:
        studies = [s for s in studies if s[0] in isin]

    # Return result
    return [[database, patient_id, study] for study in studies]



def series(dbtree, stdy, desc=None, contains=None, isin=None):
    database, patient_id, study = stdy[0], stdy[1], stdy[2]
    study_as_str = isinstance(study, str)
    if study_as_str:
        study = (study, 0)
    series = []
    for pt in sorted(dbtree, key=lambda pt: pt['PatientID']):
        if pt['PatientID'] == patient_id:
            study_idx = {}
            for st in sorted(pt['studies'], key=lambda st: st['StudyInstanceUID']):
                study_desc = st['StudyDescription']
                if study_desc in study_idx:
                    study_idx[study_desc] += 1
                else:
                    study_idx[study_desc] = 0
                if study[0] == study_desc:
                    if study_as_str:
                        if study_idx[study_desc] > 0:
                            raise AmbiguousError(
                                f"Multiple studies named {study_desc} in patient {patient_id}. Please provide an index along with the study description."
                            )
                if study == (study_desc, study_idx[study_desc]):
                    series_idx = {}
                    for sr in sorted(st['series'], key=lambda sr: sr['SeriesNumber']):
                        series_desc = sr['SeriesDescription']
                        if series_desc in series_idx:
                            series_idx[series_desc] += 1
                        else:
                            series_idx[series_desc] = 0
                        series.append((series_desc, series_idx[series_desc]))
                    if not study_as_str:
                        break

    # Apply filters (if any)
    if desc is not None:    
        series = [s for s in series if s[0]==desc]
    if contains is not None:    
        series = [s for s in series if contains in s[0]]
    if isin is not None:   
        series = [s for s in series if s[0] in isin] 

    # Return result
    return [[database, patient_id, study, s] for s in series] 
    


# def append(dbtree, parent, child_name): 
#     if len(parent) == 1:
#         return _new_patient(dbtree, parent, child_name)
#     elif len(parent) == 2:
#         return _new_study(dbtree, parent, child_name)
#     elif len(parent) == 3:
#         return _new_series(dbtree, parent, child_name)

# def _new_patient(dbtree, database, patient_id):
#     if patient_id in patients(dbtree, database):
#         raise ValueError(
#             f"Cannot create a new patient with id {patient_id}."
#             f"The ID is already taken."
#         )
#     return [database, patient_id]
    
# def new_study(dbtree, patient, study): #len(patient)=2
#     desc = study if isinstance(study, str) else study[0]
#     studies_in_patient = studies(dbtree, patient, desc=desc)
#     cnt = len(studies_in_patient)
#     return patient + [(desc, cnt)]
    
# def new_series(dbtree, study, sery): #len(study)=3
#     desc = sery if isinstance(sery, str) else sery[0]
#     series_in_study = series(dbtree, study, desc=desc)
#     cnt = len(series_in_study)
#     return study + [(desc, cnt)]



def print_tree(dbtree):
    tree = summary(dbtree)
    for patient, studies in tree.items():
        print(f"Patient: ({patient[0]}, {patient[1]})")
        for study, series in studies.items():
            print(f"  Study: ({study[0]}, {study[1]})")
            for s in series:
                print(f"    Series: ({s[0]}, {s[1]})")


def summary(dbtree):
    # A human-readable summary tree

    summary = {}

    for patient in sorted(dbtree, key=lambda pt: pt['PatientID']):
        pat_id, pat_name = patient['PatientID'], patient['PatientName']
        summary[pat_id, pat_name] = {}

        study_idx = {}
        for study in sorted(patient['studies'], key=lambda st: st['StudyInstanceUID']):
            study_desc = study['StudyDescription']
            if study_desc in study_idx:
                study_idx[study_desc] += 1
            else:
                study_idx[study_desc] = 0
            summary[pat_id, pat_name][study_desc, study_idx[study_desc]] = []

            series_idx = {}
            for series in sorted(study['series'], key=lambda sr: sr['SeriesNumber']):
                series_desc = series['SeriesDescription']
                if series_desc in series_idx:
                    series_idx[series_desc] += 1
                else:
                    series_idx[series_desc] = 0
                summary[pat_id, pat_name][study_desc, study_idx[study_desc]].append((series_desc, series_idx[series_desc]))
    
    return summary


