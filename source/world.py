"""Campus geometry, redrawn from the user's reference. No raster map required."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Place:
    id: str
    name: str
    position: tuple
    anchor: tuple
    category: str

NODES = {}
EDGES = []

def add_node(name, x, y):
    NODES[name] = (x, y)
    return name

def connect(a, b):
    EDGES.append((a, b))

def road(prefix, coordinates):
    ids = [add_node(f'{prefix}{i}', *p) for i, p in enumerate(coordinates)]
    for a, b in zip(ids, ids[1:]):
        connect(a, b)
    return ids

# Named intersections are shared by road lines.
def junction(x, y):
    key = f'j{x}_{y}'
    return add_node(key, x, y)

def line(points):
    ids = [junction(*p) for p in points]
    for a, b in zip(ids, ids[1:]):
        if (a, b) not in EDGES and (b, a) not in EDGES:
            connect(a, b)

line([(90,355),(225,355),(285,355),(365,355),(415,355),(445,355),(650,355),(865,355),(995,395)])
line([(90,155),(125,155),(140,155),(200,155),(260,155),(320,155),(380,155),(445,155)])
line([(90,155),(90,235),(90,355),(90,465),(90,650),(90,735),(335,735),(650,735)])
line([(285,155),(285,205),(285,295),(285,355)])
# Insert the dormitory lane in the northern road.
EDGES.remove(('j260_155','j320_155'))
line([(260,155),(285,155),(320,155)])
line([(445,105),(445,155),(445,205),(445,290),(445,295),(445,355)])
line([(125,155),(125,180),(125,235)])
line([(650,190),(650,355),(650,450),(650,480),(650,580),(650,650),(650,735)])
line([(365,355),(365,480),(365,580),(335,580),(335,735)])
line([(995,395),(995,580),(995,620)])
line([(865,355),(865,420)])

PLACES = []
def place(key, name, xy, anchor, category):
    add_node(key, *xy)
    connect(key, junction(*anchor))
    PLACES.append(Place(key, name, xy, anchor, category))

for num, x in [(9,140),(8,200),(7,260),(6,320),(5,380)]:
    place(f'dorm{num}', f'{num}栋宿舍', (x,144), (x,155), '宿舍')
place('dorm1','1栋宿舍',(305,205),(285,205),'宿舍')
place('dorm3','3栋宿舍',(425,205),(445,205),'宿舍')
place('dorm2','2栋宿舍',(305,295),(285,295),'宿舍')
place('dorm4','4栋宿舍',(425,295),(445,295),'宿舍')
place('library','图书馆',(465,105),(445,105),'学习')
place('teaching','教学楼',(465,205),(445,205),'学习')
place('lab','实验楼',(465,290),(445,290),'学习')
place('activity','学生活动中心',(140,235),(125,235),'生活')
place('shop','小卖部',(142,180),(125,180),'生活')
place('food','食堂',(225,337),(225,355),'生活')
place('gas','加油站',(105,235),(90,235),'生活')
place('lake','日月湖',(670,190),(650,190),'风景')
place('gym','体育馆',(120,465),(90,465),'运动')
place('pool','游泳池',(415,377),(415,355),'运动')
place('tennis','网球场',(380,480),(365,480),'运动')
place('basket1','篮球场·东区',(630,450),(650,450),'运动')
place('basket2','篮球场·西区',(150,650),(90,650),'运动')
place('track','田径场',(635,650),(650,650),'运动')
place('admin','行政楼',(700,480),(650,480),'办公')
place('red','红楼',(925,420),(865,420),'办公')
place('science','科创园',(1020,580),(995,580),'学习')
place('north','北门',(90,377),(90,355),'校门')
place('south','南门',(995,643),(995,620),'校门')
place('west','西门',(650,759),(650,735),'校门')
BY_ID = {p.id:p for p in PLACES}
START = 'food'
TRUNK_EDGES = [(a,b) for a,b in EDGES if a.startswith('j') and b.startswith('j')]

def length(a,b):
    return math.dist(NODES[a],NODES[b])
