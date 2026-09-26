"""Blocking/route checks on the source map, never on the occlusion mask."""
from collections import deque

def tile(point):
    x,y=point
    assert x%16==0 and y%16==0, ('Actor must stand on a tile',point)
    return x//16,y//16-1

def clear(grid,point):
    x,y=point;w,h=grid['width'],grid['height']
    return 0<=x<w and 0<=y<h and not grid['cells'][y*w+x]

def route(grid,start,end,occupied=()):
    first,last=tile(start),tile(end);busy={tile(p) for p in occupied}
    assert clear(grid,first) and first not in busy, ('Blocked actor start',start)
    assert clear(grid,last) and last not in busy, ('Blocked actor destination',end)
    queue=deque([first]);parent={first:None}
    while queue and last not in parent:
        x,y=queue.popleft()
        for nxt in ((x,y-1),(x-1,y),(x+1,y),(x,y+1)):
            if clear(grid,nxt) and nxt not in busy and nxt not in parent:
                parent[nxt]=(x,y);queue.append(nxt)
    assert last in parent, ('No collision-free route',start,end)
    path=[];at=last
    while at is not None:path.append([at[0]*16,(at[1]+1)*16]);at=parent[at]
    path.reverse()
    return path
