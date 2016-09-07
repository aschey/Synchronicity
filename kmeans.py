from collections import namedtuple
from random import sample
from math import sqrt

Point = namedtuple('Point', ('coords'))
Cluster = namedtuple('Cluster', ('points', 'center'))
RGB_SIZE = 3

def getPoints(img):
    colors = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        colors.append(color)
            
    return _separateColors(colors)

def cluster(points, k, minDiff):
    # choose k random points to start each cluster
    clusters = [Cluster([p], p) for p in sample(points, k)]
    while True:
        plists = [[] for i in range(k)]

        for p in points:
            smallestDist = float('Inf')
            for i in range(k):
                # calculate the distance from each point to the center of each cluster
                dist = _euclidean(p, clusters[i].center)
                if dist < smallestDist:
                    smallestDist = dist
                    idx = i
            # add the point to the cluster where it's closest to the center
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = _calculateCenter(plists[i])
            new = Cluster(plists[i], center)
            clusters[i] = new
            diff = max(diff, _euclidean(old.center, new.center))

        if diff < minDiff:
            break

    return clusters

def _separateColors(rgbs):
    lights = []
    darks = []
    for c in rgbs:
        if _isLight(c):
            lights.append(Point(c))
        elif _isDark(c):
            darks.append(Point(c))
    return lights, darks

def _getLuminance(rgb):
    return ((rgb[0] * 299) + (rgb[1] * 587) + (rgb[2] * 114)) / 1000 

def _isLight(rgb):
    return _getLuminance(rgb) >= 50

def _isDark(rgb):
    return _getLuminance(rgb) <= 25

def _calculateCenter(points):
    # find the average of each rgb value in the point
    vals = [0.0 for i in range(RGB_SIZE)]
    plen = 0
    for p in points:
        plen += 1
        for i in range(RGB_SIZE):
            vals[i] += p.coords[i]
    return Point([(v / plen) for v in vals])

def _euclidean(p1, p2):
    return sqrt(sum([(p1.coords[i] - p2.coords[i]) ** 2 for i in range(RGB_SIZE)]))


