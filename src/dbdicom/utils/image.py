
import numpy as np



def affine_matrix(      # single slice function
    image_orientation,  # ImageOrientationPatient
    image_position,     # ImagePositionPatient
    pixel_spacing,      # PixelSpacing
    slice_spacing):     # SpacingBetweenSlices

    row_spacing = pixel_spacing[0]
    column_spacing = pixel_spacing[1]
    
    row_cosine = np.array(image_orientation[:3])
    column_cosine = np.array(image_orientation[3:])
    slice_cosine = np.cross(row_cosine, column_cosine)

    affine = np.identity(4, dtype=np.float32)
    affine[:3, 0] = row_cosine * column_spacing
    affine[:3, 1] = column_cosine * row_spacing
    affine[:3, 2] = slice_cosine * slice_spacing
    affine[:3, 3] = image_position
    
    return affine 


def slice_location( 
        image_orientation:list,  # ImageOrientationPatient
        image_position:list,    # ImagePositionPatient
    ) -> float:
    """Calculate Slice Location"""

    row_cosine = np.array(image_orientation[:3])    
    column_cosine = np.array(image_orientation[3:]) 
    slice_cosine = np.cross(row_cosine, column_cosine)

    # # The coronal orientation has a left-handed reference frame
    # if np.array_equal(np.around(image_orientation, 3), [1,0,0,0,0,-1]):
    #     slice_cosine = -slice_cosine

    return np.dot(np.array(image_position), slice_cosine)


def dismantle_affine_matrix(affine):
    # Note: nr of slices can not be retrieved from affine_matrix
    # Note: slice_cosine is not a DICOM keyword but can be used 
    # to work out the ImagePositionPatient of any other slice i as
    # ImagePositionPatient_i = ImagePositionPatient + i * SpacingBetweenSlices * slice_cosine
    column_spacing = np.linalg.norm(affine[:3, 0])
    row_spacing = np.linalg.norm(affine[:3, 1])
    slice_spacing = np.linalg.norm(affine[:3, 2])
    row_cosine = affine[:3, 0] / column_spacing
    column_cosine = affine[:3, 1] / row_spacing
    slice_cosine = affine[:3, 2] / slice_spacing
    return {
        'PixelSpacing': [row_spacing, column_spacing], 
        'SpacingBetweenSlices': slice_spacing,  
        'ImageOrientationPatient': row_cosine.tolist() + column_cosine.tolist(), 
        'ImagePositionPatient': affine[:3, 3].tolist(), # first slice for a volume
        'slice_cosine': slice_cosine.tolist()} 


    

def clip(array, value_range = None):

    array[np.isnan(array)] = 0
    if value_range is None:
        finite = array[np.isfinite(array)]
        value_range = [np.amin(finite), np.amax(finite)]
    return np.clip(array, value_range[0], value_range[1])
    

def scale_to_range(array, bits_allocated, signed=False):
        
    range = 2.0**bits_allocated - 1
    if signed:
        minval = -2.0**(bits_allocated-1)
    else:
        minval = 0
    maximum = np.amax(array)
    minimum = np.amin(array)
    if maximum == minimum:
        slope = 1
    else:
        slope = range / (maximum - minimum)
    intercept = -slope * minimum + minval
    array = array * slope
    array = array + intercept

    if bits_allocated == 8:
        if signed:
            return array.astype(np.int8), slope, intercept
        else:
            return array.astype(np.uint8), slope, intercept
    if bits_allocated == 16:
        if signed:
            return array.astype(np.int16), slope, intercept
        else:
            return array.astype(np.uint16), slope, intercept
    if bits_allocated == 32:
        if signed:
            return array.astype(np.int32), slope, intercept
        else:
            return array.astype(np.uint32), slope, intercept
    if bits_allocated == 64:
        if signed:
            return array.astype(np.int64), slope, intercept
        else:
            return array.astype(np.uint64), slope, intercept

