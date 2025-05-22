**********************************
Creating and modifying DICOM files
**********************************

Reading DICOM attributes
^^^^^^^^^^^^^^^^^^^^^^^^

An object's DICOM attributes can be read by using the DICOM keyword of the attribute:

.. code-block:: python

    nr_of_rows = series.Rows


All attributes can be accessed at series, study, patient or folder level and will return a list of unique values. For instance to return a list with all distinct series descriptions in a study:

.. code-block:: python

    desc = study.SeriesDescription

DICOM attributes can also be accessed using the list notation, using either the keyword as a string or a (group, element) pair:

.. code-block:: python

    columns = series['Columns']
    columns = series[(0x0028, 0x0010)]

The tags can also be accessed as a list, for instance:

.. code-block:: python

    dimensions = ['Rows', (0x0028, 0x0010)]
    dimensions = series[dimensions] 


This will return a list with two items. As shown in the example, the items in the list can be either KeyWord strings or (group, element) pairs. This also works on higher-level objects:

.. code-block:: python

    dimensions = ['Rows', (0x0028, 0x0010)]
    dimensions = patient[dimensions] 


Editing attributes
^^^^^^^^^^^^^^^^^^


DICOM tags can be modified using the same notations:

.. code-block:: python

    series.EchoTime = 23.0

or also:

.. code-block:: python

    series['EchoTime'] = 23.0

or also:

.. code-block:: python

    series[(0x0018, 0x0081)] = 23.0

Multiple tags can be inserted in the same line:

.. code-block:: python

    shape = ['Rows', 'Columns']
    series[shape] = [128, 192]

When setting values in a series, study or patient, all the datasets in the object will be modified. For instance, to set all the Rows in all datasets of a series to 128:

.. code-block:: python

    series.Rows = 128


Custom attributes
^^^^^^^^^^^^^^^^^

Apart from the predefined public and private DICOM keywords, ``dbdicom`` also provides a number of custom attributes for more convenient access to higher level properties. In order to distinguish these from existing DICOM attributes which are defined in *CamelCase*, the custom attributes follow the *lower_case* notation. 

For instance, to set one of the standard `matplotlib color maps <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_, you can do:

.. code-block:: python

    series.colormap = 'YlGnBu'
    series.colormap = 'Oranges'


and so on.. The colormaps can be retrieved the same way:

.. code-block:: python

    cm_series = series.colormap


As for standard DICOM attributes this returns a list if unique values for the series. 

Custom attributes can easily be added to any DICOM dataset type and the number of available attributes is set to grow as the need arises.


Save and restore
^^^^^^^^^^^^^^^^

All changes made in a DICOM folder are reversible until they are saved.
To save all changes, use ``save()``:

.. code-block:: python

    database.save()

This will permanently save all changes. In order to reverse any changes made, use ``restore()`` to revert back to the last saved state:

.. code-block:: python

    database.restore()


This will roll back all changes on disk to the last changed state. ``save()`` and ``restore()`` can also be called at the level of individual objects:

.. code-block:: python

    series.restore()

will reverse all changes made since the last save, but only for this series. Equivalently:

.. code-block:: python

    series.save()


will save all changes made in the series (but not other objects in the database) permanently. 


Working with series
^^^^^^^^^^^^^^^^^^^

A DICOM series typically represents images that are acquired together, such as 3D volumes or time series. Some dedicated functionality exists for series that is not relevant for objects elsewhere in the hierarchy. 

To extract the images in a series as a numpy array, use ``array()``:

.. code-block:: python

    array = series.pixel_values()


This will return an array with dimensions ``(x,y,n)`` where ``n`` enumerates the images in the series. The array can also be returned with other dimensions:

.. code-block:: python

    array = series.pixel_values(dims=('SliceLocation', 'FlipAngle'))


This returns an array with dimensions ``(x,y,z,t)`` where ``z`` corresponds to slice locations and ``t`` to flip angles. Any number of dimensions can be added in this way. 

Replacing the images of a series with a given numpy array works the same way:

.. code-block:: python

    series.set_pixel_values(array, dims=('SliceLocation', 'FlipAngle'))


Another useful tool on series level is extracting a subseries. Let's say we have an MRI series with phase and magnitude data mixed, and we want to split it up into separate series:


.. code-block:: python

    phase = series.subseries(image_type='PHASE')
    magn = series.subseries(image_type='MAGNITUDE')

This will create two new series in the same study. The ``image_type`` keyword is defined in dbdicom for MR images to simplify access to phase or magnitude data, but the method also works for any standard DICOM keyword, or combinations thereof. For instance, to extract a subseries of all images with a flip angle of 20 and a TR of 5:

.. code-block:: python

    sub = series.subseries(FlipAngle=20, RepetitionTime=5)

As an example of additional functions that can be built on top of standard packages, consider the use of scipy's ``map_coordinates`` function to overly two images. The pipeline for scipy provides a wrapper for this functions which makes the operation available directly on ``dbdicom`` series:

.. code-block:: python

    from dbdicom.extensions import scipy
    overlay = scipy.map_to(series, target)

If series is a binary mask (or can be interpreted as one), a similar function can be used to overlay the mask on another series:

.. code-block:: python

    overlay = scipy.map_mask_to(series, target)


Creating DICOM data from scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To create a DICOM series from a numpy array, use ``dbdicom.series()``:

.. code-block:: python

    import numpy as np
    import dbdicom as db

    array = np.random.normal(size=(10, 128, 192))
    series = db.as_series(array)


After this you can save it to a folder in DICOM, or set some header elements before saving:

.. code-block:: python

    series.PatientName = 'Random noise'
    series.StudyDate = '19112022'
    series.AcquisitionTime = 12*60*60
    series.save(path)

You can build an entire database explicitly as well. For instance, the following code builds a database with two patients (James Bond and Scarface) who each underwent and MRI and an XRay study:

.. code-block:: python

    database = db.database()

    james_bond = database.new_patient(PatientName='James Bond')
    james_bond_mri = james_bond.new_study(StudyDescription='MRI')
    james_bond_mri_localizer = james_bond_mri.new_series(SeriesDescription='Localizer')
    james_bond_mri_T2w = james_bond_mri.new_series(SeriesDescription='T2w')
    james_bond_xray = james_bond.new_study(StudyDescription='Xray')
    james_bond_xray_chest = james_bond_xray.new_series(SeriesDescription='Chest')
    james_bond_xray_head = james_bond_xray.new_series(SeriesDescription='Head')

    scarface = database.new_patient(PatientName='Scarface')
    scarface_mri = scarface.new_study(StudyDescription='MRI')
    scarface_mri_localizer = scarface_mri.new_series(SeriesDescription='Localizer')
    scarface_mri_T2w = scarface_mri.new_series(SeriesDescription='T2w')
    scarface_xray = scarface.new_study(StudyDescription='Xray')
    scarface_xray_chest = scarface_xray.new_series(SeriesDescription='Chest')
    scarface_xray_head = scarface_xray.new_series(SeriesDescription='Head')


Creating objects
^^^^^^^^^^^^^^^^

Some routines are available for creating DICOM objects from scratch, modelled on ``numpy`` creation routines. For instance, to create a new series with given dimensions:

.. code-block:: python

    import dbdicom as db
    series = db.series((10, 128, 192))

This will create a DICOM series of type 'MRImage' (shorthand 'mri') with 10 slices of 128 columns and 192 rows each. Currently, writing in data types other than 'MRImage' is not supported, so the data type argument is not necessary.