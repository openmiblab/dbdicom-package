from tqdm import tqdm

import numpy as np
import pandas as pd
import scipy
import dbdicom
import vreg
from dbdicom import Series


def fill_slice_gaps(series, ref, slice_thickness=None, mask=None):
    # slice_thickness - make thin slices for smoother interpolation
    z,t = 'SliceLocation','AcquisitionTime'
    if slice_thickness is not None:
        thick = series.values('SliceThickness')
        series.set_values(slice_thickness, 'SliceThickness') 
    input_array = pixel_values(series, dims=(z,t), on=ref)
    input_geom, _ = mask_array(series, on=ref, dim=t, geom=True)
    if slice_thickness is not None:
        series.set_values(thick, 'SliceThickness')
    if mask is not None:
        mask, _ = mask_array(mask, on=ref, dim=t)
        mask = mask[...,0]
    series.message('Interpolating slice gaps..')
    output_array = vreg.fill_gaps(input_array[...,0], input_geom[...,0], mask=mask)
    output_series = ref.copy(SeriesDescription = series.instance().SeriesDescription + '_fill')
    output_series.set_pixel_values(output_array, dims=z)
    return output_series


def _equal_geometry(affine1, affine2):
    # Check if both are the same, 
    # ignoring the order in the list
    if not isinstance(affine2, list):
        affine2 = [affine2]
    if not isinstance(affine1, list):
        affine1 = [affine1]
    if len(affine1) != len(affine2):
        return False
    unmatched = list(range(len(affine2)))
    for a1 in affine1:
        imatch = None
        for i in unmatched:
            if np.array_equal(a1[0], affine2[i][0]):
                # If a slice group with the same affine is found, 
                # check if the image dimensions are the same too.
                dim1 = a1[1][0].array().shape
                dim2 = affine2[i][1][0].array().shape
                if dim1 == dim2:
                    imatch = i
                    break
        if imatch is not None:
            unmatched.remove(imatch)
    return unmatched == []


def map_to(source:Series, target:Series, **kwargs):
    """Map non-zero pixels onto another series"""

    # Get transformation matrix
    source.status.message('Loading transformation matrices..')
    affine_source = source.affine_matrix()
    affine_target = target.affine_matrix() 
    if _equal_geometry(affine_source, affine_target): 
        source.status.hide()
        return source

    if isinstance(affine_target, list):
        mapped_series = []
        for affine_slice_group in affine_target:
            slice_group_target = target.new_sibling()
            slice_group_target.adopt(affine_slice_group[1])
            mapped = _map_series_to_slice_group(source, slice_group_target, affine_source, affine_slice_group[0], **kwargs)
            mapped_series.append(mapped)
            slice_group_target.remove()
        desc = source.instance().SeriesDescription + ' [overlay]'
        mapped_series = dbdicom.merge(mapped_series, inplace=True)
        mapped_series.SeriesDescription = desc
    else:
        mapped_series = _map_series_to_slice_group(source, target, affine_source, affine_target[0], **kwargs)
    return mapped_series


def _map_series_to_slice_group(source, target, affine_source, affine_target, **kwargs):

    if isinstance(affine_source, list):
        array_target, headers_target = target.array(['SliceLocation','AcquisitionTime'], pixels_first=True)
        array = None
        for affine_slice_group in affine_source:
            slice_group_source = source.new_sibling()
            slice_group_source.adopt(affine_slice_group[1])
            array_sg, weight_sg = _map_slice_group_to_slice_group_array(slice_group_source, affine_slice_group[0], target, affine_target, array_target.shape[:3], **kwargs)
            slice_group_source.remove()
            if array is None:
                array = array_sg
                weight = weight_sg
            else:
                array += weight_sg*array_sg
                weight += weight_sg   
        nozero = np.where(weight > 0)
        array[nozero] = array[nozero]/weight[nozero]

        # Create new series
        mapped_series = source.new_sibling(suffix='overlay')
        ns, nt, nk = array.shape[2], array.shape[3], array.shape[4]
        cnt=0
        for t in range(nt):
            for k in range(nk):
                for s in range(ns):
                    cnt+=1
                    source.progress(cnt, ns*nt*nk, 'Saving results..')
                    image = headers_target[s,0,0].copy_to(mapped_series)
                    image.AcquisitionTime = t
                    image.set_array(array[:,:,s,t,k])
        return mapped_series
    else:
        return _map_slice_group_to_slice_group(source, affine_source[0], target, affine_target, **kwargs)
    

def _map_slice_group_to_slice_group_array(source, affine_source, target, output_affine, target_shape, **kwargs):

    # Get source arrays
    array_source, headers_source = source.array(['SliceLocation','AcquisitionTime'], pixels_first=True)
    
    # Get message status updates
    source_desc = source.instance().SeriesDescription
    target_desc = target.instance().SeriesDescription
    message = 'Mapping ' + source_desc + ' onto ' + target_desc
    source.message(message)

    array_mapped = np.empty(target_shape + array_source.shape[3:])
    weights_mapped = np.empty(target_shape + array_source.shape[3:])
    slice_thickness = headers_source[0,0,0].SliceThickness

    for t in range(array_source.shape[3]):
        for k in range(array_source.shape[4]):
            array_mapped[:,:,:,t,k], _ = vreg.affine_reslice_slice_by_slice(
                array_source[:,:,:,t,k], affine_source, 
                output_affine, output_shape=target_shape,
                slice_thickness = slice_thickness,
                **kwargs,
            )
            weights_mapped[:,:,:,t,k], _ = vreg.affine_reslice_slice_by_slice(
                np.ones(array_source.shape[:3]), affine_source, 
                output_affine, output_shape=target_shape,
                slice_thickness = slice_thickness,
                **kwargs,
            )

    return array_mapped, weights_mapped


def _map_slice_group_to_slice_group(source, affine_source, target, output_affine, **kwargs):

    # Get source arrays
    array_source, headers_source = source.array(['SliceLocation','AcquisitionTime'], pixels_first=True)
    array_target, headers_target = target.array(['SliceLocation','AcquisitionTime'], pixels_first=True)

    # Get message status updates
    source_desc = source.instance().SeriesDescription
    target_desc = target.instance().SeriesDescription
    message = 'Mapping ' + source_desc + ' onto ' + target_desc
    source.message(message)

    # Create new series
    # Retain source acquisition times
    # Assign acquisition time of slice=0 to all slices
    mapped_series = source.new_sibling(suffix='overlay')
    nt, nk = array_source.shape[3], array_source.shape[4]
    ns = headers_target.shape[0] 
    acq_times = [headers_source[0,t,0].AcquisitionTime for t in range(nt)]
    slice_thickness = headers_source[0,0,0].SliceThickness
    cnt=0
    for t in range(nt):
        for k in range(nk):
            array_mapped, _ = vreg.affine_reslice_slice_by_slice(
                array_source[:,:,:,t,k], 
                affine_source, 
                output_affine, 
                output_shape=array_target.shape[:3],
                slice_thickness = slice_thickness, **kwargs)
            for s in range(ns):
                cnt+=1
                source.progress(cnt, ns*nt*nk, 'Saving results..')
                image = headers_target[s,0,0].copy_to(mapped_series)
                image.AcquisitionTime = acq_times[t]
                image.set_array(array_mapped[:,:,s])
    return mapped_series


def mask_array(mask, on=None):

    # Get all frames and return if empty
    frames = on.instances()
    if frames == []:
        raise ValueError("Empty series")
    
    mask_vol = mask.volume()

    # Read frames
    regions = []
    regions_frames = []
    for i, f in tqdm(enumerate(frames), total=len(frames), desc='Reading volumes..', disable=mask.in_gui()):
        if mask.in_gui():
            mask.progress(i+1, len(frames), 'Reading values..')
        vol = f.get_dataset().get_values('volume')
        mask_vol_i = mask_vol.slice_like(vol)
        mask_vol_i = np.squeeze(mask_vol_i.values > 0.5)
        if np.count_nonzero(mask_vol_i):
            regions.append(mask_vol_i)
            regions_frames.append(f)
    mask.status.hide()
    return regions, regions_frames



# def _OLD_mask_array(mask, on=None, dim='InstanceNumber', geom=False):

#     if on is None:
#         # geom keyword not yet implemented
#         return dbdicom.array(mask, sortby=['SliceLocation', dim], mask=True, pixels_first=True, first_volume=True)

#     # Get transformation matrix
#     mask.message('Loading transformation matrices..')
#     affine_source = mask.affine_matrix()
#     affine_target = on.affine_matrix() 

#     if isinstance(affine_target, list):
#         mapped_arrays = []
#         mapped_headers = []
#         for affine_slice_group_target in affine_target:
#             mapped, headers = _map_mask_series_to_slice_group(
#                 mask, 
#                 affine_slice_group_target[1], 
#                 affine_source, 
#                 affine_slice_group_target[0],
#                 dim=dim, geom=geom,
#             )
#             mapped_arrays.append(mapped)
#             mapped_headers.append(headers)
#     else:
#         mapped_arrays, mapped_headers = _map_mask_series_to_slice_group(
#             mask, on, affine_source, affine_target[0], dim=dim, geom=geom)
#     return mapped_arrays, mapped_headers


# def _map_mask_series_to_slice_group(source, target, affine_source, affine_target, **kwargs):

#     if isinstance(affine_source, list):
#         mapped_arrays = []
#         for affine_slice_group in affine_source:
#             mapped, headers = _map_mask_slice_group_to_slice_group(
#                 affine_slice_group[1], 
#                 target, 
#                 affine_slice_group[0], 
#                 affine_target,
#                 **kwargs,
#             )
#             mapped_arrays.append(mapped)
#         array = np.logical_or(mapped_arrays[0], mapped_arrays[1])
#         for a in mapped_arrays[2:]:
#             array = np.logical_or(array, a)
#         return array, headers
#     else:
#         return _map_mask_slice_group_to_slice_group(source, target, affine_source[0], affine_target, **kwargs)


# def _map_mask_slice_group_to_slice_group(source, target, affine_source, affine_target, dim='InstanceNumber', geom=False):

#     if isinstance(source, list):
#         status = source[0].status
#     else:
#         status = source.status

#     # Get arrays
#     array_source, headers_source = dbdicom.array(source, sortby=['SliceLocation',dim], pixels_first=True, first_volume=True)
#     array_target, headers_target = dbdicom.array(target, sortby=['SliceLocation',dim], pixels_first=True, first_volume=True)

#     if geom:
#         # mask shows geometry of source
#         array_source = np.full(array_source.shape, 1)
        
#     # For mapping mask onto series, the time dimensions must be the same.
#     # If they are not, the mask is extruded on to the series time dimensions.
#     nk = array_target.shape[3]
#     if array_source.shape[3] != nk:
#         status.message('Extruding ROI on time series..')
#         array_source = np.amax(array_source, axis=-1)
#         array_source = np.repeat(array_source[:,:,:,np.newaxis], nk, axis=3)
    
#     # If the dimensions and affines are equal there is nothing to do
#     if np.array_equal(affine_source, affine_target):
#         if array_source.shape == array_target.shape:
#             # Make sure the result is a mask
#             array_source[array_source > 0.5] = 1
#             array_source[array_source <= 0.5] = 0
#             return array_source, headers_target

#     slice_thickness = headers_source[0,0].SliceThickness
#     array_target = np.empty(array_target.shape[:3] + (array_source.shape[3],))
#     for t in range(array_source.shape[3]):
#         array_target[:,:,:,t], _ = vreg.affine_reslice_slice_by_slice(
#             array_source[:,:,:,t], 
#             affine_source, 
#             affine_target, 
#             output_shape = array_target.shape[:3],
#             slice_thickness = slice_thickness,
#             mask=True)

#     return array_target, headers_target


def mask_statistics(masks, images):
    if not isinstance(masks, list):
        masks = [masks]
    if not isinstance(images, list):
        images = [images]
    df_all_masks = None
    for mask in masks:
        df_mask = None
        for img in images:
            data = mask_values(mask, img)
            df_img = mask_data_statistics(data, mask, img)
            if df_mask is None:
                df_mask = df_img
            else:
                df_mask = pd.concat([df_mask, df_img], ignore_index=True)
        if df_all_masks is None:
            df_all_masks = df_mask
        else:
            df_all_masks = pd.concat([df_all_masks, df_mask], ignore_index=True)
    return df_all_masks


def mask_values(mask, image):
    msk_arr, img_hdrs = mask_array(mask, on=image)
    values = _mask_data_slice_groups(msk_arr, img_hdrs) 
    return values


def mask_data_statistics(data, mask, image):
    # Get mask array
    #msk_arr, img_hdrs = mask_array(mask, on=image)
    #data = _mask_data_slice_groups(msk_arr, img_hdrs)
    props = _summary_stats(data)
    instance = image.instance()
    columns = ['PatientID', 'StudyDescription', 'SeriesDescription', 'Region of Interest', 'Parameter', 'Value', 'Unit']
    ids = [instance.PatientID, instance.StudyDescription, instance.SeriesDescription, mask.instance().SeriesDescription]
    data = []
    for par, val in props.items():
        row = ids + [par, val, '']
        data.append(row)
    return pd.DataFrame(data, columns=columns)


def _mask_data_slice_groups(msk_arr, img_hdrs):
    if isinstance(msk_arr, list): 
        # Loop over slice groups
        data = [_mask_data(arr, img_hdrs[m]) for m, arr in enumerate(msk_arr)]
        data = [d for d in data if d is not None]
        if data == []:
            data = None
        else:
            data = np.concatenate(data)
    else: 
        # single slice group
        data = _mask_data(msk_arr, img_hdrs)
    return data


def _mask_data(msk_arr, imgs):
    data = []
    for i, image in np.ndenumerate(imgs):
        if image is not None:
            if len(i) == 1:
                mask = msk_arr[:,:,i[0]]
            elif len(i) == 2:
                mask = msk_arr[:,:,i[0],i[1]]
            if np.count_nonzero(mask) > 0:
                array = image.array()
                array = array[mask > 0.5]  
                data.append(array.ravel())
    if data == []:
        return None
    else:
        return np.concatenate(data)
    

def _summary_stats(data):
    if data is None:
        return {}
    return {
        'Mean': np.mean(data),
        'Standard deviation': np.std(data),
        'Maximum': np.amax(data),
        'Minimum': np.amin(data),
        '2.5% percentile': np.percentile(data, 2.5),
        '5% percentile': np.percentile(data, 5),
        '10% percentile': np.percentile(data, 10),
        '25% percentile': np.percentile(data, 25),
        'Median': np.percentile(data, 50),
        '75% percentile': np.percentile(data, 75),
        '90% percentile': np.percentile(data, 90),
        '95% percentile': np.percentile(data, 95),
        '97.5% percentile': np.percentile(data, 97.5),
        'Range': np.amax(data) - np.amin(data),
        'Interquartile range':np.percentile(data, 75) - np.percentile(data, 25),
        '90 percent range': np.percentile(data, 95) - np.percentile(data, 5),
        'Coefficient of variation': np.std(data)/np.mean(data),
        'Heterogeneity': (np.percentile(data, 95) - np.percentile(data, 5))/np.percentile(data, 50),
        'Kurtosis': scipy.stats.kurtosis(data),
        'Skewness': scipy.stats.skew(data),
    }

# no longer public - replace by vreg.pixel_values()
# Needs an approach that does no create a DICOM series first
def array(series, on=None, **kwargs):
    """Return the array overlaid on another series"""

    if on is None:
        array, _ = series.array(**kwargs)
    else:
        series_map = map_to(series, on)
        array, _ = series_map.array(**kwargs)
        if series_map != series:
            series_map.remove()
    return array

def pixel_values(series, dims=('InstanceNumber',), on=None):
    # Wrapper for array following new API

    if np.isscalar(dims):
        dims = (dims,)

    return array(series, on=on, sortby=list(dims), pixels_first=True, first_volume=True)




def print_current(vk):
    print(vk)


def _get_input_volume(series:Series):
    if series is None:
        return None, None
    desc = series.instance().SeriesDescription
    affine = series.unique_affines()
    if affine.shape[0] > 1:
        msg = 'This function only works for series with a single slice group. \n'
        msg += 'Multiple slice groups detected in ' + desc + ' - please split the series first.'
        raise ValueError(msg)
    else:
        affine = affine[0,:,:]
    #array, headers = series.array('SliceLocation', pixels_first=True, first_volume=True)
    array = series.pixel_values(dims=('SliceLocation',))
    if array is None:
        msg = 'Series ' + desc + ' is empty - cannot perform alignment.'
        raise ValueError(msg)  
    return array, affine


def _get_input(moving, static, region=None, margin=0):

    array_moving, affine_moving = _get_input_volume(moving)
    array_static, affine_static = _get_input_volume(static)
    
    moving.message('Performing coregistration. Please be patient. Its hard work and I need to concentrate..')
    
    # If a region is provided, use it extract a bounding box around the static array
    if region is not None:
        array_region, affine_region = _get_input_volume(region)
        array_static, affine_static = vreg.mask_volume(array_static, affine_static, array_region, affine_region, margin)
    
    return array_static, affine_static, array_moving, affine_moving



def find_translation(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0)->np.ndarray:
    """Find the translation that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The translation will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin)

    Returns:
        np.ndarray: 3-element numpy array with values of the translation that maps the moving volume on to the static volume.
    """

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': static_pixel_spacing, 'tolerance': tolerance},
        'callback': lambda vk: moving.status.message('Current parameter: ' + str(vk)),
    }
    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }
    
    # Align volumes
    try:
        translation_estimate = vreg.align(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = np.zeros(3, dtype=np.float32), 
            resolutions = [4,2,1], 
            transformation =  vreg.translate,
            metric = func[metric],
            optimization = optimization,
        )
    except:
        print('Failed to align volumes..')
        translation_estimate = None

    return translation_estimate


def apply_translation(series_moving:Series, parameters:np.ndarray, target:Series=None, description:str=None)->Series:
    """Apply active translation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): three-element numpy array with coordinates of the translation in the absolute reference frame (mm).
        target (dbdicom.Series, optional): If provided, the result is mapped onto the geometry of this series. If none is provided, the result has the same geometry of the moving series. Defaults to None.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """

    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    array_moving = series_moving.pixel_values(dims=('SliceLocation',))
    if array_moving.size == 0:
        msg = desc_moving + ' is empty - cannot perform alignment.'
        raise ValueError(msg)
    
    if target is None:
        shape_moved = array_moving.shape
        affine_moved = affine_moving
    else:
        array_moved = target.pixel_values(dims=('SliceLocation',))
        shape_moved = array_moved.shape
        affine_moved = target.affine()

    series_moving.message('Applying translation..')   
    if description is None:
        description = desc_moving + ' [translation]'
    array_moved = vreg.translate(array_moving, affine_moving, shape_moved, affine_moved, parameters)
    series_moved = series_moving.new_sibling(SeriesDescription=description)
    series_moved.set_pixel_values(array_moved, coords={'SliceLocation': np.arange(array_moved.shape[-1])})
    series_moved.set_affine(affine_moved)
    return series_moved


def apply_passive_translation(series_moving:Series, parameters:np.ndarray)->Series:
    """Apply passive translation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The vectors are defined in an absolute reference frame in units of mm.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orentations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the transformed volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    series_moving.message('Applying passive rigid transformation..')
    output_affine = vreg.passive_translation(affine_moving, parameters)
    series_moved = series_moving.copy(SeriesDescription = desc_moving + ' [passive translation]')
    series_moved.set_affine(output_affine, dims=('SliceLocation',), multislice=True)
    return series_moved


def find_rigid_transformation(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0, prereg=False)->np.ndarray:
    """Find the rigid transform that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The rigid transform will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin).

    Returns:
        np.ndarray: 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The vectors are defined in an absolute reference frame in units of mm.
    """

    if prereg:
        translation = find_translation(moving, static, tolerance=tolerance, metric=metric, region=region, margin=margin)
        rigid_estimate = np.concatenate([np.zeros(3, dtype=np.float32), translation])
    else:
        rigid_estimate = np.zeros(6, dtype=np.float32)

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)
    
    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    rot_gradient_step, translation_gradient_step, _ = vreg.affine_resolution(array_static.shape, static_pixel_spacing)
    gradient_step = np.concatenate((1.0*rot_gradient_step, 0.5*translation_gradient_step))
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': gradient_step, 'tolerance': tolerance},
        'callback': lambda vk: moving.status.message('Current parameter: ' + str(vk)),
    }
    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }

    # Align volumes
    try:
        rigid_estimate = vreg.align(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = rigid_estimate,
            resolutions = [4,2,1], 
            transformation = vreg.rigid,
            metric = func[metric],
            optimization = optimization,
        )
    except:
        print('Failed to align volumes..')
        rigid_estimate = None

    return rigid_estimate


def apply_rigid_transformation(series_moving:Series, parameters:np.ndarray,  target:Series=None, description:str=None)->Series:
    """Apply rigid transformation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The vectors are defined in an absolute reference frame in units of mm.
        target (dbdicom.Series, optional): If provided, the result is mapped onto the geometry of this series. If none is provided, the result has the same geometry of the moving series. Defaults to None.
        description (str, optional): Series description of the resulting series. Defaults to None.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orentations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the transformed volume.
    """
    # TODO: target is not the right word. geometry?
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    array_moving = series_moving.pixel_values(dims=('SliceLocation',))
    if array_moving.size == 0:
        msg = desc_moving + ' is empty - cannot perform alignment.'
        raise ValueError(msg)
    
    if target is None:
        shape_moved = array_moving.shape
        affine_moved = affine_moving
    else:
        array_moved = target.pixel_values(dims=('SliceLocation',))
        shape_moved = array_moved.shape
        affine_moved = target.affine()

    series_moving.message('Applying rigid transformation..')
    array_moved = vreg.rigid(array_moving, affine_moving, shape_moved, affine_moved, parameters)
    if description is None:
        description = desc_moving + ' [rigid]'
    series_moved = series_moving.new_sibling(SeriesDescription = description)
    series_moved.set_pixel_values(array_moved, slice={'SliceLocation': np.arange(array_moved.shape[-1])})
    series_moved.set_affine(affine_moved)
    return series_moved


def apply_passive_rigid_transformation(series_moving:Series, parameters:np.ndarray,description:str=None)->Series:
    """Apply passive rigid transformation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The vectors are defined in an absolute reference frame in units of mm.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orentations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the transformed volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    series_moving.message('Applying passive rigid transformation..')
    output_affine = vreg.passive_rigid_transform(affine_moving, parameters)
    if description is None:
        description = desc_moving + ' [passive rigid]'
    series_moved = series_moving.copy(SeriesDescription = description)
    series_moved.set_affine(output_affine, dims=('SliceLocation',), multislice=True)
    return series_moved


def find_sbs_inslice_translation(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0)->np.ndarray:
    """Find the slice-by-slice inslice translation that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The translation will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin).

    Returns:
        np.ndarray: list of 3-element numpy arrays with values of the translation that maps the moving volume onto the static volume. The list has one entry per slice of the volume.
    """
    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)    
    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }
    
     # Perform coregistration
    translation_estimate = np.zeros(2, dtype=np.float32)
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': 0.5*static_pixel_spacing[:2], 'tolerance': tolerance}, 
    #    'callback': lambda vk: moving.message('Current parameter: ' + str(vk)),
    }
    try:
        translation_estimate = vreg.align_slice_by_slice(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = translation_estimate, 
            resolutions = [1],
            transformation = vreg.translate_inslice,
            metric = func[metric],
            optimization = optimization,
            slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',))),
            progress = lambda z, nz: moving.progress(z+1, nz, 'Coregistering slice-by-slice using translations'),
        )
    except:
        print('Failed to align volumes..')
        translation_estimate = np.zeros(2, dtype=np.float32)

    return translation_estimate


def apply_sbs_inslice_translation(series_moving:Series, parameters:np.ndarray, target:Series=None)->Series:
    """Apply slice-by-slice inslice translation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): list of 3-element numpy arrays with values of the translation that maps the moving volume onto the static volume. The list has one entry per slice of the volume.
        target (dbdicom.Series, optional): If provided, the result is mapped onto the geometry of this series. If none is provided, the result has the same geometry of the moving series. Defaults to None.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        desc_moving = series_moving.instance().SeriesDescription
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]
    
    translation = [vreg.inslice_translation(affine_moving, par) for par in parameters]
    return apply_sbs_translation(series_moving, translation, target=target)


def apply_sbs_passive_inslice_translation(series_moving:Series, parameters:np.ndarray)->Series:
    """Apply slice-by-slice passive translation of an image volume.

    Passive in this context means that the coordinates are transformed rather than the image array itself.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The list contains one entry per slice, ordered by slice location. The vectors are defined in an absolute reference frame in units of mm.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        desc_moving = series_moving.instance().SeriesDescription
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]
    translation = [vreg.inslice_translation(affine_moving, par) for par in parameters]
    return apply_sbs_passive_translation(series_moving, translation)


def find_sbs_translation(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0, prereg=False)->np.ndarray:
    """Find the slice-by-slice translation that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The translation will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin).

    Returns:
        np.ndarray: list of 3-element numpy arrays with values of the translation that maps the moving volume onto the static volume. The list has one entry per slice of the volume.
    """

    if prereg:
        translation = find_translation(moving, static, tolerance=tolerance, metric=metric, region=region, margin=margin)
    else:
        translation = np.zeros(3, dtype=np.float32)

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)

    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }

    # # Find an initial value with a brute force
    # optimization = {
    #     'method': 'brute', 
    #     'options': {'grid':[[-10,10,10], [-10,10,10], [-10,10,10]]}, 
    # }
    # translation = vreg.align_slice_by_slice(
    #     moving = array_moving, 
    #     moving_affine = affine_moving, 
    #     static = array_static, 
    #     static_affine = affine_static, 
    #     transformation = vreg.translate,
    #     metric = func[metric],
    #     optimization = optimization,
    #     slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',))),
    #     progress = lambda z, nz: moving.progress(z+1, nz, 'Performing brute force pre-search'),
    # )

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': 0.1*static_pixel_spacing, 'tolerance': tolerance}, 
    #    'callback': lambda vk: moving.message('Current parameter: ' + str(vk)),
    }

    
    # Perform coregistration
    try:
        translation_estimate = vreg.align_slice_by_slice(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = translation, 
            resolutions = [4,2,1],
            transformation = vreg.translate,
            metric = func[metric],
            optimization = optimization,
            slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',))),
            progress = lambda z, nz: moving.progress(z+1, nz, 'Coregistering slice-by-slice using translations'),
        )
    except:
        print('Failed to align volumes..')
        translation_estimate = None

    return translation_estimate


def apply_sbs_translation(series_moving:Series, parameters:np.ndarray, target:Series=None)->Series:
    """Apply slice-by-slice translation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): list of 3-element numpy arrays with values of the translation that maps the moving volume onto the static volume. The list has one entry per slice of the volume.
        target (dbdicom.Series, optional): If provided, the result is mapped onto the geometry of this series. If none is provided, the result has the same geometry of the moving series. Defaults to None.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    array_moving = series_moving.pixel_values(dims=('SliceLocation',))
    if array_moving.size == 0:
        msg = desc_moving + ' is empty - cannot perform alignment.'
        raise ValueError(msg)
    slice_thickness = series_moving.values('SliceThickness', dims=('SliceLocation',))

    if target is None:
        shape_moved = array_moving.shape
        affine_moved = affine_moving
    else:
        array_moved = target.pixel_values(dims=('SliceLocation',))
        shape_moved = array_moved.shape
        affine_moved = target.affine()

    series_moving.message('Applying slice-by-slice translation..')
    array_moved = vreg.transform_slice_by_slice(array_moving, affine_moving, shape_moved, affine_moved, parameters, vreg.translate, slice_thickness)
    series_moved = series_moving.new_sibling(SeriesDescription = desc_moving + ' [sbs translation]')
    series_moved.set_pixel_values(array_moved, slice={'SliceLocation': np.arange(array_moved.shape[-1])})
    series_moved.set_affine(affine_moved)
    return series_moved


def apply_sbs_passive_translation(series_moving:Series, parameters:np.ndarray)->Series:
    """Apply slice-by-slice passive translation of an image volume.

    Passive in this context means that the coordinates are transformed rather than the image array itself.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The list contains one entry per slice, ordered by slice location. The vectors are defined in an absolute reference frame in units of mm.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    series_moving.message('Applying slice-by-slice passive translation..')
    output_affine = vreg.passive_translation_slice_by_slice(affine_moving, parameters)
    series_moved = series_moving.new_sibling(SeriesDescription = desc_moving + ' [sbs passive translation]')
    frames = series_moving.frames(dims=('SliceLocation',))
    for z in range(frames.size):
        imz = frames[z].copy_to(series_moved)
        #affine_z = output_affine[z]
        #affine_z[:3,2] *= imz.SliceThickness/np.linalg.norm(affine_z[:3,2])
        affine_z = vreg.multislice_to_singleslice_affine(output_affine[z], imz.SliceThickness)
        imz.set_affine(affine_z)
    return series_moved


def find_sbs_rigid_transformation_with_prealign(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0, moving_mask:Series=None, static_mask:Series=None, resolutions=[4,2,1])->np.ndarray:
    """Find the rigid transform that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The rigid transform will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin).

    Returns:
        np.ndarray: 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The vectors are defined in an absolute reference frame in units of mm.
    """

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)
    array_moving_mask, affine_moving_mask = _get_input_volume(moving_mask)
    array_static_mask, affine_static_mask = _get_input_volume(static_mask)

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    rot_gradient_step, translation_gradient_step, _ = vreg.affine_resolution(array_static.shape, static_pixel_spacing)
    gradient_step = np.concatenate((1.0*rot_gradient_step, 0.5*translation_gradient_step))
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': gradient_step, 'tolerance': tolerance}, 
        'callback': lambda vk: moving.message('Current parameter: ' + str(vk)),
    }
    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }
    
    # Align volumes
    try:
        rigid_estimate = vreg.align(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            #parameters = np.array([0, 0, 0, 0, 0, 0], dtype=np.float32), 
            parameters = np.zeros(6, dtype=np.float32),
            resolutions = [4,2,1], 
            transformation =  vreg.rigid,
            metric = func[metric],
            optimization = optimization,
            static_mask = array_static_mask,
            static_mask_affine = affine_static_mask,
            moving_mask = array_moving_mask,
            moving_mask_affine = affine_moving_mask,
        )
    except:
        print('Failed to align volumes..')
        #rigid_estimate = np.array([0, 0, 0, 0, 0, 0], dtype=np.float32)
        rigid_estimate = np.zeros(6, dtype=np.float32)
    
    del optimization['callback']
    try:
        parameters = vreg.align_slice_by_slice(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = rigid_estimate, 
            resolutions = resolutions,
            transformation = vreg.rigid,
            metric = func[metric],
            optimization = optimization,
            slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',))),
            progress = lambda z, nz: moving.progress(z+1, nz, 'Coregistering slice-by-slice using rigid transformations'),
            static_mask = array_static_mask,
            static_mask_affine = affine_static_mask,
            moving_mask = array_moving_mask,
            moving_mask_affine = affine_moving_mask,
        )
    except:
        print('Failed to align slice-by-slice..')
        parameters = None

    return parameters


def find_sbs_rigid_transformation(moving:Series, static:Series, tolerance=0.1, metric='mutual information', region:Series=None, margin:float=0, moving_mask:Series=None, static_mask:Series=None, resolutions=[4,2,1])->np.ndarray:
    """Find the slice-by-slice rigid transformation that maps a moving volume onto a static volume.

    Args:
        moving (dbdicom.Series): Series with the moving volume.
        static (dbdicom.Series): Series with the static volume
        tolerance (float, optional): Positive tolerance parameter to decide convergence of the gradient descent. A smaller value means a more accurate solution but also a lomger computation time. Defaults to 0.1.
        metric (str, option): Determines which metric to use in the optimization. Current options are 'mutual information' (default) or 'sum of squares'.
        region (dbdicom.Series, optional): Series with region of interest to restrict the alignment. The translation will be chosen based on the goodness of the alignment in the bounding box of this region. If none is provided, the entire volume is used. Defaults to None.
        margin (float, optional): in case a region is provided, this specifies a margin (in mm) to take around the region. Default is 0 (no margin).
        moving_mask (dbdicom.Series): Series for masking the moving volume.
        static_mask (dbdicom.Series): Series for masking the static volume.

    Returns:
        np.ndarray: list of 6-element numpy arrays with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The list contains one entry per slice, ordered by slice location. The vectors are defined in an absolute reference frame in units of mm.
    """

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static, region=region, margin=margin)
    array_moving_mask, affine_moving_mask = _get_input_volume(moving_mask)
    array_static_mask, affine_static_mask = _get_input_volume(static_mask)

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    rot_gradient_step, translation_gradient_step, _ = vreg.affine_resolution(array_static.shape, static_pixel_spacing)
    gradient_step = np.concatenate((1.0*rot_gradient_step, 0.5*translation_gradient_step))
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': gradient_step, 'tolerance': tolerance}, 
    }
    func = {
        'sum of squares': vreg.sum_of_squares,
        'mutual information': vreg.mutual_information,
        'interaction': vreg.interaction,
    }
    
    # Perform coregistration
    try:
        parameters = vreg.align_slice_by_slice(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = np.zeros(6, dtype=np.float32), 
            resolutions = resolutions,
            transformation = vreg.rigid,
            metric = func[metric],
            optimization = optimization,
            slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',))),
            progress = lambda z, nz: moving.progress(z+1, nz, 'Coregistering slice-by-slice using rigid transformations'),
            static_mask = array_static_mask,
            static_mask_affine = affine_static_mask,
            moving_mask = array_moving_mask,
            moving_mask_affine = affine_moving_mask,
        )
    except:
        print('Failed to align volumes..')
        parameters = None

    return parameters


def apply_sbs_passive_rigid_transformation(series_moving:Series, parameters:np.ndarray, description=None)->Series:
    """Apply slice-by-slice passive rigid transformation of an image volume.

    Passive in this context means that the coordinates are transformed rather than the image array itself.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The list contains one entry per slice, ordered by slice location. The vectors are defined in an absolute reference frame in units of mm.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.unique_affines()
    if affine_moving.shape[0] > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0,:,:]

    if description is None:
        description = desc_moving + ' [sbs passive rigid]'
    output_affine = vreg.passive_rigid_transform_slice_by_slice(affine_moving, parameters)

    series_moved = series_moving.new_sibling(SeriesDescription = description)
    frames = series_moving.frames(('SliceLocation','InstanceNumber'))
    cnt=0
    for z in range(frames.shape[0]):
        for t in range(frames.shape[1]):
            cnt+=1
            series_moving.progress(cnt, frames.size, 'Applying transformation to ' + desc_moving)
            affine_zt = vreg.multislice_to_singleslice_affine(output_affine[z], frames[z,t].SliceThickness)
            frames[z,t].copy_to(series_moved).set_affine(affine_zt)

    return series_moved



def apply_sbs_rigid_transformation(series_moving:Series, parameters:np.ndarray, target:Series=None)->Series:
    """Apply slice-by-slice rigid transformation of an image volume.

    Args:
        series_moving (dbdicom.Series): Series containing the volune to be moved.
        parameters (np.ndarray): 6-element numpy array with values of the translation (first 3 elements) and rotation vector (last 3 elements) that map the moving volume on to the static volume. The list contains one entry per slice, ordered by slice location. The vectors are defined in an absolute reference frame in units of mm.
        target (dbdicom.Series, optional): If provided, the result is mapped onto the geometry of this series. If none is provided, the result has the same geometry as the moving series. Defaults to None.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orientations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the translated volume.
    """
    desc_moving = series_moving.instance().SeriesDescription
    affine_moving = series_moving.affine()
    if len(affine_moving) > 1:
        msg = 'Multiple slice groups detected in ' + desc_moving + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine_moving = affine_moving[0]

    array_moving = series_moving.pixel_values(dims=('SliceLocation',))
    if array_moving.size == 0:
        msg = desc_moving + ' is empty - cannot perform alignment.'
        raise ValueError(msg)
    slice_thickness = list(series_moving.values('SliceThickness', dims=('SliceLocation',)))

    if target is None:
        shape_moved = array_moving.shape
        affine_moved = affine_moving
    else:
        array_moved = target.pixel_values(dims=('SliceLocation',))
        shape_moved = array_moved.shape
        affine_moved = target.affine()

    series_moving.message('Applying slice-by-slice rigid transformation..')
    array_moved = vreg.transform_slice_by_slice(array_moving, affine_moving, shape_moved, affine_moved, parameters, vreg.rigid, slice_thickness)
    series_moved = series_moving.new_sibling(SeriesDescription = desc_moving + ' [sbs rigid]')
    series_moved.set_pixel_values(array_moved, slice={'SliceLocation': np.arange(array_moved.shape[-1])})
    series_moved.set_affine(affine_moved)
    return series_moved


def rigid_around_com_sos(moving, static, tolerance=0.1):

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static)

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    rot_gradient_step, translation_gradient_step, _ = vreg.affine_resolution(array_static.shape, static_pixel_spacing)
    gradient_step = np.concatenate((1.0*rot_gradient_step, 0.5*translation_gradient_step))
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': gradient_step, 'tolerance': tolerance}, 
        'callback': lambda vk: moving.message('Current parameter: ' + str(vk)),
    }
    
    # Align volumes
    try:
        rigid_estimate = vreg.align(
            moving = array_moving, 
            moving_affine = affine_moving, 
            static = array_static, 
            static_affine = affine_static, 
            parameters = np.array([0, 0, 0, 0, 0, 0], dtype=np.float32), 
            resolutions = [4,2,1], 
            transformation =  vreg.rigid_around_com,
            metric = vreg.sum_of_squares,
            optimization = optimization,
        )
    except:
        print('Failed to align volumes..')
        return None

    coregistered = vreg.rigid_around_com(array_moving, affine_moving, array_static.shape, affine_static, rigid_estimate)
    
    moving.message('Writing coregistered series to database..')
    
    # Save results as new dicom series
    desc = moving.instance().SeriesDescription
    coreg = moving.new_sibling(SeriesDescription = desc + ' [rigid com]')
    coreg.set_pixel_values(coregistered, slice={'SliceLocation': np.arange(coregistered.shape[-1])})
    return coreg


def sbs_rigid_around_com_sos(moving, static, tolerance=0.1):

    array_static, affine_static, array_moving, affine_moving = _get_input(moving, static)
    slice_thickness = list(moving.values('SliceThickness', dims=('SliceLocation',)))

    # Define initial values and optimization
    _, _, static_pixel_spacing = vreg.affine_components(affine_static)
    rot_gradient_step, translation_gradient_step, _ = vreg.affine_resolution(array_static.shape, static_pixel_spacing)
    gradient_step = np.concatenate((1.0*rot_gradient_step, 0.5*translation_gradient_step))
    optimization = {
        'method': 'GD', 
        'options': {'gradient step': gradient_step, 'tolerance': tolerance}, 
        #'callback': lambda vk: moving.message('Current parameter: ' + str(vk)),
    }

    # Perform coregistration
    estimate = vreg.align_slice_by_slice(
        moving = array_moving, 
        static = array_static, 
        parameters = np.array([0, 0, 0, 0, 0, 0], dtype=np.float32), 
        moving_affine = affine_moving, 
        static_affine = affine_static, 
        transformation = vreg.rigid_around_com,
        metric = vreg.sum_of_squares,
        optimization = optimization,
        resolutions = [4,2,1],
        slice_thickness = slice_thickness,
        progress = lambda z, nz: moving.progress(z, nz, 'Coregistering slice-by-slice using rigid transformations'),
    )

    # The generic slice-by-slice transform does not work for center of mass rotations. 
    # Calculate rotation center and use rigid rotation around given center instead.
    estimate_center = [] 
    for z in range(len(estimate)):
        array_moving_z, affine_moving_z = vreg.extract_slice(array_moving, affine_moving, z, slice_thickness)
        center = estimate[z][3:] + vreg.center_of_mass(vreg.to_3d(array_moving_z), affine_moving_z)
        pars = np.concatenate((estimate[z][:3], center, estimate[z][3:]))
        estimate_center.append(pars)
    
    # Calculate coregistered (using rigid around known center)
    coregistered = vreg.transform_slice_by_slice(array_moving, affine_moving, array_static.shape, affine_static, estimate_center, vreg.rigid_around, slice_thickness)

    # Save results as new dicom series
    moving.message('Writing coregistered series to database..')
    desc = moving.instance().SeriesDescription
    coreg = moving.new_sibling(SeriesDescription = desc + ' [sbs rigid com]')
    coreg.set_pixel_values(coregistered, slice={'SliceLocation': np.arange(coregistered.shape[-1])})

    return coreg


def rotate(series:Series, parameters:np.ndarray, reshape=False, output_shape:tuple=None, output_affine:np.ndarray=None, mode='constant', **kwargs)->Series:
    """Rotate a series in 3D

    Args:
        series (dbdicom.Series): Series containing the volume to be rotated.
        parameters (np.ndarray): 3-element numpy array with values of the rotation vector. The vectors are defined in the absolute (scanner) reference frame in units of mm.
        reshape (bool, optional): if True, the array size and affine will be adjusted to contain the complete rotate data. If False, the original array size and affine is retained. Defaults to True.
        output_shape (tuple, optional): determines the shape of the result. If not provided, the shape of the original (reshape=False) or reshaped array (reshape=True) is used. Defaults to False.
        output_affine (ndarray, optional): determines the affine of the result. If not provided, the affine of the original (reshape=False) or reshaped array (reshape=True) is used. Defaults to None.
        mode (str, optional): Determines how the input array is extended beyond its boundaries. See `scipy.ndimage.map_coordinates <https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.map_coordinates.html>`_ for more detail. Defaults to constant = 0.
        kwargs: List of optionional arguments specifying valid DICOM (keyword = value) pairs.

    Raises:
        ValueError: If the moving series contains multiple slice groups with different orentations. 
        ValueError: If the array to be moved is empty.

    Returns:
        dbdicom.Series: Sibling dbdicom series in the same study, containing the rotated volume.
    """

    # Check that the series has a single slice group
    affine = series.unique_affines()
    if affine.shape[0] > 1:
        desc = series.instance().SeriesDescription
        msg = 'Multiple slice groups detected in ' + desc + '\n'
        msg += 'This function only works for series with a single slice group. \n'
        msg += 'Please split the series first.'
        raise ValueError(msg)
    else:
        affine = affine[0,:,:]

    # Check that the array is not empty
    array = series.pixel_values(dims=('SliceLocation',))
    if array.size == 0:
        desc = series.instance().SeriesDescription
        msg = desc + ' is empty - cannot perform alignment.'
        raise ValueError(msg)
    
    # Perform rotation
    series.message('Applying rotation..')
    if reshape:

        # Perform rotation and reshape
        output_arr, output_aff = vreg.rotate_reshape(array, affine, parameters, mode=mode)

        # If no output geometry is specified, return the results as they are.
        if output_shape is None and output_affine is None:
            output_array, output_affine = output_arr, output_aff

        # If an output geometry is specified, reslice the result to this geometry.
        else:
            if output_shape is None:
                output_shape = output_arr.shape
            if output_affine is None:
                output_affine = output_aff 
            output_array, output_affine = vreg.affine_reslice(output_arr, output_aff, output_affine, output_shape)

    else:
        # If not provided, use default values for array shape and affine
        if output_shape is None:
            output_shape = array.shape
        if output_affine is None:
            output_affine = affine
        output_array = vreg.rotate(array, affine, output_shape, output_affine, parameters, mode=mode)

    # Save results in a new series
    output_series = series.new_sibling(WindowCenter=series.WindowCenter, WindowWidth=series.WindowWidth, **kwargs)
    output_series.set_pixel_values(output_array, slice={'SliceLocation': np.arange(output_array.shape[-1])})
    output_series.set_affine(output_affine)

    return output_series