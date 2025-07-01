import os
from datetime import datetime
import json
from typing import Union

from tqdm import tqdm
import numpy as np
import vreg
from pydicom.dataset import Dataset

import dbdicom.utils.arrays
import dbdicom.dataset as dbdataset
import dbdicom.database as dbdatabase
import dbdicom.register as register
import dbdicom.const as const



class DataBaseDicom():
    """Class to read and write a DICOM folder.

    Args:
        path (str): path to the DICOM folder.
    """

    def __init__(self, path):

        if not os.path.exists(path):
            os.makedirs(path)
        self.path = path

        file = self._register_file()
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    self.register = json.load(f)
                # remove the json file after reading it. If the database
                # is not properly closed this will prevent that changes
                # have been made which are not reflected in the json 
                # file on disk
                # os.remove(file)
            except Exception as e:
                # raise ValueError(
                #     f'Cannot open {file}. Please close any programs that are '
                #     f'using it and try again. Alternatively you can delete the file '
                #     f'manually and try again.'
                # )
                # If the file can't be read, delete it and load again
                os.remove(file)
                self.read()
        else:
            self.read()


    def read(self):
        """Read the DICOM folder again
        """
        self.register = dbdatabase.read(self.path)
        # For now ensure all series have just a single CIOD
        # Leaving this out for now until the issue occurs again.
        # self._split_series()
        return self

    

    def delete(self, entity):
        """Delete a DICOM entity from the database

        Args:
            entity (list): entity to delete
        """
        removed = register.index(self.register, entity)
        # delete datasets marked for removal
        for index in removed:
            file = os.path.join(self.path, index)
            if os.path.exists(file): 
                os.remove(file)
        # and drop then from the register
        self.register = register.drop(self.register, removed)
        return self
    

    def close(self): 
        """Close the DICOM folder
        
        This also saves changes in the header file to disk.
        """
        file = self._register_file()
        with open(file, 'w') as f:
            json.dump(self.register, f, indent=4)
        return self

    def _register_file(self):
        return os.path.join(self.path, 'dbtree.json') 
    

    def summary(self):
        """Return a summary of the contents of the database.

        Returns:
            dict: Nested dictionary with summary information on the database.
        """
        return register.summary(self.register)
    

    def print(self):
        """Print the contents of the DICOM folder
        """
        register.print_tree(self.register)
        return self
    
    def patients(self, name=None, contains=None, isin=None):
        """Return a list of patients in the DICOM folder.

        Args:
            name (str, optional): value of PatientName, to search for 
                individuals with a given name. Defaults to None.
            contains (str, optional): substring of PatientName, to 
                search for individuals based on part of their name. 
                Defaults to None.
            isin (list, optional): List of PatientName values, to search 
                for patients whose name is in the list. Defaults to None.

        Returns:
            list: list of patients fulfilling the criteria.
        """
        return register.patients(self.register, self.path, name, contains, isin)
    
    def studies(self, entity=None, desc=None, contains=None, isin=None):
        """Return a list of studies in the DICOM folder.

        Args:
            entity (str or list): path to a DICOM folder (to search in 
                the whole folder), or a two-element list identifying a 
                patient (to search studies of a given patient).
            desc (str, optional): value of StudyDescription, to search for 
                studies with a given description. Defaults to None.
            contains (str, optional): substring of StudyDescription, to 
                search for studies based on part of their description. 
                Defaults to None.
            isin (list, optional): List of StudyDescription values, to search 
                for studies whose description is in a list. Defaults to None.

        Returns:
            list: list of studies fulfilling the criteria.
        """
        if entity == None:
            entity = self.path
        if isinstance(entity, str):
            studies = []
            for patient in self.patients():
                studies += self.studies(patient, desc, contains, isin)
            return studies
        elif len(entity)==1:
            studies = []
            for patient in self.patients():
                studies += self.studies(patient, desc, contains, isin)
            return studies
        else:
            return register.studies(self.register, entity, desc, contains, isin)
    
    def series(self, entity=None, desc=None, contains=None, isin=None):
        """Return a list of series in the DICOM folder.

        Args:
            entity (str or list): path to a DICOM folder (to search in 
                the whole folder), or a list identifying a 
                patient or a study (to search series of a given patient 
                or study).
            desc (str, optional): value of SeriesDescription, to search for 
                series with a given description. Defaults to None.
            contains (str, optional): substring of SeriesDescription, to 
                search for series based on part of their description. 
                Defaults to None.
            isin (list, optional): List of SeriesDescription values, to search 
                for series whose description is in a list. Defaults to None.

        Returns:
            list: list of series fulfilling the criteria.
        """
        if entity == None:
            entity = self.path
        if isinstance(entity, str):
            series = []
            for study in self.studies(entity):
                series += self.series(study, desc, contains, isin)
            return series
        elif len(entity)==1:
            series = []
            for study in self.studies(entity):
                series += self.series(study, desc, contains, isin)
            return series            
        elif len(entity)==2:
            series = []
            for study in self.studies(entity):
                series += self.series(study, desc, contains, isin)
            return series
        else: # path = None (all series) or path = patient (all series in patient)
            return register.series(self.register, entity, desc, contains, isin)


    def volume(self, entity:Union[list, str], dims:list=None) -> Union[vreg.Volume3D, list]:
        """Read volume or volumes.

        Args:
            entity (list, str): DICOM entity to read
            dims (list, optional): Non-spatial dimensions of the volume. Defaults to None.

        Returns:
            vreg.Volume3D | list: If the entity is a series this returns 
            a volume, else a list of volumes.
        """
        if isinstance(entity, str): # path to folder
            return [self.volume(s, dims) for s in self.series(entity)]
        if len(entity) < 4: # folder, patient or study
            return [self.volume(s, dims) for s in self.series(entity)]
        if dims is None:
            dims = []
        elif isinstance(dims, str):
            dims = [dims]
        else:
            dims = list(dims)
        dims = ['SliceLocation'] + dims

        files = register.files(self.register, entity)
        
        # Read dicom files
        values = []
        volumes = []
        for f in tqdm(files, desc='Reading volume..'):
            ds = dbdataset.read_dataset(f)
            values.append(dbdataset.get_values(ds, dims))
            volumes.append(dbdataset.volume(ds))

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
                    "have the same coordinates."     
                )
            
        # Infer spacing between slices from slice locations
        # Technically only necessary if SpacingBetweenSlices not set or incorrect
        vols = infer_slice_spacing(vols)

        # Join 2D volumes into 3D volumes
        try:
            vol = vreg.join(vols)
        except ValueError:
            # some vendors define the slice vector as -cross product 
            # of row and column vector. Check if that solves the issue.
            for v in vols.reshape(-1):
                v.affine[:3,2] = -v.affine[:3,2]
                # Then try again
            vol = vreg.join(vols)
        if vol.ndim > 3:
            vol.set_coords(c0)
            vol.set_dims(dims[1:])
        return vol

    
    def write_volume(
            self, vol:Union[vreg.Volume3D, tuple], series:list, 
            ref:list=None, 
        ):
        """Write a vreg.Volume3D to a DICOM series

        Args:
            vol (vreg.Volume3D): Volume to write to the series.
            series (list): DICOM series to read
            ref (list): Reference series
        """
        if isinstance(vol, tuple):
            vol = vreg.volume(vol[0], vol[1])
        if ref is None:
            ds = dbdataset.new_dataset('MRImage')
            #ds = dbdataset.new_dataset('ParametricMap')
        else:
            if ref[0] == series[0]:
                ref_mgr = self
            else:
                ref_mgr = DataBaseDicom(ref[0])
            files = register.files(ref_mgr.register, ref)
            ref_mgr.close()
            ds = dbdataset.read_dataset(files[0]) 

        # Get the attributes of the destination series
        attr = self._series_attributes(series)
        n = self._max_instance_number(attr['SeriesInstanceUID'])

        if vol.ndim==3:
            slices = vol.split()
            for i, sl in tqdm(enumerate(slices), desc='Writing volume..'):
                dbdataset.set_volume(ds, sl)
                self._write_dataset(ds, attr, n + 1 + i)
        else:
            i=0
            vols = vol.separate().reshape(-1)
            for vt in tqdm(vols, desc='Writing volume..'):
                for sl in vt.split():
                    dbdataset.set_volume(ds, sl)
                    dbdataset.set_value(ds, sl.dims, sl.coords[:,...])
                    self._write_dataset(ds, attr, n + 1 + i)
                    i+=1
        return self


    def to_nifti(self, series:list, file:str, dims=None):
        """Save a DICOM series in nifti format.

        Args:
            series (list): DICOM series to read
            file (str): file path of the nifti file.
            dims (list, optional): Non-spatial dimensions of the volume. 
                Defaults to None.
        """
        vol = self.volume(series, dims)
        vreg.write_nifti(vol, file)
        return self

    def from_nifti(self, file:str, series:list, ref:list=None):
        """Create a DICOM series from a nifti file.

        Args:
            file (str): file path of the nifti file.
            series (list): DICOM series to create
            ref (list): DICOM series to use as template.
        """
        vol = vreg.read_nifti(file)
        self.write_volume(vol, series, ref)
        return self
    
    def pixel_data(self, series:list, dims:list=None, coords=False, attr=None) -> np.ndarray:
        """Read the pixel data from a DICOM series

        Args:
            series (list or str): DICOM series to read. This can also 
                be a path to a folder containing DICOM files, or a 
                patient or study to read all series in that patient or 
                study. In those cases a list is returned.
            dims (list, optional): Dimensions of the array.
            coords (bool): If set to True, the coordinates of the 
                arrays are returned alongside the pixel data
            attr (list, optional): list of DICOM attributes that are 
                read on the fly to avoid reading the data twice.

        Returns:
            numpy.ndarray or tuple: numpy array with pixel values, with 
                at least 3 dimensions (x,y,z). If 
                coords is set these are returned too as an array with 
                coordinates of the slices according to dims. If include 
                is provided the values are returned as a dictionary in the last 
                return value. 
        """
        if isinstance(series, str): # path to folder
            return [self.pixel_data(s, dims, coords, attr) for s in self.series(series)]
        if len(series) < 4: # folder, patient or study
            return [self.pixel_data(s, dims, coords, attr) for s in self.series(series)]

        if dims is None:
            dims = ['InstanceNumber']
        elif np.isscalar(dims):
            dims = [dims]
        else:
            dims = list(dims)

        # Ensure return_vals is a list
        if attr is None:
            params = []
        elif np.isscalar(attr):
            params = [attr]
        else:
            params = list(attr)

        files = register.files(self.register, series)
        
        # Read dicom files
        coords_array = []
        arrays = np.empty(len(files), dtype=dict)
        if attr is not None:
            values = np.empty(len(files), dtype=dict)
        for i, f in tqdm(enumerate(files), desc='Reading pixel data..'):
            ds = dbdataset.read_dataset(f)  
            coords_array.append(dbdataset.get_values(ds, dims))
            # save as dict so numpy does not stack as arrays
            arrays[i] = {'pixel_data': dbdataset.pixel_data(ds)}
            if attr is not None:
                values[i] = {'values': dbdataset.get_values(ds, params)}

        # Format as mesh
        coords_array = np.stack([v for v in coords_array], axis=-1)
        coords_array, inds = dbdicom.utils.arrays.meshvals(coords_array)

        arrays = arrays[inds].reshape(coords_array.shape[1:])
        arrays = np.stack([a['pixel_data'] for a in arrays.reshape(-1)], axis=-1)
        arrays = arrays.reshape(arrays.shape[:2] + coords_array.shape[1:])

        if attr is None:
            if coords:
                return arrays, coords_array
            else:
                return arrays

        # Return values as a dictionary
        values = values[inds].reshape(-1)
        values_dict = {}
        for p in range(len(params)):
            # Get the type from the first value
            vp0 = values[0]['values'][p]
            # Build an array of the right type
            vp = np.zeros(values.size, dtype=type(vp0))
            # Populate the array with values for parameter p
            for i, v in enumerate(values):
                vp[i] = v['values'][p]
            # Reshape values for parameter p
            vp = vp.reshape(coords_array.shape[1:])
            # Eneter in the dictionary
            values_dict[params[p]] = vp

        # If only one, return as value
        if len(params) == 1:
            values_return = values_dict[attr[0]]
        else:
            values_return = values_dict
        
        # problem if the values are a list. Needs an array with a prespeficied dtype
        # values = values[inds].reshape(coords_array.shape[1:])
        # values = np.stack([a['values'] for a in values.reshape(-1)], axis=-1) 
        # values = values.reshape((len(params), ) + coords_array.shape[1:])

        if coords:
            return arrays, coords_array, values_return
        else:
            return arrays, values_return
        

    def values(self, series:list, attr=None, dims:list=None, coords=False) -> Union[dict, tuple]:
        """Read the values of some or all attributes from a DICOM series

        Args:
            series (list or str): DICOM series to read. This can also 
                be a path to a folder containing DICOM files, or a 
                patient or study to read all series in that patient or 
                study. In those cases a list is returned.
            attr (list, optional): list of DICOM attributes to read.
            dims (list, optional): Dimensions to sort the attributes. 
                If dims is not provided, values are sorted by 
                InstanceNumber.
            coords (bool): If set to True, the coordinates of the 
                attributes are returned alongside the values

        Returns:
            dict or tuple: values as a dictionary in the last 
                return value, where each value is a numpy array with 
                the required dimensions. If coords is set to True, 
                these are returned too.
        """
        if isinstance(series, str): # path to folder
            return [self.values(s, attr, dims, coords) for s in self.series(series)]
        if len(series) < 4: # folder, patient or study
            return [self.values(s, attr, dims, coords) for s in self.series(series)]

        if dims is None:
            dims = ['InstanceNumber']
        elif np.isscalar(dims):
            dims = [dims]
        else:
            dims = list(dims)

        files = register.files(self.register, series)

        # Ensure return_vals is a list
        if attr is None:
            # If attributes are not provided, read all 
            # attributes from the first file
            ds = dbdataset.read_dataset(files[0])
            exclude = ['PixelData', 'FloatPixelData', 'DoubleFloatPixelData']
            params = []
            param_labels = []
            for elem in ds:
                if elem.keyword not in exclude:
                    params.append(elem.tag)
                    # For known tags use the keyword as label
                    label = elem.tag if len(elem.keyword)==0 else elem.keyword
                    param_labels.append(label)
        elif np.isscalar(attr):
            params = [attr]
            param_labels = params[:]
        else:
            params = list(attr)
            param_labels = params[:]

        # Read dicom files
        coords_array = []
        values = np.empty(len(files), dtype=dict)
        for i, f in tqdm(enumerate(files), desc='Reading values..'):
            ds = dbdataset.read_dataset(f)  
            coords_array.append(dbdataset.get_values(ds, dims))
            # save as dict so numpy does not stack as arrays
            values[i] = {'values': dbdataset.get_values(ds, params)}

        # Format as mesh
        coords_array = np.stack([v for v in coords_array], axis=-1)
        coords_array, inds = dbdicom.utils.arrays.meshvals(coords_array)

        # Sort values accordingly
        values = values[inds].reshape(-1)

        # Return values as a dictionary
        values_dict = {}
        for p in range(len(params)):
            # Get the type from the first value
            vp0 = values[0]['values'][p]
            # Build an array of the right type
            vp = np.zeros(values.size, dtype=type(vp0))
            # Populate the arrate with values for parameter p
            for i, v in enumerate(values):
                vp[i] = v['values'][p]
            # Reshape values for parameter p
            vp = vp.reshape(coords_array.shape[1:])
            # Eneter in the dictionary
            values_dict[param_labels[p]] = vp

        # If only one, return as value
        if len(params) == 1:
            values_return = values_dict[params[0]]
        else:
            values_return = values_dict

        if coords:
            return values_return, coords_array
        else:
            return values_return
        

    def files(self, entity:list) -> list:
        """Read the files in a DICOM entity

        Args:
            entity (list or str): DICOM entity to read. This can 
                be a path to a folder containing DICOM files, or a 
                patient or study to read all series in that patient or 
                study. 

        Returns:
            list: list of valid dicom files.
        """
        if isinstance(entity, str): # path to folder
            files = []
            for s in self.series(entity):
                files += self.files(s)
            return files
        if len(entity) < 4: # folder, patient or study
            files = []
            for s in self.series(entity):
                files += self.files(s)
            return files

        return register.files(self.register, entity)

    
    
    def unique(self, pars:list, entity:list) -> dict:
        """Return a list of unique values for a DICOM entity

        Args:
            pars (list, str/tuple): attribute or attributes to return.
            entity (list): DICOM entity to search (Patient, Study or Series)

        Returns:
            dict: if a pars is a list, this returns a dictionary with 
            unique values for each attribute. If pars is a scalar 
            this returnes a list of values.
        """
        if not isinstance(pars, list):
            single=True
            pars = [pars]
        else:
            single=False

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
            try: 
                va.sort()
            except:
                pass
            values.append(va)

        if single:
            return values[0]
        else:
            return {p: values[i] for i, p in enumerate(pars)} 
    
    def copy(self, from_entity, to_entity):
        """Copy a DICOM  entity (patient, study or series)

        Args:
            from_entity (list): entity to copy
            to_entity (list): entity after copying.
        """
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
    
    def move(self, from_entity, to_entity):
        """Move a DICOM entity

        Args:
            entity (list): entity to move
        """
        self.copy(from_entity, to_entity)
        self.delete(from_entity)
        return self
    
    def split_series(self, series:list, attr:Union[str, tuple]) -> dict:
        """
        Split a series into multiple series
        
        Args:
            series (list): series to split.
            attr (str or tuple): dicom attribute to split the series by. 
        Returns:
            dict: dictionary with keys the unique values found (ascending) 
            and as values the series corresponding to that value.         
        """

        # Find all values of the attr and list files per value
        all_files = register.files(self.register, series)
        files = {}
        for f in tqdm(all_files, desc=f'Reading {attr}'):
            ds = dbdataset.read_dataset(f)
            v = dbdataset.get_values(ds, attr)
            if v in files:
                files[v].append(f)
            else:
                files[v] = [f]

        # Copy the files for each value (sorted) to new series
        values = sorted(list(files.keys()))
        split_series = {}
        for v in tqdm(values, desc='Writing new series'):
            series_desc = series[-1] if isinstance(series, str) else series[-1][0]
            series_v = series[:3] + [f'{series_desc}_{attr}_{v}']
            self._files_to_series(files[v], series_v)
            split_series[v] = series_v
        return split_series


    def _values(self, attributes:list, entity:list):
        # Create a np array v with values for each instance and attribute
        # if set(attributes) <= set(dbdatabase.COLUMNS):
        #     index = register.index(self.register, entity)
        #     v = self.register.loc[index, attributes].values
        # else:
        files = register.files(self.register, entity)
        v = np.empty((len(files), len(attributes)), dtype=object)
        for i, f in enumerate(files):
            ds = dbdataset.read_dataset(f)
            v[i,:] = dbdataset.get_values(ds, attributes)
        return v

    def _copy_patient(self, from_patient, to_patient):
        from_patient_studies = register.studies(self.register, from_patient)
        for from_study in tqdm(from_patient_studies, desc=f'Copying patient {from_patient[1:]}'):
            # Count the studies with the same description in the target patient
            study_desc = from_study[-1][0]
            if to_patient[0]==from_patient[0]:
                cnt = len(self.studies(to_patient, desc=study_desc))
            else:
                mgr = DataBaseDicom(to_patient[0])
                cnt = len(mgr.studies(to_patient, desc=study_desc))
                mgr.close()    
            # Ensure the copied studies end up in a separate study with the same description
            to_study = to_patient + [(study_desc, cnt)]         
            self._copy_study(from_study, to_study)

    def _copy_study(self, from_study, to_study):
        from_study_series = register.series(self.register, from_study)
        for from_series in tqdm(from_study_series, desc=f'Copying study {from_study[1:]}'):
            # Count the series with the same description in the target study
            series_desc = from_series[-1][0]
            if to_study[0]==from_study[0]:
                cnt = len(self.series(to_study, desc=series_desc))
            else:
                mgr = DataBaseDicom(to_study[0])
                cnt = len(mgr.series(to_study, desc=series_desc))
                mgr.close()
            # Ensure the copied series end up in a separate series with the same description
            to_series = to_study + [(series_desc, cnt)]
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
        attr = self._series_attributes(to_series)
        n = self._max_instance_number(attr['SeriesInstanceUID'])
        
        # Copy the files to the new series 
        for i, f in tqdm(enumerate(files), total=len(files), desc=f'Copying series {to_series[1:]}'):
            # Read dataset and assign new properties
            ds = dbdataset.read_dataset(f)
            self._write_dataset(ds, attr, n + 1 + i)

    def _max_study_id(self, patient_id):
        for pt in self.register:
            if pt['PatientID'] == patient_id:
                # Find the largest integer StudyID
                n = []
                for st in pt['studies']:
                    try:
                        n.append(int(st['StudyID']))
                    except:
                        pass
                if n == []:
                    return 0
                else:
                    return int(np.amax(n))
        return 0
    
    def _max_series_number(self, study_uid):
        for pt in self.register:
            for st in pt['studies']:
                if st['StudyInstanceUID'] == study_uid:
                    n = [sr['SeriesNumber'] for sr in st['series']]
                    return int(np.amax(n))
        return 0

    def _max_instance_number(self, series_uid):
        for pt in self.register:
            for st in pt['studies']:
                for sr in st['series']:
                    if sr['SeriesInstanceUID'] == series_uid:
                        n = list(sr['instances'].keys())
                        return int(np.amax([int(i) for i in n]))
        return 0

    # def _attributes(self, entity):
    #     if len(entity)==4:
    #         return self._series_attributes(entity)
    #     if len(entity)==3:
    #         return self._study_attributes(entity)
    #     if len(entity)==2:
    #         return self._patient_attributes(entity)       


    def _patient_attributes(self, patient):
        try:
            # If the patient exists and has files, read from file
            files = register.files(self.register, patient)
            attr = const.PATIENT_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except:
            # If the patient does not exist, generate values
            if patient in self.patients():
                raise ValueError(
                    f"Cannot create patient with id {patient[1]}."
                    f"The ID is already taken. Please provide a unique ID."
                )
            attr = ['PatientID', 'PatientName']
            vals = [patient[1], 'Anonymous']
        return {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}


    def _study_attributes(self, study):
        patient_attr = self._patient_attributes(study[:2])
        try:
            # If the study exists and has files, read from file
            files = register.files(self.register, study)
            attr = const.STUDY_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except register.AmbiguousError as e:
            raise register.AmbiguousError(e)
        except:
            # If the study does not exist or is empty, generate values
            if study[:-1] not in self.patients():
                study_id = 1
            else:
                study_id = 1 + self._max_study_id(study[-1])
            attr = ['StudyInstanceUID', 'StudyDescription', 'StudyID']
            study_uid = dbdataset.new_uid()
            study_desc = study[-1] if isinstance(study[-1], str) else study[-1][0]
            #study_date = datetime.today().strftime('%Y%m%d')
            vals = [study_uid, study_desc, str(study_id)]
        return patient_attr | {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}


    def _series_attributes(self, series):
        study_attr = self._study_attributes(series[:3])
        try:
            # If the series exists and has files, read from file
            files = register.files(self.register, series)
            attr = const.SERIES_MODULE
            ds = dbdataset.read_dataset(files[0])
            vals = dbdataset.get_values(ds, attr)
        except register.AmbiguousError as e:
            raise register.AmbiguousError(e)
        except:
            # If the series does not exist or is empty, generate values
            try:
                study_uid = register.study_uid(self.register, series[:-1])
            except:
                series_number = 1
            else:
                series_number = 1 + self._max_series_number(study_uid)
            attr = ['SeriesInstanceUID', 'SeriesDescription', 'SeriesNumber']
            series_uid = dbdataset.new_uid()
            series_desc = series[-1] if isinstance(series[-1], str) else series[-1][0]
            vals = [series_uid, series_desc, int(series_number)]
        return study_attr | {attr[i]:vals[i] for i in range(len(attr)) if vals[i] is not None}

        
    def _write_dataset(self, ds:Dataset, attr:dict, instance_nr:int):
        # Set new attributes 
        attr['SOPInstanceUID'] = dbdataset.new_uid()
        attr['InstanceNumber'] = str(instance_nr)
        dbdataset.set_values(ds, list(attr.keys()), list(attr.values()))
        # Save results in a new file
        rel_dir = os.path.join(
            f"Patient__{attr['PatientID']}", 
            f"Study__{attr['StudyID']}__{attr['StudyDescription']}", 
            f"Series__{attr['SeriesNumber']}__{attr['SeriesDescription']}",
        )
        os.makedirs(os.path.join(self.path, rel_dir), exist_ok=True)
        rel_path = os.path.join(rel_dir, dbdataset.new_uid() + '.dcm')
        dbdataset.write(ds, os.path.join(self.path, rel_path))
        # Add an entry in the register
        register.add_instance(self.register, attr, rel_path)



def infer_slice_spacing(vols):
    # In case spacing between slices is not (correctly) encoded in 
    # DICOM it can be inferred from the slice locations.

    shape = vols.shape
    vols = vols.reshape((shape[0], -1))
    slice_spacing = np.zeros(vols.shape[-1])

    for d in range(vols.shape[-1]):

        # For single slice volumes there is nothing to do
        if vols[:,d].shape[0]==1:
            continue

        # Get a normal slice vector from the first volume.
        mat = vols[0,d].affine[:3,:3]
        normal = mat[:,2]/np.linalg.norm(mat[:,2])

        # Get slice locations by projection on the normal.
        pos = [v.affine[:3,3] for v in vols[:,d]]
        slice_loc = [np.dot(p, normal) for p in pos]

        # Sort slice locations and take consecutive differences.
        slice_loc = np.sort(slice_loc)
        distances = slice_loc[1:] - slice_loc[:-1]

        # Round to 10 micrometer and check if unique
        distances = np.around(distances, 2)
        slice_spacing_d = np.unique(distances)

        # Check if unique - otherwise this is not a volume
        if len(slice_spacing_d) > 1:
            raise ValueError(
                'Cannot build a volume - spacings between slices are not unique.'
            )
        else:
            slice_spacing_d= slice_spacing_d[0]
        
        # Set correct slice spacing in all volumes
        for v in vols[:,d]:
            v.affine[:3,2] = normal * abs(slice_spacing_d)

        slice_spacing[d] = slice_spacing_d

    # Check slice_spacing is the same across dimensions
    slice_spacing = np.unique(slice_spacing)
    if len(slice_spacing) > 1:
        raise ValueError(
            'Cannot build a volume - spacings between slices are not unique.'
        )    

    return vols.reshape(shape)




