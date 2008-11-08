import multiprocessing
import multitask
import PASKIL_jpg_plugin
from PASKIL import allskyImage
import time

def f():
    return [0.1]*100
p = multitask.ProcessQueueBase(workers=1)
for j in range(2000):    
    
    for i in range(200):
        t = p.create_task(f)
        p.commit_task(t)
    t.result()
p.exit()