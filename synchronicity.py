#Author: Charles Leifer
#TODO:
    # enforce min distance between colors
    # auto-detect which config lines to edit
    # make backup system
    # allow user to choose config dir
    # configurable backup history size
    # allow choosing 256, 16 or hex colors
    
from PIL import Image
from collections import namedtuple
from math import sqrt
from sys import argv
from sklearn import cluster
from numpy import array
import random
import subprocess
import os
import re

#Point = namedtuple('Point', ('coords', 'n', 'ct'))
#Cluster = namedtuple('Cluster', ('points', 'center', 'n'))

Line = namedtuple("Line", ("lineNumber", "editIndeces"))

# convert the decimal color values to a hex string
rtoh = lambda rgb: '#%s' % ''.join(('%02x' % p for p in rgb))

def main(filename):
    numLights = int(input("How many light colors do you want? "))
    numDarks = int(input("How many dark colors do you want? "))
    subprocess.call("clear", shell=True)
    if numLights > numDarks:
        numColors = numLights
    else:
        numColors = numDarks
    img = Image.open(filename)
    img.thumbnail((200, 200))
    w, h = img.size
    #rules = Rule.load()
    # get all rgb color values in the image and the amount of each
    #points = getPoints(img)
    tmpPoints = []
    #for count, color in img.getcolors(w*h):
    #    for i in range(count):
    #        newcolor = []
    #        for c in color:
    #            newcolor.append(c)# + random.randint(-5,5))
    #        tmpPoints.append(newcolor)
    for count, color in img.getcolors(w*h):
        tmpPoints.append(color)
    lights, darks = separateColors(tmpPoints)
    lightRgbs = createClusters(lights, numLights, "lightcolors.ppm")
    darkRgbs = createClusters(darks, numDarks, "darkcolors.ppm")
    printToScreen(numColors)
    #subprocess.call("feh lightcolors.ppm &", shell=True)
    #subprocess.call("feh darkcolors.ppm &", shell=True)
    backgroundIndex = int(input("Which color do you want to be the background? "))
    foregroundIndex = int(input("Which color do you want to be the foreground? "))
    cursorIndex = int(input("Which color do you want to be the cursor color? "))
    #print("pick 16 colors")
    otherCols = []
    #for i in range(16):
    #    otherCols.append(colors[int(input())])
    background = darkRgbs[backgroundIndex]
    foreground = lightRgbs[foregroundIndex]
    cursor = lightRgbs[cursorIndex]
    #colors.remove(background)
    lightRgbs.remove(foreground)
    lightRgbs.remove(cursor)
    random.shuffle(lightRgbs)
    #tconfigLines = readTerminatorConfig()
    #writeArrayToFile(tconfigLines, "/home/aschey/.config/terminator/config.backup")
    #modifiedConfig = modifyTerminatorConfig(tconfigLines, lightRgbs, background, foreground, cursor)
    #writeArrayToFile(modifiedConfig, "/home/aschey/.config/terminator/config")

def createClusters(points, n, filename):
    kmeans = cluster.KMeans(n_clusters=n)
    kmeans.fit(points)
    clusters = [c[:3] for c in kmeans.cluster_centers_]
    rgbs = [list(map(int, c)) for c in clusters]
    writeToPPM(rgbs, filename, n)
    return list(map(rtoh, rgbs))

class Theme(object):
    def __init__(self):
        self.name = ""
        self.files = {}

    def save():
        self.name = input("Enter the theme name: ")
        self.name += ".theme"
        with open("/home/aschey/.synchronicity/" + self.name, "w") as f:
            for appName in self.files.keys():
                f.write("[" + appName + "]\n")
                for line in self.files[appName]:
                    f.write("\t" + line + "\n")
                f.write("[/" + appName + "]\n\n")

    @staticmethod
    def load(filename):
        theme = Theme()
        theme.name = filename[:-6]
        addLines = False
        with open(filename, "r") as f:
            for line in f:
                if line[:4] == "name":
                    appName = line[7:]
                    theme.files[appName] = []
                    addLines = True
                elif addLines:
                    theme.files[appName].append(line)
                
                if line == "[/Application]":
                    addLines = False

        return theme

    @staticmethod
    def createThemeFile(self, rules, newColors):
        newFile = []
        colorIndex = 0
        for rule in rules:
            fileArray = []
            with open(rule.filename, "r") as f:
                for line in f:
                    fileArray.append(line)
            for line in rule.lines:
                editLine = fileArray[line.lineNumber]
                newLine = line
                for indeces in line.editIndeces:
                    newLine = self.changeLine(newLine, indeces[0], indeces[1], colors[colorIndex])
                    colorIndex += 1
                newFile.append(newLine)
        with open(rule.filename, "w") as f:
            for line in newFile:
                f.write(line)
    
    def changeLine(self, line, start, end, newValue):
        newLine = line[:start]
        newLine += newValue
        newLine += line[end:]
        return newLine

class Rule(object):
    def __init__(self):
        self.filename = ""
        self.appName = ""
        self.mode = ""
        self.lines = []

    @staticmethod
    def create():
        lines = []
        count = 1
        lineNo = 1
        rule = Rule()
        self.filename = input("Enter the full file path: ")
        self.appName = input("Enter the application name: ")
        print("Enter the color input format.")
        print("Choices are:")
        print("'hex' eg. #00ff00")
        print("'rgb' eg. 123 435 643")
        print("'numeric' eg. 234")
        rule.mode = input()
        if rule.mode == "hex":
            search = re.compile("\#\w{6}")
        elif rule.mode == "rgb":
            search = re.compile("\d{1,3} \d{1,3} \d{1,3}")
        else:
            search = re.compile("\d{1,3}")
        autodetect = input("Try to autodetect lines which contain colors? This \
                may return a lot of false positives if 'numeric' mode is selected. Enter (y/n): ")
        if autodetect == "y":
            tempLines = []
            print("Possible lines to modify found:")
            with open(rule.filename, "r") as f:
                for line in f:
                    matches = search.findall(line)
                    if len(matches) > 0:
                        textLine = Line(lineNumber = lineNo, editIndeces = [])
                        print(str(count) + ". " + line)
                        count += 1
                        start = 0
                        for match in matches:
                            indeces = self.getIndeces(start, match, line)
                            textLine.editIndeces.append(indeces)
                            start = indeces[1]
                        tempLines.append(textLine)
                lineNo += 1
            linesToModify = input("Enter which lines you wish to modify. Do not include spaces. Example: 2-5,8,10: ")
            linesToModify = linesToModify.split(",")
            modifyIndeces = []
            for lineNumber in linesToModify:
                print(lineNumber)
                try:
                    lineNumber = int(lineNumber)
                    modifyIndeces.append(lineNumber)
                except ValueError:
                    start = int(lineNumber[0])
                    end = int(lineNumber[2])
                    for i in range(start, end+1):
                        modifyIndeces.append(i)
            modifyList = sorted(modifyIndeces)
            for i in range(len(tempLines)):
                if i in modifyList:
                    rule.lines.append(line)
            #for line in tempLines:
            #    if line.foundIndex in modifyList:
            #        self.lines.append(line)

    def getIndeces(self, start, match, line):
        for i in range(start, len(line) - len(match)):
            if line[i:i+len(match)] == match:
                return (i, i+len(match))
        return None

    @staticmethod
    def save(rules):
        if not os.path.isdir("/home/aschey/.synchronicity"):
            subprocess.call("mkdir /home/aschey/.synchronicity", shell=True)
        with open("/home/aschey/.synchronicity/rules.config", "w") as f:
            for rule in self.rules:
                f.write("[Rule]\n")
                f.write("application_name: " + rule.appName + "\n")
                f.write("filename: " + rule.filename + "\n")
                f.write("mode: " + rule.mode + "\n")
                for line in self.rules.lines:
                    f.write("line_number: " + line.lineNumber + "\n")
                    f.write("substrings_to_edit: " + str(editIndeces) + "\n")
                f.write("[/Rule]\n\n")

    @staticmethod
    def load():
        rules = []
        with open("/home/aschey/.synchroncitiy/rules.config", "r") as f:
            for line in f:
                if line == "[Rule]":
                    rule = Rule()
                elif line[:8] == "filename":
                    rule.filename = line[11:]
                elif line[:4] == "mode":
                    rule.mode = line[6:]
                elif line[:11] == "line_number":
                    newLine = Line(lineNumber = line[13:])
                elif line[:18] == "substrings_to_edit":
                    newLine.editIndeces = list(line[20:])
                    rule.lines.append(newLine)
                elif line == "[/Rule]":
                    rules.append(rule)
        return rules

def separateColors(rgbs):
    lights = []
    darks = []
    for c in rgbs:
        if isLight(c):
            lights.append(c)
        elif isDark(c):
            darks.append(c)
    return lights, darks

def isLight(rgb):
    return ((rgb[0] * 299) + (rgb[1] * 587) + (rgb[2] * 114)) / 1000 >= 50

def isDark(rgb):
    return ((rgb[0] * 299) + (rgb[1] * 587) + (rgb[2] * 114)) / 1000 <= 25

def modifyTerminatorConfig(tconfigLines, colors, background, foreground, cursor):
    configColors = ":".join(colors)
    modifiedConfig = []
    for line in tconfigLines:
        if line[4:11] == "palette":
            modifiedConfig.append(line[:14] + '"' + configColors + '"\n')
        elif line[4:16] == "cursor_color":
            modifiedConfig.append(line[:18] + '"' + cursor + '"\n')
        elif line[4:20] == "foreground_color":
            modifiedConfig.append(line[:23] + '"' + foreground + '"\n')
        elif line[4:20] == "background_color":
            modifiedConfig.append(line[:23] + '"' + background + '"\n')
        else:
            modifiedConfig.append(line)

    return modifiedConfig
            
def writeArrayToFile(fileLines, newFileName):
    # Note: Assumes newlines are already included
    with open(newFileName, "w") as f:
        for line in fileLines:
            f.write(line)

def readTerminatorConfig():
    tconfigLines = []
    with open("/home/aschey/.config/terminator/config", "r") as f:
        for line in f:
            tconfigLines.append(line)
    return tconfigLines

def writeToPPM(rgbs, filename, numColors):
    colorwidth = 54
    with open(filename, 'w') as f:
        f.write('P3\n')
        f.write(str(numColors * colorwidth) + " " + str(colorwidth) + "\n")
        f.write('255\n')
        for i in range(colorwidth):
            for rgb in rgbs:
                for j in range(colorwidth):
                    for val in rgb:
                        f.write(str(val) + " ")
                    f.write("\n")

def printToScreen(numColors):
    for i in range(10):
        print()
    #command = "printf \"\\n\\n\\n\\n\\n\\n\\n\\n\\n\"; ./drawimage.sh darkcolors.ppm 0; ./drawimage.sh lightcolors.ppm 50; printf \" "
    command = "./drawimage.sh darkcolors.ppm 60; ./drawimage.sh lightcolors.ppm 116; printf \"\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n   "
    for i in range(numColors):
        command += "%2d       "
    command += "\\n\" "
    colorNums = map(str, list(range(1, numColors+1)))
    command += " ".join(colorNums)
    #print(command)
    subprocess.call(command, shell=True)

def getPoints(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        points.append(Point(color, 3, count))
    return points

def calculateCenter(points, n):
    # find the average of each rgb value in the point
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)

def euclidean(p1, p2):
    return sqrt(sum([(p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)]))

def kmeans(points, k, minDiff):
    # choose k random points to start each cluster
    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]
    while True:
        plists = [[] for i in range(k)]

        for p in points:
            smallestDist = float('Inf')
            for i in range(k):
                # calculate the distance from each point to the center of each cluster
                dist = euclidean(p, clusters[i].center)
                if dist < smallestDist:
                    smallestDist = dist
                    idx = i
            # add the point to the cluster where it's closest to the center
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculateCenter(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < minDiff:
            break

    return clusters

main('/home/aschey/Pictures/wallpapers/deja_entendu.jpeg')
#rule = Rule()
#rule.createRule()
