import os
import shutil
import numpy as np
import dbdicom as db
import vreg


tmp = os.path.join(os.getcwd(), 'tests', 'tmp')
os.makedirs(tmp, exist_ok=True)


def test_write_volume():
    values = 100*np.random.rand(128, 192, 20).astype(np.float32)
    vol = vreg.volume(values)
    series = [tmp, '007', 'dbdicom_test', 'ax']
    db.write_volume(vol, series)
    shutil.rmtree(tmp)

def test_volume():
    values = 100*np.random.rand(128, 192, 20).astype(np.float32)
    vol = vreg.volume(values)
    series = [tmp, '007', 'test', 'ax']
    db.write_volume(vol, series)
    vol2 = db.volume(series)
    assert np.linalg.norm(vol2.values-vol.values) < 0.0001*np.linalg.norm(vol.values)
    assert np.linalg.norm(vol2.affine-vol.affine) == 0
    shutil.rmtree(tmp)

def test_write_database():
    values = 100*np.random.rand(16, 16, 4).astype(np.float32)
    vol = vreg.volume(values)
    db.write_volume(vol, [tmp, '007', 'test', 'ax'])    # create series ax
    db.write_volume(vol, [tmp, '007', 'test', 'ax'])    # add to it
    db.write_volume(vol, [tmp, '007', 'test', ('ax', 0)])   # add to it
    db.write_volume(vol, [tmp, '007', 'test', ('ax', 1)])   # create a new series ax
    db.write_volume(vol, [tmp, '007', 'test', ('ax', 3)])   # create a new series ax
    try:
        db.write_volume(vol, [tmp, '007', 'test', 'ax'])   # Ambiguous
    except:
        assert True
    else:
        assert False
    db.write_volume(vol, [tmp, '008', 'test', 'ax'])            # Create a new patient
    db.write_volume(vol, [tmp, '008', 'test', 'ax-2'])          # Add a new series
    db.write_volume(vol, [tmp, '008', ('test', 0), 'ax'])       # Add to the series ax 
    db.write_volume(vol, [tmp, '008', ('test', 1), 'ax'])       # Add to a new study
    try:
        db.write_volume(vol, [tmp, '008', 'test', 'ax'])       # Ambiguous
    except:
        assert True
    else:
        assert False

    series = db.series(tmp)
    [print(s) for s in series]

    assert ('ax', 2) in [s[-1] for s in series]
    assert [] == db.series(tmp, contains='b')
    assert 2 == len(db.patients(tmp))
    assert 2 == len(db.patients(tmp, name='Anonymous'))

    shutil.rmtree(tmp)

def test_copy():
    tmp1 = os.path.join(tmp, 'dir1')
    tmp2 = os.path.join(tmp, 'dir2')
    os.makedirs(tmp1, exist_ok=True)
    os.makedirs(tmp2, exist_ok=True)
    values = 100*np.random.rand(16, 16, 4).astype(np.float32)
    vol = vreg.volume(values)
    db.write_volume(vol, [tmp1, '007', 'test', 'ax'])    # create series ax
    db.write_volume(vol, [tmp1, '007', 'test2', 'ax2'])    # create series ax
    db.copy([tmp1, '007', 'test2', 'ax2'], [tmp2, '007', 'test2', 'ax2'])
    db.copy([tmp1, '007', 'test2', 'ax2'], [tmp2, '007', 'test2', 'ax'])
    db.copy([tmp1, '007', 'test2', 'ax2'], [tmp2, '007', 'test2', 'ax'])
    print('0')
    [print(s) for s in db.series(tmp2)]
    db.copy([tmp1, '007', 'test2'], [tmp2, '008', 'test2'])
    print('1')
    [print(s) for s in db.series(tmp2)]
    assert 2==len(db.patients(tmp2))
    assert 3==len(db.series(tmp2))
    db.copy([tmp1, '007', 'test2'], [tmp2, '008', 'test2']) 
    print('2')
    [print(s) for s in db.series(tmp2)]
    assert 4==len(db.series(tmp2))
    db.copy([tmp1, '007'], [tmp2, '008'])
    print('3')
    [print(s) for s in db.series(tmp2)]
    assert 6==len(db.series(tmp2))
    assert 4==len(db.studies(tmp2))

    shutil.rmtree(tmp)


if __name__ == '__main__':

    test_write_volume()
    test_volume()
    test_write_database()
    test_copy()

    print('All api tests have passed!!!')