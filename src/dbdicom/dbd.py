import os
from datetime import datetime

from tqdm import tqdm
import numpy as np
import pandas as pd
import vreg
from pydicom.dataset import Dataset

import dbdicom.utils.arrays
import dbdicom.utils.files as filetools
import dbdicom.utils.dcm4che as dcm4che
import dbdicom.dataset as dbdataset
import dbdicom.register as register
import dbdicom.mods as mods



class DataBaseDicom():

    def __init__(self, path):

        if not os.path.exists(path):
            os.makedirs(path)
        self.path = path

        file = self._register_file()
        if os.path.exists(file):
            try:
                self.register = pd.read_pickle(file)
            except:
                # If the file is corrupted, delete it and load again
                os.remove(file)
                self.read()
        else:
            self.read()


    def read(self):

        files = filetools.all_files(self.path)
        self.register = dbdataset.read_dataframe(
            files, 
            register.COLUMNS + ['NumberOfFrames','SOPClassUID'], 
            path=self.path, 
            images_only = True)
        self.register['removed'] = False
        self.register['created'] = False
        # No support for multiframe data at the moment
        self._multiframe_to_singleframe()
        # For now ensure all series have just a single CIOD
        self._split_series()
        return self
    

    def close(self): 

        created = self.register.created & (self.register.removed==False) 
        removed = self.register.removed
        created = created[created].index
        removed = removed[removed].index

        # delete datasets marked for removal
        for index in removed.tolist():
            file = os.path.join(self.path, index)
            if os.path.exists(file): 
                os.remove(file)
        # and drop then from the register
        self.register.drop(index=removed, inplace=True)

        # for new or edited data, mark as saved.
        self.register.loc[created, 'created'] = False

        # save register
        file = self._register_file()
        self.register.to_pickle(file)
        return self
    

    def restore(self):  

        created = self.register.created 
        removed = self.register.removed & (self.register.created==False)
        created = created[created].index
        removed = removed[removed].index

        # permanently delete newly created datasets
        for index in created.tolist():
            file = os.path.join(self.path, index)
            if os.path.exists(file): 
                os.remove(file)

        # and drop then from the register
        self.register.drop(index=created, inplace=True)

        # Restore those that were marked for removal
        self.register.loc[removed, 'removed'] = False

        # save register
        file = self._register_file()
        self.register.to_pickle(file)
        return self    


    def summary(self):
        return register.summary(self.register)
    
    def print(self):
        register.print_tree(self.register)
        return self
    
    def patients(self, name=None, contains=None, isin=None):
        return register.patients(self.register, self.path, name, contains, isin)
    
    def studies(self, entity=None, name=None, contains=None, isin=None):
        if entity == None:
            entity = self.path
        if isinstance(entity, str):
            studies = []
            for patient in self.patients():
                studies += self.studies(patient, name, contains, isin)
            return studies
        else:
            return register.studies(self.register, entity, name, contains, isin)
    
    def series(self, entity=None, name=None, contains=None, isin=None):
        if entity == None:
            entity = self.path
        if isinstance(entity, str):
            series = []
            for study in self.studies(entity):
                series += self.series(study, name, contains, isin)
            return series
        elif len(entity)==2:
            series = []
            for study in self.studies(entity):
                series += self.series(study, name, contains, isin)
            return series
        else: # path = None (all series) or path = patient (all series in patient)
            return register.series(self.register, entity, name, contains, isin)


    def volume(self, series:list, dims:list=None, multislice=False) -> vreg.Volume3D:
        if dims is None:
            dims = []
        elif isinstance(dims, str):
            dims = [dims]
        else:
            dims = list(dims)
        dims = ['SliceLocation'] + dims

        files = register.files(self.register, series)
        
        # Read dicom files
        values = []
        volumes = []
        for f in tqdm(files, desc='Reading volume..'):
            ds = dbdataset.read_dataset(f)  
            values.append(dbdataset.get_values(ds, dims))
            volumes.append(dbdataset.volume(ds, multislice))

        # Format as mesh
        coords = np.stack(values, axis=-1)
        coords, inds = dbdicom.utils.arrays.meshvals(coords)
        vols = np.array(volumes)
        vols = vols[inds].reshape(coords.shape[1:])

        # Check that all slices have the same coordinates
        c0 = coords[1:,0,...]
        for k in range(coords.shape[1]-1):
            if not np.array_equal(coords[1:,k+1,...], c0):
                raise ValueError(
                    "Cannot build a single volume. Not all slices "
                    "have the same coordinates. \nIf you set " 
                    "firstslice=True, the coordinates of the lowest "
                    "slice will be assigned to the whole volume."     
                )

        # Join 2D volumes into 3D volumes
        vol = vreg.join(vols)
        if vol.ndim > 3:
            vol.set_coords(c0)
            vol.set_dims(dims[1:])
        return vol

    
    def write_volume(
            self, vol:vreg.Volume3D, series:list, 
            ref:list=None, multislice=False,
        ):
        if ref is None:
            ds = dbdataset.new_dataset('MRImage')
        else:
            if ref[0] == series[0]:
                ref_mgr = self
            else:
                ref_mgr = DataBaseDicom(ref[0])
            files = register.files(ref_mgr.register, ref)
            ds = dbdataset.read_dataset(files[0]) 

        # Get the attributes of the destination series
        attr = self._attributes(series)
        n = self._max_instance_number(attr['SeriesInstanceUID'])

        new_instances = {}
        if vol.ndim==3:
            slices = vol.split()
            for i, sl in tqdm(enumerate(slices), desc='Writing volume..'):
                dbdataset.set_volume(ds, sl, multislice)
                self._write_dataset(ds, attr, n + 1 + i, new_instances)
        else:
            i=0
            vols = vol.separate().reshape(-1)
            for vt in tqdm(vols, desc='Writing volume..'):
                for sl in vt.split():
                    dbdataset.set_volume(ds, sl, multislice)
                    dbdataset.set_value(ds, sl.dims, sl.coords[:,...])
                    self._write_dataset(ds, attr, n + 1 + i, new_instances)
                    i+=1
            return self
        self._update_register(new_instances)


    def to_nifti(self, series:list, file:str, dims=None, multislice=False):
        vol = self.volume(series, dims, multislice)
        vreg.write_nifti(vol, file)
        return self

    def from_nifti(self, file:str, series:list, ref:list=None, multislice=False):
        vol = vreg.read_nifti(file)
        self.write_volume(vol, series, ref, multislice)
        return self
    
    def pixel_data(self, series:list, dims:list=None, include=None) -> np.ndarray:
        if np.isscalar(dims):
            dims = [dims]
        else:
            dims = list(dims)

        # Ensure return_vals is a list
        if include is None:
            params = []
        elif np.isscalar(include):
            params = [include]
        else:
            params = list(include)

        files = register.files(self.register, series)
        
        # Read dicom files
        coords = []
        arrays = np.empty(len(files), dtype=dict)
        if include is not None:
            values = np.empty(len(files), dtype=dict)
        for i, f in tqdm(enumerate(files), desc='Reading pixel data..'):
            ds = dbdataset.read_dataset(f)  
            coords.append(dbdataset.get_values(ds, dims))
            # save as dict so numpy does not stack as arrays
            arrays[i] = {'pixel_data': dbdataset.pixel_data(ds)}
            if include is not None:
                values[i] = {'values': dbdataset.get_values(ds, params)}

        # Format as mesh
        coords = np.stack([v for v in coords], axis=-1)
        coords, inds = dbdicom.utils.arrays.meshvals(coords)

        arrays = arrays[inds].reshape(coords.shape[1:])
        arrays = np.stack([a['pixel_data'] for a in arrays.reshape(-1)], axis=-1)
        arrays = arrays.reshape(arrays.shape[:2] + coords.shape[1:])

        if include is None:
            return arrays, coords
        
        values = values[inds].reshape(coords.shape[1:])
        values = np.stack([a['values'] for a in values.reshape(-1)], axis=-1)
        values = values.reshape((len(params), ) + coords.shape[1:])

        return arrays, coords, values
    
    
    def unique(self, pars:list, entity:list) -> dict:
        v = self._values(pars, entity)

        # Return a list with unique values for each attribute
        values = []
        for a in range(v.shape[1]):
            va = v[:,a]
            # Remove None values
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
        return {p: values[i] for i, p in enumerate(pars)} 
    
    def copy(self, from_entity, to_entity):
        if len(from_entity) == 4:
            if len(to_entity) != 4:
                raise ValueError(
                    f"Cannot copy series {from_entity} to series {to_entity}. "
                    f"{to_entity} is not a series (needs 4 elements)."
                )
            return self._copy_series(from_entity, to_entity)
        if len(from_entity) == 3:
            if len(to_entity) != 3:
                raise ValueError(
                    f"Cannot copy study {from_entity} to study {to_entity}. "
                    f"{to_entity} is not a study (needs 3 elements)."
                )
            return self._copy_study(from_entity, to_entity)
        if len(from_entity) == 2:
            if len(to_entity) != 2:
                raise ValueError(
                    f"Cannot copy patient {from_entity} to patient {to_entity}. "
                    f"{to_entity} is not a patient (needs 2 elements)."
                )                
            return self._copy_patient(from_entity, to_entity)
        raise ValueError(
            f"Cannot copy {from_entity} to {to_entity}. "
        )
    
    def delete(self, entity):
        index = register.index(self.register, entity)
        self.register.loc[index,'removed'] = True
        return self

    def move(self, from_entity, to_entity):
        self.copy(from_entity, to_entity)
        self.delete(from_entity)
        return self

    def _values(self, attributes:list, entity:list):
        # Create a np array v with values for each instance and attribute
        if set(attributes) <= set(self.register.columns):
            index = register.index(self.register, entity)
            v = self.register.loc[index, attributes].values
        else:
            files = register.files(self.register, entity)
            v = np.empty((len(files), len(attributes)), dtype=object)
            for i, f in enumerate(files):
                ds = dbdataset.read_dataset(f)
                v[i,:] = dbdataset.get_values(ds, attributes)
        return v

    def _copy_patient(self, from_patient, to_patient):
        from_patient_studies = register.studies(self.register, from_patient)
        for from_study in tqdm(from_patient_studies, desc=f'Copying patient {from_patient[1:]}'):
            if to_patient[0]==from_patient[0]:
                to_study = register.append(self.register, to_patient, from_study[-1])
            else:
                mgr = DataBaseDicom(to_study[0])
                to_study = register.append(mgr.register, to_patient, from_study[-1])                
            self._copy_study(from_study, to_study)

    def _copy_study(self, from_study, to_study):
        from_study_series = register.series(self.register, from_study)
        for from_series in tqdm(from_study_series, desc=f'Copying study {from_study[1:]}'):
            if to_study[0]==from_study[0]:
                to_series = register.append(self.register, to_study, from_series[-1])
            else:
                mgr = DataBaseDicom(to_study[0])
                to_series = register.append(mgr.register, to_study, from_series[-1])
            self._copy_series(from_series, to_series)

    def _copy_series(self, from_series, to_series):
        # Get the files to be exported
        from_series_files = register.files(self.register, from_series)

        if to_series[0] == from_series[0]:
            # Copy in the same database
            self._files_to_series(from_series_files, to_series)
        else:
            # Copy to another database
            mgr = DataBaseDicom(to_series[0])
            mgr._files_to_series(from_series_files, to_series)
            mgr.close()


    def _files_to_series(self, files, to_series):

        # Get the attributes of the destination series
        attr = self._attributes(to_series)
        n = self._max_instance_number(attr['SeriesInstanceUID'])
        
        # Copy the files to the new series 
        new_instances = {}
        for i, f in tqdm(enumerate(files), total=len(files), desc=f'Copying series {to_series[1:]}'):
            # Read dataset and assign new properties
            ds = dbdataset.read_dataset(f)
            self._write_dataset(ds, attr, n + 1 + i, new_instances)
        self._update_register(new_instances)


    def _max_series_number(self, study_uid):
        df = self.register
        df = df[(df.StudyInstanceUID==study_uid) & (df.removed==False)]
        n = df['SeriesNumber'].values
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)  
        return max_number 

    def _max_instance_number(self, series_uid):
        df = self.register
        df = df[(df.SeriesInstanceUID==series_uid) & (df.removed==False)]
        n = df['InstanceNumber'].values
        n = n[n != -1]
        max_number=0 if n.size==0 else np.amax(n)  
        return max_number 


    def _attributes(self, entity):
        if len(entity)==4:
            return self._series_attributes(entity)
        if len(entity)==3:
            return self._study_attributes(entity)
        if len(entity)==2:
            return self._patient_attributes(entity)       


    def _patient_attributes(self, patient):
        try:
            # If the patient exists and has files, read from file
            files = register.files(self.register, patient)
            attr = mods.PATIENT_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except:
            # If the patient does not exist, generate values
            attr = ['PatientID', 'PatientName']
            patient_id = dbdataset.new_uid()
            patient_name = patient[-1] if isinstance(patient[-1], str) else patient[-1][0]
            vals = [patient_id, patient_name]
        return {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}


    def _study_attributes(self, study):
        patient_attr = self._patient_attributes(study[:2])
        try:
            # If the study exists and has files, read from file
            files = register.files(self.register, study)
            attr = mods.STUDY_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except:
            # If the study does not exist, generate values
            attr = ['StudyInstanceUID', 'StudyDescription', 'StudyDate']
            study_id = dbdataset.new_uid()
            study_desc = study[-1] if isinstance(study[-1], str) else study[-1][0]
            study_date = datetime.today().strftime('%Y%m%d')
            vals = [study_id, study_desc, study_date]
        return patient_attr | {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}


    def _series_attributes(self, series):
        study_attr = self._study_attributes(series[:3])
        try:
            # If the series exists and has files, read from file
            files = register.files(self.register, series)
            attr = mods.SERIES_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except:
            # If the series does not exist or is empty, generate values
            try:
                study_uid = register.uid(self.register, series[:-1])
            except:
                series_number = 1
            else:
                series_number = 1 + self._max_series_number(study_uid)
            attr = ['SeriesInstanceUID', 'SeriesDescription', 'SeriesNumber']
            series_id = dbdataset.new_uid()
            series_desc = series[-1] if isinstance(series[-1], str) else series[-1][0]
            vals = [series_id, series_desc, series_number]
        return study_attr | {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}

        
    def _write_dataset(self, ds:Dataset, attr:dict, instance_nr:int, register:dict):
        # Set new attributes 
        attr['SOPInstanceUID'] = dbdataset.new_uid()
        attr['InstanceNumber'] = instance_nr
        dbdataset.set_values(ds, list(attr.keys()), list(attr.values()))
        # Save results in a new file
        rel_path = os.path.join('dbdicom', dbdataset.new_uid() + '.dcm') 
        dbdataset.write(ds, os.path.join(self.path, rel_path))
        # Add a row to the register
        register[rel_path] = dbdataset.get_values(ds, self.register.columns)


    def _update_register(self, new_instances:dict):
        # A new instances to the register
        df = pd.DataFrame.from_dict(new_instances, orient='index', columns=self.register.columns)
        df['removed'] = False
        df['created'] = True
        self.register = pd.concat([self.register, df])


    def _register_file(self):
        filename = os.path.basename(os.path.normpath(self.path)) + ".pkl"
        return os.path.join(self.path, filename) 
    

    def _multiframe_to_singleframe(self):
        """Converts all multiframe files in the folder into single-frame files.
        
        Reads all the multi-frame files in the folder,
        converts them to singleframe files, and delete the original multiframe file.
        """
        singleframe = self.register.NumberOfFrames.isnull() 
        multiframe = singleframe == False
        nr_multiframe = multiframe.sum()
        if nr_multiframe != 0: 
            for relpath in tqdm(self.register[multiframe].index.values, desc="Converting multiframe file " + relpath):
                filepath = os.path.join(self.path, relpath)
                singleframe_files = dcm4che.split_multiframe(filepath) 
                if singleframe_files != []:            
                    # add the single frame files to the dataframe
                    df = dbdataset.read_dataframe(singleframe_files, self.register.columns, path=self.path)
                    df['removed'] = False
                    df['created'] = False
                    self.register = pd.concat([self.register, df])
                    # delete the original multiframe 
                    os.remove(filepath)
                # drop the file also if the conversion has failed
                self.register.drop(index=relpath, inplace=True)
        self.register.drop('NumberOfFrames', axis=1, inplace=True)


    def _split_series(self):
        """
        Split series with multiple SOP Classes.

        If a series contain instances from different SOP Classes, 
        these are separated out into multiple series with identical SOP Classes.
        """
        # For each series, check if there are multiple
        # SOP Classes in the series and split them if yes.
        all_series = self.series()
        for series in tqdm(all_series, desc='Splitting series with multiple SOP Classes.'):
            series_index = register.index(self.register, series)
            df_series = self.register.loc[series_index]
            sop_classes = df_series.SOPClassUID.unique()
            if len(sop_classes) > 1:
                # For each sop_class, create a new series and move all
                # instances of that sop_class to the new series
                desc = series[-1] if isinstance(series, str) else series[0]
                for i, sop_class in enumerate(sop_classes[1:]):
                    df_sop_class = df_series[df_series.SOPClassUID == sop_class]
                    relpaths = df_sop_class.index.tolist()
                    sop_class_files = [os.path.join(self.path, p) for p in relpaths]
                    sop_class_series = series[:-1] + [desc + f' [{i+1}]']
                    self._files_to_series(sop_class_files, sop_class_series)
                    # Delete original files permanently
                    self.register.drop(relpaths)
                    for f in sop_class_files:
                        os.remove(f)
        self.register.drop('SOPClassUID', axis=1, inplace=True)


