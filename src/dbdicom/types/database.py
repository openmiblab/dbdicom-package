# Importing annotations to handle or sign in import type hints
from __future__ import annotations


from dbdicom.record import Record
from dbdicom.utils.files import gif2numpy



class Database(Record):

    name = 'Database'

    def loc(self):
        return self.manager._dbloc()
        # df = self.manager.register
        # return df.removed==False

    def _set_key(self):
        #if not self.manager.register.empty:
        if not self.manager._empty():
            self._key = self.manager._keys(0)
            #self._key = self.manager.register.index[0]
        else:
            self._key = None

    def close(self):
        return self.manager.close()

    def set_path(self,path):
        # Used in example of clear
        self.manager.path=path

    def parent(self):
        return

    def children(self, **kwargs):
        return self.patients(**kwargs)

    def new_child(self, dataset=None, **kwargs): 
        attr = {**kwargs, **self.attributes}
        return self.new_patient(**attr)
    
    def new_sibling(self, suffix=None, **kwargs):
        msg = 'You cannot create a sibling from a database \n'
        msg += 'You can start a new database with db.database()'
        raise RuntimeError(msg)

    def save(self, path=None):
        #self.manager.save('Database')
        self.manager.save()
        self.write(path)
        return self

    def restore(self, path=None):
        self.manager.restore()
        self.write(path)
        return self

    def open(self, path):
        self.manager.open(path)
        return self

    def close(self):
        return self.manager.close()

    def scan(self):
        self.manager.scan()
        return self

    def import_dicom(self, files):
        uids = self.manager.import_datasets(files)
        return uids is not None

    # def import_nifti(self, files):
    #     self.manager.import_datasets_from_nifti(files)

    def import_gif(self, files):
        study = self.new_patient().new_study()
        for file in files:
            array = gif2numpy(file)
            series = study.new_series()
            series.set_array(array)
        return study

    def _copy_from(self, record):
        uids = self.manager.copy_to_database(record.uid, **self.attributes)
        if isinstance(uids, list):
            return [self.record('Patient', uid, **self.attributes) for uid in uids]
        else:
            return self.record('Patient', uids, **self.attributes)

    def zeros(*args, **kwargs): # OBSOLETE - remove
        return zeros(*args, **kwargs)
    





# Helper functions to convert from new-API objects (lists) into old-API objects (Records) 
# This can be used to run old-API functions using the new API as an intermediate step





def _patient(database, patient, force=False):  
    patient_name = patient[0] if isinstance(patient, tuple) else patient
    patient_objects = Record.patients(database, PatientName=patient_name) 
    if len(patient_objects) == 0:
        if force:
            return database.new_patient(PatientName=patient_name)
        else:
            raise ValueError(f"No patients {patient_name} found.")
    elif len(patient_objects) == 1:
        if isinstance(patient, tuple):
            if patient[1] >= 1:
                raise ValueError(
                    f"Patient {patient} does not exist. "
                    f"Only one patient with PatientName {patient_name}."
                )
        return patient_objects[0]
    elif len(patient_objects) > 1:
        if isinstance(patient, tuple):
            if patient[1] >= len(patient_objects):
                raise ValueError(
                    f"Patient {patient} does not exist. "
                    f"Only {len(patient_objects)} patients with PatientName {patient_name}."
                )
            else:
                return patient_objects[patient[1]]
        else:
            raise ValueError(
                f"Multiple patients found with the same PatientName {patient_name}."
                f"Please call the function with an index for the patient you want. "
            )             

def _study(database, study, force=False):   

    if len(study) != 2:
        raise ValueError(
            "A study is defined by 2 elements: patient and study."
        )
    patient = _patient(database, study[0], force)

    study_desc = study[-1][0] if isinstance(study[-1], tuple) else study[-1]
    study_objects = Record.studies(patient, StudyDescription=study_desc)
    if len(study_objects) == 0:
        if force:
            return patient.new_study(StudyDescription=study_desc)
        else:
            raise ValueError(f"No studies {study} found.")
    elif len(study_objects) == 1:
        if isinstance(study[-1], tuple):
            if study[-1][1] >= 1:
                raise ValueError(
                    f"Study {study} does not exist. "
                    f"Only one study with StudyDescription {study[-1][0]}. "
                )
        return study_objects[0]
    elif len(study_objects) > 1:
        if isinstance(study[-1], tuple):
            if study[-1][1] >= len(study_objects):
                raise ValueError(
                    f"Study {study} does not exist. "
                    f"Only {len(study_objects)} studies with StudyDescription {study[-1][0]}."
                )
            else:
                return study_objects[study[-1][1]]
        else:
            raise ValueError(
                f"Multiple studies found with the same StudyDescription {study_desc}."
                f"Please call the function with an index for the study you want. "
            )  
        
def _series(database, series, force=False):

    if len(series) != 3:
        raise ValueError(
            "A series is defined by 3 elements: patient, study and series."
        )
    study = _study(database, series[:2], force)

    series_desc = series[-1][0] if isinstance(series[-1], tuple) else series[-1]
    series_objects = Record.series(study, SeriesDescription=series_desc)
    if len(series_objects) == 0:
        if force:
            return study.new_series(SeriesDescription=series_desc)
        else:
            raise ValueError(f"No series {series} found.")
    elif len(series_objects) == 1:
        if isinstance(series[-1], tuple):
            if series[-1][1] >= 1:
                raise ValueError(
                    f"Series {series} does not exist. "
                    f"Only one series with SeriesDescription {series[-1][0]}. "
                )
        return series_objects[0]
    elif len(series_objects) > 1:
        if isinstance(series[-1], tuple):
            if series[-1][1] >= len(series_objects):
                raise ValueError(
                    f"Series {series} does not exist. "
                    f"Only {len(series_objects)} studies with SeriesDescription {series[-1][0]}."
                )
            else:
                return series_objects[series[-1][1]]
        else:
            raise ValueError(
                f"Multiple series found with the same SeriesDescription {series_desc}."
                f"Please call the function with an index for the series you want. "
            )  
            



def zeros(database, shape, dtype='mri'): # OBSOLETE - remove
    study = database.new_study()
    return study.zeros(shape, dtype=dtype)


