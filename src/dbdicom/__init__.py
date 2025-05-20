# OLD API

from dbdicom.create import (
    database, 
    patient,
    study,
    series, 
    as_series,
    zeros,
    ones,
    empty_series,
)
from dbdicom.record import (
    copy_to, 
    move_to, 
    group, 
    merge, 
)
from dbdicom.types.series import (
    array
)
from dbdicom.record import Record
from dbdicom.types.database import Database
from dbdicom.types.patient import Patient
from dbdicom.types.study import Study
from dbdicom.types.series import Series
from dbdicom.utils import image
from dbdicom import extensions
from dbdicom import dro

# New API

from dbdicom.api import *