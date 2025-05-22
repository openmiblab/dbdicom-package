#########
Reference
#########

.. warning::

   This reference guide presents the dbdicom version 0.3 API. This 
   replaces the v0.2 API which is no longer supported and will be 
   phased out.


This reference manual details functions, modules, and objects 
included in dbdicom, describing what they are and what they do.
All operations are available via a *functional* and an *object-oriented* 
API. 

The *functional API* is slightly more compact and easier to use 
but also a little slower as the index file of the database is read and 
written at each operation. 

For interactive use or when many operations are performed in rapid 
succession, such as in a loop, the *object-oriented API* may be 
preferable.


**************
Functional API
**************

Summarize the database
----------------------

.. autosummary::
   :toctree: ../api/
   :template: autosummary.rst

   dbdicom.print
   dbdicom.summary


Retrieve information entities
-----------------------------


.. autosummary::
   :toctree: ../api/
   :template: autosummary.rst

   dbdicom.patients
   dbdicom.studies
   dbdicom.series


Edit information entities
-------------------------

.. autosummary::
   :toctree: ../api/
   :template: autosummary.rst

   dbdicom.copy
   dbdicom.delete
   dbdicom.move

Read and write DICOM series
---------------------------

.. autosummary::
   :toctree: ../api/
   :template: autosummary.rst

   dbdicom.volume
   dbdicom.write_volume
   dbdicom.pixel_data
   dbdicom.unique


Import/export to other formats
------------------------------

.. autosummary::
   :toctree: ../api/
   :template: autosummary.rst

   dbdicom.to_nifti
   dbdicom.from_nifti


*******************
Object oriented API
*******************


.. autosummary::
   :toctree: ../api/
   :template: custom-class-template.rst
   :recursive:

   dbdicom.DataBaseDicom
  
   
