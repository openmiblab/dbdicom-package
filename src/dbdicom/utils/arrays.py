import numpy as np


def meshvals(coords):
    # Input array shape: (d, f) with d = nr of dims and f = nr of frames
    # Output array shape: (d, f1,..., fd)
    if coords.size == 0:
        return np.array([])
    # Sort by column
    sorted_indices = np.lexsort(coords[::-1])
    sorted_array = coords[:, sorted_indices]
    # Find shape
    shape = _mesh_shape(sorted_array)  
    # Reshape
    mesh_array = sorted_array.reshape(shape)
    return mesh_array, sorted_indices


def _mesh_shape(sorted_array):
    
    nd = np.unique(sorted_array[0,:]).size
    shape = (sorted_array.shape[0], nd)

    for dim in range(1,shape[0]):
        shape_dim = (shape[0], np.prod(shape[1:]), -1)
        sorted_array = sorted_array.reshape(shape_dim)
        nd = [np.unique(sorted_array[dim,d,:]).size for d in range(shape_dim[1])]
        shape = shape + (max(nd),)

    if np.prod(shape) != sorted_array.size:
        raise ValueError(
            'These are not mesh coordinates.'
            'Make sure to specify dimensions for a multidimensional series.'
        ) 
    
    return shape