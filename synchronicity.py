#TODO:
    # enforce min distance between colors
    # make backup system
    # allow user to choose config dir
    # configurable backup history size
    # random theme on startup
    # warn about backup when changing theme
    # allow user to choose backgrounds
    
from PIL import Image
from collections import namedtuple
from math import sqrt
from sys import argv
from sklearn import cluster
from numpy import array
from enum import Enum, unique
from configobj import ConfigObj
from argparse import ArgumentParser
import random
import subprocess
import os
import re

CONFIG_DIR = os.path.expanduser("~/.synchronicity")
CONFIG_FILE_PATH = CONFIG_DIR + "/rules.ini"

global Rules

def createClusters(points, n, filename):
    kmeans = cluster.KMeans(n_clusters = n)
    kmeans.fit(points)
    clusters = [c[:3] for c in kmeans.cluster_centers_]
    rgbs = [list(map(int, c)) for c in clusters]
    writeToPPM(rgbs, filename, n)
    return list(map(rgbToHex, rgbs))

# convert the decimal color values to a hex string
def rgbToHex(rgb):
    return "#" + "".join("{0:02x}".format(val) for val in rgb).upper()

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

def callCommand(command):
    subprocess.call(command, shell = True)

def getFilePath(*args):
    pathElements = [CONFIG_DIR] + list(args)
    return "/".join(pathElements)

def writeArrayToFile(fileLines, newFileName):
    # Note: Assumes newlines are already included
    with open(newFileName, "w") as f:
        for line in fileLines:
            f.write(line)

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

def buildFormatString(numColors):
    return "".join(["\\n" for i in range(6)]) + "   " + "".join(["%2d       " for i in range(numColors)])

def getNumbersString(start, end):
    return " ".join([str(i) for i in range(start, end)])

def lineStringToList(lineString):
    modifyIndeces = []
    splitLine = lineString.split(",")
    for lineNumber in splitLine:
        try:
            lineNumber = int(lineNumber)
            modifyIndeces.append(lineNumber)
        except ValueError:
            start = int(lineNumber[0])
            end = int(lineNumber[2])
            for i in range(start, end + 1):
                modifyIndeces.append(i)
    return sorted(modifyIndeces)


def copyFiles(sourceDestPairs):
    command = ""
    for sourceDestPair in sourceDestPairs:
        command += "cp {0} {1};".format(sourceDestPair[0], sourceDestPair[1])
    callCommand(command)

def printToScreen(numLights, numDarks):
    numColors = numDarks + numLights
    lightFormat = buildFormatString(numLights)
    darkFormat = buildFormatString(numDarks)
    lightVals = getNumbersString(1, numLights + 1)
    darkVals = getNumbersString(numLights + 1, numColors + 1)

    command = "./drawimage.sh lightcolors.ppm 60; ./drawimage.sh darkcolors.ppm 140; printf \"{0}\n\" {1}; printf \"{2}\n\" {3};".format(lightFormat, lightVals, darkFormat, darkVals)
    callCommand(command)

def createTheme(args):
    numLights = args.l
    numDarks = args.d
    filename = args.f
    name = args.n
    subprocess.call("clear", shell=True)
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
    for count, color in img.getcolors(w * h):
        tmpPoints.append(color)
    lights, darks = separateColors(tmpPoints)
    lightRgbs = createClusters(lights, numLights, "lightcolors.ppm")
    darkRgbs = createClusters(darks, numDarks, "darkcolors.ppm")
    allRgbs = lightRgbs + darkRgbs
    printToScreen(numLights, numDarks)
    backgroundIndex = int(input("Which color do you want to be the background? "))
    foregroundIndex = int(input("Which color do you want to be the foreground? "))
    cursorIndex = int(input("Which color do you want to be the cursor? "))
    palette = (lightRgbs if backgroundIndex > numLights else darkRgbs)
    #print("pick 16 colors")
    otherCols = []
    #for i in range(16):
    #    otherCols.append(colors[int(input())])
    background = allRgbs[backgroundIndex - 1]
    foreground = allRgbs[foregroundIndex - 1]
    cursor = allRgbs[cursorIndex - 1]
    #colors.remove(background)
    palette.remove(foreground)
    palette.remove(cursor)
    random.shuffle(palette)
    Theme(lightRgbs, darkRgbs, foreground, background, cursor).create(name)

def backup(args):
    sourceDestPairs = [(rule.filePath, getFilePath(rule.appName + ".backup")) for rule in Rules]
    copyFiles(sourceDestPairs)

def createRule(args):
    autodetect = not args.no_autodetect
    defaultColorType = ColorType[args.d]
    Rule(args.f, args.a, args.i).create(autodetect, defaultColorType)

def loadTheme(args):
    Theme.load(args.n)

def revert(args):
    sourceDestPairs = [(getFilePath(rule.appName + ".backup"), rule.filePath) for rule in Rules]
    copyFiles(sourceDestPairs)

def rmRule(args):
    appName = args.n
    del Rule.config[appName]
    Rule.config.write()

def parseArgs():
    argParser = ArgumentParser()
    subparsers = argParser.add_subparsers()

    themeParser = subparsers.add_parser("theme")
    themeParser.add_argument("-n", required = True)
    themeParser.add_argument("-f", required = True)
    themeParser.add_argument("-l", type = int, required = True)
    themeParser.add_argument("-d", type = int, required = True)
    themeParser.set_defaults(func = createTheme)

    ruleParser = subparsers.add_parser("rule")
    ruleParser.add_argument("-f", required = True)
    ruleParser.add_argument("-a", required = True)
    ruleParser.add_argument("-i", choices = ["hex", "rgb", "numeric"], default = "hex")
    ruleParser.add_argument("-d", choices = ["dark", "light"], default = "dark")
    ruleParser.add_argument("--no-autodetect", action = "store_true")
    ruleParser.set_defaults(func = createRule)

    backupParser = subparsers.add_parser("backup")
    backupParser.set_defaults(func = backup)

    loadParser = subparsers.add_parser("load")
    loadParser.add_argument("-n", required = True)
    loadParser.set_defaults(func = loadTheme)

    revertParser = subparsers.add_parser("revert")
    revertParser.set_defaults(func = revert)

    rmRuleParser = subparsers.add_parser("rm-rule")
    rmRuleParser.add_argument("n")
    rmRuleParser.set_defaults(func = rmRule)

    args = argParser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        argParser.parse_args(["-h"])

@unique
class ColorRegex(Enum):
    hex = "(?:^|[\s=:])[\"']?(\#\w{6})[\"']?(?!\S)"
    rgb = "(?:^|[\s=:])[\"']?(\d{1,3} \d{1,3} \d{1,3})[\"']?(?!\S)"
    decimal = "(?:^|[\s=:])[\"']?(\d{1,3})[\"']?(?!\S)"

@unique
class ColorType(Enum):
    dark = "dark"
    light = "light"

class ColorList(object):
    def __init__(self):
        self.index = 0
        self.colors = []

    def next(self):
        currentColor = self.colors[self.index]
        self.index += 1
        if self.index == len(self.colors):
            self.index = 0
        return currentColor

class Line(object): #= namedtuple("Line", ("lineNumber", "editIndeces", "useCursorColor", "useBackgroundColor", "useForegroundColor"))
    def __init__(self, lineNumber, colorType, useCursorColor = False, useBackgroundColor = False, useForegroundColor = False):
        self.lineNumber = lineNumber
        self.colorType = colorType
        self.editIndeces = []
        self.useCursorColor = useCursorColor
        self.useBackgroundColor = useBackgroundColor
        self.useForegroundColor = useForegroundColor

class Theme(object):
    def __init__(self, lightColors, darkColors, foreground, background, cursor):
        self.lightColors = ColorList(lightColors)
        self.darkColors = ColorList(darkColors)
        self.foreground = foreground
        self.background = background
        self.cursor = cursor

        #self.create(newColors, background, foreground, cursor)

    #def save():
    #    self.name = input("Enter the theme name: ")
    #    self.name += ".theme"
    #    with open("/home/aschey/.synchronicity/" + self.name, "w") as f:
    #        for appName in self.files.keys():
    #            f.write("[" + appName + "]\n")
    #            for line in self.files[appName]:
    #                f.write("\t" + line + "\n")
    #            f.write("[/" + appName + "]\n\n")
    
    @staticmethod
    def load(name):
        sourceDestPairs = [(getFilePath(name, rule.appName), rule.filePath) for rule in Rules]
        
        copyFiles(sourceDestPairs)

        #theme = Theme()
        #theme.name = filename[:-6]
        #addLines = False
        #with open(filename, "r") as f:
        #    for line in f:
        #        if line[:4] == "name":
        #            appName = line[7:]
        #            theme.files[appName] = []
        #            addLines = True
        #        elif addLines:
        #            theme.files[appName].append(line#)
        #        
        #        if line == "[/Application#]":
        #            addLines = False

        #return theme

    #def backupConfig(self, rule):
    #    command = "cp {0} {1}".format(rule.filePath, getFilePath(self.name, rule.appName + ".backup"))
    #    callCommand(command)

    def nextColor(self, line):
        if line.useBackgroundColor:
            return self.background

        if line.useForegroundColor:
            return self.foreground

        if line.useCursorColor:
            return self.cursor

        if line.colorType == ColorType.light:
            return self.lightColors.next()

        return self.darkColors.next()


    def updateConfigFiles(self):
        rules = Rule.loadAll()

        for rule in rules:
            #self.backupConfig(rule)
            colorIndex = 0
            with open(rule.filePath, "r") as f:
                configLines = [line for line in f]
            for line in rule.lines:
                editLine = configLines[line.lineNumber]
                newLine = editLine
                for indeces in line.editIndeces:
                    newLine = self.changeLine(newLine, indeces[0], indeces[1], self.nextColor(line))
                configLines[line.lineNumber] = newLine

            writeArrayToFile(configLines, getFilePath(self.name, rule.appName))
                
                    

    def create(self, name):
        callCommand("mkdir " + getFilePath(name))
        self.updateConfigFiles()

    def changeLine(self, line, start, end, newValue):
        return line[:start] + newValue + line[end:]

class Rule(object):
    config = ConfigObj(CONFIG_FILE_PATH, indent_type = "\t", unrepr = True)

    def __init__(self, filePath, appName, inputFormat):
        self.filePath = os.path.expanduser(filePath.strip())
        self.appName = appName
        self.mode = ColorRegex[inputFormat]
        self.lines = []

    def create(self, autodetect, defaultColorType):
        lines = []
        count = 1
        lineNo = 0
        #self.filePath = os.path.expanduser(filePath.strip())
        #self.appName = appName
        #self.mode = ColorRegex[inputFormat]
        search = re.compile(self.mode.value)
        linesFound = []
        if autodetect:
            print("Possible lines to modify found:")
            with open(self.filePath, "r") as f:
                for line in f:
                    matches = search.findall(line)
                    if len(matches) > 0:
                        textLine = Line(lineNumber = lineNo, colorType = defaultColorType,
                                useCursorColor = (True if "cursor" in line else False),
                                useBackgroundColor = (True if "background" in line else False),
                                useForegroundColor = (True if "foreground" in line else False))

                        print(str(count) + ". " + line.strip())
                        count += 1
                        start = 0
                        for match in matches:
                            indeces = self.getIndeces(start, match, line)
                            textLine.editIndeces.append(indeces)
                            start = indeces[1]
                        linesFound.append(textLine)
                    lineNo += 1
        else:
            pass
            #TODO: function to get manual lines
        modifyLines = input("Enter which lines you wish to modify. Enter nothing to modify all lines. Example: 2-5,8,10: ").replace(" ", "")
        nonDefaultColorType = (ColorType.light if defaultColorType == ColorType.dark else ColorType.dark)
        nonDefaultLines = input("Enter which lines should use " + nonDefaultColorType.name + " colors: ")
        modifyAll = (True if len(linesToModify) == 0 else False)
        if modifyAll:
            self.lines = linesFound
        else:
            modifyList = lineStringToList(linesToModify)
            #if not modifyAll:
                
            #    for lineNumber in modifyList:
            #        try:
            #            lineNumber = int(lineNumber)
            #            modifyIndeces.append(lineNumber)
            #        except ValueError:
            #            start = int(lineNumber[0])
            #            end = int(lineNumber[2])
            #            for i in range(start, end + 1):
            #                modifyIndeces.append(i)
            #modifyList = sorted(modifyIndeces)
            for i in range(len(linesFound)):
                if i in modifyList:
                    self.lines.append(linesFound[i])

        nonDefaultList = lineStringToList(nonDefaultLines)
        for lineNumber in nonDefaultList:
            self.lines[lineNumber - 1].color = nonDefaultColorType
        self.save()
        print()
        print("Save successful.")

    def getIndeces(self, start, match, line):
        for i in range(start, len(line) - len(match)):
            if line[i:i + len(match)] == match:
                return (i, i + len(match))
        return None

    def save(self):
        if not os.path.isdir(CONFIG_DIR):
            callCommand("mkdir " + CONFIG_DIR)

        Rule.config[self.appName] = {}
        configRule = Rule.config[self.appName]
        configRule["filePath"] = self.filePath
        configRule["mode"] = self.mode.name
        lineNumber = 1
        for line in self.lines:
            lineHeader = "line " + str(lineNumber)
            lineNumber += 1

            configRule[lineHeader] = {}
            lineConfig = configRule[lineHeader]
            lineConfig["lineNumber"] = line.lineNumber
            lineConfig["color"] = line.color
            if line.useCursorColor:
                lineConfig["cursor"] = True
            if line.useBackgroundColor:
                lineConfig["background"] = True
            if line.useForegroundColor:
                lineConfig["foreground"] = True

            lineConfig["substringsToEdit"] = line.editIndeces

        Rule.config.write()
        
    @staticmethod
    def loadAll():
        rules = []
        for appName, values in Rule.config.items():
            rule = Rule(values["filePath"], appName, values["mode"])
            rule.appName = appName
            rule.filePath = values["filePath"]
            rule.mode = values["mode"]

            for key, lineValues in Rule.getLineNumberItems(appName):
                line = Line(lineNumber = lineValues["lineNumber"], color = lineValues["color"])
                line.useCursorColor = lineValues.get("cursor", False)
                line.useBackgroundColor = lineValues.get("background", False)
                line.useForegroundColor = lineValues.get("foreground", False)
                line.editIndeces = lineValues["substringsToEdit"]
                rule.lines.append(line) 
            rules.append(rule)

        return rules

    @staticmethod
    def getLineNumberItems(appName):
        return [(key, value) for key, value in Rule.config[appName].items() if key.startswith("line ")]

def main(filename):
    global Rules
    Rules = Rule.loadAll()
    parseArgs()

    

                    

#def modifyTerminatorConfig(tconfigLines, colors, background, foreground, cursor):
#    configColors = ":".join(colors)
#    modifiedConfig = []
#    for line in tconfigLines:
#        if line[4:11] == "palette":
#            modifiedConfig.append(line[:14] + '"' + configColors + '"\n')
#        elif line[4:16] == "cursor_color":
#            modifiedConfig.append(line[:18] + '"' + cursor + '"\n')
#        elif line[4:20] == "foreground_color":
#            modifiedConfig.append(line[:23] + '"' + foreground + '"\n')
#        elif line[4:20] == "background_color":
#            modifiedConfig.append(line[:23] + '"' + background + '"\n')
#        else:
#            modifiedConfig.append(line)
#
#    return modifiedConfig
            

#def readTerminatorConfig():
#    tconfigLines = []
#    with open("/home/aschey/.config/terminator/config", "r") as f:
#        for line in f:
#            tconfigLines.append(line)
#    return tconfigLines


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

if __name__ == "__main__":
    main('/home/aschey/Pictures/wallpapers/deja_entendu.jpeg')
    #Rule().create()
