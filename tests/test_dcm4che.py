import os
import shutil
import numpy as np
import pydicom

import dbdicom.utils.dcm4che as dcm4che

datapath = os.path.join(os.path.dirname(__file__), 'data')
multiframe = os.path.join(datapath, 'MULTIFRAME')
MOLLI_enhanced = os.path.join(datapath, 'MOLLI_enhanced')

# Helper functions

def create_tmp_database(path):
    tmp = os.path.join(os.path.dirname(__file__), 'tmp')
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    shutil.copytree(path, tmp)
    return tmp




def test_multiframe_conversion():

    tmp = create_tmp_database(multiframe)
    multiframe_files = [os.path.join(tmp, f) for f in os.listdir(tmp) if os.path.isfile(os.path.join(tmp, f))]
    multiframe_files = [f for f in multiframe_files if os.path.basename(f) in ['IM_0010','IM_0014']]
    for file in multiframe_files:
        singleframe_files = dcm4che.split_multiframe(file)
        assert [] != singleframe_files
        assert len(singleframe_files) in [20, 104]
        for f in singleframe_files:
            ds = pydicom.dcmread(f, force=True)
            assert ds.SeriesDescription in ['Cor_B0map_BH', 'Ax_localiser_BH']
    shutil.rmtree(tmp)

def test_multiframe_conversion_with_raw_data():

    tmp = create_tmp_database(MOLLI_enhanced)
    multiframe_files = [os.path.join(tmp, f) for f in os.listdir(tmp) if os.path.isfile(os.path.join(tmp, f))]
    for file in multiframe_files:
        singleframe_files = dcm4che.split_multiframe(file)
        for f in singleframe_files:
            ds = pydicom.dcmread(f, force=True)
    shutil.rmtree(tmp)



if __name__ == "__main__":

    test_multiframe_conversion()
    test_multiframe_conversion_with_raw_data()

    print('-------------------------')
    print('dcm4che passed all tests!')
    print('-------------------------')

