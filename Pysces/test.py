import multiprocessing
import multitask
import PASKIL_jpg_plugin
from PASKIL import allskyImage
import time


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