***********************
Browsing a DICOM folder
***********************


Reading and opening a DICOM database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open a DICOM database in a given folder, and print a summary of the content:

.. code-block:: python

    import dbdicom as db

    database = db.database('C:\\Users\\MyName\\MyData\\DICOMtestData')
    database.print()

The first time the database is opened this will be relatively slow because all files need to be read and summarized. If the folder is reopened again later, the table can be read directly and opening will be much faster. 

Use ``scan()`` to force a rereading of the database. This may be of use when files have become corrupted, or have been removed/modified by external applications:

.. code-block:: python

    database.scan()

After making changes to the DICOM data, the folder should be closed 
properly so any changes can be either saved or rolled back as needed:

.. code-block:: python

    database.close()

If unsaved changes exist, ``close()`` will prompt the user to either save or restore to the last saved state.


Retrieving objects from the folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A DICOM database has a hierarchical structure. 

::

    database
    ├── Patient 1
    │   ├── Study 1
    │   │   ├── Series 1
    │   │   ├── ...
    │   │   └── Series n
    │   │── Study 2
    │   ├── ...
    │   └── Study n
    ├── Patient 2
    ├── ...          
    └── Patient n          


A *patient* can be an actual patient but can also be a healthy volunteer, an animal, a physical reference object, or a digital reference object. Typically a *study* consist of all the data derived in a single examination of a subject. A *series* usually represents and individual examination in a study, such an MR sequence. The files contain the data and are *instances* of real-world objects such as images or regions-of-interest. 

To return a list of all patients, studies or series in the folder: 

.. code-block:: python

    series = database.series()
    studies = database.studies()
    patients = database.patients()

The same functions can be used to retrieve the children of a certain parent object. For instance, to get all studies of a patient:

.. code-block:: python

    studies = patient.studies()


Or all series under the first of those studies:

.. code-block:: python

    series = studies()[0].series()


And so on for all other levels in the hierarchy. These functions also work to find objects higher up in the hierarchy. For instance, to find the patient of a given series:

.. code-block:: python

    patient = series.patients()


In this case the function will return a single item.

Finding DICOM objects in the folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each DICOM file has a number of attributes describing the properties of the object. Examples are PatientName, StudyDate, etc. A convenient list of attributes for specific objects can be found `here <https://dicom.innolitics.com/>`_.

Each known attribute is identified most easily by a keyword, which has a capitalised notation. Objects in the folder can be can also be listed by searching on any DICOM tag:

.. code-block:: python

    series = database.series(PatientName = 'John Dory')


This will only return the series for patient John Dory. This also works with multiple DICOM tags:

.. code-block:: python

    series = database.series(
        PatientName = 'John Dory', 
        ReferringPhysicianName = 'Dr. No', 
    )


In this case objects are only returned if both conditions are fullfilled. Any arbitrary number of conditions can be entered, and higher order objects can be found in the same way:

.. code-block:: python

    studies = database.studies(
        PatientName = 'John Dory', 
        ReferringPhysicianName = 'Dr. No', 
    )


As an alternative to calling explicit object types, you can call ``children()`` and ``parent`` to move through the hierarchy:

.. code-block:: python

    studies = patient.children()
    patient = studies[0].parent


The same convenience functions are available, such as searching by keywords:

.. code-block:: python

    studies = patient.children(ReferringPhysicianName = 'Dr. No')


Moving and removing objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To remove an object from the folder, call ``remove()`` on the object:

.. code-block:: python

    study.remove()
    series.remove()


``remove()`` can  be called on Patient, Study or Series.

Moving an object to another parent can be done with ``move_to()``. For instance to move a study from one patient to another:

.. code-block:: python

    study = folder.patients()[0].studies()[0]
    new_parent = folder.patients()[1]
    study.move_to(new_parent)


Copying and creating objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Any object can be copied by calling ``copy()``: 

.. code-block:: python

    study = folder.patients()[0].studies()[0]
    new_study = study.copy()


This will create a copy of the object in the same parent object, i.e. ``study.copy()`` in the example above has created a new study in patient 0. This can be used for instance to copy-paste a study from one patient to another: 

.. code-block:: python

    study = folder.patients()[0].studies()[0]
    new_parent = folder.patients()[1]
    study.copy().move_to(new_parent)

This is equivalent to using ``copy_to()``:

.. code-block:: python

    study.copy_to(new_parent)   

Instead of copying, and object can also be moved:

.. code-block:: python

    study.move_to(new_parent)   

To create a new object, call ``new_child()`` on the parent:

.. code-block:: python

    series = study.new_child()

*series* will now be a new (empty) series under *study*. This can also be written more explicitly for clarity:

.. code-block:: python

    series = study.new_series()

And equivalently for ``new_patient`` and ``new_study``. New sibling objects under the same parent can be created by:

.. code-block:: python

    new_series = series.new_sibling()

here ``new_series`` will be a series under the same study as ``series``. Objects higher up the hierarchy can be created using ``new_pibling`` (i.e. sibling of the parent):

.. code-block:: python

    new_study = series.new_pibling()


This is shorthand for:

.. code-block:: python

    new_study = series.parent().new_sibling()


When new objects are created, they can be assigned properties up front, for instance:

.. code-block:: python

    new_study = series.new_pibling(
        StudyDescription='Parametric maps',
        StudyDate = '12.12.22')


This will ensure that all data that appear under the new study will have these attributes. 


Export and import
^^^^^^^^^^^^^^^^^

To import DICOM files from an external folder, call ``import_dicom()`` on a database with a list of files:

.. code-block:: python

    database.import_dicom(files)


To export dicom datasets out of the folder to an external folder, call ``export_as_dicom()`` on any dicom object with the export path as argument:

.. code-block:: python

    series.export_as_dicom(path)


Exporting in other formats is similar:

.. code-block:: python

    study.export_as_csv(path)
    study.export_as_nifti(path)
    study.export_as_png(path)


The pixel data from a series can also be exported in numpy format:

.. code-block:: python

    series.export_as_npy(path)

This exports the array in dimensions ``(x,y,n)`` where ``n`` enumerates the images and ``x,y`` are the pixels. To export in different dimensions use the ``sortby`` keyword with one or more DICOM tags:

.. code-block:: python

    series.export_as_npy(path, sortby=['SliceLocation','AcquisitionTime'])


This exports an array with dimensions ``(x,y,z,t,n)`` sorted by slice location and acquisition time.
