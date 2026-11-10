"""Measure a stable stop at the requested goal; never infer it from a command."""
import math

def angle_delta(a,b):
    return math.atan2(math.sin(a-b),math.cos(a-b))

class ArrivalGuard:
    def __init__(self):
        self.samples={}

    def update(self,name,command,t,x,y,yaw,target,empty_path,moving_mode):
        old=self.samples.get(name)
        sample={"command":command,"t":t,"x":x,"y":y,"yaw":yaw,"since":None}
        eligible=(target is not None and empty_path and moving_mode
                  and math.hypot(x-target[0],y-target[1])<.05
                  and abs(angle_delta(yaw,target[2]))<.03)
        sample["eligible"]=eligible
        if eligible and old and old["eligible"] and old["command"]==command:
            dt=t-old["t"]
            if 0<dt<=1.5:
                speed=math.hypot(x-old["x"],y-old["y"])/dt
                angular=abs(angle_delta(yaw,old["yaw"]))/dt
                if speed<.01 and angular<.02:
                    sample["since"]=old["since"] if old["since"] is not None else old["t"]
        self.samples[name]=sample
        return sample["since"] is not None and t-sample["since"]>=1.
