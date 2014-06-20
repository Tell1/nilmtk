#!/usr/bin/python
from __future__ import print_function, division
import unittest
from nilmtk.pipeline import Pipeline, EnergyNode, ClipNode
from nilmtk.pipeline.energynode import _energy_for_power_series
from nilmtk import TimeFrame, ElecMeter, HDFDataStore
from nilmtk.elecmeter import ElecMeterID
from nilmtk.consts import JOULES_PER_KWH
from nilmtk.tests.testingtools import data_dir
from os.path import join
import numpy as np
import pandas as pd
from datetime import timedelta
from copy import deepcopy

METER_ID = ElecMeterID(instance=1, building=1, dataset='REDD')

def check_energy_numbers(testcase, energy):
    energy = energy.combined
    true_active_kwh =  0.0163888888889
    testcase.assertAlmostEqual(energy['active'], true_active_kwh)
    testcase.assertAlmostEqual(energy['reactive'], true_active_kwh*0.9)
    testcase.assertAlmostEqual(energy['apparent'], true_active_kwh*1.1)


class TestEnergy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        filename = join(data_dir(), 'energy.h5')
        cls.datastore = HDFDataStore(filename)
        ElecMeter.load_meter_devices(cls.datastore)
        cls.meter_meta = cls.datastore.load_metadata('building1')['elec_meters'][METER_ID.instance]

    def test_energy_per_power_series(self):
        data = np.array([0,  0,  0, 100, 100, 100, 150, 150, 200,   0,   0, 100, 5000,    0])
        secs = np.arange(start=0, stop=len(data)*10, step=10)
        true_kwh = ((data[:-1] * np.diff(secs)) / JOULES_PER_KWH).sum()
        index = [pd.Timestamp('2010-01-01') + timedelta(seconds=sec) for sec in secs]
        df = pd.Series(data=data, index=index)
        kwh = _energy_for_power_series(df, max_sample_period=15)
        self.assertAlmostEqual(true_kwh, kwh)

    def test_pipeline(self):
        meter = ElecMeter(store=self.datastore, metadata=self.meter_meta, 
                          meter_id=METER_ID)
        nodes = [ClipNode(), EnergyNode()]
        pipeline = Pipeline(nodes)
        pipeline.run(meter)
        energy = deepcopy(pipeline.results['energy'])
        check_energy_numbers(self, energy)

        # test multiple keys
        multi_meter_meta = deepcopy(self.meter_meta)
        multi_meter_meta['sensors'] += multi_meter_meta['sensors']
        multi_meter = ElecMeter(store=self.datastore, metadata=multi_meter_meta,
                                meter_id=METER_ID)
        pipeline.run(multi_meter)
        multi_meter_energy = deepcopy(pipeline.results['energy'])
        for ac_type, en in multi_meter_energy.combined.iteritems():
            self.assertEqual(energy.combined[ac_type]*2, en)

if __name__ == '__main__':
    unittest.main()


