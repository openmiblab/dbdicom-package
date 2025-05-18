# Importing annotations to handle or sign in import type hints
from __future__ import annotations

import timeit
import os
import numpy as np
import nibabel as nib
import pandas as pd
import matplotlib.pyplot as plt
import vreg


from dbdicom.record import Record
from dbdicom.ds.create import new_dataset
import dbdicom.utils.image as image


class Instance(Record):

    name = 'SOPInstanceUID'

    def keys(self):
        return [self.key()]

    def parent(self):
        #uid = self.manager.register.at[self.key(), 'SeriesInstanceUID']
        uid = self.manager._at(self.key(), 'SeriesInstanceUID')
        return self.record('Series', uid, key=self.key())

    def children(self, **kwargs):
        return

    def new_child(self, **kwargs): 
        return

    def _copy_from(self, record, **kwargs):
        return

    def copy_to_series(self, series):
        uid = self.manager.copy_instance_to_series(self.key(), series.keys(), series)
        return self.record('Instance', uid)

    def read_dataset(self):
        # More intuitive alias as this is reading into memory
        return self.get_dataset()
    
    def write_dataset(self, dataset):
        in_memory = self.key() in self.manager.dataset
        self.set_dataset(dataset)
        # This bit added ad-hoc because set_dataset() places the datset in memory
        # So if the instance is not in memory, it needs to be written and removed again
        if not in_memory:
            self.clear()    
        
    def set_dataset(self, dataset): 
        self._key = self.manager.set_instance_dataset(self.uid, dataset, self.key())


    # def map_to(self, target):
    #     return map_to(self, target)

    # def map_mask_to(self, target):
    #     return map_mask_to(self, target)


    def export_as_png(self, path, center=None, width=None, colormap=None):
        # Export image in png format.
        if center is None or width is None:
            c, w = self.window
        if center is None:
            center = c
        if width is None:
            width = w
        if colormap is None:
            colormap = self.colormap
        if colormap is None:
            colormap = 'gray'

        vmin = center - width/2
        vmax = center + width/2
        array = np.transpose(self.pixel_values())
        plt.imshow(array, cmap=colormap, vmin=vmin, vmax=vmax)
        cBar = plt.colorbar()
        cBar.minorticks_on()
        filename = self.label()
        filename = os.path.join(path, filename + '.png')
        plt.savefig(fname=filename)
        plt.close()


    def export_as_csv(self, path):
        # Export 2D pixel Array in csv format
        table = np.transpose(self.pixel_values())
        cols = ['Column' + str(x) for x in range(table.shape[0])]
        rows = ['Row' + str(y) for y in range(table.shape[1])]
        filepath = self.label()
        filepath = os.path.join(path, filepath + '.csv')
        df = pd.DataFrame(table, index=rows, columns=cols)
        df.to_csv(filepath)


    # def export_as_nifti(self, path, affine=None):
    #     # Export series as a single Nifty file
    #     ds = self.get_dataset()
    #     if affine is None:
    #         affine = ds.get_values('affine_matrix')
    #     array = self.pixel_values()
    #     dicomHeader = nib.nifti1.Nifti1DicomExtension(2, ds)
    #     niftiObj = nib.Nifti1Image(array, image.affine_to_RAH(affine))
    #     niftiObj.header.extensions.append(dicomHeader)
    #     filepath = self.label()
    #     filepath = os.path.join(path, filepath + '.nii')
    #     nib.save(niftiObj, filepath)


    def export_as_npy(self, path):
        # Export instance as a single NPY file
        array = self.pixel_values()
        filepath = self.label()
        filepath = os.path.join(path, filepath + '.npy')
        with open(filepath, 'wb') as f:
            np.save(f, array)


    def BGRA_array(self):
        return image.BGRA(
            self.pixel_values(),
            self.lut, 
            width = self.WindowWidth,
            center = self.WindowCenter,
        )
    

    def affine(self):
        ds = self.read_dataset()
        return ds.get_values('affine')
        # return image.affine_matrix(self.ImageOrientationPatient, 
        #                            self.ImagePositionPatient, 
        #                            self.PixelSpacing, 
        #                            self.SliceThickness)
    
    def set_affine(self, affine):
        ds = self.read_dataset()
        ds.set_values('affine', affine)
        self.write_dataset(ds)
        # p = image.dismantle_affine_matrix(affine)
        # self.read()
        # #self.SpacingBetweenSlices = p['SpacingBetweenSlices']
        # self.PixelSpacing = p['PixelSpacing']
        # self.SliceThickness = p['SliceThickness']
        # self.ImageOrientationPatient = p['ImageOrientationPatient']
        # self.ImagePositionPatient = p['ImagePositionPatient']
        # self.SliceLocation = np.dot(p['ImagePositionPatient'], p['slice_cosine'])
        # self.clear()

    def pixel_values(self, **kwargs):
        return pixel_values(self, **kwargs)

    def set_pixel_values(self, array):
        set_pixel_values(self, array)  

    def volume(self):
        ds = self.read_dataset()
        v = ds.get_values(['pixel_values', 'affine'])
        return vreg.volume(v[0], v[1])
    
    def set_volume(self, vol:vreg.Volume3D):
        ds = self.read_dataset()
        #ds.set_volume(vol)
        ds.set_values('volume', vol)
        self.write_dataset(ds)
        # self.set_pixel_values(np.squeeze(volume.values))
        # self.set_affine(volume.affine)


    # OBSOLETE API
    


    def array(self):  # replace by pixel_values
        return pixel_values(self)

    def get_pixel_array(self):  # replace by pixel_values
        return pixel_values(self)

    def set_array(self, array): # replace by set_pixel_values
        set_pixel_values(self, array)

    def set_pixel_array(self, array): # replace by set_pixel_values
        set_pixel_values(self, array)      



def pixel_values(frame:Instance, return_vals=()): 
    ds = frame.read_dataset()  
    if ds is None:
        # TODO: Raise an error instead
        if return_vals == ():
            return None
        else:
            return None, None
    attributes = list(return_vals) + ['pixel_values']
    v = ds.get_values(attributes)
    if return_vals == ():
        return v[-1]
    else:
        values = {tag: v[i]for i, tag in enumerate(return_vals)}
        return v[-1], values
    
    
def set_pixel_values(frame:Instance, array): 
    ds = frame.read_dataset()
    if ds is None:
        ds = new_dataset('MRImage')
    #ds.set_pixel_values(array)
    ds.set_values('pixel_values', array)
    frame.write_dataset(ds)
  







