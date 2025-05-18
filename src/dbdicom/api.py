
import numpy as np
import vreg

from dbdicom.dbd import DataBaseDicom


def open(path:str) -> DataBaseDicom:
    return DataBaseDicom(path)

def summary(path):
    dbd = open(path)
    return dbd.summary()

def print(path):
    dbd = open(path)
    dbd.print()

def patients(path, name=None, contains=None, isin=None):
    dbd = open(path)
    return dbd.patients(name, contains, isin)

def studies(entity, name=None, contains=None, isin=None):
    if isinstance(entity, str): # path = folder
        dbd = open(entity)
        return dbd.studies(entity, name, contains, isin)
    elif len(entity)==2: # path = patient
        dbd = open(entity[0])
        return dbd.studies(entity, name, contains, isin)
    else:
        raise ValueError(
            "The path must be a folder or a 2-element list "
            "with a folder and a patient name."
        )

def series(entity, name=None, contains=None, isin=None): 
    if isinstance(entity, str): # path = folder
        dbd = open(entity)
        return dbd.series(entity, name, contains, isin)
    elif len(entity) in [2,3]:
        dbd = open(entity[0])
        return dbd.series(entity, name, contains, isin)
    else:
        raise ValueError(
            "To retrieve a series, the entity must be a database, patient or study."
        )
    
def copy(from_entity, to_entity):
    dbd = open(from_entity[0])
    dbd.copy(from_entity, to_entity)
    dbd.close()

def delete(entity):
    dbd = open(entity[0])
    dbd.delete(entity)
    dbd.close()

def move(entity):
    dbd = open(entity[0])
    dbd.move(entity)
    dbd.close()

def volume(series:list, dims:list=None, multislice=False) -> vreg.Volume3D:
    dbd = open(series[0])
    return dbd.volume(series, dims, multislice)

def write_volume(vol:vreg.Volume3D, series:list, ref:list=None, 
                 multislice=False):
    dbd = open(series[0])
    dbd.write_volume(vol, series, ref, multislice)
    dbd.close()

def to_nifti(series:list, file:str, dims=None, multislice=False):
    dbd = open(series[0])
    dbd.to_nifti(series, file, dims, multislice)

def from_nifti(file:str, series:list, ref:list=None, multislice=False):
    dbd = open(series[0])
    dbd.from_nifti(file, series, ref, multislice)
    dbd.close()

def pixel_data(series:list, dims:list=None, include=None) -> np.ndarray:
    dbd = open(series[0])
    return dbd.pixel_data(series, dims, include)

# write_pixel_data()
# values()
# write_values()
# to_png(series, folder, dims)
# to_npy(series, folder, dims)
# split(series, attribute)
# extract(series, *kwargs) # subseries

# zeros(series, shape, dims)

def unique(pars:list, obj:list) -> dict:
    dbd = open(obj[0])
    return dbd.unique(pars, obj)






if __name__=='__main__':

    pass