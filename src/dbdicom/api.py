
import numpy as np
import vreg

from dbdicom.dbd import DataBaseDicom


def open(path:str) -> DataBaseDicom:
    """Open a DICOM database

    Args:
        path (str): path to the DICOM folder

    Returns:
        DataBaseDicom: database instance.
    """
    return DataBaseDicom(path)

def print(path):
    """Print the contents of the DICOM folder

    Args:
        path (str): path to the DICOM folder
    """
    dbd = open(path)
    dbd.print()
    dbd.close()


def summary(path) -> dict:
    """Return a summary of the contents of the database.

    Args:
        path (str): path to the DICOM folder

    Returns:
        dict: Nested dictionary with summary information on the database.
    """
    dbd = open(path)
    s = dbd.summary()
    dbd.close()
    return s


def patients(path, name:str=None, contains:str=None, isin:list=None)->list:
    """Return a list of patients in the DICOM folder.

    Args:
        path (str): path to the DICOM folder
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
    dbd = open(path)
    p = dbd.patients(name, contains, isin)
    dbd.close()
    return p


def studies(entity:str | list, name:str=None, contains:str=None, isin:list=None)->list:
    """Return a list of studies in the DICOM folder.

    Args:
        entity (str or list): path to a DICOM folder (to search in 
            the whole folder), or a two-element list identifying a 
            patient (to search studies of a given patient).
        name (str, optional): value of StudyDescription, to search for 
            studies with a given description. Defaults to None.
        contains (str, optional): substring of StudyDescription, to 
            search for studies based on part of their description. 
            Defaults to None.
        isin (list, optional): List of StudyDescription values, to search 
            for studies whose description is in a list. Defaults to None.

    Returns:
        list: list of studies fulfilling the criteria.
    """
    if isinstance(entity, str): # path = folder
        dbd = open(entity)
        s = dbd.studies(entity, name, contains, isin)
        dbd.close()
        return s
    elif len(entity)==2: # path = patient
        dbd = open(entity[0])
        s = dbd.studies(entity, name, contains, isin)
        dbd.close()
        return s
    else:
        raise ValueError(
            "The path must be a folder or a 2-element list "
            "with a folder and a patient name."
        )

def series(entity:str | list, name:str=None, contains:str=None, isin:list=None)->list:
    """Return a list of series in the DICOM folder.

    Args:
        entity (str or list): path to a DICOM folder (to search in 
            the whole folder), or a list identifying a 
            patient or a study (to search series of a given patient 
            or study).
        name (str, optional): value of SeriesDescription, to search for 
            series with a given description. Defaults to None.
        contains (str, optional): substring of SeriesDescription, to 
            search for series based on part of their description. 
            Defaults to None.
        isin (list, optional): List of SeriesDescription values, to search 
            for series whose description is in a list. Defaults to None.

    Returns:
        list: list of series fulfilling the criteria.
    """
    if isinstance(entity, str): # path = folder
        dbd = open(entity)
        s = dbd.series(entity, name, contains, isin)
        dbd.close()
        return s
    elif len(entity) in [2,3]:
        dbd = open(entity[0])
        s = dbd.series(entity, name, contains, isin)
        dbd.close()
        return s
    else:
        raise ValueError(
            "To retrieve a series, the entity must be a database, patient or study."
        )
    
def copy(from_entity:list, to_entity:list):
    """Copy a DICOM entity (patient, study or series)

    Args:
        from_entity (list): entity to copy
        to_entity (list): entity after copying.
    """
    dbd = open(from_entity[0])
    dbd.copy(from_entity, to_entity)
    dbd.close()


def delete(entity:list):
    """Delete a DICOM entity

    Args:
        entity (list): entity to delete
    """
    dbd = open(entity[0])
    dbd.delete(entity)
    dbd.close()


def move(from_entity:list, to_entity:list):
    """Move a DICOM entity

    Args:
        entity (list): entity to move
    """
    dbd = open(from_entity[0])
    dbd.copy(from_entity, to_entity)
    dbd.delete(from_entity)
    dbd.close()


def volume(series:list, dims:list=None, multislice=False) -> vreg.Volume3D:
    """Read a vreg.Volume3D from a DICOM series

    Args:
        series (list): DICOM series to read
        dims (list, optional): Non-spatial dimensions of the volume. Defaults to None.
        multislice (bool, optional): Whether the data are to be read 
            as multislice or not. In multislice data the voxel size 
            is taken from the slice gap rather thsan the slice thickness. Defaults to False.

    Returns:
        vreg.Volume3D: vole read from the series.
    """
    dbd = open(series[0])
    vol = dbd.volume(series, dims, multislice)
    dbd.close()
    return vol

def write_volume(vol:vreg.Volume3D, series:list, ref:list=None, 
                 multislice=False):
    """Write a vreg.Volume3D to a DICOM series

    Args:
        vol (vreg.Volume3D): Volume to write to the series.
        series (list): DICOM series to read
        dims (list, optional): Non-spatial dimensions of the volume. Defaults to None.
        multislice (bool, optional): Whether the data are to be read 
            as multislice or not. In multislice data the voxel size 
            is taken from the slice gap rather thsan the slice thickness. Defaults to False.
    """
    dbd = open(series[0])
    dbd.write_volume(vol, series, ref, multislice)
    dbd.close()

def to_nifti(series:list, file:str, dims:list=None, multislice=False):
    """Save a DICOM series in nifti format.

    Args:
        series (list): DICOM series to read
        file (str): file path of the nifti file.
        dims (list, optional): Non-spatial dimensions of the volume. 
            Defaults to None.
        multislice (bool, optional): Whether the data are to be read 
            as multislice or not. In multislice data the voxel size 
            is taken from the slice gap rather thaan the slice thickness. Defaults to False.
    """
    dbd = open(series[0])
    dbd.to_nifti(series, file, dims, multislice)
    dbd.close()

def from_nifti(file:str, series:list, ref:list=None, multislice=False):
    """Create a DICOM series from a nifti file.

    Args:
        file (str): file path of the nifti file.
        series (list): DICOM series to create
        ref (list): DICOM series to use as template.
        multislice (bool, optional): Whether the data are to be written
            as multislice or not. In multislice data the voxel size 
            is written in the slice gap rather thaan the slice thickness. Defaults to False.
    """
    dbd = open(series[0])
    dbd.from_nifti(file, series, ref, multislice)
    dbd.close()

def pixel_data(series:list, dims:list=None, include:list=None) -> tuple:
    """Read the pixel data from a DICOM series

    Args:
        series (list): DICOM series to read
        dims (list, optional): Dimensions of the array.
        include (list, optional): list of DICOM attributes that are 
            read on the fly to avoid reading the data twice.

    Returns:
        tuple: numpy array with pixel values and an array with 
            coordinates of the slices according to dims. If include 
            is provide these are returned as a dictionary in a third 
            return value.
    """
    dbd = open(series[0])
    array = dbd.pixel_data(series, dims, include)
    dbd.close()
    return array

# write_pixel_data()
# values()
# write_values()
# to_png(series, folder, dims)
# to_npy(series, folder, dims)
# split(series, attribute)
# extract(series, *kwargs) # subseries

# zeros(series, shape, dims)

def unique(pars:list, entity:list) -> dict:
    """Return a list of unique values for a DICOM entity

    Args:
        pars (list): attributes to return.
        entity (list): DICOM entity to search (Patient, Study or Series)

    Returns:
        dict: dictionary with unique values for each attribute.
    """
    dbd = open(entity[0])
    u = dbd.unique(pars, entity)
    dbd.close()
    return u






if __name__=='__main__':

    pass