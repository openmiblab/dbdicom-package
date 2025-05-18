# Importing annotations to handle or sign in import type hints
from __future__ import annotations

import os
import datetime
from tqdm import tqdm

# Import packages
import numpy as np
import pandas as pd
import dbdicom.ds.dataset as dbdataset
from dbdicom.ds import MRImage
from dbdicom.utils.files import export_path




class Record():

    name = 'Record'

    def __init__(self, create, manager, uid='Database', key=None, **kwargs):   

        self._logfile = None
        self._key = key
        self._mute = False
        self.uid = uid
        self.attributes = kwargs
        self.manager = manager
        self.new = create
        
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.uid == other.uid

    def __getattr__(self, attribute):
        return self.get_values(attribute)

    def __getitem__(self, attributes):
        return self.get_values(attributes)

    def __setattr__(self, attribute, value):
        if attribute in ['_key','_mute', 'uid', 'manager', 'attributes', 'new', '_logfile']:
            self.__dict__[attribute] = value
        else:
            self._set_values([attribute], [value])
           
    def __setitem__(self, attributes, values):
        self._set_values(attributes, values)

    def loc(self):
        return self.manager._loc(self.name, self.uid)
        # df = self.manager.register
        # return (df.removed==False) & (df[self.name]==self.uid)

    def keys(self):
        loc = self.loc()
        keys = self.manager._keys(loc)
#        keys = self.manager.register.index[self.loc()]
        if len(keys) == 0:
            if self.name == 'Database':
                return keys
            else:
                raise Exception("This record has no data")
        else:
            self._key = keys[0]
            return keys

    def _set_key(self):
        loc = self.loc()
        all_keys = self.manager._keys(loc)
        if len(all_keys) == 0:
            msg = 'This record has been removed from the database and can no longer be accessed.'
            raise ValueError(msg)
        self._key = all_keys[0]

    def key(self):
        try:
            key_removed = self.manager._at(self._key, 'removed')
        except:
            self._set_key()
        else:
            if key_removed:
                self._set_key()
        return self._key

    @property
    def status(self): 
        return self.manager.status

    @property
    def dialog(self):
        return self.manager.dialog
    
    
    def set_log(self, filepath:str=None):
        """Set a new file for logging.

        Args:
            filepath: full path to a log file. If not provided the current log file is removed. Alternatively the value 'Default' can be assigned, in which case a standard file at the same location of the database is automatically opened. Defaults to None.

        Raises:
            FileNotFoundError: if the log file cannot be written to.

        See also:
            `log`

        Examples:

            Set a new log file:

            >>> record.set_log('path/to/logfile')
            
            and start logging:

            >>> record.log('Starting new calculation...)

            Alternatively, start a new log at the default location:

            >>> record.set_log('Default')
        """
        if filepath is None:
            self._logfile = None
            return
        if filepath == 'Default':
            # Use default log name
            self._logfile = os.path.join(self.manager.path, "activity_log.txt")
        else:
            self._logfile = filepath
        try:
            file = open(self._logfile, 'a')
            file.write(str(datetime.datetime.now())[0:19] + "Starting a new log..")
            file.close()
        except:
            msg = 'Cannot write to log ' + self._logfile
            raise FileNotFoundError(msg)
        
    def log(self, message:str):
        """Write an entry in the log file.

        If no logfile is set, this function only writes a message in the terminal.

        Args:
            message (str): text message to be written in the log file. The function automatically includes some timing information so this does not need to be included in the message. 

        Raises:
            FileNotFoundError: if the log file cannot be written to.

        See also:
            `set_log`

        Examples:
            Set a default file for logging and write a first message:

            >>> record.set_log('Default')
            >>> record.log('Starting new calculation...)
        """
        
        self.message(message)
        if self._logfile is None:
            return
        try:
            file = open(self._logfile, 'a')
            file.write("\n"+str(datetime.datetime.now())[0:19] + ": " + message)
            file.close()
        except:
            msg = 'Cannot write to log ' + self._logfile
            raise FileNotFoundError(msg)
        
    
# Properties


    def print(self):
        """Print a summary of the record and its contents.

        See Also:
            :func:`~path`

        Example:
            Print a summary of a database:

            >>> database = db.dro.database_hollywood()
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient James Bond
                    Study MRI [19821201]
                        Series 001 [Localizer]
                            Nr of instances: 0
                        Series 002 [T2w]
                            Nr of instances: 0
                    Study Xray [19821205]
                        Series 001 [Chest]
                            Nr of instances: 0
                        Series 002 [Head]
                            Nr of instances: 0
                Patient Scarface
                    Study MRI [19850105]
                        Series 001 [Localizer]
                            Nr of instances: 0
                        Series 002 [T2w]
                            Nr of instances: 0
                    Study Xray [19850106]
                        Series 001 [Chest]
                            Nr of instances: 0
                        Series 002 [Head]
                            Nr of instances: 0
            ----------------------------------  

            Or print a summary of any record in the hierarchy:

            >>> patients = database.patients(PatientName='Scarface')  
            >>> patients[0].print()
            ---------- PATIENT -------------
            Patient Scarface
                Study MRI [19850105]
                    Series 001 [Localizer]
                        Nr of instances: 0
                    Series 002 [T2w]
                        Nr of instances: 0
                Study Xray [19850106]
                    Series 001 [Chest]
                        Nr of instances: 0
                    Series 002 [Head]
                        Nr of instances: 0
            --------------------------------
        """
        self.manager.print(self.uid, self.name) 

    
    def path(self) -> str:
        """Directory of the DICOM database

        Returns:
            str: full path to the directory

        See Also:
            :func:`~print`

        Example:
            Create a new database in memory:

            >>> database = db.database()
            >>> print(database.path())
            None

            Open an existing DICOM database:

            >>> database = db.database('path\\to\\DICOM\\database')
            >>> print(database.path())
            path\to\DICOM\database
        """
        return self.manager.path
    

    def empty(self)->bool:
        """Check if the record has data.

        Returns:
            bool: False if the record has data, True if not

        See Also:
            :func:`~print`
            :func:`~path`

        Example:

            Check if a database on disk is empty:

            >>> database = db.database('path\\to\\database')
            >>> print(database.empty)
            False

            Create a new database from scratch and verify that it is empty:

            >>> database = db.database()
            >>> print(database.empty())
            True

            Creating a new series in the database, and verify that it is no longer empty:

            >>> series = database.new_series()
            >>> print(database.empty())
            False   

            Verify that the new series is empty:

            >>> print(series.empty())
            True

            Populate the series with a numpy array and verify that it is now no longer empty:

            >>> zeros = np.zeros((3, 2, 128, 128))
            >>> series.set_pixel_values(zeros)
            >>> print(series.empty())
            False
        """
        if self.manager.register.empty:
            return True
        return self.children() == []
    

    def files(self) -> list:
        """Return a list of all DICOM files saved in the database

        Returns:
            list: A list of absolute filepaths to valid DICOM files

        See Also:
            :func:`~print`
            :func:`~path`
            :func:`~empty`

        Example:

            A new database in memory has no files on disk:
    
            >>> database = db.database()
            >>> print(database.files())
            []

            If a series is created in memory, there are no files on disk:

            >>> series = db.zeros((3,128,128))
            >>> print(series.files())
            []

            If a series is created in memory, then written to disk, there are files associated. Since the default format is single-frame MRImage, there are 3 files in this case:

            >>> series.write('path\\to\\DICOM\\database')
            >>> print(series.files())
            ['path\\to\\DICOM\\database\\dbdicom\\1.2.826.0.1.3680043.8.498.10200622747714198480020099226433338888.dcm', 'path\\to\\DICOM\\database\\dbdicom\\1.2.826.0.1.3680043.8.498.95074529334441498207488699470663781148.dcm', 'path\\to\\DICOM\\database\\dbdicom\\1.2.826.0.1.3680043.8.498.30452523525370800574103459899629273584.dcm']
        """
        files = [self.manager.filepath(key) for key in self.keys()]
        files = [f for f in files if f is not None] # Added 29/05/23 - check if this creates issues
        return files
    
    
    def label(self)->str:
        """Return a human-readable label describing the record.

        Returns:
            str: label with descriptive information.

        See Also:
            :func:`~print`

        Example:
            Print the label of a default series:

            >>> series = db.zeros((3,128,128), SeriesDescription='Empty demo')
            >>> print(series.label())
            Series 001 [Empty demo]
        """
        return self.manager.label(self.uid, key=self.key(), type=self.__class__.__name__)
    


# Navigating the tree


    def parent(self):
        """Return the parent of the record.

        Returns:
            Record: The parent object.

        See Also:
            :func:`~children`
            :func:`~siblings`
            :func:`~series`
            :func:`~studies`
            :func:`~patients`
            :func:`~database`
            
        Example:
            Find the parent of a study:

            >>> study = db.study()
            >>> patient = study.parent()
            >>> print(patient.PatientName)
            New Patient
        """
        # Note this function is reimplemented in all subclasses. 
        # It is included in the Record class only for documentation purposes.
        return None

    
    def children(self, **kwargs)->list:
        """Return all children of the record.

        Args:
            kwargs: Provide any number of valid DICOM (tag, value) pair as keywords to filter the list.

        Returns:
            list: A list of all children.

        See Also:
            :func:`~parent`
            :func:`~siblings`
            :func:`~series`
            :func:`~studies`
            :func:`~patients`
            :func:`~database`
            
        Example:
            Find the patients of a given database:

            >>> database = db.dro.database_hollywood()
            >>> patients = database.children()
            >>> print([p.PatientName for p in patients])
            ['James Bond', 'Scarface']

            Find all patients with a given name:

            >>> patients = database.children(PatientName='James Bond')
            >>> print([p.PatientName for p in patients])
            ['James Bond']

            Find the studies that have been performed on a given patient:
            >>> studies = patients[0].children()
            >>> print([s.StudyDescription for s in studies])
            ['MRI', 'Xray']
        """
        # Note this function is reimplemented in all subclasses. 
        # It is included in the Record class for documentation purposes.
        return []
    
    
    def siblings(self, **kwargs)->list:
        """Return all siblings of the record.

        Args:
            kwargs: Provide any number of valid DICOM (tag, value) pair as keywords to filter the list.

        Returns:
            list: A list of all siblings.

        See Also:
            :func:`~parent`
            :func:`~children`
            :func:`~series`
            :func:`~studies`
            :func:`~patients`
            :func:`~database`
            
        Example:
            Retrieve a study from a database, and find all other studies performed on the same patient:

            >>> database = db.dro.database_hollywood()
            >>> study = database.studies()[0]
            >>> print([s.StudyDescription for s in study.siblings()])
            ['Xray']
        """
        siblings = self.parent().children(**kwargs)
        siblings.remove(self)
        return siblings

    
    def series(self, series=None, sort=True, 
               sortby=['PatientName', 'StudyDescription', 'SeriesNumber'], 
               select={}, **kwargs) -> list:
        """Return a list of series under the record.

        If the record is a study, this returns the record's children. If it is a patient, this returns a list the record's grand children.

        Args:
            sort (bool, optional): Set to False to return an unsorted list (faster). Defaults to True.
            sortby (list, optional):  list of DICOM keywords to sort the result. This argument is ignored if sort=False. Defaults to ['PatientName', 'StudyDescription', 'SeriesNumber'].
            kwargs (keyword arguments, optional): Set any number of valid DICOM (tag, value) pairs as keywords to filer the list. The result will only contain series with the appropriate values

        Returns:
            list: A list of dbdicom Series objects.

        See Also:
            :func:`~parent`
            :func:`~children`
            :func:`~siblings`
            :func:`~studies`
            :func:`~patients`
            :func:`~database`

        Example:
            Find all series in a database, and print their labels:

            >>> database = db.dro.database_hollywood()
            >>> series_list = database.series()
            >>> print([s.label() for s in series_list])
            ['Series 001 [Localizer]', 'Series 002 [T2w]', 'Series 001 [Chest]', 'Series 002 [Head]', 'Series 001 [Localizer]', 'Series 002 [T2w]', 'Series 001 [Chest]', 'Series 002 [Head]']

            Find all series with a given SeriesDescription:

            >>> series_list = database.series(SeriesDescription='Chest')
            >>> print([s.label() for s in series_list])
            ['Series 001 [Chest]', 'Series 001 [Chest]']

            Find all series with a given SeriesDescription of a given Patient:

            >>> series_list = database.series(SeriesDescription='Chest', PatientName='James Bond')
            >>> print([s.label() for s in series_list])
            ['Series 001 [Chest]']
        """
        if series is not None:
            kwargs = {'SeriesDescription': series} | kwargs
            return self.series(sort=sort, sortby=sortby, select=select, **kwargs)
        keys = self.keys()
        series = self.manager.series(keys=keys, sort=sort, sortby=sortby, select=select, **kwargs)
        return [self.record('Series', uid) for uid in series]

    
    def studies(self, sort=True, sortby=['PatientName', 'StudyDescription'], **kwargs)->list:
        """Return a list of studies under the record.

        If the record is a patient, this returns the record's children. If it is a series, this returns the parent study.

        Args:
            sort (bool, optional): Set to False to return an unsorted list (faster). Defaults to True.
            sortby (list, optional):  list of DICOM keywords to sort the result. This argument is ignored if sort=False. Defaults to ['PatientName', 'StudyDescription'].
            kwargs (keyword arguments, optional): Set any number of valid DICOM (tag, value) pairs as keywords to filer the list. The result will only contain studies with the appropriate values.

        Returns:
            list: A list of dbdicom Study objects.

        See Also:
            :func:`~parent`
            :func:`~children`
            :func:`~siblings`
            :func:`~series`
            :func:`~patients`
            :func:`~database`
        
        Example:
            Find all studies in a database:

            >>> database = db.dro.database_hollywood()
            >>> studies_list = database.studies()
            >>> print([s.label() for s in studies_list])
            ['Study MRI [19821201]', 'Study Xray [19821205]', 'Study MRI [19850105]', 'Study Xray [19850106]']

            Find all studies of a given Patient:

            >>> studies_list = database.studies(PatientName='James Bond')
            >>> print([s.label() for s in studies_list])
            ['Study MRI [19821201]', 'Study Xray [19821205]']
        """
        studies = self.manager.studies(keys=self.keys(), sort=sort, sortby=sortby, **kwargs)
        return [self.record('Study', uid) for uid in studies]

    
    def patients(self, sort=True, sortby=['PatientName'], **kwargs)->list:
        """Return a list of patients under the record.

        If the record is a database, this returns the children. If it is a series or a study, this returns the parent patient.

        Args:
            sort (bool, optional): Set to False to return an unsorted list (faster). Defaults to True.
            sortby (list, optional):  list of DICOM keywords to sort the result. This argument is ignored if sort=False. Defaults to ['PatientName'].
            kwargs (keyword arguments, optional): Set any number of valid DICOM (tag, value) pairs as keywords to filer the list. The result will only contain patients with the appropriate values.

        Returns:
            list: A list of dbdicom Patient objects.

        See Also:
            :func:`~parent`
            :func:`~children`
            :func:`~siblings`
            :func:`~series`
            :func:`~studies`
            :func:`~database`

        Example:
            Find all patients in a database:

            >>> database = db.dro.database_hollywood()
            >>> patients_list = database.patients()
            >>> print([s.label() for s in patients_list])
            ['Patient James Bond', 'Patient Scarface']

            Find all patients with a given name:

            >>> patients_list = database.patients(PatientName='James Bond')
            >>> print([s.label() for s in patients_list])
            ['Patient James Bond']
        """
        patients = self.manager.patients(keys=self.keys(), sort=sort, sortby=sortby, **kwargs)
        return [self.record('Patient', uid) for uid in patients]
    
    
    def database(self):
        """Return the database of the record.

        Returns:
            Database: Database of the record

        See Also:
            :func:`~parent`
            :func:`~children`
            :func:`~siblings`
            :func:`~series`
            :func:`~studies`

        Example:
            Get the database of a study:

            >>> study = db.study()
            >>> database = study.database()
            >>> print(database.label())
            Database [in memory]
        """
        return self.record('Database')


# Edit a record


    def new_patient(self, **kwargs):
        """Create a new patient.

        Args:
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the new patient.

        Returns:
            Patient: instance of the new patient

        See Also:
            :func:`~new_study`
            :func:`~new_series`
            :func:`~new_pibling`

        Example:
            Create a new patient in a database:

            >>> database = db.database()
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
            ----------------------------------
            
            >>> nemo = database.new_patient(PatientName='Nemo')
            >>> dory = database.new_patient(PatientName='Dory')
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
            Patient Dory
            Patient Nemo
            ----------------------------------

            A lower-level record can also create a new patient. Create a new series and show its default database:

            >>> series = db.series()
            >>> series.database().print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient New Patient
                    Study New Study [None]
                    Series 001 [New Series]
                        Nr of instances: 0
            ----------------------------------

            The series can create new patients in its database directly:

            >>> dory = series.new_patient(PatientName='Dory')
            >>> nemo = series.new_patient(PatientName='Nemo')
            >>> series.print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient Dory
                Patient Nemo
                Patient New Patient
                    Study New Study [None]
                        Series 001 [New Series]
                            Nr of instances: 0
            ----------------------------------
        """
        attr = {**kwargs, **self.attributes}
        uid, key = self.manager.new_patient(parent=self.uid, **attr)
        return self.record('Patient', uid, key, **attr)
    

    def new_study(self, **kwargs):
        """Create a new study.

        Args:
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the new study.

        Returns:
            Study: instance of the new study

        See Also:
            :func:`~new_patient`
            :func:`~new_series`
            :func:`~new_pibling`

        Example:
            Create a new study in a patient:

            >>> dory = db.patient(PatientName='Dory')
            >>> dory.print()
            ---------- PATIENT -------------
            Patient Dory
            --------------------------------

            >>> fMRI = dory.new_study(StudyDescription='fMRI', StudyDate='20091001')
            >>> CThead = dory.new_study(StudyDescription='CT head', StudyDate='20091002')
            >>> dory.print()
            ---------- PATIENT -------------
            Patient Dory
                Study CT head [20091002]
                Study fMRI [20091001]
            --------------------------------

            Any other record can also create a new study. Missing intermediate generations are created automatically:

            >>> database = db.database()
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
            ----------------------------------

            >>> fMRI = database.new_study(StudyDescription='fMRI')
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient New Patient
                    Study fMRI [None]
            ----------------------------------
        """
        attr = {**kwargs, **self.attributes}
        uid, key = self.manager.new_study(parent=self.uid, key=self.key(),**attr)
        return self.record('Study', uid, key, **attr)
    

    def new_series(self, **kwargs):
        """Create a new series.

        Args:
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the new series.

        Returns:
            Series: instance of the new series

        See Also:
            :func:`~new_patient`
            :func:`~new_study`
            :func:`~new_pibling`

        Example:
            Consider an empty study:

            >>> fMRI = db.study(StudyDescription='fMRI', StudyDate='20230203')
            >>> fMRI.print()
            ---------- STUDY ---------------
            Study fMRI [20230203]
            --------------------------------

            Create two new series in the study:

            >>> rstate = fMRI.new_series(SeriesDescription='Resting state')
            >>> ftap = fMRI.new_series(SeriesDescription='Finger tap')
            >>> fMRI.print()
            ---------- STUDY ---------------
            Study fMRI [20230203]
                Series 001 [Resting state]
                    Nr of instances: 0
                Series 002 [Finger tap]
                    Nr of instances: 0
            --------------------------------

            Any other record can also create a new series. Missing intermediate generations are created automatically:

            >>> database = db.database()
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
            ----------------------------------

            >>> rstate = database.new_series(SeriesDescription='Resting state')
            >>> ftap = database.new_series(SeriesDescription='Finger tap')
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
            Patient New Patient
                Study New Study [None]
                    Series 001 [Resting state]
                        Nr of instances: 0
            Patient New Patient
                Study New Study [None]
                    Series 001 [Finger tap]
                        Nr of instances: 0
            ----------------------------------

            Note since any missing levels in the hierarchy are automatically created, these new series now end up in different patients.

        """
        attr = {**kwargs, **self.attributes}
        uid, key = self.manager.new_series(parent=self.uid, **attr)
        return self.record('Series', uid, key, **attr)
    

    def new_child(self, **kwargs):
        """Create a new child of the record.

        Args:
            kwargs: Any valid DICOM (tag, value) pair to assign to the new sibling.

        See Also:
            :func:`~new_patient`
            :func:`~new_study`
            :func:`~new_series`
            :func:`~new_sibling`
            :func:`~new_pibling`

        Example:
            Consider an empty study:

            >>> fMRI = db.study(StudyDescription='fMRI', StudyDate='20230203')
            >>> fMRI.print()
            ---------- STUDY ---------------
            Study fMRI [20230203]
            --------------------------------

            Create two new series in the study:

            >>> rstate = fMRI.new_child(SeriesDescription='Resting state')
            >>> ftap = fMRI.new_child(SeriesDescription='Finger tap')
            >>> fMRI.print()
            ---------- STUDY ---------------
            Study fMRI [20230203]
                Series 001 [Resting state]
                    Nr of instances: 0
                Series 002 [Finger tap]
                    Nr of instances: 0
            --------------------------------

            Note the same result could also be obtained by calling :func:`~new_series` on the study.
        """
        # Note this function is implemented in all subclasses - included here for documentation purposes.
        pass

    
    def new_sibling(self, suffix:str=None, **kwargs):
        """Create a new sibling of the record under the same parent.

        Args:
            kwargs: Any valid DICOM (tag, value) pair to assign to the new sibling.

        Raises:
            RuntimeError: when called on a Record of type Database. New records can only be created within an existing database.

        See Also:
            :func:`~new_patient`
            :func:`~new_study`
            :func:`~new_series`
            :func:`~new_pibling`

        Example:
            Create a sibling series under the same study:

            >>> rstate = db.series(SeriesDescription='Resting state')
            >>> ftap = rstate.new_sibling(SeriesDescription='Finger tap')
            >>> rstate.parent().print()
            ---------- STUDY ---------------
            Study New Study [None]
                Series 001 [Resting state]
                    Nr of instances: 0
                Series 002 [Finger tap]
                    Nr of instances: 0
            --------------------------------
        """
        # Note this function is implemented in all subclasses - included here for documentation purposes.
        # Note the suffix argument is deprecated and should not be used.
        pass

    
    def new_pibling(self, **kwargs):
        """Create a new sibling of the parent record (pibling).

        Args:
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the new pibling.

        Returns:
            Record: instance of the new parent

        See Also:
            :func:`~new_patient`
            :func:`~new_study`
            :func:`~new_series`

        Example:
            Use a series to create a new study directly. A use case is where image processing results derived from a series should be saved in a separate study under the same patient. 

            >>> fMRI = db.study(StudyDescription='fMRI', StudyDate='202305010')
            >>> rstate = fMRI.new_series(SeriesDescription='Resting state')
            >>> rstate_results = rstate.new_pibling(StudyDescription='fMRI resting state analysis', StudyDate='20230603')
            >>> rstate.patient().print()
            ---------- PATIENT -------------
            Patient New Patient
            Study New Study [None]
                Series 001 [Resting state]
                    Nr of instances: 0
            Study fMRI resting state analysis [20230603]
            --------------------------------
        """
        type = self.__class__.__name__
        if type == 'Database':
            return None
        if type == 'Patient':
            return None
        return self.parent().new_sibling(**kwargs)

    
    def remove(self):
        """Remove a record from the database.

        See Also:
            :func:`~copy`
            :func:`~copy_to`
            :func:`~move_to`

        Example:
            Create a new study in an empty database, then remove it again:

            >>> database = db.database()
            >>> study = database.new_study(StudyDescription='Demo Study')
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient New Patient
                    Study Demo Study [None]
            ----------------------------------

            >>> study.remove()
            >>> database.print()
            ---------- DATABASE --------------
            Location:  In memory
                Patient New Patient
            ----------------------------------

            A record that has been removed from the database can no longer be accessed. Any attempt to do so will raise an error:

            >>> print(study.label())
            ValueError: This record has been removed from the database and can no longer be accessed.

        Note: 
            Removing a record will also remove all of its children, and this will be permanent after saving the record with :func:`~save`. 
            
            If a record has been removed accidentally in an interactive session, use :func:`~restore` to revert back to the last saved state. 
        """
        self.manager.delete(self.uid, keys=self.keys())


    def move_to(self, parent):
        """Move the record to another parent.

        Args:
            parent: parent where the record will be moved to.

        See Also:
            :func:`~remove`
            :func:`~copy`
            :func:`~copy_to`

        Example:
            Create a database with two studies and a single series in one:

            >>> demo = db.series(SeriesDescription='!!WATCH ME MOVE!!')
            >>> test = demo.new_pibling(StudyDescription='Test')
            >>> series.patient().print()
            ---------- PATIENT -------------
            Patient New Patient
                Study New Study [None]
                    Series 001 [!!WATCH ME MOVE!!]
                        Nr of instances: 0
            Study Test [None]
            --------------------------------

            Now move the series to the other study:

            >>> series.move_to(study)
            >>> series.patient().print()
            ---------- PATIENT -------------
            Patient New Patient
                Study New Study [None]
                Study Test [None]
                    Series 001 [Demo]
                        Nr of instances: 0
            --------------------------------

        """
        move_to(self, parent)
        return self


    def copy_to(self, parent, **kwargs):
        """Return a copy of the record under another parent.

        Args:
            parent: parent where the copy will be placed.
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the copy.

        Returns:
            Record: copy of the same type.

        See Also:
            :func:`~remove`
            :func:`~copy`
            :func:`~move_to`

        Example:
            Create a database with a single patient/study/series:

            >>> series = db.series(SeriesDescription='Demo')
            >>> series.patient().print()
            ---------- PATIENT -------------
            Patient New Patient
                Study New Study [None]
                    Series 001 [Demo]
                        Nr of instances: 0
            --------------------------------

            Create a new study *Copies* under the same patient, and copy the the *Demo* series into it:

            >>> study = series.new_pibling(StudyDescription='Copies')
            >>> copy = series.copy_to(study, SeriesDescription='Copy of Demo')

            The same patient now has two studies, each with a single series:

            >>> series.patient().print()
            ---------- PATIENT -------------
            Patient New Patient
                Study Copies [None]
                    Series 001 [Copy of Demo]
                        Nr of instances: 0
                Study New Study [None]
                    Series 001 [Demo]
                        Nr of instances: 0
            --------------------------------
        """
        return parent._copy_from(self, **kwargs)
    
    
    def copy(self, **kwargs):
        """Return a copy of the record under the same parent.

        Args:
            kwargs (optional): Any valid DICOM (tag, value) pair can be assigned up front as properties of the copy.

        Returns:
            Record: copy of the same type.

        See Also:
            :func:`~remove`
            :func:`~copy_to`
            :func:`~move_to`

        Example:
            Create a new DICOM study and build two copies in the same patient, assigning a new study description on the fly:

            >>> study = db.study(StudyDescription='Original', StudyDate='20001231')
            >>> copy1 = study.copy(StudyDescription='Copy 1')
            >>> copy2 = study.copy(StudyDescription='Copy 2')
            >>> study.parent().print()
            ---------- PATIENT -------------
            Patient New Patient
                Study Copy 1 [20001231]
                Study Copy 2 [20001231]
                Study Original [20001231]
            --------------------------------
        """
        return self.copy_to(self.parent(), **kwargs)


# Load and save


    def restore(self):
        """Restore the record to the last changed state.

        .. warning::

            Restoring is irreversible! Any edits made to the record since the last time it was saved will be lost.

        See Also:
            :func:`~save`
        
            Create a new patient and change the name:

            >>> patient = db.patient(PatientName='James Bond')
            >>> patient.PatientName = 'Scarface'
            >>> print(patient.PatientName)
            Scarface

            Calling restore will undo the changes:

            >>> patient.restore()
            >>> print(patient.PatientName)
            James Bond
        """        
        rows = self.manager._extract_record(self.name, self.uid)
        self.manager.restore(rows)
        self.write()


    def save(self, path=None):
        """Save any changes made to the record.

        .. warning::

            Saving is irreversible! Any edits made to the record before saving cannot be undone.

        See Also:
            :func:`~restore`
        
        Example:
            Create a new patient, change the name, and save:

            >>> patient = db.patient(PatientName='James Bond')
            >>> patient.PatientName = 'Scarface'
            >>> patient.save()

            At this point the original information can no longer be restored. Calling restore does not revert back to the original:

            >>> patient.restore()
            >>> print(patient.PatientName)
            Scarface
        """
        rows = self.manager._extract_record(self.name, self.uid)
        self.manager.save(rows)
        self.write(path)
        return self
        

    def load(self):
        """Load the record into memory.

        After loading the record into memory, all subsequent changes will be made in memory only. Call clear() to write any changes to disk and remove it from memory. 

        Note: 
            If the record already exists in memory, read() does nothing. This is to avoid that any changes made after reading are overwritten.

        See Also:
            :func:`~clear`

        Example:

            As an example, we can verify that editing data in memory is faster than on disk. We'll need the time package and a large series on disk: 

            >>> from time import time
            >>> path = 'path\\to\\empty\\folder'
            >>> series = db.zeros((20,20,256,256), in_database=db.database(path))

            Now measure the time it takes to set the slice locations to a constant value:

            >>> t=time(); series.SliceLocation=1; print(time()-t)
            17.664631605148315

            Since the series was created on disk, this is editing on disk. Now load the series into memory and perform the same steps:

            >>> series.load()
            >>> t=time(); series.SliceLocation=1; print(time()-t)
            2.3518126010894775

            On the machine where this was executed, the same computation runs more than 10 times faster in memory.
        """
        self.manager.read(self.uid, keys=self.keys())
        return self
    

    def clear(self):
        """Clear the record from memory.

        This will write the record to disk and clear it from memory. After this step, subsequent calculations will be performed from disk.

        Note: 
            If the record does not exist in memory, or if its database does not have a path on disk associated, read() does nothing.

        See Also:
            :func:`~read`

        Example:

            As an example, we can verify that editing data in memory is faster than on disk. We'll need the time package and a large series in memory. We also provide a path to a directory for writing data: 

            >>> from time import time
            >>> series = db.zeros((20,20,256,256))
            >>> series.database().set_path(path)

            Now measure the time it takes to set the slice locations to a constant value:

            >>> t=time(); series.SliceLocation=1; print(time()-t)
            1.9060208797454834

            Since the series was created in memory, this is editing in memory. Now we clear the series from memory and perform the same computation:

            >>> series.clear()
            >>> t=time(); series.SliceLocation=1; print(time()-t)
            17.933974981307983

            The computation is now run from disk and is 10 times slower because of the need to read and write the files.
        """
        self.manager.clear(self.uid, keys=self.keys())


    def export_as_dicom(self, path:str):
        """Export record in DICOM format to an external directory.

        Note since this is exporting outside of the current database this will assign new identifiers to the exported data. 

        Args:
            path (str): path to export directory.

        See Also:
            :func:`~export_as_png`
            :func:`~export_as_nifti`
            :func:`~export_as_npy`
            :func:`~export_as_csv`

        Example:

            Create a 4D series and export as DICOM

            >>> series = db.ones((128, 128, 10, 5))
            >>> path = 'path\\to\\empty\\folder'
            >>> series.export_as_dicom(path)

            This should create a single folder in the directory, populated with 50 DICOM files.
        """
        if self.name == 'Database':
            folder = 'Database' 
        else:
            folder = self.label()
        path = export_path(path, folder)
        for child in self.children():
            child.export_as_dicom(path)


    def export_as_png(self, path:str, center:float=None, width:float=None, colormap:str=None): 
        """Export record in PNG format.

        Args:
            path (str): path to export directory.
            center (float, optional): center of the color window. Defaults to None, in which case the center is taken from the DICOM header.
            width (float, optional): width of the color window. Defaults to None, in which case the width is taken from the DICOM header.
            colormap (str, optional): color map to use as lookup table. Any valid matplotlib colormap can be entered here. Please the `matplotlib colormap reference <https://matplotlib.org/stable/gallery/color/colormap_reference.html>`_ for a complete list. Defaults to None, in which case the colormap is taken from the DICOM header. 

        See Also:
            :func:`~export_as_dicom`
            :func:`~export_as_nifti`
            :func:`~export_as_npy`
            :func:`~export_as_csv`

        Example:

            Create a 4D series and export as PNG, using the colormap plasma:

            >>> series = db.ones((128, 128, 10, 5))
            >>> path = 'path\\to\\empty\\folder'
            >>> series.export_as_png(path, center=1, width=0.5, colormap='plasma')

            This should create a single folder in the directory, populated with 50 PNG files.
        """
        if self.name == 'Database':
            folder = 'Database' 
        else:
            folder = self.label()
        path = export_path(path, folder)
        for child in self.children():
            child.export_as_png(path, center=center, width=width, colormap=colormap)

    def export_as_csv(self, path:str):
        """Export record in CSV format to an external directory.

        Args:
            path (str): path to export directory.

        See Also:
            :func:`~export_as_png`
            :func:`~export_as_nifti`
            :func:`~export_as_npy`
            :func:`~export_as_dicom`

        Example:

            Create a 4D series and export as CSV:

            >>> series = db.ones((128, 128, 10, 5))
            >>> path = 'path\\to\\empty\\folder'
            >>> series.export_as_csv(path)

            This should create a single folder in the directory, populated with 50 CSV files.
        """
        if self.name == 'Database':
            folder = 'Database' 
        else:
            folder = self.label()
        path = export_path(path, folder)
        for child in self.children():
            child.export_as_csv(path)


    # def export_as_nifti(self, path:str, dims:tuple=None):
    #     """Export record in NIFTI format to an external directory.

    #     Args:
    #         path (str): path to export directory.
    #         dims (tuple, optional): when set, volumes are extracted along the given dimensions and exported in single files. If dims is not set, each image will be exported in its own file. 

    #     See Also:
    #         :func:`~export_as_png`
    #         :func:`~export_as_dicom`
    #         :func:`~export_as_npy`
    #         :func:`~export_as_csv`

    #     Example:

    #         Create a 4D series and export as NIFTI:

    #         >>> series = db.ones((128, 128, 10, 5))
    #         >>> path = 'path\\to\\empty\\folder'
    #         >>> series.export_as_nifti(path)

    #         This should create a single folder in the directory, populated with 50 NIFTI files.

    #         In order to export the entire series in a single volume, provide the dimensions along which the volume is to be taken:

    #         >>> dims = ('SliceLocation', 'AcquisitionTime')
    #         >>> series.export_as_nifti(path, dims=dims)

    #         This will now create a single nifti file.

    #         Note: in this case the dimensions must be specified as slice location and acquisition time because these are the default dimensions used by series creation functions like :func:`~ones`.
    #     """
    #     if self.name == 'Database':
    #         folder = 'Database' 
    #     else:
    #         folder = self.label()
    #     path = export_path(path, folder)
    #     for child in self.children():
    #         child.export_as_nifti(path, dims=dims)


    def export_as_npy(self, path:str, dims:tuple=None):
        """Export record in numpy's NPY format to an external directory.

        Args:
            path (str): path to export directory.
            dims (tuple, optional): when set, volumes are extracted along the given dimensions and exported in single files. If dims is not set (None), each image will be exported in its own file. Defaults to None.

        See Also:
            :func:`~export_as_png`
            :func:`~export_as_nifti`
            :func:`~export_as_dicom`
            :func:`~export_as_csv`

        Example:

            Create a 4D series:

            >>> series = db.ones((128, 128, 10, 5))

            Export the series as npy, with each slice in a separate file:

            >>> path = 'path\\to\\empty\\folder'
            >>> series.export_as_npy(path)

            This will create 50 npy files in the folder, one for each image. To save the entire volume in a single file, specify the dimensions of the volume:

            >>> dims = ('SliceLocation', 'AcquisitionTime')
            >>> series.export_as_npy(path, dims)

            This will create a single npy file. 

            Note: in this case the dimensions must be specified as slice location and acquisition time because these are the default dimensions used by series creation functions like :func:`~ones`.
        """
        if self.name == 'Database':
            folder = 'Database' 
        else:
            folder = self.label()
        path = export_path(path, folder)
        for child in self.children():
            child.export_as_npy(path, dims=dims)



    def progress(self, value: float, maximum: float, message: str=None):
        """Print progress message to the terminal..

        Args:
            value (float): current status
            maximum (float): maximal value
            message (str, optional): Message to include in the update. Defaults to None.

        Note:
            When working through a terminal this could easily be replicated with a print statement. The advantage of using the progress interface is that the code does not need to be changed when the computation is run through a graphical user interface (assuming this uses a compatible API). 
            
            Another advantage is that messaging can be muted/unmuted using .mute() and .unmute(), for instance when the object is passed to a subroutine.

        See Also:
            :func:`~message`
            :func:`~mute`
            :func:`~unmute`

        Example:
            >>> nr_of_slices = 3
            >>> series = db.zeros((nr_of_slices,128,128))
            >>> for slice in range(nr_of_slices):
                series.progress(1+slice, nr_of_slices, 'Looping over slices')
            Looping over slices [33 %]
            Looping over slices [67 %]
            Looping over slices [100 %]  
        """
        if not self._mute:
            self.manager.status.progress(value, maximum, message=message)

    def in_gui(self):
        return hasattr(self.manager.status, 'progressBar')


    def message(self, message: str):
        """Print a message to the user.

        Args:
            message (str): Message to be printed.

        Note:
            When working through a terminal a print statement would have exactly the same effect. The advantage of using the message interface is that the code does not need to be changed when the computation is run through a graphical user interface (assuming this uses a compatible API). 
            
            Another advantage is that messaging can be muted/unmuted using .mute() and .unmute() for instance when the object is passed to a subroutine.

        See Also:
            :func:`~progress`
            :func:`~mute`
            :func:`~unmute`

        Example:

            >>> series.message('Starting computation..')
            Starting computation..
            
            After muting the same statment does not send a message:

            >>> series.mute()
            >>> series.message('Starting computation..')

            Unmute to reactivate sending messages:

            >>> series.unmute()
            >>> series.message('Starting computation..')
            Starting computation..
        """
        if not self._mute:
            self.manager.status.message(message)

    def mute(self):
        """Prevent the object from sending status updates to the user

        See Also:
            :func:`~unmute`
            :func:`~message`
            :func:`~progress`
        
        Example:
            >>> series = db.zeros((3,128,128))
            >>> print('My message: ')
            >>> series.message('Hello World')
            >>> series.mute()
            >>> print('My message: ')
            >>> series.message('Hello World')

            My message: 
            Hello World
            My message:
        """
        self._mute = True
        self.status.muted = True
        
    def unmute(self):
        """Allow the object from sending status updates to the user

        Note:
            Records are unmuted by default, so unmuting is only necessary after a previouse call to mute(). Unmuting has no effect when the record is already unmuted.

        See Also:
            :func:`~mute`
            :func:`~message`
            :func:`~progress`
        
        Example:
            >>> series = db.zeros((3,128,128))
            >>> print('My message: ')
            >>> series.message('Hello World')
            >>> series.mute()
            >>> print('My message: ')
            >>> series.message('Hello World')
            >>> series.unmute()
            >>> print('My message: ')
            >>> series.message('Hello World')

            My message: 
            Hello World
            My message:
            My message:
            Hello World
        """
        self._mute = False
        self.status.muted = False

    def type(self):
        return self.__class__.__name__

    def exists(self):
        #if self.manager.register is None:
        if not self.manager.is_open():
            return False
        try:
            keys = self.keys().tolist()
        except:
            return False
        return keys != []

    def record(self, type, uid='Database', key=None, **kwargs):
        return self.new(self.manager, uid, type, key=key, **kwargs)

    def register(self):
        return self.manager._extract(self.keys())
        #return self.manager.register.loc[self.keys(),:]
    
    def instances(self, sort=True, sortby=None, select={}, **kwargs): 
        inst = self.manager.instances(keys=self.keys(), sort=sort, sortby=sortby, select=select, **kwargs)
        return [self.record('Instance', uid, key) for key, uid in inst.items()]

    def images(self, sort=True, sortby=None, **kwargs): 
        inst = self.manager.instances(keys=self.keys(), sort=sort, sortby=sortby, images=True, **kwargs)
        return [self.record('Instance', uid, key) for key, uid in inst.items()]



    # This needs a test whether the instance is an image - else move to the next
    def image(self, **kwargs):
        return self.instance(**kwargs)
    
    # Needs a unit test
    def instance(self, uid=None, key=None):
        if key is not None:
            #uid = self.manager.register.at[key, 'SOPInstanceUID']
            uid = self.manager._at(key, 'SOPInstanceUID')
            if uid is None:
                return
            return self.record('Instance', uid, key=key)
        if uid is not None:
            return self.record('Instance', uid)
        key = self.key()
        #uid = self.manager.register.at[key, 'SOPInstanceUID']
        uid = self.manager._at(key, 'SOPInstanceUID')
        return self.record('Instance', uid, key=key)

    # Needs a unit test
    def sery(self, uid=None, key=None):
        if key is not None:
            #uid = self.manager.register.at[key, 'SeriesInstanceUID']
            uid = self.manager._at(key, 'SeriesInstanceUID')
            if uid is None:
                return
            return self.record('Series', uid, key=key)
        if uid is not None:
            return self.record('Series', uid)
        key = self.key()
        #uid = self.manager.register.at[key, 'SeriesInstanceUID']
        uid = self.manager._at(key, 'SeriesInstanceUID')
        return self.record('Series', uid, key=key)

    # Needs a unit test
    def study(self, uid=None, key=None):
        if key is not None:
            #uid = self.manager.register.at[key, 'StudyInstanceUID']
            uid = self.manager._at(key, 'StudyInstanceUID')
            if uid is None:
                return
            return self.record('Study', uid, key=key)
        if uid is not None:
            return self.record('Study', uid)
        key = self.key()
        #uid = self.manager.register.at[key, 'StudyInstanceUID']
        uid = self.manager._at(key, 'StudyInstanceUID')
        return self.record('Study', uid, key=key)

    # Needs a unit test
    def patient(self, uid=None, key=None):
        if key is not None:
            #uid = self.manager.register.at[key, 'PatientID']
            uid = self.manager._at(key, 'PatientID')
            if uid is None:
                return
            return self.record('Patient', uid, key=key)
        if uid is not None:
            return self.record('Patient', uid)
        key = self.key()
        #uid = self.manager.register.at[key, 'PatientID']
        uid = self.manager._at(key, 'PatientID')
        return self.record('Patient', uid, key=key)




    def read(self): # Obsolete - replace by load()
        return self.load()


    def write(self, path=None):
        if path is not None:
            self.manager.path = path
        try:
            keys = self.keys()
        except: # empty database
            pass
        else:
            self.manager.write(self.uid, keys=keys)
        self.manager._write_df()


    def new_instance(self, dataset=None, **kwargs):
        attr = {**kwargs, **self.attributes}
        uid, key = self.manager.new_instance(parent=self.uid, dataset=dataset, **attr)
        return self.record('Instance', uid, key, **attr)

    def _set_values(self, attributes, values):
        keys = self.keys()
        self._key = self.manager.set_values(attributes, values, keys)

    def get_values(self, attributes):
        return self.manager.get_values(attributes, self.keys())
    
    def init_dataset(self, dtype='mri'):
        if dtype=='mri':
            ds = MRImage()
        else: # dummy option for now
            ds = MRImage()
        for a in self.attributes:
            ds.set_values(a, self.attributes[a])
        return ds

    def get_dataset(self):
        ds = self.manager.get_dataset(self.uid, self.keys())
        return ds

    def set_dataset(self, dataset):
        self.manager.set_dataset(self.uid, dataset, self.keys())

    def read_dataframe(*args, **kwargs):
        return read_dataframe(*args, **kwargs)

    def series_data(self):
        attr = dbdataset.module_series()
        vals = self[attr]
        return attr, vals

    def study_data(self):
        attr = dbdataset.module_study()
        vals = self[attr]
        return attr, vals

    def patient_data(self):
        attr = dbdataset.module_patient()
        vals = self[attr]
        return attr, vals

    
    # def tree(*args, **kwargs):
    #     return tree(*args, **kwargs)



#
# Functions on a list of records of the same database
#


def copy_to(records:list, parent:Record):
    """Copy a list of records to a new parent.

    Args:
        records (list): list of Records of the same type
        parent (Record): location for the copies.

    See also:
        `copy`
        `move_to`

    Example:

        Consider the hollywood demo database:

        >>> database = db.dro.database_hollywood()

        There are currently two MRI studies in the database:

        >>> MRIs = database.studies(StudyDescription='MRI)
        >>> len(MRIs)
        2

        Create a new patient and copy the MRI studies there:

        >>> tarantino = database.new_patient(PatientName='Tarantino')
        >>> db.copy_to(MRIs, tarantino)
        >>> tarantino_MRIs = tarantino.studies()
        >>> len(tarantino_MRIs)
        2

        Note that all header information is automatically updated:

        >>> tarantino_MRIs[0].PatientName
        Tarantino

        Since the studies were copied, the originals remained and the total number of studies in the database has increased:

        >>> MRIs = database.studies(StudyDescription='MRI)
        >>> len(MRIs)
        4
    """
    if not isinstance(records, list):
        return records.copy_to(parent)
    copy = []
    desc = parent.label()
    for r, record in enumerate(records):
        record.progress(r+1, len(records), 'Copying to ' + desc)
        copy_record = record.copy_to(parent)
        if isinstance(copy_record, list):
            copy += copy_record
        else:
            copy.append(copy_record)
    record.status.hide()
    return copy

def move_to(records:list, target:Record):
    """Move a list of records to a new parent.

    Args:
        records (list): list of Records of the same type
        parent (Record): location for the copies.

    See also:
        `copy`
        `copy_to`

    Example:

        Consider the hollywood demo database:

        >>> database = db.dro.database_hollywood()

        There are currently two MRI studies in the database:

        >>> MRIs = database.studies(StudyDescription='MRI)
        >>> len(MRIs)
        2

        Create a new patient and move the MRI studies there:

        >>> tarantino = database.new_patient(PatientName='Tarantino')
        >>> db.copy_to(MRIs, tarantino)
        >>> tarantino_MRIs = tarantino.studies()
        >>> len(tarantino_MRIs)
        2

        Note that all header information is automatically updated:

        >>> tarantino_MRIs[0].PatientName
        Tarantino

        Since the studies were moved, the total number of studies in the database has stayed the same:

        >>> MRIs = database.studies(StudyDescription='MRI)
        >>> len(MRIs)
        2

        And the original patients do not have any MRI studies left:

        >>> jb = database.patients(PatientName = 'James Bond')
        >>> MRIs = jb[0].studies(StudyDescription='MRI')
        >>> len(MRIs)
        0
    """
    if not isinstance(records, list):
        records = [records]
    mgr = records[0].manager
    uids = [rec.uid for rec in records]
    mgr.move_to(uids, target.uid, **target.attributes)
    return records

def group(records:list, into:Record=None, inplace=False)->Record:
    if not isinstance(records, list):
        records = [records]
    if into is None:
        into = records[0].new_pibling()
    if inplace:
        move_to(records, into)
    else:
        copy_to(records, into)
    return into



def merge(records:list, into:Record=None, inplace=False)->Record:
    """Merge a list of records into a single new record.

    Args:
        records (list): list of Records of the same type
        into (Record, optional): location for the merged series. If None is provided, the merged series is created in the parent of the first record in the list. Defaults to None.
        inplace (bool, optional): If set to True, the original series will be removed and only the merged series retain. If set to False the original series will contine to exist. Default is False.

    Returns: 
        new_record (Record): the merged record.

    See also:
        `copy`
        `copy_to`

    Example:

        The first patient in the hollywood demo database currently has two studies

        >>> database = db.dro.database_hollywood()
        >>> jb = database.patients(PatientName = 'James Bond')[0]
        >>> len(jb.studies())
        2

        If we merge them together, the patient now has three studies, the original MRI and Xray studies, and the new merged study:

        >>> new_study = db.merge(jb.studies())
        >>> len(jb.studies())
        3
        >>> jb.StudyDescription
        ['MRI', 'New Study', 'Xray']

        Since the original MRI and Xray studies had two series each, the new study now has 2+2=4 series:

        >>> len(new_study.series())
        4 

        We have used here the default setting of ``inplace=False``, so the original series are preserved. To see what happens with ``inplace=True``, lets merge all 3 studies of the patient: 

        >>> single_jb_study = db.merge(jb.studies(), inplace=True)

        Since we have merged in place, the original 3 studies have been removed and there is now only one study left.
        
        >>> len(jb.studies())
        1

        The new study now groups the 8 series that were in the original 3 studies:

        >>> len(single_jb_study.series())
        8
    """
    if not isinstance(records, list):
        records = [records]
    children = []
    for record in records:
        children += record.children()
    new_record = group(children, into=into, inplace=inplace)
    if inplace:
        for record in records:
            record.remove()
    return new_record




# 
# Read and write
#


def read_dataframe(record, tags, select={}, **filters):
    if set(tags) <= set(record.manager.columns):
        df = record.register()[tags] 
        filters = {**select, **filters}
        for f in filters:
            if f in df:
                if isinstance(filters[f], np.ndarray):
                    df = df[df[f].isin(filters[f])]
                else:
                    df = df[df[f] == filters[f]] 
        return df
    instances = record.instances(select=select, **filters)
    return _read_dataframe_from_instance_array_values(instances, tags)


def read_dataframe_from_instance_array(instances, tags):
    mgr = instances[0].manager
    if set(tags) <= set(mgr.columns):
        keys = [i.key() for _, i in np.ndenumerate(instances)]
        return mgr._extract(keys)[tags]
    return _read_dataframe_from_instance_array_values(instances, tags)

    
def _read_dataframe_from_instance_array_values(instances, tags):
    indices = []
    data = []
    for i, instance in enumerate(instances):
        index = instance.key()
        values = instance.get_values(tags)
        indices.append(index)
        data.append(values)
        instance.progress(i+1, len(instances), 'Reading dataframe..')
    return pd.DataFrame(data, index=indices, columns=tags)

