# Importing annotations to handle or sign in import type hints
from __future__ import annotations

import os
import numpy as np
from dbdicom.manager import Manager
from dbdicom.types.database import Database
from dbdicom.types.patient import Patient
from dbdicom.types.study import Study
from dbdicom.types.series import Series, _grid_to_coords
from dbdicom.types.instance import Instance


def create(manager, uid='Database', type=None, key=None, **kwargs):

    if uid is None:
        return
    if uid == 'Database':
        return Database(create, manager, **kwargs)

    # This case is included for convenience but should be avoided 
    # at all costs because the lookup of type at creation is very expensive.
    # Considering removing and make type a requirement
    if type is None:
        type = manager.type(uid)

    if type == 'Patient':
        return Patient(create, manager, uid, key=key, **kwargs)
    if type == 'Study':
        return Study(create, manager, uid, key=key, **kwargs)
    if type == 'Series':
        return Series(create, manager, uid, key=key, **kwargs)
    if type == 'Instance':
        return Instance(create, manager, uid, key=key, **kwargs)


def database(path:str=None, **kwargs) -> Database:
    """create a new database in memory or open an existing one on disk.

    Args:
        path (str, optional): path to an existing database. In case none is provided, this will create a new empty database.
        kwargs: any valid DICOM (tag, value) pair can be provided as keyword argument. These attributes will be assigned to the database and inherited by all DICOM objects later saved in the database.

    Returns:
        Database: Instance of the Database class.

    Note:
        If no path is provided, a new database is created in memory. Any changes or additions to that database will only exist in memory until the new database is saved with .save().

    See Also:
        :func:`~patient`
        :func:`~study`
        :func:`~series`
    
    Example:

        Create a new database in memory and print the contents:

        >>> database = db.database()
        >>> database.print()
        ---------- DATABASE --------------
        Location:  In memory
        ----------------------------------

        Open an existing DICOM database and check the contents (in this example we are using an edited version of a RIDER dataset case):

        >>> database = db.database('path\\to\\RIDER\\case')
        >>> database.print()
        ---------- DATABASE --------------
        Location:  path\to\DICOM\database
            Study BRAIN^RESEARCH [19040321]
                Series 014 [sag 3d gre +c]
                    Nr of instances: 176
            Study BRAIN^RESEARCH [19040321]
                Series 017 [sag 3d flair +c]
                    Nr of instances: 210
            Study BRAIN^RESEARCH [19040321]
                Series 005 [ax tensor]
                    Nr of instances: 468
                Series 006 [ax 5 flip]
                    Nr of instances: 16
                Series 007 [ax 10 flip]
                    Nr of instances: 16
                Series 008 [ax 15 flip]
                    Nr of instances: 16
                Series 009 [ax 20 flip]
                    Nr of instances: 16
                Series 010 [ax 25 flip]
                    Nr of instances: 16
                Series 011 [ax 30 flip]
                    Nr of instances: 16
                Series 012 [perfusion]
                    Nr of instances: 1040
            Study BRAIN^RESEARCH [19040323]
                Series 017 [sag 3d flair +c]
                    Nr of instances: 160
                Series 018 [sag 3d flair +c_Copy]
                    Nr of instances: 160
                Series 019 [MergedSeries]
                    Nr of instances: 320
            Study BRAIN^RESEARCH [19040323]
                Series 005 [ax tensor]
                    Nr of instances: 468
                Series 006 [ax 5 flip]
                    Nr of instances: 16
                Series 007 [ax 10 flip]
                    Nr of instances: 16
                Series 008 [ax 15 flip]
                    Nr of instances: 16
                Series 009 [ax 20 flip]
                    Nr of instances: 16
                Series 010 [ax 25 flip]
                    Nr of instances: 16
                Series 011 [ax 30 flip]
                    Nr of instances: 16
                Series 012 [perfusion]
                    Nr of instances: 1040
            Study BRAIN^RESEARCH [19040323]
                Series 015 [sag 3d gre +c]
                    Nr of instances: 176
        ----------------------------------
    """

    if path is None:
        mgr = Manager()
    elif not os.path.exists(path):
        raise NameError(
            f"Database {path} does not exist. "
        )
    else:
        mgr = Manager(path, **kwargs)
        mgr.open(path)
    return Database(create, mgr, **kwargs) 


def patient(in_database:Database=None, **kwargs)->Patient: 
    """Create an empty DICOM patient record.

    Args:
        in_database (Database, optional): If provided, the patient is created in this database. Defaults to None.
        kwargs: Any valid DICOM (tag, value) pair to set properties of the new patient

    Returns:
        Study: DICOM patient with defaults for all attributes.

    See Also:
        :func:`~database`
        :func:`~study`
        :func:`~series`

    Example:
        Create an empty patient in memory:

        >>> patient = db.patient()
        >>> patient.print()
        ---------- PATIENT -------------
        Patient New Patient
        --------------------------------

        Note since no patient object is provided, a default database is created automatically.

        >>> patient.database().print()
        ---------- DATABASE --------------
        Location:  In memory
            Patient New Patient
        ----------------------------------
    """
    if in_database is None:
        db = database()
    else:
        db = in_database
    patient = db.new_patient(**kwargs)
    if in_database is None:
        db.save()
    return patient


def study(in_patient:Patient=None, in_database:Database=None, **kwargs)->Study: 
    """Create an empty DICOM study record.

    Args:
        in_patient (Patient, optional): If provided, the study is created in this Patient. Defaults to None.
        in_database (Database, optional): If provided, the study is created in this database. Defaults to None.
        kwargs: Any valid DICOM (tag, value) pair to set properties of the new study

    Returns:
        Study: DICOM study with defaults for all attributes.

    See Also:
        :func:`~database`
        :func:`~patient`
        :func:`~series`

    Example:
        Create an empty study in memory:

        >>> study = db.study()
        >>> study.print()
        ---------- STUDY ---------------
        Study New Study [None]
        --------------------------------

        Note since no patient object is provided, a default hierarchy is created automatically:

        >>> study.database().print()
        ---------- DATABASE --------------
        Location:  In memory
            Patient New Patient
                Study New Study [None]
        ----------------------------------
    """
    
    if in_patient is not None:
        study = in_patient.new_study(**kwargs)
    else:
        if in_database is None:
            db = database()
        else:
            db = in_database
        patient = db.new_patient()
        study = patient.new_study(**kwargs)
        if in_database is None:
            db.save()
    return study


def series(dtype='mri', in_study:Study=None, in_database:Database=None, **kwargs)->Series: 
    """Create an empty DICOM series.

    Args:
        dtype (str, optional): The type of the series to create. Defaults to 'mri'.
        in_study (Study, optional): If provided, the series is created in this study. Defaults to None.
        in_database (Database, optional): If provided, the series is created in this database. Defaults to None.
        kwargs: Any valid DICOM (tag, value) pair to set properties of the new patient

    Returns:
        Series: DICOM series with defaults for all attributes.
 
    Raises:
        ValueError: if a dtype is requested that is currently not yet implemented

    See Also:
        :func:`~database`
        :func:`~patient`
        :func:`~study`
        :func:`~as_series`
        :func:`~zeros`

    Example:
        Create an empty series in memory. 

        >>> series = db.series()
        >>> series.print()
        ---------- SERIES --------------
        Series 001 [New Series]
            Nr of instances: 0
        --------------------------------

        Note since no patient and study records are provided, a default hierarchy is created automatically:

        >>> series.database().print()
        ---------- DATABASE --------------
        Location:  In memory
        Patient New Patient
            Study New Study [None]
                Series 001 [New Series]
                    Nr of instances: 0
        ----------------------------------
    """
    if dtype not in ['mri', 'MRImage']:
        message = 'dbdicom can only create images of type MRImage at this stage'
        raise ValueError(message)
    
    if in_study is not None:
        series = in_study.new_series()
    else:
        if in_database is None:
            _database = database()
            _database.mute()
        else:
            _database = in_database
        patient = _database.new_patient()
        study = patient.new_study()
        series = study.new_series(**kwargs)
        if in_database is None:
            _database.save()
    return series


def as_series(array:np.ndarray, coords:dict=None, gridcoords:dict=None, dtype='mri', in_study:Study=None, in_database:Database=None, **kwargs)->Series:
    """Create a DICOM series from a numpy array.

    Args:
        array (np.ndarray): numpy.ndarray with image data
        coords (dict, optional): Dictionary with coordinate labels and values. For 3- or 4-dimensional arrays this is optional but for arrays with more than 4 dimensions either *coords* or *gridcoords* are required. 
        gridcoords (dict, optional): regularly gridded coordinates can also be provided as a coordinate grid.
        dtype (str, optional): The type of the series to create. Defaults to 'mri'.
        in_study (Study, optional): If provided, the series is created in this study. Defaults to None.
        in_database (Database, optional): If provided, the series is created in this database. Defaults to None.
        kwargs: Any valid DICOM (tag, value) pair to set properties of the new patient

    Returns:
        Series: DICOM series containing the provided array as image data and defaults for all other parameters.
 
    Raises:
        ValueError: if a dtype is requested that is currently not yet implemented
        ValueError: If the coords do not match up with the shape of the array.

    See Also:
        :func:`~series`
        :func:`~zeros`

    Example:
        Create a series containing a 4-dimensional array. Since the default format is single-frame MRImage, this produces 6 separate files.

        >>> array = np.zeros((128, 128, 3, 2))
        >>> zeros = db.as_series(array)
        >>> zeros.print()
        ---------- SERIES --------------
        Series 001 [New Series]
            Nr of instances: 6 
                MRImage 000001   
                MRImage 000002   
                MRImage 000003
                MRImage 000004
                MRImage 000005
                MRImage 000006
        --------------------------------

        Since no coordinates are provided, these are assumed to be SliceLocation and AcquisitionTime with default values:

        >>> print(zeros.SliceLocation)
        [0.0, 1.0, 2.0]
        >>> print(zeros.AcquisitionTime)
        [0.0, 1.0]

        To override these defaults, set coordinates explicitly using a dictionary. For instance, for an MRI series of images acquired at a single slice location for 3 flip angles and 2 repetition times, the coordinates of the series are:

        >>> coords = {
        ...    'FlipAngle': [2, 15, 30],
        ...    'RepetitionTime': [2.5, 5.0],
        ... }

        Now create another series, providing coordinates, and list the unique values of flip angle and repetition time:
        >>> zeros = db.as_series(array, coords)
        >>> print(zeros.FlipAngle)
        [2.0, 15.0, 30.0]
        >>> print(zeros.RepetitionTime)
        [2.5, 5.0]
    """
    shape = array.shape
    if coords is None:
        if gridcoords is None:
            if len(shape) > 4:
                msg = 'With more than 4 dimensions, the coords argument is required.'
                raise ValueError(msg)
            gridcoords = {}
            if len(shape) == 2:
                gridcoords['InstanceNumber'] = np.array([1])
            if len(shape) > 2:
                gridcoords['SliceLocation'] = np.arange(shape[2])
            if len(shape) > 3:
                gridcoords['AcquisitionTime'] = np.arange(shape[3])
    if gridcoords is not None:
        coords = _grid_to_coords(gridcoords)
    sery = series(dtype=dtype, in_study=in_study, in_database=in_database, **kwargs)
    sery.expand(coords)
    sery.set_pixel_values(array, dims=tuple(coords))
    return sery


def empty_series(coords:dict=None, gridcoords:dict=None,  dtype='mri', in_study:Study=None, in_database:Database=None, **kwargs)->Series:

    if gridcoords is not None:
        coords = _grid_to_coords(gridcoords)
    sery = series(dtype=dtype, in_study=in_study, in_database=in_database, **kwargs)
    if coords is None:
        return sery
    sery.expand(coords)
    return sery


def zeros(shape:tuple, coords:dict=None, gridcoords:dict=None, **kwargs) -> Series:
    """Create a DICOM series populated with zeros.

    This is a convenience wrapper providing a numpy-like interface for :func:`~as_series`.

    Args:
        shape (tuple): shape of the array
        kwargs: see :func:`~series`
        
    Returns:
        Series: DICOM series with zero values

    See Also:
        :func:`~ones`

    Example:
        Create a series containing a 4-dimensional array of zeros:

        >>> zeros = db.zeros((128, 128, 2, 3))
        >>> zeros.print()
        ---------- SERIES --------------
        Series 001 [New Series]
            Nr of instances: 6
                MRImage 000001
                MRImage 000002
                MRImage 000003
                MRImage 000004
                MRImage 000005
                MRImage 000006
        --------------------------------

        This is effectively shorthand for:
        
        >>> array = np.zeros((128, 128, 2, 3))
        >>> zeros = db.as_series(array)
    """

    array = np.zeros(shape, dtype=np.float32)
    return as_series(array, coords=coords, gridcoords=gridcoords, **kwargs)


def ones(shape:tuple, coords:dict=None, gridcoords:dict=None, **kwargs) -> Series:
    """Create a DICOM series populated with ones.

    This is a convenience wrapper providing a numpy-like interface for :func:`~as_series`.

    Args:
        shape (tuple): shape of the array
        kwargs: see :func:`~series`
        
    Returns:
        Series: DICOM series with values of one.

    See Also:
        :func:`~zeros`

    Example:
        Create a series containing a 4-dimensional array of ones:

        >>> zeros = db.ones((128, 128, 2, 3))
        >>> zeros.print()
        ---------- SERIES --------------
        Series 001 [New Series]
            Nr of instances: 6
                MRImage 000001
                MRImage 000002
                MRImage 000003
                MRImage 000004
                MRImage 000005
                MRImage 000006
        --------------------------------

        This is effectively shorthand for:
        
        >>> array = np.ones((128, 128, 2, 3))
        >>> zeros = db.as_series(array)
    """
    array = np.ones(shape, dtype=np.float32)
    return as_series(array, coords=coords, gridcoords=gridcoords, **kwargs)







