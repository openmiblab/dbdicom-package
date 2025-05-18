import math
import numpy as np
from scipy.interpolate import interpn
from scipy.ndimage import affine_transform


def as_mosaic(array, rows=None):
    """Reformat a 3D array (x,y,z) into a 2D mosaic"""

    nz = array.shape[2]
    if rows is None:
        rows = math.ceil(math.sqrt(nz))
    cols = math.ceil(nz/rows)
    mosaic = np.zeros((array.shape[0]*cols, array.shape[1]*rows))
    for k in range(nz):
        j = math.floor(k/cols)
        i = k-j*cols
        mosaic[
            i*array.shape[0]:(i+1)*array.shape[0],
            j*array.shape[1]:(j+1)*array.shape[1],
        ] = array[:,:,k]
    return mosaic




def ellipsoid(a, b, c, spacing=(1., 1., 1.), levelset=False):
    """
    Generates ellipsoid with semimajor axes aligned with grid dimensions
    on grid with specified `spacing`.

    Parameters
    ----------
    a : float
        Length of semimajor axis aligned with x-axis.
    b : float
        Length of semimajor axis aligned with y-axis.
    c : float
        Length of semimajor axis aligned with z-axis.
    spacing : tuple of floats, length 3
        Spacing in (x, y, z) spatial dimensions.
    levelset : bool
        If True, returns the level set for this ellipsoid (signed level
        set about zero, with positive denoting interior) as np.float64.
        False returns a binarized version of said level set.

    Returns
    -------
    ellip : (N, M, P) array
        Ellipsoid centered in a correctly sized array for given `spacing`.
        Boolean dtype unless `levelset=True`, in which case a float array is
        returned with the level set above 0.0 representing the ellipsoid.

    Note
    ----
    This function is copy-pasted directly from skimage source code without modification - this to avoid bringing in skimage as an essential dependency. 

    """
    if (a <= 0) or (b <= 0) or (c <= 0):
        raise ValueError('Parameters a, b, and c must all be > 0')

    offset = np.r_[1, 1, 1] * np.r_[spacing]

    # Calculate limits, and ensure output volume is odd & symmetric
    low = np.ceil(- np.r_[a, b, c] - offset)
    high = np.floor(np.r_[a, b, c] + offset + 1)

    for dim in range(3):
        if (high[dim] - low[dim]) % 2 == 0:
            low[dim] -= 1
        num = np.arange(low[dim], high[dim], spacing[dim])
        if 0 not in num:
            low[dim] -= np.max(num[num < 0])

    # Generate (anisotropic) spatial grid
    x, y, z = np.mgrid[low[0]:high[0]:spacing[0],
                       low[1]:high[1]:spacing[1],
                       low[2]:high[2]:spacing[2]]

    if not levelset:
        arr = ((x / float(a)) ** 2 +
               (y / float(b)) ** 2 +
               (z / float(c)) ** 2) <= 1
    else:
        arr = ((x / float(a)) ** 2 +
               (y / float(b)) ** 2 +
               (z / float(c)) ** 2) - 1

    return arr


def multislice_affine_transform(array_source, affine_source, output_affine, slice_thickness=None, **kwargs):
    """Generalization of scipy's affine transform.
    
    This version also works when the source array is 2D and when it is multislice 2D (ie. slice thickness < slice spacing).
    In these scenarios each slice is first reshaped into a volume with provided slice thickness and mapped separately.
    """
    
    slice_spacing = np.linalg.norm(affine_source[:3,2])

    # Single-slice 2D sequence
    if array_source.shape[2] == 1:
        return _map_multislice_array(array_source, affine_source, output_affine, **kwargs)

    # Multi-slice 2D sequence
    elif slice_spacing != slice_thickness:
        return _map_multislice_array(array_source, affine_source, output_affine, slice_thickness=slice_thickness, **kwargs)

    # 3D volume sequence
    else:
        return _map_volume_array(array_source, affine_source, output_affine, **kwargs)



def _map_multislice_array(array, affine, output_affine, output_shape=None, slice_thickness=None, mask=False, label=False, cval=0):

    # Turn each slice into a volume and map as volume.
    array_mapped = None
    for z in range(array.shape[2]):
        array_z, affine_z = slice_to_volume(array, affine, z, slice_thickness=slice_thickness)
        array_mapped_z = _map_volume_array(array_z, affine_z, output_affine, output_shape=output_shape, cval=cval)
        if array_mapped is None:
            array_mapped = array_mapped_z
        else:
            array_mapped += array_mapped_z

    # If source is a mask array, set values to [0,1].
    if mask:
        array_mapped[array_mapped > 0.5] = 1
        array_mapped[array_mapped <= 0.5] = 0
    elif label:
        array_mapped = np.around(array_mapped)

    return array_mapped


def slice_to_volume(array, affine, z=0, slice_thickness=None):

    # Reshape array to 4D (x,y,z + remainder)
    shape = array.shape
    if len(shape) > 3:
        nk = np.prod(shape[3:])
    else:
        nk = 1
    array = array.reshape(shape[:3] + (nk,))
    
    # Extract a 2D array
    array_z = array[:,:,z,:]
    array_z = array_z[:,:,np.newaxis,:]

    # Duplicate the array in the z-direction to create 2 slices.
    nz = 2
    array_z = np.repeat(array_z, nz, axis=2)

    # Reshape to original nr of dimensions
    if len(shape) > 3:
        dim = shape[:2] + (nz,) + shape[3:]
    else:
        dim = shape[:2] + (nz,)
    array_z = array_z.reshape(dim)

    # Offset the slice position accordingly
    affine_z = affine.copy()
    affine_z[:3,3] += z*affine_z[:3,2]

    # Set the slice spacing to equal the slice thickness
    if slice_thickness is not None:
        slice_spacing = np.linalg.norm(affine_z[:3,2])
        affine_z[:3,2] *= slice_thickness/slice_spacing

    # Offset the slice position by half of the slice thickness.
    affine_z[:3,3] -= affine_z[:3,2]/2

    return array_z, affine_z


def _map_volume_array(array, affine, output_affine, output_shape=None, mask=False, label=False, cval=0):

    shape = array.shape
    if shape[2] == 1:
        msg = 'This function only works for an array with at least 2 slices'
        raise ValueError(msg)

    # Get transformation matrix
    source_to_target = np.linalg.inv(affine).dot(output_affine)
    source_to_target = np.around(source_to_target, 3) # remove round-off errors in the inversion

    # Reshape array to 4D (x,y,z + remainder)
    if output_shape is None:
        output_shape = shape[:3]
    nk = np.prod(shape[3:])
    output = np.empty(output_shape + (nk,))
    array = array.reshape(shape[:3] + (nk,))

    #Perform transformation
    for k in range(nk):
        output[:,:,:,k] = affine_transform(
            array[:,:,:,k],
            matrix = source_to_target[:3,:3],
            offset = source_to_target[:3,3],
            output_shape = output_shape,
            cval = cval,
            order = 0 if mask else 3,
        )

    # If source is a mask array, set values to [0,1]
    if mask:
        output[output > 0.5] = 1
        output[output <= 0.5] = 0

    # If source is a label array, round to integers
    elif label:
        output = np.around(output)

    return output.reshape(output_shape + shape[3:])



# https://discovery.ucl.ac.uk/id/eprint/10146893/1/geometry_medim.pdf

def interpolate3d_scale(array, scale=2):

    array, _ = interpolate3d_isotropic(array, [1,1,1], isotropic_spacing=1/scale)
    return array


def interpolate3d_isotropic(array, spacing, isotropic_spacing=None):

    if isotropic_spacing is None:
        isotropic_spacing = np.amin(spacing)

    # Get x, y, z coordinates for array
    nx = array.shape[0]
    ny = array.shape[1]
    nz = array.shape[2]
    Lx = (nx-1)*spacing[0]
    Ly = (ny-1)*spacing[1]
    Lz = (nz-1)*spacing[2]
    x = np.linspace(0, Lx, nx)
    y = np.linspace(0, Ly, ny)
    z = np.linspace(0, Lz, nz)

    # Get x, y, z coordinates for isotropic array
    nxi = 1 + np.floor(Lx/isotropic_spacing)
    nyi = 1 + np.floor(Ly/isotropic_spacing)
    nzi = 1 + np.floor(Lz/isotropic_spacing)
    Lxi = (nxi-1)*isotropic_spacing
    Lyi = (nyi-1)*isotropic_spacing
    Lzi = (nzi-1)*isotropic_spacing
    xi = np.linspace(0, Lxi, nxi.astype(int))
    yi = np.linspace(0, Lyi, nyi.astype(int))
    zi = np.linspace(0, Lzi, nzi.astype(int))

    # Interpolate to isotropic
    ri = np.meshgrid(xi,yi,zi, indexing='ij')
    array = interpn((x,y,z), array, np.stack(ri, axis=-1))
    return array, isotropic_spacing


def bounding_box(
    image_orientation,  # ImageOrientationPatient (assume same for all slices)
    image_positions,    # ImagePositionPatient for all slices
    pixel_spacing,      # PixelSpacing (assume same for all slices)
    rows,               # Number of rows
    columns):           # Number of columns   

    """
    Calculate the bounding box of an 3D image stored in slices in the DICOM file format.

    Parameters:
        image_orientation (list): 
            a list of 6 elements representing the ImageOrientationPatient DICOM tag for the image. 
            This specifies the orientation of the image slices in 3D space.
        image_positions (list): 
            a list of 3-element lists representing the ImagePositionPatient DICOM tag for each slice in the image. 
            This specifies the position of each slice in 3D space.
        pixel_spacing (list): 
            a list of 2 elements representing the PixelSpacing DICOM tag for the image. 
            This specifies the spacing between pixels in the rows and columns of each slice.
        rows (int): 
            an integer representing the number of rows in each slice.
        columns (int): 
            an integer representing the number of columns in each slice.

    Returns:
        dict: a dictionary with keys 'RPF', 'LPF', 'LPH', 'RPH', 'RAF', 'LAF', 'LAH', and 'RAH', 
        representing the Right Posterior Foot, Left Posterior Foot, Left Posterior Head, 
        Right Posterior Head, Right Anterior Foot, Left Anterior Foot, 
        Left Anterior Head, and Right Anterior Head, respectively. 
        Each key maps to a list of 3 elements representing the x, y, and z coordinates 
        of the corresponding corner of the bounding box.
   
    """

    row_spacing = pixel_spacing[0]
    column_spacing = pixel_spacing[1]

    row_cosine = np.array(image_orientation[:3])
    column_cosine = np.array(image_orientation[3:])
    slice_cosine = np.cross(row_cosine, column_cosine)

    # The coronal orientation has a left-handed reference frame
    if np.array_equal(np.around(image_orientation, 3), [1,0,0,0,0,-1]):
        slice_cosine = -slice_cosine

    number_of_slices = len(image_positions)
    image_locations = [np.dot(np.array(pos), slice_cosine) for pos in image_positions]
    slab_thickness = max(image_locations) - min(image_locations)
    slice_spacing = slab_thickness / (number_of_slices - 1)
    image_position_first_slice = image_positions[image_locations.index(min(image_locations))]

    # ul = Upper Left corner of a slice
    # ur = Upper Right corner of a slice
    # bl = Bottom Left corner of a slice
    # br = Bottom Right corner of a slice
    
    # Initialize with the first slice
    ul = image_position_first_slice
    ur = ul + row_cosine * (columns-1) * column_spacing
    br = ur + column_cosine * (rows-1) * row_spacing
    bl = ul + column_cosine * (rows-1) * row_spacing
    corners = np.array([ul, ur, br, bl])
    amin = np.amax(corners, axis=0)
    amax = np.amax(corners, axis=0)
    box = {
        'RPF': [amin[0],amax[1],amin[2]], # Right Posterior Foot 
        'LPF': [amax[0],amax[1],amin[2]], # Left Posterior Foot
        'LPH': [amax[0],amax[1],amax[2]], # Left Posterior Head
        'RPH': [amin[0],amax[1],amax[2]], # Right Posterior Head
        'RAF': [amin[0],amin[1],amin[2]], # Right Anterior Foot
        'LAF': [amax[0],amin[1],amin[2]], # Left Anterior Foot
        'LAH': [amax[0],amin[1],amax[2]], # Left Anterior Head
        'RAH': [amin[0],amin[1],amax[2]], # Right Anterior Head
    }

    # Update with all other slices
    # PROBABLY SUFFICIENT TO USE ONLY THE OUTER SLICES!!
    for _ in range(1, number_of_slices):

        ul += slice_cosine * slice_spacing
        ur = ul + row_cosine * (columns-1) * column_spacing
        br = ur + column_cosine * (rows-1) * row_spacing
        bl = ul + column_cosine * (rows-1) * row_spacing

        corners = np.array([ul, ur, br, bl])
        amin = np.amin(corners, axis=0)
        amax = np.amax(corners, axis=0)

        box['RPF'][0] = min([box['RPF'][0], amin[0]])    
        box['RPF'][1] = max([box['RPF'][1], amax[1]]) 
        box['RPF'][2] = min([box['RPF'][2], amin[2]]) 

        box['LPF'][0] = max([box['LPF'][0], amax[0]]) 
        box['LPF'][1] = max([box['LPF'][1], amax[1]]) 
        box['LPF'][2] = min([box['LPF'][2], amin[2]]) 

        box['LPH'][0] = max([box['LPH'][0], amax[0]]) 
        box['LPH'][1] = max([box['LPH'][1], amax[1]]) 
        box['LPH'][2] = max([box['LPH'][2], amax[2]]) 

        box['RPH'][0] = min([box['RPH'][0], amin[0]]) 
        box['RPH'][1] = max([box['RPH'][1], amax[1]]) 
        box['RPH'][2] = max([box['RPH'][2], amax[2]]) 

        box['RAF'][0] = min([box['RAF'][0], amin[0]]) 
        box['RAF'][1] = min([box['RAF'][1], amin[1]]) 
        box['RAF'][2] = min([box['RAF'][2], amin[2]]) 

        box['LAF'][0] = max([box['LAF'][0], amax[0]]) 
        box['LAF'][1] = min([box['LAF'][1], amin[1]]) 
        box['LAF'][2] = min([box['LAF'][2], amin[2]]) 

        box['LAH'][0] = max([box['LAH'][0], amax[0]]) 
        box['LAH'][1] = min([box['LAH'][1], amin[1]]) 
        box['LAH'][2] = max([box['LAH'][2], amax[2]]) 

        box['RAH'][0] = min([box['RAH'][0], amin[0]]) 
        box['RAH'][1] = min([box['RAH'][1], amin[1]]) 
        box['RAH'][2] = max([box['RAH'][2], amax[2]]) 

    return box



def standard_affine_matrix(
    bounding_box, 
    pixel_spacing, 
    slice_spacing,
    orientation = 'axial'): 

    row_spacing = pixel_spacing[0]
    column_spacing = pixel_spacing[1]
    
    if orientation == 'axial':
        image_position = bounding_box['RAF']
        row_cosine = np.array([1,0,0])
        column_cosine = np.array([0,1,0])
        slice_cosine = np.array([0,0,1])
    elif orientation == 'coronal':
        image_position = bounding_box['RAH']
        row_cosine = np.array([1,0,0])
        column_cosine = np.array([0,0,-1])
        slice_cosine = -np.array([0,1,0]) 
    elif orientation == 'sagittal':
        image_position = bounding_box['LAH']
        row_cosine = np.array([0,1,0])
        column_cosine = np.array([0,0,-1])
        slice_cosine = np.array([-1,0,0])          

    affine = np.identity(4, dtype=np.float32)
    affine[:3, 0] = row_cosine * column_spacing
    affine[:3, 1] = column_cosine * row_spacing
    affine[:3, 2] = slice_cosine * slice_spacing
    affine[:3, 3] = image_position
    
    return affine 


def affine_matrix(      # single slice function
    image_orientation,  # ImageOrientationPatient
    image_position,     # ImagePositionPatient
    pixel_spacing,      # PixelSpacing
    slice_thickness):     # SliceThickness

    row_spacing = pixel_spacing[0]
    column_spacing = pixel_spacing[1]
    
    row_cosine = np.array(image_orientation[:3])
    column_cosine = np.array(image_orientation[3:])
    slice_cosine = np.cross(row_cosine, column_cosine)

    # The coronal orientation has a left-handed reference frame
    if np.array_equal(np.around(image_orientation, 3), [1,0,0,0,0,-1]):
        slice_cosine = -slice_cosine

    affine = np.identity(4, dtype=np.float32)
    affine[:3, 0] = row_cosine * column_spacing
    affine[:3, 1] = column_cosine * row_spacing
    affine[:3, 2] = slice_cosine * slice_thickness
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

    # The coronal orientation has a left-handed reference frame
    if np.array_equal(np.around(image_orientation, 3), [1,0,0,0,0,-1]):
        slice_cosine = -slice_cosine

    return np.dot(np.array(image_position), slice_cosine)


def image_position_from_slice_location(slice_location:float, affine=np.eye(4))->list:
    v = dismantle_affine_matrix(affine)
    return list(affine[:3, 3] + slice_location * np.array(v['slice_cosine']))


def image_position_patient(affine, number_of_slices):
    slab = dismantle_affine_matrix(affine)
    image_positions = []
    image_locations = []
    for s in range(number_of_slices):
        pos = [
            slab['ImagePositionPatient'][i] 
            + s*slab['SpacingBetweenSlices']*slab['slice_cosine'][i]
            for i in range(3)
        ]
        loc = np.dot(np.array(pos), np.array(slab['slice_cosine']))
        image_positions.append(pos)
        image_locations.append(loc)
    return image_positions, image_locations


def affine_matrix_multislice(
    image_orientation,  # ImageOrientationPatient (assume same for all slices)
    image_positions,    # ImagePositionPatient for all slices
    pixel_spacing):     # PixelSpacing (assume same for all slices)

    row_spacing = pixel_spacing[0]
    column_spacing = pixel_spacing[1]
    
    row_cosine = np.array(image_orientation[:3])    
    column_cosine = np.array(image_orientation[3:]) 
    slice_cosine = np.cross(row_cosine, column_cosine)

    # The coronal orientation has a left-handed reference frame
    if np.array_equal(np.around(image_orientation, 3), [1,0,0,0,0,-1]):
        slice_cosine = -slice_cosine

    image_locations = [np.dot(np.array(pos), slice_cosine) for pos in image_positions]
    #number_of_slices = len(image_positions)
    number_of_slices = np.unique(image_locations).size
    if number_of_slices == 1:
        msg = 'Cannot calculate affine matrix for the slice group. \n'
        msg += 'All slices have the same location. \n'
        msg += 'Use the single-slice affine formula instead.'
        raise ValueError(msg)
    slab_thickness = np.amax(image_locations) - np.amin(image_locations)
    slice_spacing = slab_thickness / (number_of_slices - 1)
    image_position_first_slice = image_positions[image_locations.index(np.amin(image_locations))]

    affine = np.identity(4, dtype=np.float32)
    affine[:3, 0] = row_cosine * column_spacing 
    affine[:3, 1] = column_cosine * row_spacing
    affine[:3, 2] = slice_cosine * slice_spacing
    affine[:3, 3] = image_position_first_slice

    return affine


def dismantle_affine_matrix(affine):
    # Note: nr of slices can not be retrieved from affine_matrix
    # Note: slice_cosine is not a DICOM keyword but can be used 
    # to work out the ImagePositionPatient of any other slice i as
    # ImagePositionPatient_i = ImagePositionPatient + i * SpacingBetweenSlices * slice_cosine
    column_spacing = np.linalg.norm(affine[:3, 0])
    row_spacing = np.linalg.norm(affine[:3, 1])
    slice_thickness = np.linalg.norm(affine[:3, 2])
    row_cosine = affine[:3, 0] / column_spacing
    column_cosine = affine[:3, 1] / row_spacing
    slice_cosine = affine[:3, 2] / slice_thickness
    return {
        'PixelSpacing': [row_spacing, column_spacing], 
#        'SpacingBetweenSlices': slice_thickness,  # Obsolete
        'SliceThickness': slice_thickness, 
        'ImageOrientationPatient': row_cosine.tolist() + column_cosine.tolist(), 
        'ImagePositionPatient': affine[:3, 3].tolist(), # first slice for a volume
        'slice_cosine': slice_cosine.tolist()} 


def unstack_affine(affine, nz):

    pos0 = affine[:3, 3]
    slice_vec = affine[:3, 2] 

    affines = []
    for z in range(nz):
        affine_z = affine.copy()
        affine_z[:3, 3] = pos0 + z*slice_vec
        affines.append(affine_z)

    return affines


def stack_affines(affines):

    aff = [dismantle_affine_matrix(a) for a in affines]

    # Check that all affines have the same orientation
    orient = [a['ImageOrientationPatient'] for a in aff]
    orient = [x for i, x in enumerate(orient) if i==orient.index(x)]
    if len(orient) > 1:
        raise ValueError(
            "Slices have different orientations and cannot be stacked")
    orient = orient[0]

    # Check that all affines have the same slice_cosine
    slice_cosine = [a['slice_cosine'] for a in aff]
    slice_cosine = [x for i, x in enumerate(slice_cosine) if i==slice_cosine.index(x)]
    if len(slice_cosine) > 1:
        raise ValueError(
            "Slices have different slice cosines and cannot be stacked")
    slice_cosine = slice_cosine[0]

    # Check all slices have the same thickness
    thick = [a['SpacingBetweenSlices'] for a in aff] # note incorrectly named
    thick = np.unique(thick)
    if len(thick)>1:
        raise ValueError(
            "Slices have different slice thickness and cannot be stacked")
    thick = thick[0]

    # Check all slices have the same pixel spacing
    pix_space = [a['PixelSpacing'] for a in aff] 
    pix_space = [x for i, x in enumerate(pix_space) if i==pix_space.index(x)]
    if len(pix_space)>1:
        raise ValueError(
            "Slices have different pixel sizes and cannot be stacked. ")
    pix_space = pix_space[0]

    # Get orientations (orthogonal assumed here)
    row_vec = np.array(orient[:3])   
    column_vec = np.array(orient[3:]) 
    slice_vec = np.array(slice_cosine)

    # Check that all slice spacings are equal
    pos = [a['ImagePositionPatient'] for a in aff]
    loc = np.array([np.dot(p, slice_vec) for p in pos])
    # Get unique slice spacing (to micrometer precision)
    slice_spacing = np.unique(np.around(loc[1:]-loc[:-1], 3))
    # If there is more than 1 slice spacing, the series is multislice
    if slice_spacing.size != 1:
        raise ValueError(
            "There are different spacings between consecutive slices. "
            "The slices cannot be stacked.")
    slice_spacing = slice_spacing[0]
    
    # Check the slice spacing is equal to the slice thickness
    if np.around(thick-slice_spacing, 3) != 0:
        raise ValueError(
            "This is a multi-slice sequence, i.e. the slice spacing is "
            "different from the slice thickness. If you want to stack the "
            "slices, set the slice thickness equal to the slice spacing "
            "first (" + str(slice_spacing) + " mm).")
    
    # Check that all positions are on the slice vector
    for p in pos[1:]:
        # Position relative to first slice position
        prel = np.array(p)-np.array(pos[0])
        # Parallel means cross product has length zero
        norm = np.linalg.norm(np.cross(slice_vec, prel))
        # Round to micrometers to avoid numerical error
        if np.round(norm, 3) != 0:
            raise ValueError(
                "Slices are not aligned and cannot be stacked")

    # Build affine for the stack
    affine = np.identity(4, dtype=np.float32)
    affine[:3, 0] = row_vec * pix_space[1] 
    affine[:3, 1] = column_vec * pix_space[0]
    affine[:3, 2] = slice_vec * slice_spacing
    affine[:3, 3] = pos[0]  

    return affine



def affine_to_RAH(affine):
    """Convert to the coordinate system used in NifTi"""

    rot_180 = np.identity(4, dtype=np.float32)
    rot_180[:2,:2] = [[-1,0],[0,-1]]
    return np.matmul(rot_180, affine)
    

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
    array *= slope
    array += intercept

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


def _scale_to_range(array, bits_allocated):
    # Obsolete - generalized as above
        
    range = 2.0**bits_allocated - 1
    maximum = np.amax(array)
    minimum = np.amin(array)
    if maximum == minimum:
        slope = 1
    else:
        slope = range / (maximum - minimum)
    intercept = -slope * minimum
    array *= slope
    array += intercept

    if bits_allocated == 8:
        return array.astype(np.uint8), slope, intercept
    if bits_allocated == 16:
        return array.astype(np.uint16), slope, intercept
    if bits_allocated == 32:
        return array.astype(np.uint32), slope, intercept
    if bits_allocated == 64:
        return array.astype(np.uint64), slope, intercept


def BGRA(array, RGBlut=None, width=None, center=None):

    if (width is None) or (center is None):
        max = np.amax(array)
        min = np.amin(array)
    else:
        max = center+width/2
        min = center-width/2

    # Scale pixel array into byte range
    array = np.clip(array, min, max)
    array -= min
    if max > min:
        array *= 255/(max-min)
    array = array.astype(np.ubyte)

    BGRA = np.empty(array.shape[:2]+(4,), dtype=np.ubyte)
    BGRA[:,:,3] = 255 # Alpha channel

    if RGBlut is None:
        # Greyscale image
        for c in range(3):
            BGRA[:,:,c] = array
    else:
        # Scale LUT into byte range
        RGBlut *= 255
        RGBlut = RGBlut.astype(np.ubyte)       
        # Create RGB array by indexing LUT with pixel array
        for c in range(3):
            BGRA[:,:,c] = RGBlut[array,2-c]

    return BGRA




