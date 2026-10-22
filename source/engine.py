"""Shortest paths, exact small-route optimization and fair round events."""
from dataclasses import dataclass, field
import heapq
import math
import random
from world import NODES, EDGES, PLACES, TRUNK_EDGES, START, length

def edge_key(a,b):
    return tuple(sorted((a,b)))

@dataclass
class Event:
    title: str = '晴天畅行'
    description: str = '今天路况很好，按你的节奏配送吧。'
    blocked: set = field(default_factory=set)
    slow: dict = field(default_factory=dict)

class Network:
    def __init__(self, event=None):
        self.event = event or Event()
        self.graph = {key:[] for key in NODES}
        self.cache = {}
        for a,b in EDGES:
            key=edge_key(a,b)
            if key in self.event.blocked:
                continue
            weight=length(a,b)*self.event.slow.get(key,1)
            self.graph[a].append((b,weight))
            self.graph[b].append((a,weight))

    def shortest(self, start, end):
        if (start,end) in self.cache:
            return self.cache[start,end]
        distances={start:0.0}; previous={}; heap=[(0.0,start)]
        while heap:
            distance,u=heapq.heappop(heap)
            if distance!=distances[u]:
                continue
            if u==end:
                path=[end]
                while path[0]!=start:
                    path.insert(0,previous[path[0]])
                result=(distance,path)
                self.cache[start,end]=result
                return result
            for v,weight in self.graph[u]:
                candidate=distance+weight
                if candidate<distances.get(v,math.inf):
                    distances[v]=candidate; previous[v]=u
                    heapq.heappush(heap,(candidate,v))
        raise ValueError(f'Unreachable: {start} -> {end}')

    def route(self, order, start=START):
        distance=0.0; path=[start]; at=start
        for target in order:
            cost,leg=self.shortest(at,target)
            distance+=cost; path.extend(leg[1:]); at=target
        return distance,path

    def optimize(self, order, start=START):
        """Held-Karp <=12 stops; nearest insertion + 2-opt above that threshold."""
        order=list(order)
        if not order:
            return 0.0,[],True
        n=len(order)
        if n<=12:
            initial=[self.shortest(start,x)[0] for x in order]
            pair=[[self.shortest(a,b)[0] for b in order] for a in order]
            dp={};parent={}
            for j in range(n):
                dp[1<<j,j]=initial[j]
            for mask in range(1,1<<n):
                for j in range(n):
                    if (mask,j) not in dp:
                        continue
                    for k in range(n):
                        if mask&(1<<k):
                            continue
                        key=(mask|(1<<k),k);candidate=dp[mask,j]+pair[j][k]
                        if candidate<dp.get(key,math.inf):
                            dp[key]=candidate;parent[key]=j
            mask=(1<<n)-1;last=min(range(n),key=lambda j:dp[mask,j]);cost=dp[mask,last];answer=[]
            while mask:
                answer.append(order[last]);old=last;last=parent.get((mask,last));mask^=1<<old
            return cost,list(reversed(answer)),True
        # Try every initial stop; improve open paths rather than forcing a return.
        candidates=[list(order)]
        for first in order:
            rest=set(order);rest.remove(first);candidate=[first]
            while rest:
                target=min(rest,key=lambda x:(self.shortest(candidate[-1],x)[0],x))
                candidate.append(target);rest.remove(target)
            candidates.append(candidate)
        candidate=min(candidates,key=lambda x:self.route(x,start)[0]);cost=self.route(candidate,start)[0]
        for _ in range(12):
            changed=False
            for a in range(n-1):
                for b in range(a+1,n):
                    attempt=candidate[:a]+candidate[a:b+1][::-1]+candidate[b+1:]
                    next_cost=self.route(attempt,start)[0]
                    if next_cost<cost-1e-7:
                        candidate,cost=attempt,next_cost;changed=True
            if not changed:
                break
        return cost,candidate,False

def random_event(rng=None):
    rng=rng or random
    kind=rng.choices(['clear','closed','water','club'],weights=[1,4,3,2])[0]
    if kind=='clear':
        return Event()
    choices=list(TRUNK_EDGES);rng.shuffle(choices)
    for a,b in choices:
        key=edge_key(a,b)
        if kind=='closed':
            event=Event('道路施工 · 请绕行','红色路段暂时封闭。看看换个送餐顺序能否少绕路！',{key})
            network=Network(event)
            try:
                for place in PLACES:
                    network.shortest(START,place.id)
            except ValueError:
                continue
            return event
        if kind=='water':
            return Event('临时积水 · 慢行通过','蓝色路段通行成本变为 2.2 倍，绕行也许更划算。',slow={key:2.2})
        return Event('社团活动 · 人流拥挤','紫色路段通行成本变为 1.8 倍，注意安排配送顺序。',slow={key:1.8})
    return Event()
