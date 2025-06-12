import os
import shutil
import numpy as np
import dbdicom as db
import vreg


tmp_path = os.path.join(os.getcwd(), 'tmp')


def test_write_volume():
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    values = 100*np.random.rand(128, 192, 20).astype(np.float32)
    vol = vreg.volume(values)
    series = [tmp_path, '007', 'dbdicom_test', 'random_axial']
    db.write_volume(vol, series)
    shutil.rmtree(tmp_path)


if __name__ == '__main__':

    test_write_volume()

    print('All api tests have passed!!!')