import multiprocessing
import settings_manager
import multitask
import PASKIL_jpg_plugin
from PASKIL import allskyImage
import time


s = settings_manager.SettingsManager()

for i in range(10000):
    p = s.create_proxy()
    p.start()
    p.get(["output"])
    p.exit()
s.exit()


def f2():
    return

def f(p):
     t = p.create_task(f2)
     p.commit_task(t)
p = multitask.ProcessQueueBase(workers=2)
tp = multitask.ProcessQueueBase(workers=2)    

for j in range(1):    
    for i in range(100):
        t = tp.create_task(f,p)
        tp.commit_task(t)
    t.result()
p.exit()
tp.exit()