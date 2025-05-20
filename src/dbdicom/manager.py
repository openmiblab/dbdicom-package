"""
Maintains an index of all files on disk.
"""

import os
import copy
import timeit

#from tkinter import N
import pandas as pd
import numpy as np
from tqdm import tqdm

from dbdicom.message import StatusBar, Dialog
import dbdicom.utils.files as filetools
import dbdicom.utils.dcm4che as dcm4che
import dbdicom.ds.dataset as dbdataset
from dbdicom.ds.create import read_dataset, SOPClass
import dbdicom.register

class DatabaseCorrupted(Exception):
    pass




class Manager(): 
    """Programming interface for reading and writing a DICOM folder."""

    # TODO: Add AccessionNumber so studies can be sorted correctly without reading the files
    # Note this makes all existing pkl files unusable - ensure backwards compatibility.

    # The column labels of the register
    columns = [   
        # Identifiers (unique)
        'PatientID', 
        'StudyInstanceUID', 
        'SeriesInstanceUID', 
        'SOPInstanceUID', 
        'SOPClassUID', 
        # Human-readable identifiers (not unique)
        'PatientName', 
        'StudyDescription', 
        'StudyDate', 
        'SeriesDescription', 
        'SeriesNumber', 
        'InstanceNumber', 
        # Geometry information
        'ImageOrientationPatient', 
        'ImagePositionPatient', 
        'PixelSpacing', 
        'SliceThickness', 
        'SliceLocation', 
        'AcquisitionTime',
    ]

    # Non-UID subset of column labels with their respective indices
    # These are non-critical and can be set manually by users
    _descriptives = {
        'PatientName': 5,
        'StudyDescription': 6, 
        'StudyDate': 7,
        'SeriesDescription': 8,
        'ImageOrientationPatient':11, 
        'ImagePositionPatient':12, 
        'PixelSpacing':13, 
        'SliceThickness':14, 
        'SliceLocation':15, 
        'AcquisitionTime':16,
    }

    def default(self):
        return [None, None, None, None, None,
            None, None, None, None, int(-1), int(-1),
            None, None, None, float(-1.0), float(-1.0), None,
        ]


    def __init__(self, path=None, dataframe=None, status=StatusBar(), dialog=Dialog()):
        """Initialise the folder with a path and objects to message to the user.
        
        When used inside a GUI, status and dialog should be instances of the status bar and 
        dialog class defined in `wezel`.

        path = None: The index manages data in memory
        dataframe = None: no database open
        """  
        if dataframe is None:
            #dataframe = pd.DataFrame(index=[], columns=self.columns)
            dataframe = pd.DataFrame(index=[], columns=self.columns+['removed','created']) # Added 28/05/2023
        # THIS NEEDS A MECHANISM TO PREVENT ANOTHER Manager to open the same database.
        self.status = status
        self.dialog = dialog 
        self.path = path
        self.register = dataframe
        self.dataset = {}

    def scan(self, unzip=False):
        """
        Reads all files in the folder and summarises key attributes in a table for faster access.
        """
#       Take unzip out until test is developed - less essential feature
#        if unzip:
#            filetools._unzip_files(self.path, self.status)

        #self.read_dataframe()

        if self.path is None:
            self.register = pd.DataFrame(index=[], columns=self.columns)
            self.dataset = {}
            return
        files = filetools.all_files(self.path)
        self.register = dbdataset.read_dataframe(
            files, 
            self.columns+['NumberOfFrames'], 
            self.status, 
            path=self.path, 
            message='Reading database..', 
            images_only = True)
        self.register['removed'] = False
        self.register['created'] = False
        # No support for multiframe data at the moment
        self._multiframe_to_singleframe()
        self.register.drop('NumberOfFrames', axis=1, inplace=True)
        # For now ensure all series have just a single CIOD
        self._split_series()
        #self.save()
        return self


    def _split_series(self):
        """
        Split series with multiple SOP Classes.

        If a series contain instances from different SOP Classes, 
        these are separated out into multiple series with identical SOP Classes.
        """
        df = self.register
        df = df[df.removed == False]

        # For each series, check if there are multiple
        # SOP Classes in the series and split them if yes.
        all_series = df.SeriesInstanceUID.unique()
        for s, series in enumerate(all_series):
            msg = 'Splitting series with multiple data types'
            self.status.progress(s+1, len(all_series), message=msg)
            df_series = df[df.SeriesInstanceUID == series]
            sop_classes = df_series.SOPClassUID.unique()
            if len(sop_classes) > 1:
                # For each sop_class, create a new series and move all
                # instances of that sop_class to the new series
                study = self.parent(series)
                series_desc = df_series.SeriesDescription.values[0]
                for i, sop_class in enumerate(sop_classes[1:]):
                    desc = series_desc + ' [' + str(i+1) + ']'
                    new_series, _ = self.new_series(parent=study, SeriesDescription=desc)
                    df_sop_class = df_series[df_series.SOPClassUID == sop_class]
                    instances = df_sop_class.SOPInstanceUID.values.tolist()
                    moved = self.move_to_series(instances, new_series)
                    

    def _multiframe_to_singleframe(self):
        """Converts all multiframe files in the folder into single-frame files.
        
        Reads all the multi-frame files in the folder,
        converts them to singleframe files, and delete the original multiframe file.
        """
        if self.path is None:
            # Low priority - we are not creating multiframe data from scratch yet
            # So will always be loaded from disk initially where the solution exists. 
            # Solution: save data in a temporary file, use the filebased conversion, 
            # the upload the solution and delete the temporary file.
            raise ValueError('Multi-frame to single-frame conversion does not yet exist from data in memory')
        singleframe = self.register.NumberOfFrames.isnull() 
        multiframe = singleframe == False
        nr_multiframe = multiframe.sum()
        if nr_multiframe != 0: 
            cnt=0
            for relpath in self.register[multiframe].index.values:
                cnt+=1
                msg = "Converting multiframe file " + relpath
                self.status.progress(cnt, nr_multiframe, message=msg)
                #
                # Create these in the dbdicom folder, not in the original folder.
                #
                filepath = os.path.join(self.path, relpath)
                singleframe_files = dcm4che.split_multiframe(filepath) 
                if singleframe_files != []:            
                    # add the single frame files to the dataframe
                    df = dbdataset.read_dataframe(singleframe_files, self.columns, path=self.path)
                    df['removed'] = False
                    df['created'] = False
                    self.register = pd.concat([self.register, df])
                    # delete the original multiframe 
                    os.remove(filepath)
                # drop the file also if the conversion has failed
                self.register.drop(index=relpath, inplace=True)

    def _pkl(self):
        """ Returns the file path of the .pkl file"""
        if self.path is None:
            return None
        filename = os.path.basename(os.path.normpath(self.path)) + ".pkl"
        return os.path.join(self.path, filename) 

    def npy(self, uid):
        # Not in use - default path for temporary storage in numoy format
        path = os.path.join(self.path, "dbdicom_npy")
        if not os.path.isdir(path): 
            os.mkdir(path)
        file = os.path.join(path, uid + '.npy') 
        return file

    def _write_df(self):
        """ Writes the dataFrame as a .pkl file"""
        if self.path is None:
            return
        file = self._pkl()
        self.register.to_pickle(file)

    def _read_df(self):
        """Reads the dataFrame from a .pkl file """
        if self.path is None:
            return
        file = self._pkl()
        self.register = pd.read_pickle(file)

    def write_csv(self, file):
        """ Writes the dataFrame as a .csv file for visual inspection"""
        self.register.to_csv(file)

    def filepath(self, key):
        """Return the full filepath for a given relative path.
        
        Returns None for data that live in memory only."""
        # Needs a formal test for completeness
        if self.path is None:
            return None
        return os.path.join(self.path, key)

    def filepaths(self, *args, **kwargs):
        """Return a list of full filepaths for all dicom files in the folder"""
        # Needs a formal test for completeness
        return [self.filepath(key) for key in self.keys(*args, **kwargs)]

    def open(self, path=None, unzip=False):
        """Opens a DICOM folder for read and write.
        
        Reads the contents of the folder and summarises all DICOM files
        in a dataframe for faster access next time. The dataframe is saved 
        as a pkl file when the folder is closed with `.close()`. 
        All non-DICOM files in the folder are ignored.
        
        Args:
            path: The full path to the directory that is to be opened.

        """
        if path is not None:
            self.path = path
        if self.path is None:
            raise ValueError('Cannot open database - no path is specified')
        if os.path.exists(self._pkl()):
            try:
                self._read_df()
            except:
                # If the file is corrupted, delete it and load again
                os.remove(self._pkl())
                self.scan(unzip=unzip)
        else:
            self.scan(unzip=unzip)
        return self


    def type(self, uid=None, key=None):
        """Is the UID a patient, study, series or dataset"""

        if uid is None:
            return None
        if uid == 'Database':
            return uid

        if key is None:
            df = self.register
            type = df.columns[df.isin([uid]).any()].values
            if type.size == 0: # uid does not exists in the database
                return None
            else:
                type = type[0]
        else:
            df = self.register.loc[key,:]
            type = df[df.isin([uid])].index[0]

        if type == 'PatientID':
            return 'Patient'
        if type == 'StudyInstanceUID':
            return 'Study'
        if type == 'SeriesInstanceUID':
            return 'Series'
        if type == 'SOPInstanceUID':
            return 'Instance'


    def tree(self, depth=3):
        return dbdicom.register.uid_tree(self.register, self.path, depth)


    def keys(self,
        uid = None, 
        patient = None,
        study = None,
        series = None,
        instance = None, 
        dropna = False): 
        """Return a list of indices for all dicom datasets managed by the index.
        
        These indices are strings with unique relative paths 
        that either link to an existing file in the database or can be used for 
        writing a database that is in memory.
        """

        df = self.register
        if df is None:
            raise ValueError('Cant return dicom files - no database open')

        # If no arguments are provided
        if (uid is None) & (patient is None) & (study is None) & (series is None) & (instance is None):
            return []

        if isinstance(uid, list):
            if 'Database' in uid:
                return self.keys('Database', dropna=dropna)

        not_deleted = df.removed == False

        if uid == 'Database':
            keys = not_deleted[not_deleted].index.tolist()
            if dropna:
                keys = [key for key in keys if self.register.at[key,'SOPInstanceUID'] is not None]
            return keys

        # If arguments are provided, create a list of unique datasets
        # keys = []
        if uid is not None:
            if not isinstance(uid, list):
                uid = [uid]
            uid = [i for i in uid if i is not None]
            rows = np.isin(df, uid).any(axis=1) & not_deleted
        if patient is not None:
            if not isinstance(patient, list):
                rows = (df.PatientID==patient) & not_deleted
            else:
                patient = [i for i in patient if i is not None]
                rows = df.PatientID.isin(patient) & not_deleted
        if study is not None:
            if not isinstance(study, list):
                rows = (df.StudyInstanceUID==study) & not_deleted
            else:
                study = [i for i in study if i is not None]
                rows = df.StudyInstanceUID.isin(study) & not_deleted
        if series is not None:
            if not isinstance(series, list):
                rows = (df.SeriesInstanceUID==series) & not_deleted
            else:
                series = [i for i in series if i is not None]
                rows = df.SeriesInstanceUID.isin(series) & not_deleted
        if instance is not None: 
            if not isinstance(instance, list):
                rows = (df.SOPInstanceUID==instance) & not_deleted
            else:
                instance = [i for i in instance if i is not None]
                rows = df.SOPInstanceUID.isin(instance) & not_deleted

        keys = df.index[rows].tolist()
        if dropna:
            keys = [key for key in keys if self.register.at[key,'SOPInstanceUID'] is not None]
        return keys

    def value(self, key, column):
        try:
            if isinstance(key, pd.Index):
                return self.register.loc[key, column].values
            if not isinstance(key, list) and not isinstance(column, list):
                return self.register.at[key, column]
            else:
                return self.register.loc[key, column].values
        except:
            return None

    def parent(self, uid=None):
        # For consistency with other definitions
        # Allow uid to be list and return list if multiple parents are found
        """Returns the UID of the parent object"""

        keys = self.keys(uid)
        if keys == []:
            return None
        row = self.register.loc[keys[0]].values.tolist()
        i = row.index(uid)
        if self.columns[i] == 'PatientID':
            return 'Database'
        else:
            return row[i-1]


    def filter(self, uids=None, select={}, **kwargs):
        uids = [id for id in uids if id is not None]
        if (not kwargs) and (select=={}):
            return uids
        vals = list(kwargs.values()) + list(select.values())
        attr = list(kwargs.keys()) + list(select.keys())
        return [id for id in uids if self.get_values(attr, uid=id) == vals]
        #return [id for id in uids if function(self.get_values(attr, uid=id), vals)]


    def filter_instances(self, df, select={}, **filters):
        df.dropna(inplace=True)
        filters = {**select, **filters}
        if filters == {}:
            return df
        vals = list(filters.values())
        attr = list(filters.keys())
        # keys = [key for key in df.index if self.get_values(attr, [key]) == vals]
        keys = []
        for key in df.index:
            v = self.get_values(attr, [key])
            append = True
            for i, vi in enumerate(v):
                if isinstance(vals[i], np.ndarray):
                    if vi not in vals[i]:
                        append = False
                        break
                else:
                    if vi != vals[i]:
                        append = False
                        break
            if append:
                keys.append(key)
        return df[keys]


    def instances(self, uid=None, keys=None, sort=True, sortby=None, images=False, select={}, **filters):
        if keys is None:
            keys = self.keys(uid)
        if sort:
            if sortby is None:
                sortby = ['PatientName', 'StudyDescription', 'SeriesNumber', 'InstanceNumber']
            df = self.register.loc[keys, sortby + ['SOPInstanceUID']]
            df.sort_values(sortby, inplace=True)
            df = df.SOPInstanceUID
        else:
            df = self.register.loc[keys,'SOPInstanceUID']
        df = self.filter_instances(df, select=select, **filters)
        if images == True:
            keys = [key for key in df.index if self.get_values('Rows', [key]) is not None]
            df = df[keys]
        return df


    def series(self, uid=None, keys=None, sort=True, 
               sortby=['PatientName', 'StudyDescription', 'SeriesNumber'], 
               select={}, **kwargs):
        if keys is None:
            keys = self.keys(uid)
        if sort:  
            if not isinstance(sortby, list):
                sortby = [sortby]
            df = self.register.loc[keys, sortby + ['SeriesInstanceUID']]
            df.sort_values(sortby, inplace=True)
            df = df.SeriesInstanceUID
        else:
            df = self.register.loc[keys,'SeriesInstanceUID']
        uids = df.unique().tolist()
        return self.filter(uids, select=select, **kwargs)


    def studies(self, uid=None, keys=None, sort=True, sortby=['PatientName', 'StudyDescription'], **kwargs):
        if keys is None:
            keys = self.keys(uid)
        if sort:
            df = self.register.loc[keys, sortby + ['StudyInstanceUID']]
            df.sort_values(sortby, inplace=True)
            df = df.StudyInstanceUID
        else:
            df = self.register.loc[keys,'StudyInstanceUID']
        uids = df.unique().tolist()
        return self.filter(uids, **kwargs)


    def patients(self, uid=None, keys=None, sort=True, sortby=['PatientName'], **kwargs):
        if keys is None:
            keys = self.keys(uid)
        if sort:
            df = self.register.loc[keys, sortby + ['PatientID']]
            df.sort_values(sortby, inplace=True)
            df = df.PatientID
        else:
            df = self.register.loc[keys,'PatientID']
        uids = df.unique().tolist()
        return self.filter(uids, **kwargs)
    

    def get_instance_dataset(self, key):
    
        """Gets a datasets for a single instance
        
        Datasets in memory will be returned.
        If they are not in memory, and the database exists on disk, they will be read from disk.
        If they are not in memory, and the database does not exist on disk, an exception is raised.
        """
        if key in self.dataset:
            # If in memory, get from memory
            return self.dataset[key]
        # If not in memory, read from disk
        file = self.filepath(key)
        if file is None: # No dataset assigned yet
            return
        if not os.path.exists(file):  # New instance, series, study or patient 
            return 
        return read_dataset(file, self.dialog)  


    def get_dataset(self, uid, keys=None, message=None):
        """Gets a list of datasets for a single record
        
        Datasets in memory will be returned.
        If they are not in memory, and the database exists on disk, they will 
          be read from disk.
        If they are not in memory, and the database does not exist on disk, 
          an exception is raised.
        """
        if uid is None: # empty record
            return
        if keys is None:
            keys = self.keys(uid)
        dataset = []
        for key in keys:
            ds = self.get_instance_dataset(key) 
            dataset.append(ds)
        if self.type(uid, keys[0]) == 'Instance':
            if dataset == []:
                return
            else:
                return dataset[0]
        else:
            return dataset


    def _get_values(self, keys, attr):
        """Helper function"""

        #ds = self._get_dataset(instances)
        ds = None
        for key in keys:
            ds = self.get_instance_dataset(key)
            if ds is not None:
                break
        if ds is None:
            return [None] * len(attr)
        else:
            return ds.get_values(attr)


    def series_header(self, key=None, series_uid=None):
        """Attributes and values inherited from series, study and patient"""

        if key is None:
            key = self.keys(series=series_uid)[0]

        attr_patient = ['PatientID', 'PatientName']
        attr_study = ['StudyInstanceUID', 'StudyDescription', 'StudyDate']
        attr_series = ['SeriesInstanceUID', 'SeriesDescription', 'SeriesNumber'] 

        parent = self.register.at[key, 'SeriesInstanceUID']
        keys = self.keys(series=parent, dropna=True)
        if keys != []:
            attr = list(set(dbdataset.module_patient() + dbdataset.module_study() + dbdataset.module_series()))
            vals = self._get_values(keys, attr)
        else:
            parent = self.register.at[key, 'StudyInstanceUID']
            keys = self.keys(study=parent, dropna=True)
            if keys != []:
                attr = list(set(dbdataset.module_patient() + dbdataset.module_study()))
                vals = self._get_values(keys, attr)
                attr += attr_series
                vals += self.value(key, attr_series).tolist()
            else:
                parent = self.register.at[key, 'PatientID']
                keys = self.keys(patient=parent, dropna=True)
                if keys != []:
                    attr = dbdataset.module_patient()
                    vals = self._get_values(keys, attr)
                    attr += attr_study + attr_series
                    vals += self.value(key, attr_study + attr_series).tolist()
                else:
                    attr = attr_patient + attr_study + attr_series
                    vals = self.value(key, attr).tolist()
        return attr, vals


    def study_header(self, key=None, study_uid=None):
        """Attributes and values inherited from series, study and patient"""

        if key is None:
            key = self.keys(study=study_uid)[0]

        attr_patient = ['PatientID', 'PatientName']
        attr_study = ['StudyInstanceUID', 'StudyDescription', 'StudyDate']

        parent = self.register.at[key, 'StudyInstanceUID']
        keys = self.keys(study=parent, dropna=True)
        if keys != []:
            attr = list(set(dbdataset.module_patient() + dbdataset.module_study()))
            vals = self._get_values(keys, attr)
        else:
            parent = self.register.at[key, 'PatientID']
            keys = self.keys(patient=parent, dropna=True)
            if keys != []:
                attr = dbdataset.module_patient()
                vals = self._get_values(keys, attr)
                attr += attr_study
                vals += self.value(key, attr_study).tolist()
            else:
                attr = attr_patient + attr_study
                vals = self.value(key, attr).tolist()
        return attr, vals


    def patient_header(self, key):
        """Attributes and values inherited from series, study and patient"""

        attr_patient = ['PatientID', 'PatientName']

        parent = self.register.at[key, 'PatientID']
        keys = self.keys(patient=parent, dropna=True)
        if keys != []:
            attr = dbdataset.module_patient()
            vals = self._get_values(keys, attr)
        else:
            attr = attr_patient
            vals = self.value(key, attr).tolist()
        return attr, vals


    def label(self, uid=None, key=None, type=None):
        """Return a label to describe a row as Patient, Study, Series or Instance"""

        if self.register is None:
            raise ValueError('Cant provide labels - no database open')

        if uid is None:
            if key is None:
                return ''
    
        if uid == 'Database':
            if self.path is None:
                return 'Database [in memory]'
            else:
                return 'Database [' + self.path + ']'

        if type is None:
            type = self.type(uid)

        if type == 'Patient':
            if key is None:
                key = self.keys(patient=uid)[0]
            row = self.register.loc[key]
            name = row.PatientName
            #id = row.PatientID
            label = str(name)
            #label += ' [' + str(id) + ']'
            return type + " {}".format(label)
        if type == 'Study':
            if key is None:
                key = self.keys(study=uid)[0]
            row = self.register.loc[key]
            descr = row.StudyDescription
            date = row.StudyDate
            label = str(descr)
            label += ' [' + str(date) + ']'
            return type + " {}".format(label)
        if type == 'Series':
            if key is None:
                key = self.keys(series=uid)[0]
            row = self.register.loc[key]
            descr = row.SeriesDescription
            nr = row.SeriesNumber
            label = str(nr).zfill(3)  
            label += ' [' + str(descr) + ']'
            return type + " {}".format(label)
        if type == 'Instance':
            if key is None:
                key = self.keys(instance=uid)[0]
            row = self.register.loc[key]
            nr = row.InstanceNumber
            label = str(nr).zfill(6)
            return SOPClass(row.SOPClassUID) + " {}".format(label)


    def print_database(self):
        print('---------- DATABASE --------------')
        if self.path is None:
            print('Location: ', 'In memory')
        else:
            print('Location: ', self.path)
        for patient in self.patients('Database'):
            print('  ' + self.label(patient, type='Patient'))
            for study in self.studies(patient):
                print('    ' + self.label(study, type='Study'))
                for series in self.series(study):
                    print('      ' + self.label(series, type='Series'))
                    print('        Nr of instances: ' + str(len(self.instances(series)))) 
        print('----------------------------------')


    def print_patient(self, patient):
        print('---------- PATIENT -------------')
        print('' + self.label(patient, type='Patient'))
        for study in self.studies(patient):
            print('  ' + self.label(study, type='Study'))
            for series in self.series(study):
                print('    ' + self.label(series, type='Series'))
                print('      Nr of instances: ' + str(len(self.instances(series)))) 
        print('--------------------------------')


    def print_study(self, study):
        print('---------- STUDY ---------------')
        print('' + self.label(study, type='Study'))
        for series in self.series(study):
            print('  ' + self.label(series, type='Series'))
            print('    Nr of instances: ' + str(len(self.instances(series)))) 
        print('--------------------------------')


    def print_series(self, series):
        print('---------- SERIES --------------')
        instances = self.instances(series)
        print('' + self.label(series, type='Series'))
        print('    Nr of instances: ' + str(len(instances)))
        for instance in self.instances(series):
            print('      ' + self.label(instance, type='Instance')) 
        print('--------------------------------')


    def print_instance(self, instance):
        print('---------- INSTANCE -------------')
        print('' + self.label(instance, type='Instance')) 
        print('--------------------------------')


    def print(self, uid='Database', name='Database'):
        if name=='Database':
            self.print_database()
        elif name=='PatientID':
            self.print_patient(uid)
        elif name=='StudyInstanceUID':
            self.print_study(uid)
        elif name=='SeriesInstanceUID':
            self.print_series(uid)
        elif name=='SOPInstanceUID':
            self.print_instance(uid)   


    def read(self, *args, keys=None, message=None, **kwargs):
        """Read the dataset from disk.
        """
        if keys is None:
            keys = self.keys(*args, **kwargs)
        for i, key in enumerate(keys):
            #if message is not None:
            #    self.status.progress(i, len(keys), message)
            # do not read if they are already in memory
            # this could overwrite changes made in memory only
            if not key in self.dataset:
                instance_uid = self.value(key, 'SOPInstanceUID')
                ds = self.get_dataset(instance_uid, [key])
                if ds is not None:
                    self.dataset[key] = ds

    def write(self, *args, keys=None, message=None, **kwargs):
        """Writing data from memory to disk.

        This does nothing if the data are not in memory, or if the database does not exist on disk.
        """
        if keys is None:
            keys = self.keys(*args, **kwargs)
        for i, key in enumerate(keys):
            if key in self.dataset:
                file = self.filepath(key)
                if file is not None:
                    self.dataset[key].write(file, self.status)

    def clear(self, *args, keys=None, **kwargs):
        """Clear all data from memory"""

        # Instances are only cleared from memory if the database exists on disk.
        if self.path is None:
            return
        
        if keys is None:
            keys = self.keys(*args, **kwargs)
        # write to disk first so that any changes made in memory are not lost
        self.write(*args, keys=keys, **kwargs)
        # then delete the instances from memory
        for key in keys:
            self.dataset.pop(key, None) 

    def close(self):
        """Close an open database.
        """

        #if not self.is_open(): 
        if self.register is None:
            return True
        # This is the case where the database exists in memory only
        # Needs testing..
        if self.path is None: 
            reply = self.dialog.question( 
                title = 'Closing DICOM folder', 
                message = 'Save changes before closing?',
                cancel = True, 
            )
            if reply == "Cancel": 
                return False
            elif reply == "Yes":
                path = self.dialog.directory('Please enter the full path to an existing folder')
                if path is None:
                    return False
                self.path = path
                self.save()
                #self.save('Database')
                return self.close()
            elif reply == "No":
                return True
            
        if not self.is_saved():
            reply = self.dialog.question( 
                title = 'Closing DICOM folder', 
                message = 'Save changes before closing?',
                cancel = True, 
            )
            if reply == "Cancel": 
                return False
            if reply == "Yes":
                self.save()
                #self.save('Database')
            elif reply == "No":
                self.restore()

        self._write_df()
        self.write()
        self.register = None            
        self.path = None
        return True


    def is_saved(self):
        """Check if the folder is saved.
        
        Returns: 
            True if the folder is saved and False otherwise.
        """
        # Needs a formal test for completeness
        if (self.register.removed==True).any():
            return False
        if (self.register.created==True).any():
            return False
        return True

    def is_open(self):
        """Check if a database is currently open, either in memory or on disk
        
        Returns: 
            True if a database is open and False otherwise.
        """
        # Needs a formal test for completeness
        return self.register is not None


    def delete(self, *args, keys=None, **kwargs):
        """Deletes some datasets
        
        Deleted datasets are stashed and can be recovered with restore()
        Using save() will delete them permanently
        """
        if keys is None:
            keys = self.keys(*args, **kwargs)
        self.register.loc[keys,'removed'] = True


    def save(self, rows=None): 

        self.status.message('Saving changes..')

        created = self.register.created & (self.register.removed==False) 
        removed = self.register.removed
        if rows is not None:
            created = created & rows
            removed = removed & rows
        created = created[created].index
        removed = removed[removed].index

        # delete datasets marked for removal
        for key in removed.tolist():
            # delete in memory
            if key in self.dataset:
                del self.dataset[key]
            # delete on disk
            file = self.filepath(key) 
            if file is not None:
                if os.path.exists(file): 
                    os.remove(file)
        # and drop then from the dataframe
        self.register.drop(index=removed, inplace=True)

        # for new or edited data, mark as saved.
        self.register.loc[created, 'created'] = False

        self._write_df()
        self.write()
        return self


    def restore(self, rows=None):  

        created = self.register.created 
        removed = self.register.removed & (self.register.created==False)
        if rows is not None:
            created = created & rows
            removed = removed & rows
        created = created[created].index
        removed = removed[removed].index

        # permanently delete newly created datasets
        for key in created.tolist():
            # delete in memory
            if key in self.dataset:
                del self.dataset[key]
            # if on disk, delete files
            file = self.filepath(key) 
            if file is not None:
                if os.path.exists(file): 
                    os.remove(file)
        self.register.drop(index=created, inplace=True)

        # Restore those that were marked for removal
        self.register.loc[removed, 'removed'] = False

        self._write_df()
        # self.write()      


    def new_row(self, data, key=None):
        if key is None:
            key = self.new_key()
        if key in self.register.index:
            self.register.loc[key,self.columns] = data
        else:
            df = pd.DataFrame([data], [key], columns=self.columns)
            df['removed'] = False
            df['created'] = True
            try:
                self.register = pd.concat([self.register, df])
            except:
                msg = 'Cannot update the header \n'
                msg += 'Some of the new values are of the incorrect type.\n'
                raise TypeError(msg)  
        return key
    
    def delete_row(self, key):
        if self.register.at[key, 'created']:
            # If the row was newly created, it can be dropped
            self.register.drop(index=key, inplace=True)
        else:
            # If this is the first modification, mark for removal
            self.register.at[key, 'removed'] == True


    def drop_placeholder_row(self, parent_key, missing='SOPInstanceUID'):
        # If a parent has more than one children, and one of them is None, then delete that row.
        if missing == 'SOPInstanceUID':
            parent_uid = self.value(parent_key, 'SeriesInstanceUID')
            parent_keys = self.keys(series=parent_uid)
        elif missing == 'SeriesInstanceUID':
            parent_uid = self.value(parent_key, 'StudyInstanceUID')
            parent_keys = self.keys(study=parent_uid)
        elif missing == 'StudyInstanceUID':
            parent_uid = self.value(parent_key, 'PatientID')
            parent_keys = self.keys(patient=parent_uid)
        elif missing == 'PatientID':
            parent_keys = self.register.index
        if len(parent_keys) > 1:
            df = self.register.loc[parent_keys, missing]
            empty = df[df.values == None].index
            if len(empty) == 1:
                self.delete_row(empty[0])
                # Return new parent key
                if missing == 'SOPInstanceUID':
                    return self.keys(series=parent_uid)[0]
                if missing == 'SeriesInstanceUID':
                    return self.keys(study=parent_uid)[0]
                if missing == 'StudyInstanceUID':
                    return self.keys(patient=parent_uid)[0]
                if missing == 'PatientID':
                    return self.register.index[0]
        return parent_key

    
    def update_row_data(self, key, data):

        # If the row has been created or modified, use existing row
        if self.register.at[key, 'created'] == True:
            for i, c in enumerate(self.columns): 
                try:
                    self.register.at[key, c] = data[i]
                except:
                    msg = 'Cannot write header value in register. \n'
                    msg += 'The value of ' + c +' is of incorrect type.\n'
                    msg += 'Value: ' + str(data[i])
                    raise TypeError(msg)
    
        # If the row has never been modified, save in new row and remove current
        else:
            self.register.at[key, 'removed'] = True
            key = self.new_row(data)

        return key
    

    def clone_study_data(self, key, **kwargs):
        data = self.default()
        data[0] = self.value(key, 'PatientID')
        data[1] = dbdataset.new_uid()
        data[5] = self.value(key, 'PatientName')
        data[6] = kwargs['StudyDescription'] if 'StudyDescription' in kwargs else 'New Study'
        for val in kwargs:
            if val in self._descriptives:
                data[self._descriptives[val]] = kwargs[val]
        return data
    
    def clone_series_data(self, key, study, **kwargs):
        data = self.register.loc[key, self.columns].values.tolist()
        data[2] = dbdataset.new_uid()
        data[3] = self.default()[3]
        data[4] = self.default()[4]
        data[8] = kwargs['SeriesDescription'] if 'SeriesDescription' in kwargs else 'New Series'
        data[9] = self.new_series_number(study)
        data[10] = self.default()[10]
        for val in kwargs:
            if val in self._descriptives:
                data[self._descriptives[val]] = kwargs[val]
        return data


    def new_patient(self, parent='Database', **kwargs):
        data = self.default()
        data[0] = dbdataset.new_uid()
        data[5] = kwargs['PatientName'] if 'PatientName' in kwargs else 'New Patient'
        for val in kwargs:
            if val in self._descriptives:
                data[self._descriptives[val]] = kwargs[val]
        key = self.new_row(data)
        return data[0], key


    def new_study(self, parent=None, key=None, **kwargs):
        if key is None:
            if parent is None:
                parent, key = self.new_patient()
            elif self.type(parent) != 'Patient':
                parent, key = self.new_patient(parent)
            else:
                key = self.keys(patient=parent)[0]
        data = self.clone_study_data(key, **kwargs)
        if self.value(key, 'StudyInstanceUID') is None:
            key = self.update_row_data(key, data)
        else:
            key = self.new_row(data)
        return data[1], key


    def new_series(self, parent=None, key=None, **kwargs):
        if key is None:
            if parent is None:
                parent, key = self.new_study()
            elif self.type(parent) != 'Study':
                #parent = self.studies(parent)[0]
                parent, key = self.new_study(parent)
            else:
                key = self.keys(study=parent)[0]
        data = self.clone_series_data(key, parent, **kwargs)
        if self.value(key, 'SeriesInstanceUID') is None:
            key = self.update_row_data(key, data)  # Empty study
        else:
            key = self.new_row(data)  # Study with existing series
        return data[2], key


    
    def new_instance(self, parent=None, dataset=None, key=None, **kwargs):

        if key is None:
            if parent is None:
                parent, key = self.new_series()
                keys = self.keys(series=parent)
            elif self.type(parent) != 'Series':
                parent, key = self.new_series(parent)
                keys = self.keys(series=parent)
            else:
                keys = self.keys(series=parent)
                key = keys[0]
        else:
            if parent is None:
                parent = self.register.at[key, 'SeriesInstanceUID']
            keys = self.keys(series=parent)

        # Find largest instance number
        n = self.register.loc[keys,'InstanceNumber'].values
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)

        # Populate attributes in index file
        data = self.value(key, self.columns)
        data[3] = dbdataset.new_uid()
        data[4] = self.default()[4]
        data[10] = 1 + max_number
        for val in kwargs:
            if val in self._descriptives:
                data[self._descriptives[val]] = kwargs[val]

        # Add new data to the register
        if self.value(key, 'SOPInstanceUID') is None:
            key = self.update_row_data(key, data) # Empty series
        else:
            key = self.new_row(data)  # Series with existing instances

        # Set dataset if needed
        if dataset is not None:
            self.set_instance_dataset(data[3], dataset, key)

        return data[3], key


    def set_instance_dataset(self, instance, ds, key=None):

        if isinstance(ds, list):
            if len(ds) > 1:
                raise ValueError(
                    'Cannot set multiple datasets to a single instance')
            else:
                ds = ds[0]
        if key is None:
            keys = self.keys(instance)
            if keys == []: # instance does not exist
                return
            key = keys[0]

        data = self.register.loc[key, self.columns]
        data[4] = ds.SOPClassUID
        data[11:] = ds.get_values(self.columns[11:])
        key = self.update_row_data(key, data)
        ds.set_values(self.columns[:11], data[:11]) 
        #self.dataset[key] = ds
        file = self.filepath(key)
        if file is not None:
            ds.write(file, self.status)
        return key


    def merge_series(self, series_uids, study_uid, **kwargs):

        # Create a new series and get the row data
        merged_uid, merged_key = self.new_series(study_uid, **kwargs)
        merged_data = self.register.loc[merged_key, self.columns].values
        
        new_data = []
        new_keys = []
        instance_number = 1

        for series_uid in tqdm(series_uids, desc='Merging series..'):

            # Get the series keys sorted by instance number
            loc = self.register.SeriesInstanceUID == series_uid 
            loc &= self.register.removed == False 
            inst = self.register.loc[loc, 'InstanceNumber'].sort_values()
            keys = inst.keys()

            # Copy each dataset to the merged series
            for key in tqdm(keys, desc='Copying datasets..'):

                # Read dataset
                datapath = self.filepath(key)
                ds = read_dataset(datapath, self.dialog)

                # Create new data for the register
                data = merged_data.copy().tolist()
                data[3] = dbdataset.new_uid()
                data[4] = ds.SOPClassUID
                data[10] = instance_number
                data[11:] = ds.value(self.columns[11:])

                # Update register rows
                if instance_number==1:
                    relpath = merged_key
                    for i, c in enumerate(self.columns): 
                        self.register.at[merged_key, c] = data[i]
                else: 
                    relpath = self.new_key()
                    new_data.append(data)
                    new_keys.append(relpath)

                # Write to the new file
                file = self.filepath(relpath)
                ds.set_value(self.columns[:11], data[:11])
                ds.write(file, self.status)

                # Increment instance number
                instance_number += 1

        # Append new data to register
        if new_data != []:
            df = pd.DataFrame(new_data, new_keys, columns=self.columns)
            df['removed'] = False
            df['created'] = True
            self.register = pd.concat([self.register, df])

        return merged_uid, merged_key

    

    def set_dataset(self, uid, dataset, keys=None):

        if keys is None:
            parent_keys = self.keys(uid)
        else:
            parent_keys = keys

        parent_key = parent_keys[0]
        if self.type(uid, parent_key) == 'Instance': 
            self.set_instance_dataset(uid, dataset, parent_key)
            return

        if not isinstance(dataset, list):
           dataset = [dataset]
         
        attr, vals = self.series_header(parent_keys[0])
        instances = self.value(parent_keys, 'SOPInstanceUID').tolist()

        for ds in dataset:
            try:
                ind = instances.index(ds.SOPInstanceUID)
            except:  
                #If there is no corresponding instance, save dataset in new instance

                # Set parent modules
                ds.set_values(attr, vals)

                # Create updated row data
                key = parent_keys[0]
                data = self.value(key, self.columns)
                data[3] = dbdataset.new_uid()
                data[4] = ds.SOPClassUID
                nrs = self.value(parent_keys, 'InstanceNumber')
                nrs = [n for n in nrs if n != -1]
                if nrs == []:
                    data[10] = 1
                else:
                    data[10] = 1 + max(nrs)
                data[11:] = ds.get_values(self.columns[11:]) # added 27/07/23
                
                # Add to database in memory as a new row
                key = self.new_row(data)
                ds.set_values(self.columns[:11], data[:11]) # modified 27/07/23
                self.dataset[key] = ds

            else: # If the instance is already in the object

                key = parent_keys[ind]
                data = self.value(key, self.columns)
                data[4] = ds.SOPClassUID
                data[11:] = ds.get_values(self.columns[11:]) # added 27/07/23
                key = self.update_row_data(key, data)
                ds.set_values(self.columns[:11], data[:11]) # added 27/07/23
                self.dataset[key] = ds

        # If the series is empty and new instances have been added then delete the row  
        parent_key = self.drop_placeholder_row(parent_key, missing='SOPInstanceUID')



    def delete_studies(self, studies: list):
        """Delete a list of studies"""

        for study in studies:
            keys = self.keys(study=study)
            self.register.loc[keys,'removed'] = True
            # If this was the last study in the patient
            # keep the patient as an empty patient
            patient = self.register.at[keys[0], 'PatientID']
            patient = (self.register.removed == False) & (self.register.PatientID == patient)
            patient_studies = self.register.StudyInstanceUID[patient]
            patient_studies_cnt = len(patient_studies.unique())
            if patient_studies_cnt == 0:
                row = self.default()
                row[0] = self.register.at[keys[0], 'PatientID']
                row[5] = self.register.at[keys[0], 'PatientName']
                self.new_row(row)


    def delete_series(self, series: list):
        """Delete a list of series"""

        for sery in series:
            keys = self.keys(series=sery)
            self.register.loc[keys,'removed'] = True
            # If this was the last series in the study
            # keep the study as an empty study
            study = self.register.at[keys[0], 'StudyInstanceUID']
            study = (self.register.removed == False) & (self.register.StudyInstanceUID == study)
            study_series = self.register.SeriesInstanceUID[study]
            study_series_cnt = len(study_series.unique())
            if study_series_cnt == 0:
                row = self.default()
                row[0] = self.register.at[keys[0], 'PatientID']
                row[1] = self.register.at[keys[0], 'StudyInstanceUID']
                row[5] = self.register.at[keys[0], 'PatientName']
                row[6] = self.register.at[keys[0], 'StudyDescription']
                row[7] = self.register.at[keys[0], 'StudyDate']
                self.new_row(row)


    def new_key(self):
        # Generate a new key
        return os.path.join('dbdicom', dbdataset.new_uid() + '.dcm') 


    def copy_instance_to_series(self, instance_key, target_keys, tmp, **kwargs):
        """Copy instances to another series"""

        new_parent_key = target_keys[0]
        attributes, values = self.series_header(new_parent_key)
        self.append_kwargs(kwargs, attributes, values)

        n = self.register.loc[target_keys,'InstanceNumber'].values
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)

        new_instance = dbdataset.new_uid()
        new_key = self.new_key()
        ds = self.get_instance_dataset(instance_key)

        if ds is None:
            row = self.value(instance_key, self.columns).tolist()
            row = self.copy_series_data(new_parent_key, row)
            row[3] = new_instance
            row[10] = 1 + max_number
            for val in kwargs:
                if val in self._descriptives:
                    row[self._descriptives[val]] = kwargs[val]
        else:
            if instance_key in self.dataset:
                ds = copy.deepcopy(ds)
                self.dataset[new_key] = ds
            ds.set_values( 
                attributes + ['SOPInstanceUID', 'InstanceNumber'], 
                values + [new_instance, 1+max_number])
            if not instance_key in self.dataset:
                ds.write(self.filepath(new_key), self.status)
            row = ds.get_values(self.columns)

        new_parent_key = self.drop_placeholder_row(new_parent_key, missing='SOPInstanceUID')
        self.new_row(row, new_key)
        
        return new_instance

    def new_instance_number(self, series):
        series_keys = self.keys(series=series)
        n = self.register.loc[series_keys,'InstanceNumber'].values
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)  
        return max_number + 1 

    def copy_to_series(self, uids, target, **kwargs):
        """Copy instances to another series"""

        target_keys = self.keys(series=target)
        new_parent_key = target_keys[0]
        attributes, values = self.series_header(new_parent_key)
        self.append_kwargs(kwargs, attributes, values)

        max_number = self.new_instance_number(target)
        keys = self.keys(uids)
        new_instances = dbdataset.new_uid(len(keys))

        for i, key in enumerate(keys):

            if len(keys) > 1:
                self.status.progress(i+1, len(keys), message='Copying to series..')

            new_key = self.new_key()
            instance_uid = self.value(key, 'SOPInstanceUID')
            ds = self.get_dataset(instance_uid, [key])
            if ds is None:
                row = self.value(key, self.columns).tolist()
                row = self.copy_series_data(new_parent_key, row)
                row[3] = new_instances[i]
                row[10] = i + max_number
                for val in kwargs:
                    if val in self._descriptives:
                        row[self._descriptives[val]] = kwargs[val]
            else:
                if key in self.dataset:
                    ds = copy.deepcopy(ds)
                    self.dataset[new_key] = ds
                ds.set_values( 
                    attributes + ['SOPInstanceUID', 'InstanceNumber'], 
                    values + [new_instances[i], i + max_number])
                if not key in self.dataset:
                    ds.write(self.filepath(new_key), self.status)
                row = ds.get_values(self.columns)

            # Add new data for the dataframe
            self.new_row(row, new_key)

        # If the series is empty and new instances have been added, then delete the row 
        new_parent_key = self.drop_placeholder_row(new_parent_key, missing='SOPInstanceUID')

        if len(keys) > 1:
            self.status.hide()

        if len(new_instances) == 1:
            return new_instances[0]
        else:
            return new_instances


    def new_series_number(self, study):
        study_keys = self.keys(study=study)
        n = self.value(study_keys, 'SeriesNumber')
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)  
        return max_number + 1 
      

    def copy_to_study(self, uid, target, **kwargs):
        """Copy series to another study"""

        target_keys = self.keys(study=target)
        target_key = target_keys[0]
        attributes, values = self.study_header(target_key)
        self.append_kwargs(kwargs, attributes, values)

        max_number = self.new_series_number(target)
        all_series = self.series(uid)
        new_series = dbdataset.new_uid(len(all_series))

        for s, series in enumerate(all_series):

            new_number = s + max_number
            series_keys = self.keys(series=series)
            for k, key in enumerate(series_keys):

                desc = self.value(key, 'SeriesDescription')
                if desc is None:
                    desc = 'Unknown'
                msg = 'Copying series ' + desc
                msg += ' (' + str(s+1) + '/' + str(len(all_series)) + ')'
                self.status.progress(k+1, len(series_keys), msg)

                new_key = self.new_key()
                instance_uid = self.value(key, 'SOPInstanceUID')
                ds = self.get_dataset(instance_uid, [key])
                if ds is None:
                    # Fill in any register data provided
                    row = self.value(key, self.columns).tolist()
                    row = self.copy_study_data(target_key, row)
                    row[2] = new_series[s]
                    #row[3] = dbdataset.new_uid()
                    row[9] = new_number
                    for val in kwargs:
                        if val in self._descriptives:
                            row[self._descriptives[val]] = kwargs[val]
                else:

                    # If the series exists in memory, create a copy in memory
                    if key in self.dataset:
                        ds = copy.deepcopy(ds)
                        self.dataset[new_key] = ds

                    # Generate new UIDs
                    ds.set_values(
                        attributes + ['SeriesInstanceUID', 'SeriesNumber', 'SOPInstanceUID'], 
                        values + [new_series[s], new_number, dbdataset.new_uid()])
                    
                    # If the series is not in memory, create a copy on disk
                    if not key in self.dataset:
                        ds.write(self.filepath(new_key), self.status)

                    # Get row values to add to dataframe
                    row = ds.get_values(self.columns)

                # Get new data for the dataframe
                self.new_row(row, new_key)

        # Update the dataframe in the index

        # If the study is empty and new series have been added
        # then delete the row 
        target_key = self.drop_placeholder_row(target_key, missing='SeriesInstanceUID')
        self.status.hide()

        if len(new_series) == 1:
            return new_series[0]
        else:
            return new_series


    def copy_to_patient(self, uid, target_key, **kwargs):
        """Copy studies to another patient"""

        attributes, values = self.patient_header(target_key)
        self.append_kwargs(kwargs, attributes, values)

        all_studies = self.studies(uid)
        new_studies = dbdataset.new_uid(len(all_studies))

        for s, study in enumerate(all_studies):
            all_series = self.series(study)
            if all_series == []:
                # Create an empty study
                new_key = self.new_key()
                key = self.keys(study=study)[0]
                row = self.value(key, self.columns).tolist()
                row[0] = self.value(target_key, 'PatientID')
                row[1] = new_studies[s]
                row[5] = self.value(target_key, 'PatientName')
                row[6] = self.value(target_key, 'StudyDescription')
                row[7] = self.value(target_key, 'StudyDate')
                for val in kwargs:
                    if val in self._descriptives:
                        row[self._descriptives[val]] = kwargs[val]
                # Get new data for the dataframe
                self.new_row(row, new_key)
            for series in all_series:
                new_series_uid = dbdataset.new_uid()
                for key in self.keys(series=series):
                    new_key = self.new_key()
                    instance_uid = self.value(key, 'SOPInstanceUID')
                    ds = self.get_dataset(instance_uid, [key])
                    if ds is None:
                        row = self.value(key, self.columns).tolist()
                        row[0] = self.value(target_key, 'PatientID')
                        row[1] = new_studies[s]
                        row[2] = new_series_uid
                        row[3] = dbdataset.new_uid()
                        row[5] = self.value(target_key, 'PatientName')
                        for val in kwargs:
                            if val in self._descriptives:
                                row[self._descriptives[val]] = kwargs[val]
                    else:
                        if key in self.dataset:
                            ds = copy.deepcopy(ds)
                            self.dataset[new_key] = ds
                        ds.set_values( 
                            attributes + ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'], 
                            values + [new_studies[s], new_series_uid, dbdataset.new_uid()])
                        if not key in self.dataset:
                            ds.write(self.filepath(new_key), self.status)
                        row = ds.get_values(self.columns)

                    # Get new data for the dataframe
                    self.new_row(row, new_key)

        # If the patient is empty and new studies have been added, then delete the row 
        target_key = self.drop_placeholder_row(target_key, missing='StudyInstanceUID')

        if len(new_studies) == 1:
            return new_studies[0]
        else:
            return new_studies


    def copy_to_database(self, uid, **kwargs):
        """Copy patient to the database"""

        all_patients = self.patients(uid)
        new_patients = dbdataset.new_uid(len(all_patients))

        for i, patient in enumerate(all_patients):
            keys = self.keys(patient=patient)
            new_patient_uid = new_patients[i]
            new_patient_name = 'Copy of ' + self.value(keys[0], 'PatientName')
            for study in self.studies(patient):
                new_study_uid = dbdataset.new_uid()
                for sery in self.series(study):
                    new_series_uid = dbdataset.new_uid()
                    for key in self.keys(series=sery):
                        new_instance_uid = dbdataset.new_uid()
                        new_key = self.new_key()
                        instance_uid = self.value(key, 'SOPInstanceUID')
                        ds = self.get_dataset(instance_uid, [key])
                        if ds is None:
                            row = self.value(key, self.columns).tolist()
                            row[0] = new_patient_uid
                            row[1] = new_study_uid 
                            row[2] = new_series_uid
                            row[3] = new_instance_uid
                            row[5] = new_patient_name
                            for val in kwargs:
                                if val in self._descriptives:
                                    row[self._descriptives[val]] = kwargs[val]
                        else:
                            #TODO: Simplify with set_dataset_values()
                            if key in self.dataset:
                                ds = copy.deepcopy(ds)
                                self.dataset[new_key] = ds
                            ds.set_values( 
                                list(kwargs.keys())+['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'PatientName'], 
                                list(kwargs.values())+[new_patient_uid, new_study_uid, new_series_uid, new_instance_uid, new_patient_name])
                            if not key in self.dataset:
                                ds.write(self.filepath(new_key), self.status)
                            row = ds.get_values(self.columns)

                        # Get new data for the dataframe
                        self.new_row(row, new_key)

        if len(new_patients) == 1:
            return new_patients[0]
        else:
            return new_patients


    def copy_series_data(self, key, row):
        row[0] = self.register.at[key, 'PatientID']
        row[1] = self.register.at[key, 'StudyInstanceUID']
        row[2] = self.register.at[key, 'SeriesInstanceUID']
        row[5] = self.register.at[key, 'PatientName']
        row[6] = self.register.at[key, 'StudyDescription']
        row[7] = self.register.at[key, 'StudyDate']
        row[8] = self.register.at[key, 'SeriesDescription']
        row[9] = self.register.at[key, 'SeriesNumber']
        return row


    def preserve_series_record(self, key):
        # If this is the last instance in the series,
        # keep the series as an empty series.
        source_series = self.register.at[key, 'SeriesInstanceUID']
        source_series = (self.register.removed == False) & (self.register.SeriesInstanceUID == source_series)
        source_series_instances = self.register.SOPInstanceUID[source_series]
        source_series_instances_cnt = source_series_instances.shape[0]
        if source_series_instances_cnt == 1:
            row = self.default()
            row = self.copy_series_data(key, row)
            self.new_row(row)


    def append_kwargs(self, kwargs, attributes, values):
        for key in kwargs:
            try:
                ind = attributes.index(key)
            except:
                attributes.append(key)
                values.append(kwargs[key])
            else:
                values[ind] = kwargs[key]


    def move_to_series(self, uid, target, **kwargs):
        """Copy datasets to another series"""

        target_keys = self.keys(series=target)
        if target_keys == []:
            msg = 'Moving data to a series that does not exist in the database'
            raise ValueError(msg)
        new_parent_key = target_keys[0]
        attributes, values = self.series_header(new_parent_key)
        self.append_kwargs(kwargs, attributes, values)

        n = self.value(target_keys, 'InstanceNumber')
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)
           
        keys = self.keys(uid)

        for i, key in enumerate(keys):

            self.status.progress(i+1, len(keys), message='Moving dataset..')
            self.preserve_series_record(key)
            instance_uid = self.value(key, 'SOPInstanceUID')
            ds = self.get_dataset(instance_uid, [key])

            if ds is None:
                row = self.value(key, self.columns).tolist()
                row = self.copy_series_data(new_parent_key, row)
                row[10] = i + 1 + max_number
                for val in kwargs:
                    if val in self._descriptives:
                        row[self._descriptives[val]] = kwargs[val]
                self.update_row_data(key, row)
            else:
                self.set_dataset_values(ds, key, attributes+['InstanceNumber'], values+[i+1+max_number])

        # If the series is empty and new instances have been added, then delete the row 
        new_parent_key = self.drop_placeholder_row(new_parent_key, 'SOPInstanceUID')

        if len(keys) == 1:
            return self.value(keys, 'SOPInstanceUID')
        else:
            return list(self.value(keys, 'SOPInstanceUID'))
        

    def copy_study_data(self, key, row):
        row[0] = self.register.at[key, 'PatientID']
        row[1] = self.register.at[key, 'StudyInstanceUID']
        row[5] = self.register.at[key, 'PatientName']
        row[6] = self.register.at[key, 'StudyDescription']
        row[7] = self.register.at[key, 'StudyDate']
        return row
    

    def preserve_study_record(self, key):
        # If this is the last series in the study
        # The create a new row for the empty study
        source_study = self.register.at[key, 'StudyInstanceUID']
        source_study_series = (self.register.removed == False) & (self.register.StudyInstanceUID == source_study)
        source_study_series = self.register.SeriesInstanceUID[source_study_series]
        source_study_series_cnt = len(source_study_series.unique())
        if source_study_series_cnt == 1:
            row = self.default()
            row = self.copy_study_data(key, row)
            self.new_row(row)

    def move_to_study(self, uid, target, **kwargs):
        """Copy series to another study"""

        target_keys = self.keys(study=target)
        new_parent_key = target_keys[0]
        attributes, values = self.study_header(new_parent_key)
        self.append_kwargs(kwargs, attributes, values)

        n = self.value(target_keys, 'SeriesNumber')
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)
            
        all_series = self.series(uid)

        for s, series in enumerate(all_series):

            self.status.progress(s+1, len(all_series), message='Moving series..')
            new_number = s + 1 + max_number
            keys = self.keys(series=series)
            self.preserve_study_record(keys[0])
            
            for key in keys:

                instance_uid = self.value(key, 'SOPInstanceUID')
                ds = self.get_dataset(instance_uid, [key])

                # If the instance is empty, just replace study data in the register.
                if ds is None:
                    row = self.value(key, self.columns).tolist()
                    row = self.copy_study_data(new_parent_key, row)
                    row[9] = new_number
                    for val in kwargs:
                        if val in self._descriptives:
                            row[self._descriptives[val]] = kwargs[val]
                    self.update_row_data(key, row)

                # Else set the values in the dataset and register.
                else:
                    self.set_dataset_values(ds, key, attributes+['SeriesNumber'], values+[new_number])

        new_parent_key = self.drop_placeholder_row(new_parent_key, 'SeriesInstanceUID')

        if len(all_series) == 1:
            return all_series[0]
        else:
            return all_series


    def copy_patient_data(self, key, row):
        row[0] = self.register.at[key, 'PatientID']
        row[5] = self.register.at[key, 'PatientName']
        return row


    def preserve_patient_record(self, key):
        # If this is the last study in the patient, create a new row for the empty patient record.
        source_patient = self.register.at[key, 'PatientID']
        source_patient = (self.register.removed == False) & (self.register.PatientID == source_patient)
        source_patient_studies = self.register.StudyInstanceUID[source_patient]
        source_patient_studies_cnt = len(source_patient_studies.unique())
        if source_patient_studies_cnt == 1:
            row = self.default()
            row = self.copy_patient_data(key, row)
            self.new_row(row)


    def move_to_patient(self, uid, target, **kwargs):
        """Copy series to another study"""

        target_keys = self.keys(patient=target)
        new_parent_key = target_keys[0]
        attributes, values = self.patient_header(new_parent_key)
        self.append_kwargs(kwargs, attributes, values)
        all_studies = self.studies(uid)

        for s, study in enumerate(all_studies):
            
            self.status.progress(s+1, len(all_studies), message='Moving study..')
            keys = self.keys(study=study)
            self.preserve_patient_record(keys[0])

            for series in self.series(keys=keys):

                # Move all instances one-by-one to new patient
                for key in self.keys(series=series):

                    instance_uid = self.value(key, 'SOPInstanceUID')
                    ds = self.get_dataset(instance_uid, [key])
                    
                    # If the instance is empty, just update the register.
                    if ds is None:
                        row = self.value(key, self.columns).tolist()
                        row = self.copy_patient_data(new_parent_key, row)
                        for val in kwargs:
                            if val in self._descriptives:
                                row[self._descriptives[val]] = kwargs[val]
                        self.update_row_data(key, row)

                    # Else set the values in the dataset and register.
                    else:
                        self.set_dataset_values(ds, key, attributes, values)

            new_parent_key = self.drop_placeholder_row(new_parent_key, 'StudyInstanceUID')

        if len(all_studies) == 1:
            return all_studies[0]
        else:
            return all_studies


    def move_to(self, source, target, **kwargs):

        type = self.type(target)
        if type == 'Patient':
            return self.move_to_patient(source, target, **kwargs)
        if type == 'Study':
            return self.move_to_study(source, target, **kwargs)
        if type == 'Series':
            return self.move_to_series(source, target, **kwargs)
        if type == 'Instance':
            raise ValueError('Cannot move to an instance. Please move to series, study or patient.')


    def create_new_instance(self, key, ds):
        series_uid = self.value(key, 'SeriesInstanceUID')
        if series_uid is None:
            study_uid = self.value(key, 'StudyInstanceUID')
            if study_uid is None:
                patient_uid = self.value(key, 'PatientID')
                if patient_uid is None:
                    _, new_key = self.new_instance('Database', ds)
                else:
                    _, new_key = self.new_instance(patient_uid, ds)
            else:
                _, new_key = self.new_instance(study_uid, ds)
        else:
            _, new_key = self.new_instance(series_uid, ds)
        return new_key




    def save_dataset(self, key, ds):
        if key in self.dataset:
            self.dataset[key] = ds
        else:
            path = self.filepath(key)
            ds.write(path, self.status)


    def set_dataset_values(self, ds, key, attributes, values):

        # If the dataset is in memory and has not yet been modified, then edit a copy.
        if key in self.dataset:
            if not self.value(key, 'created'):
                ds = copy.deepcopy(ds)

        # Change the values and get the register row data
        ds.set_values(attributes, values)
        row = ds.get_values(self.columns)

        # Update the register and save the modified dataset
        key = self.update_row_data(key, row)
        self.save_dataset(key, ds)
        return key # added
    

    def set_row_values(self, key, attributes, values):
        if not isinstance(values, list):
            values = [values]
            attributes = [attributes]
        row = self.value(key, self.columns).tolist()
        for i, attr in enumerate(attributes):
            if attr in self._descriptives:
                row[self._descriptives[attr]] = values[i]
        self.update_row_data(key, row)


    def set_values(self, attributes, values, keys=None, uid=None):
        """Set values in a dataset"""

        uids = ['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID']
        uids = [i for i in uids if i in attributes]
        if uids != []:
            raise ValueError('UIDs cannot be set using set_value(). Use copy_to() or move_to() instead.')

        if keys is None:
            keys = self.keys(uid)

        for key in keys:

            # Get the dataset
            instance_uid = self.value(key, 'SOPInstanceUID')
            if instance_uid is None: 
                ds = None
            else:
                ds = self.get_dataset(instance_uid, [key])

            if ds is None:
                # Update register entries only
                self.set_row_values(key, attributes, values)
            else:
                # Set the new values
                self.set_dataset_values(ds, key, attributes, values)

 
    def get_values(self, attributes, keys=None, uid=None):

        if keys is None:
            keys = self.keys(uid)
            if keys == []:
                return

        # Single attribute
        if np.isscalar(attributes):

            if attributes in self.columns:
                value = [self.register.at[key, attributes] for key in keys]
                # Get unique elements
                value = [x for i, x in enumerate(value) if i==value.index(x)]
            else:
                value = []
                for i, key in enumerate(keys):
                    instance_uid = self.value(key, 'SOPInstanceUID')
                    ds = self.get_dataset(instance_uid, [key])
                    if ds is None:
                        v = None
                    else:
                        v = ds.get_values(attributes)
                    if v not in value:
                        value.append(v)
            if len(value) == 1:
                return value[0]
            try: 
                value.sort() 
            except:
                pass
            return value

        # Multiple attributes
        # Create a np array v with values for each instance and attribute
        if set(attributes) <= set(self.columns):
            v = self.value(keys, attributes)
        else:
            v = np.empty((len(keys), len(attributes)), dtype=object)
            for i, key in enumerate(keys):
                instance_uid = self.value(key, 'SOPInstanceUID')
                ds = self.get_dataset(instance_uid, [key])
                if isinstance(ds, list):
                    instances = self.register.SOPInstanceUID == instance_uid
                    msg = 'Multiple instances with the same SOPInstanceUID \n'
                    msg += instance_uid + '\n'
                    msg += str(self.register.loc[instances].transpose())
                    raise DatabaseCorrupted(msg)
                if ds is None:
                    v[i,:] = [None] * len(attributes)
                else:
                    v[i,:] = ds.get_values(attributes)

        # Return a list with unique values for each attribute
        values = []
        for a in range(v.shape[1]):
            va = v[:,a]
            # Remove None values
            #va = va[va != np.array(None)]
            va = va[[x is not None for x in va]]
            va = list(va)
            # Get unique values and sort
            va = [x for i, x in enumerate(va) if i==va.index(x)]
            if len(va) == 0:
                va = None
            elif len(va) == 1:
                va = va[0]
            else:
                try: 
                    va.sort()
                except:
                    pass
            values.append(va)
        return values


    def import_dataset(self, ds):

        # Do not import SOPInstances that are already in the database
        uid = ds.SOPInstanceUID
        keys = self.keys(instance=uid)
        if keys != []:
            msg = 'Cannot import a dataset that is already in the database.'
            raise ValueError(msg)

        # Add a row to the register
        row = ds.get_values(self.columns)
        new_key = self.new_key()
        self.new_row(row, new_key)
        
        # If the database exists on disk, write file
        if self.path is not None:
            path = self.filepath(new_key)
            ds.write(path)




    # Misleading name because files are not datasets - e.g. does not work for datasets in memory.
    def import_datasets(self, files):

        # Read manager data
        df = dbdataset.read_dataframe(files, self.columns, self.status)
        df['removed'] = False
        df['created'] = True

        # Do not import SOPInstances that are already in the database
        uids = df.SOPInstanceUID.values.tolist()
        keys = self.keys(instance=uids)
        if keys != []:
            do_not_import = self.value(keys, 'SOPInstanceUID')
            rows = df.SOPInstanceUID.isin(do_not_import)
            df.drop(df[rows].index, inplace=True)
        if df.empty:
            return

        # Add those that are left to the database
        files = df.index.tolist()
        for i, file in enumerate(files):
            self.status.progress(i+1, len(files), 'Copying files..')
            new_key = self.new_key()
            ds = dbdataset.read(file)
            ds.write(self.filepath(new_key), self.status)
            df.rename(index={file:new_key}, inplace=True)
        self.register = pd.concat([self.register, df])

        # return the UIDs of the new instances
        return df.SOPInstanceUID.values.tolist()
    


    def export_datasets(self, uids, database):
        
        files = self.filepaths(uids)
        database.import_datasets(files)


    # def import_datasets_from_nifti(self, files, study=None):

    #     if study is None:
    #         study, _ = self.new_study()

    #     # Create new 
    #     nifti_series = None
    #     for i, file in enumerate(files):

    #         # Read the nifti file
    #         nim = nib.load(file)
    #         sx, sy, sz = nim.header.get_zooms() # spacing
            
    #         # If a dicom header is stored, get it
    #         # Else create one from scratch
    #         try:
    #             dcmext = nim.header.extensions
    #             dataset = DbDataset(dcmext[0].get_content())
    #         except:
    #             dataset = new_dataset()

    #         # Read the array and reshape to 3D 
    #         array = np.squeeze(nim.get_fdata())
    #         array.reshape((array.shape[0], array.shape[1], -1))
    #         n_slices = array.shape[-1]

    #         # If there is only one slice,
    #         # load it into the nifti series.
    #         if n_slices == 1:
    #             if nifti_series is None:
    #                 desc = os.path.basename(file)
    #                 nifti_series, _ = self.new_series(study, SeriesDescription=desc)
    #             affine = dbimage.affine_to_RAH(nim.affine)
    #             dataset.set_pixel_array(array[:,:,0])
    #             dataset.set_values('affine_matrix', affine)
    #             #dataset.set_values('PixelSpacing', [sy, sx])
    #             self.new_instance(nifti_series, dataset)

    #         # If there are multiple slices in the file,
    #         # Create a new series and save all files in there.
    #         else:
    #             desc = os.path.basename(file)
    #             series, _ = self.new_series(study, SeriesDescription=desc)
    #             affine = dbimage.affine_to_RAH(nim.affine)
    #             for z in range(n_slices):
    #                 ds = copy.deepcopy(dataset)
    #                 ds.set_pixel_array(array[:,:,z])
    #                 ds.set_values('affine_matrix', affine)
    #                 #ds.set_values('PixelSpacing', [sy, sx])
    #                 self.new_instance(series, ds)



#   Helper functions to hide the register from classes other than manager
#   Consider removing after eliminating dataframe

    def _empty(self):
        return self.register.empty

    def _dbloc(self):
        return self.register.removed==False

    def _keys(self, loc):
        return self.register.index[loc]

    def _at(self, row, col):
        return self.register.at[row, col]

    def _extract(self, rows):
        return self.register.loc[rows,:]

    def _loc(self, name, uid):
        df = self.register
        return (df.removed==False) & (df[name]==uid)  

    def _extract_record(self, name, uid):
        return self.register[name] == uid
    