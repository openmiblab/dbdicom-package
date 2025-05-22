dbdicom
=======

.. image:: https://img.shields.io/badge/License-Apache_2.0-blue.svg
  :target: https://opensource.org/licenses/Apache-2.0


A python interface for reading and writing DICOM databases
----------------------------------------------------------

- **Documentation:** https://openmiblab.github.io/dbdicom/
- **Source code:** https://github.com/openmiblab/dbdicom


Installation
------------

.. code-block:: console

    pip install dbdicom


Aim
---

Simplify import and export of medical imaging data in DICOM format, 
increase the transparancy of post-processing pipelines for medical 
imaging biomarkers and improving standardization by avoiding the 
need for multiple data formats.

Status
------

`dbdicom` version 0.2 (lates 0.2.6) is stable and has been rolled 
out in image processing pipelines of ongoing studies 
`iBEAt <https://bmcnephrol.biomedcentral.com/articles/10.1186/s12882-020-01901-x>`_
and
`AFiRM <ttps://www.uhdb.nhs.uk/afirm-study/>`_,
but is no longer supported and will be phased out.

Version 0.3 is a major rewrite based on these experiences aiming to 
simplify the code base and the API, and improve efficiency and 
coverage of DICOM SOP classes. Version 0.3 is currently *work in 
progress* and changes are not backwards compatible with version 0.2.

The API reference shows version 0.3 functionality but the user guide 
is for version 0.2. Updates are expected shortly.

Citing
------

When you use ``dbdicom``, please cite: 

Steven Sourbron, Joao Almeida e Sousa, Alexander Daniel, 
Charlotte Buchanan, Ebony Gunwhy, Eve Lennie, Kevin Teh, 
Steve Shillitoe, David Morris, Andrew Priest, David Thomas, and 
Susan Francis. dbdicom: an open-source python interface for reading 
and writing DICOM databases. `Proc Intl Soc Mag Reson Med 
(Toronto, Canada) <https://www.ismrm.org/23m/>`_, #3248, 2023.


License
-------

``dbdicom`` is distributed under the 
`Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`_ license - a 
permissive, free license that allows users to use, modify, and 
distribute the software without restrictions::

  Copyright (C) 2023-2025 dbdicom developers

