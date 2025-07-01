# Test data
# https://www.aliza-dicom-viewer.com/download/datasets

import os
from datetime import datetime
import struct
from tqdm import tqdm

import numpy as np
import pydicom
from pydicom.util.codify import code_file
import pydicom.config
import vreg


import dbdicom.utils.image as image
import dbdicom.utils.variables as variables
from dbdicom.sop_classes import (
    xray_angiographic_image,
    ct_image,
    mr_image,
    enhanced_mr_image,
    ultrasound_multiframe_image,
    parametric_map,
    segmentation,
)


# This ensures that dates and times are read as TM, DT and DA classes
pydicom.config.datetime_conversion = True


SOPCLASS = {
    '1.2.840.10008.5.1.4.1.1.4': 'MRImage',
    '1.2.840.10008.5.1.4.1.1.4.1': 'EnhancedMRImage',
    '1.2.840.10008.5.1.4.1.1.2': 'CTImage',
    '1.2.840.10008.5.1.4.1.1.12.2': 'XrayAngiographicImage',
    '1.2.840.10008.5.1.4.1.1.3.1': 'UltrasoundMultiFrameImage',
    '1.2.840.10008.5.1.4.1.1.30': 'ParametricMap',
    '1.2.840.10008.5.1.4.1.1.66.4': 'Segmentation',
}
SOPCLASSMODULE = {
    '1.2.840.10008.5.1.4.1.1.4': mr_image,
    '1.2.840.10008.5.1.4.1.1.4.1': enhanced_mr_image,
    '1.2.840.10008.5.1.4.1.1.2': ct_image,
    '1.2.840.10008.5.1.4.1.1.12.2': xray_angiographic_image,
    '1.2.840.10008.5.1.4.1.1.3.1': ultrasound_multiframe_image,
    '1.2.840.10008.5.1.4.1.1.30': parametric_map,
    '1.2.840.10008.5.1.4.1.1.66.4': segmentation,
}


def read_dataset(file):

    try:
        ds = pydicom.dcmread(file)
        # ds = pydicom.dcmread(file, force=True) # more robust but hides corrupted data
    except Exception:
        raise FileNotFoundError('File not found')
    
    return ds


def new_dataset(sop_class):

    if sop_class == 'MRImage':
        return mr_image.default()
    if sop_class == 'EnhancedMRImage':
        return enhanced_mr_image.default()
    if sop_class == 'CTImage':
        return ct_image.default()
    if sop_class == 'XrayAngiographicImage':
        return xray_angiographic_image.default()
    if sop_class == 'UltrasoundMultiFrameImage':
        return ultrasound_multiframe_image.default()
    if sop_class == 'ParametricMap':
        return parametric_map.default()
    else:
        raise ValueError(
            f"DICOM class {sop_class} is not currently supported"
        )



def get_values(ds, tags):
    """Return a list of values for a dataset"""

    # https://pydicom.github.io/pydicom/stable/guides/element_value_types.html
    if np.isscalar(tags): 
        return get_values(ds, [tags])[0]
            
    row = []  
    for tag in tags:
        value = None

        # If the tag is provided as string
        if isinstance(tag, str):
            if hasattr(ds, tag):
                pydcm_value = ds[tag].value
                try:
                    VR = pydicom.datadict.dictionary_VR(tag)
                except:
                    VR = None
                value = to_set_type(pydcm_value, VR) # ELIMINATE THIS STEP - return pydicom datatypes

        # If the tag is a tuple of hexadecimal values
        else: 
            if tag in ds:
                try:
                    VR = pydicom.datadict.dictionary_VR(tag)
                except:
                    VR = None
                value = to_set_type(ds[tag].value, VR)

        # If a tag is not present in the dataset, check if it can be derived
        if value is None:
            value = derive_data_element(ds, tag)

        row.append(value)
    return row


def set_values(ds, tags, values, VR=None, coords=None):

    if np.isscalar(tags): 
        tags = [tags]
        values = [values]
        VR = [VR]
    elif VR is None:
        VR = [None] * len(tags)

    if coords is not None:
        tags += list(coords.keys())
        values += list(coords.values())

    for i, tag in enumerate(tags):
                
        if values[i] is None:
            if isinstance(tag, str):
                if hasattr(ds, tag):
                    del ds[tag]
            else: # hexadecimal tuple
                if tag in ds:
                    del ds[tag]

        elif isinstance(tag, str):
            if hasattr(ds, tag):
                ds[tag].value = format_value(values[i], tag=tag)
            else:
                _add_new(ds, tag, values[i], VR=VR[i])

        else: # hexadecimal tuple
            if tag in ds:
                ds[tag].value = format_value(values[i], tag=tag)
            else:
                _add_new(ds, tag, values[i], VR=VR[i])

        #_set_derived_data_element(ds, tag, values[i])
                
    return ds



def value(ds, tags):
    # Same as get_values but without VR lookup

    # https://pydicom.github.io/pydicom/stable/guides/element_value_types.html
    if np.isscalar(tags): 
        return get_values(ds, [tags])[0]
            
    row = []  
    for tag in tags:
        value = None

        # If the tag is provided as string
        if isinstance(tag, str):

            if hasattr(ds, tag):
                value = to_set_type(ds[tag].value)

        # If the tag is a tuple of hexadecimal values
        else: 
            if tag in ds:
                value = to_set_type(ds[tag].value)

        # If a tag is not present in the dataset, check if it can be derived
        if value is None:
            value = derive_data_element(ds, tag)

        row.append(value)
    return row


def set_value(ds, tags, values):
    # Same as set_values but without VR lookup
    # This excludes new private tags - set those using add_private()
    if np.isscalar(tags): 
        tags = [tags]
        values = [values]

    for i, tag in enumerate(tags):
                
        if values[i] is None:
            if isinstance(tag, str):
                if hasattr(ds, tag):
                    del ds[tag]
            else: # hexadecimal tuple
                if tag in ds:
                    del ds[tag]

        elif isinstance(tag, str):
            if hasattr(ds, tag):
                ds[tag].value = check_value(values[i], tag)
            else:
                add_new(ds, tag, values[i])

        else: # hexadecimal tuple
            if tag in ds:
                ds[tag].value = check_value(values[i], tag)
            else:
                add_new(ds, tag, values[i])
                
    return ds



def write(ds, file, status=None):
    # check if directory exists and create it if not
    dir = os.path.dirname(file)
    if not os.path.exists(dir):
        os.makedirs(dir)
    #ds.save_as(file, write_like_original=False) # deprecated
    ds.save_as(file, enforce_file_format=True)


def codify(source_file, save_file, **kwargs):
    str = code_file(source_file, **kwargs)
    file = open(save_file, "w")
    file.write(str)
    file.close()


def read_data(files, tags, path=None, images_only=False): # obsolete??

    if np.isscalar(files):
        files = [files]
    if np.isscalar(tags):
        tags = [tags]
    dict = {}
    for i, file in tqdm(enumerate(files), 'reading files..'):
        try:
            ds = pydicom.dcmread(file, force=True, specific_tags=tags+['Rows'])
        except:
            pass
        else:
            if isinstance(ds, pydicom.dataset.FileDataset):
                if 'TransferSyntaxUID' in ds.file_meta:
                    if images_only:
                        if not 'Rows' in ds:
                            continue
                    row = get_values(ds, tags)
                    if path is None:
                        index = file
                    else:
                        index = os.path.relpath(file, path)
                    dict[index] = row 
    return dict




def _add_new(ds, tag, value, VR='OW'):
    if not isinstance(tag, pydicom.tag.BaseTag):
        tag = pydicom.tag.Tag(tag)
    if not tag.is_private: # Add a new data element
        value_repr = pydicom.datadict.dictionary_VR(tag)
        if value_repr == 'US or SS':
            if value >= 0:
                value_repr = 'US'
            else:
                value_repr = 'SS'
        elif value_repr == 'OB or OW':
            value_repr = 'OW'
        ds.add_new(tag, value_repr, format_value(value, value_repr))
    else:
        if (tag.group, 0x0010) not in ds:
            ds.private_block(tag.group, 'dbdicom ' + str(tag.group), create=True)
        ds.add_new(tag, VR, format_value(value, VR))


def add_new(ds, tag, value):
    if not isinstance(tag, pydicom.tag.BaseTag):
        tag = pydicom.tag.Tag(tag)
    if tag.is_private:
        raise ValueError("if you want to add a private data element, use "
                         "dataset.add_private()")
   # Add a new data element
    value_repr = pydicom.datadict.dictionary_VR(tag)
    if value_repr == 'US or SS':
        if value >= 0:
            value_repr = 'US'
        else:
            value_repr = 'SS'
    elif value_repr == 'OB or OW':
        value_repr = 'OW'
    ds.add_new(tag, value_repr, format_value(value, value_repr))



def add_private(ds, tag, value, VR):
    if not isinstance(tag, pydicom.tag.BaseTag):
        tag = pydicom.tag.Tag(tag)
    if (tag.group, 0x0010) not in ds:
        ds.private_block(tag.group, 'dbdicom ' + str(tag.group), create=True)
    ds.add_new(tag, VR, format_value(value, VR))


def derive_data_element(ds, tag):
    """Tags that are not required but can be derived from other required tags"""

    if tag == 'SliceLocation' or tag == (0x0020, 0x1041):
        if 'ImageOrientationPatient' in ds and 'ImagePositionPatient' in ds:
            return image.slice_location(
                ds['ImageOrientationPatient'].value, 
                ds['ImagePositionPatient'].value,
            )
    # To be extended ad hoc with other tags that can be derived



def format_value(value, VR=None, tag=None):

    # If the change below is made (TM, DA, DT) then this needs to 
    # convert those to string before setting

    # Slow - dictionary lookup for every value write

    if VR is None:
        VR = pydicom.datadict.dictionary_VR(tag)

    if VR == 'LO':
        if len(value) > 64:
            return value[-64:]
            #return value[:64]
    if VR == 'TM':
        return variables.seconds_to_str(value)
    
    return value


def check_value(value, tag):

    # If the change below is made (TM, DA, DT) then this needs to 
    # convert those to string before setting

    LO = [
        'SeriesDescription',
        'StudyDescription',
    ]
    TM = [
        'AcquisitionTime',
    ]

    if tag in LO:
        if len(value) > 64:
            return value[-64:]
    if tag in TM:
        return variables.seconds_to_str(value)
    
    return value


def to_set_type(value, VR=None):
    """
    Convert pydicom datatypes to the python datatypes used to set the parameter.
    """
    # Not a good idea to modify pydicom set/get values. confusing and requires extra VR lookups

    if VR == 'TM':
        # pydicom sometimes returns string values for TM data types
        if isinstance(value, str):
            return variables.str_to_seconds(value)

    if value.__class__.__name__ == 'MultiValue':
        return [to_set_type(v, VR) for v in value]
    if value.__class__.__name__ == 'PersonName':
        return str(value)
    if value.__class__.__name__ == 'Sequence':
        return [ds for ds in value]
    if value.__class__.__name__ == 'TM': 
        return variables.time_to_seconds(value) # return datetime.time
    if value.__class__.__name__ == 'UID': 
        return str(value) 
    if value.__class__.__name__ == 'IS': 
        return int(value)
    if value.__class__.__name__ == 'DT': 
        return variables.datetime_to_str(value) # return datetime.datetime
    if value.__class__.__name__ == 'DA':  # return datetime.date
        return variables.date_to_str(value)
    if value.__class__.__name__ == 'DSfloat': 
        return float(value)
    if value.__class__.__name__ == 'DSdecimal': 
        return int(value)
    
    return value


def new_uid(n=None):
    
    if n is None:
        return pydicom.uid.generate_uid()
    else:
        return [pydicom.uid.generate_uid() for _ in range(n)]




def window(ds):
    """Centre and width of the pixel data after applying rescale slope and intercept"""

    if 'WindowCenter' in ds: 
        centre = ds.WindowCenter
    if 'WindowWidth' in ds: 
        width = ds.WindowWidth
    if centre is None or width is None:
        array = pixel_data(ds)
        #p = np.percentile(array, [25, 50, 75])
        min = np.min(array)
        max = np.max(array)
    if centre is None: 
        centre = (max+min)/2
        #centre = p[1]
    if width is None: 
        width = 0.9*(max-min)
        #width = p[2] - p[0]
    return centre, width

def set_window(ds, center, width):
    ds.WindowCenter = center
    ds.WindowWidth = width

# List of all supported (matplotlib) colormaps

COLORMAPS =  ['cividis',  'magma', 'plasma', 'viridis', 
    'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
    'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
    'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
    'binary', 'gist_yarg', 'gist_gray', 'bone', 'pink',
    'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
    'hot', 'afmhot', 'gist_heat', 'copper',
    'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
    'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic',
    'twilight', 'twilight_shifted', 'hsv',
    'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
    'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg', 'turbo',
    'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar']

# Include support for DICOM natiove colormaps (see pydicom guide on working with pixel data)


def lut(ds):
    """Return RGB as float with values in [0,1]"""

    if 'PhotometricInterpretation' not in ds:
        return None
    if ds.PhotometricInterpretation != 'PALETTE COLOR':
        return None

    if ds.BitsAllocated == 8:
        dtype = np.ubyte
    elif ds.BitsAllocated == 16:
        dtype = np.uint16
    
    R = ds.RedPaletteColorLookupTableData
    G = ds.GreenPaletteColorLookupTableData
    B = ds.BluePaletteColorLookupTableData

    R = np.frombuffer(R, dtype=dtype)
    G = np.frombuffer(G, dtype=dtype)
    B = np.frombuffer(B, dtype=dtype)

    R = R.astype(np.float32)
    G = G.astype(np.float32)
    B = B.astype(np.float32)

    R *= 1.0/(np.power(2, ds.RedPaletteColorLookupTableDescriptor[2]) - 1)
    G *= 1.0/(np.power(2, ds.GreenPaletteColorLookupTableDescriptor[2]) - 1)
    B *= 1.0/(np.power(2, ds.BluePaletteColorLookupTableDescriptor[2]) - 1)
    
    return np.transpose([R, G, B])


def set_lut(ds, RGB):
    """Set RGB as float with values in range [0,1]"""

    ds.PhotometricInterpretation = 'PALETTE COLOR'

    RGB *= (np.power(2, ds.BitsAllocated) - 1)

    if ds.BitsAllocated == 8:
        RGB = RGB.astype(np.ubyte)
    elif ds.BitsAllocated == 16:
        RGB = RGB.astype(np.uint16)

    # Define the properties of the LUT
    ds.add_new('0x00281101', 'US', [255, 0, ds.BitsAllocated])
    ds.add_new('0x00281102', 'US', [255, 0, ds.BitsAllocated])
    ds.add_new('0x00281103', 'US', [255, 0, ds.BitsAllocated])

    # Scale the colorsList to the available range
    ds.RedPaletteColorLookupTableData = bytes(RGB[:,0])
    ds.GreenPaletteColorLookupTableData = bytes(RGB[:,1])
    ds.BluePaletteColorLookupTableData = bytes(RGB[:,2])



def affine(ds):
    # Spacing Between Slices is not required so can be absent
    slice_spacing = ds.get("SpacingBetweenSlices")
    if slice_spacing is None:
        slice_spacing = ds.get("SliceThickness")
    return image.affine_matrix(
        get_values(ds, 'ImageOrientationPatient'), 
        get_values(ds, 'ImagePositionPatient'), 
        get_values(ds, 'PixelSpacing'), 
        slice_spacing, 
    )

def set_affine(ds, affine):
    if affine is None:
        raise ValueError('The affine cannot be set to an empty value')
    v = image.dismantle_affine_matrix(affine)
    set_values(ds, 'PixelSpacing', v['PixelSpacing'])
    set_values(ds, 'SpacingBetweenSlices', v['SpacingBetweenSlices'])
    set_values(ds, 'ImageOrientationPatient', v['ImageOrientationPatient'])
    set_values(ds, 'ImagePositionPatient', v['ImagePositionPatient'])
    set_values(ds, 'SliceLocation', np.dot(v['ImagePositionPatient'], v['slice_cosine']))



def pixel_data(ds):

    try:
        mod = SOPCLASSMODULE[ds.SOPClassUID]
    except KeyError:
        raise ValueError(
            f"DICOM class {ds.SOPClassUID} is not currently supported."
        )
    if hasattr(mod, 'pixel_data'):
        return getattr(mod, 'pixel_data')(ds)
    
    try:
        array = ds.pixel_array
    except:
        raise ValueError("Dataset has no pixel data.")
    array = array.astype(np.float32)
    slope = float(getattr(ds, 'RescaleSlope', 1)) 
    intercept = float(getattr(ds, 'RescaleIntercept', 0)) 
    array *= slope
    array += intercept
    return np.transpose(array)


def set_pixel_data(ds, array):
    if array is None:
        raise ValueError('The pixel array cannot be set to an empty value.')
    
    try:
        mod = SOPCLASSMODULE[ds.SOPClassUID]
    except KeyError:
        raise ValueError(
            f"DICOM class {ds.SOPClassUID} is not currently supported."
        )
    if hasattr(mod, 'set_pixel_data'):
        return getattr(mod, 'set_pixel_data')(ds, array)
    
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15

    if array.dtype==np.int16:
        array = image.clip(array) # remove nan and infs
        ds.PixelRepresentation = 1
        ds.RescaleSlope = 1
        ds.RescaleIntercept = 0
    elif array.dtype==np.uint16:
        array = image.clip(array) # remove nan and infs
        ds.PixelRepresentation = 0
        ds.RescaleSlope = 1
        ds.RescaleIntercept = 0
    else:
        array = image.clip(array) # remove nan and infs
        array, slope, intercept = image.scale_to_range(array, ds.BitsStored)
        ds.PixelRepresentation = 0
        ds.RescaleSlope = 1 / slope
        ds.RescaleIntercept = - intercept / slope

    array = np.transpose(array)
    ds.Rows = array.shape[0]
    ds.Columns = array.shape[1]
    ds.PixelData = array.tobytes()
    
#     # if array.ndim >= 3: # remove spurious dimensions of 1
#     #     array = np.squeeze(array) 

#     array = image.clip(array.astype(np.float32))
#     array, slope, intercept = image.scale_to_range(array, ds.BitsAllocated)
#     array = np.transpose(array)

#     ds.PixelRepresentation = 0
#     #ds.SmallestImagePixelValue = int(0)
#     #ds.LargestImagePixelValue = int(2**ds.BitsAllocated - 1)
#     #ds.set_values('SmallestImagePixelValue', int(0))
#     #ds.set_values('LargestImagePixelValue', int(2**ds.BitsAllocated - 1))
#     ds.RescaleSlope = 1 / slope
#     ds.RescaleIntercept = - intercept / slope
# #        ds.WindowCenter = (maximum + minimum) / 2
# #        ds.WindowWidth = maximum - minimum
#     ds.Rows = array.shape[0]
#     ds.Columns = array.shape[1]
#     ds.PixelData = array.tobytes()


def volume(ds):
    return vreg.volume(pixel_data(ds), affine(ds))

def set_volume(ds, volume:vreg.Volume3D):
    if volume is None:
        raise ValueError('The volume cannot be set to an empty value.')
    try:
        mod = SOPCLASSMODULE[ds.SOPClassUID]
    except KeyError:
        raise ValueError(
            f"DICOM class {ds.SOPClassUID} is not currently supported."
        )
    if hasattr(mod, 'set_volume'):
        return getattr(mod, 'set_volume')(ds, volume)
    
    image = np.squeeze(volume.values)
    if image.ndim != 2:
        raise ValueError("Can only write 2D images to a dataset.")
    set_pixel_data(ds, image)
    set_affine(ds, volume.affine)
    if volume.coords is not None:
        # All other dimensions should have size 1
        coords = volume.coords.reshape((volume.coords.shape[0], -1))
        for i, d in enumerate(volume.dims):
            try:
                set_values(ds, d, coords[i,0])
            except KeyError:
                raise ValueError(
                    "Cannot write volume to DICOM. "
                    f"Volume dimension {d} is not a recognized DICOM data-element. "
                    f"Use Volume3D.set_dims() with proper DICOM keywords "
                    "or (group, element) tags to change the dimensions."
                )


def image_type(ds):
    """Determine if an image is Magnitude, Phase, Real or Imaginary image or None"""

    if (0x0043, 0x102f) in ds:
        private_ge = ds[0x0043, 0x102f]
        try: 
            value = struct.unpack('h', private_ge.value)[0]
        except: 
            value = private_ge.value
        if value == 0: 
            return 'MAGNITUDE'
        if value == 1: 
            return 'PHASE'
        if value == 2: 
            return 'REAL'
        if value == 3: 
            return 'IMAGINARY'

    if 'ImageType' in ds:
        type = set(ds.ImageType)
        if set(['M', 'MAGNITUDE']).intersection(type):
            return 'MAGNITUDE'
        if set(['P', 'PHASE']).intersection(type):
            return 'PHASE'
        if set(['R', 'REAL']).intersection(type):
            return 'REAL'
        if set(['I', 'IMAGINARY']).intersection(type):
            return 'IMAGINARY'

    if 'ComplexImageComponent' in ds:
        return ds.ComplexImageComponent

    return 'UNKNOWN'


def set_image_type(ds, value):
    ds.ImageType = value


def signal_type(ds):
    """Determine if an image is Water, Fat, In-Phase, Out-phase image or None"""

    if hasattr(ds, 'ImageType'):
        type = set(ds.ImageType)
        if set(['W', 'WATER']).intersection(type):
            return 'WATER'
        elif set(['F', 'FAT']).intersection(type):
            return 'FAT'
        elif set(['IP', 'IN_PHASE']).intersection(type):
            return 'IN_PHASE'
        elif set(['OP', 'OUT_PHASE']).intersection(type):
            return 'OP_PHASE'
    return 'UNKNOWN'


def set_signal_type(ds, value):
    ds.ImageType = value



if __name__=='__main__':

    pass
    #codify('C:\\Users\\md1spsx\\Documents\\f32bit.dcm', 'C:\\Users\\md1spsx\\Documents\\f32bit.py')