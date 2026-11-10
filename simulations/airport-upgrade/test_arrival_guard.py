import math, unittest
from arrival_guard import ArrivalGuard

class ArrivalGuardTests(unittest.TestCase):
    def samples(self,**overrides):
        guard=ArrivalGuard();results=[]
        for i in range(5):
            d=dict(name='amr',command='1',t=i*.5,x=1.,y=2.,yaw=math.pi-1e-6,
                   target=[1.,2.,-math.pi],empty_path=True,moving_mode=True)
            d.update({k:(v(i) if callable(v) else v) for k,v in overrides.items()})
            results.append(guard.update(**d))
        return results
    def test_stationary_wraparound(self):
        self.assertEqual(self.samples(yaw=lambda i:(math.pi-1e-6) if i%2 else (-math.pi+1e-6)),[False,False,True,True,True])
    def test_rejects_motion_and_incomplete_commands(self):
        for override in (dict(target=None),dict(empty_path=False),dict(moving_mode=False),dict(x=1.2),dict(yaw=0.),dict(command=lambda i:str(i)),dict(t=0.),dict(x=lambda i:1+i*.02)):
            with self.subTest(override=override):self.assertFalse(any(self.samples(**override)))
    def test_stale_samples_reset_dwell(self):
        self.assertFalse(any(self.samples(t=lambda i:i*2)))
if __name__=='__main__':unittest.main()
