#! /usr/bin/env python

#TODO:
    # enforce min distance between colors
    # allow user to choose config dir
    # configurable backup history size
    # random theme on startup
    # warn about backup when changing theme
    # allow user to choose backgrounds
    # warn when any files have been changed
    
from PIL import Image
from collections import namedtuple
from math import sqrt
from sys import argv, exit
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

def createClusters(points, n, filename):
    #kmeans = cluster.KMeans(n_clusters = n)
    #kmeans.fit(points)
    #clusters = [c[:3] for c in kmeans.cluster_centers_]
    rgbs = [list(map(int, cluster.center.coords)) for cluster in kmeans(points, n, 50)]
    #rgbs = [list(map(int, c)) for c in clusters]
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
    retCode = subprocess.call(command, shell = True)
    if not retCode == 0:
        print("command {0} failed with error code {1}".format(command, retCode))
        exit()

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
    if len(lineString) == 0:
        return []
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
    callCommand("clear")
    img = Image.open(filename)
    #img.thumbnail((200, 200))
    w, h = img.size
    tmpPoints = []
    for count, color in img.getcolors(w * h):
        tmpPoints.append(color)
    #lights, darks = separateColors(tmpPoints)
    lights, darks = getPoints(img)
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
    Theme(filename, lightRgbs, darkRgbs, foreground, background, cursor).create(name)

def backup(args):
    sourceDestPairs = [(rule.filePath, getFilePath(rule.appName + ".backup")) for rule in Rules]
    copyFiles(sourceDestPairs)

def createRule(args):
    autodetect = not args.no_autodetect
    defaultColorType = ColorType[args.d]
    Rule(args.f, args.a, args.i).create(autodetect, args.manual_background, args.manual_foreground, args.manual_cursor, defaultColorType)

def loadTheme(args):
    Theme.load(args.n)

def revert(args):
    sourceDestPairs = [(getFilePath(rule.appName + ".backup"), rule.filePath) for rule in Rules]
    copyFiles(sourceDestPairs)

def saveCurrent(args):
    themeName = args.n
    themePath = getFilePath(themeName)
    sourceDestPairs = [(rule.filePath, getFilePath(themeName, rule.appName)) for rule in Rules]
    if not os.path.isdir(themePath):
        callCommand("mkdir " + themePath)

    copyFiles(sourceDestPairs)

def rmRule(args):
    appName = args.n
    del Rule.config[appName]
    Rule.config.write()

def rmTheme(args):
    themeName = args.n
    themePath = getFilePath(themeName)
    callCommand("rm -r " + themePath)

def reconfigure(args):
    themeName = args.t
    appName = args.a
    theme = Theme.fromConfig(themeName)
    rule = Rule.load(appName)
    rule.shuffleColors()
    theme.updateConfigFile(themeName, rule)

def recreate(args):
    themeName = args.n

def startup(args):
    themeName = args.n
    Theme.loadWallpaper(themeName)

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
    ruleParser.add_argument("-d", choices = ["dark", "light"], default = "light")
    ruleParser.add_argument("--no-autodetect", action = "store_true")
    ruleParser.add_argument("--manual-background", action = "store_true")
    ruleParser.add_argument("--manual-foreground", action = "store_true")
    ruleParser.add_argument("--manual-cursor", action = "store_true")
    ruleParser.set_defaults(func = createRule)

    backupParser = subparsers.add_parser("backup")
    backupParser.set_defaults(func = backup)

    loadParser = subparsers.add_parser("load")
    loadParser.add_argument("n")
    loadParser.set_defaults(func = loadTheme)

    revertParser = subparsers.add_parser("revert")
    revertParser.set_defaults(func = revert)

    rmRuleParser = subparsers.add_parser("rm-rule")
    rmRuleParser.add_argument("n")
    rmRuleParser.set_defaults(func = rmRule)

    rmThemeParser = subparsers.add_parser("rm-theme")
    rmThemeParser.add_argument("n")
    rmThemeParser.set_defaults(func = rmTheme)

    saveCurrentParser = subparsers.add_parser("save-current")
    saveCurrentParser.add_argument("n")
    saveCurrentParser.set_defaults(func = saveCurrent)

    reconfigureParser = subparsers.add_parser("reconfigure")
    reconfigureParser.add_argument("a")
    reconfigureParser.add_argument("-t", required = True)
    reconfigureParser.set_defaults(func = reconfigure)

    recreateParser = subparsers.add_parser("recreate")
    recreateParser.add_argument("n")
    recreateParser.set_defaults(func = recreate)

    startupParser = subparsers.add_parser("startup")
    startupParser.add_argument("n")
    startupParser.set_defaults(func = startup)

    args = argParser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        argParser.parse_args(["-h"])
    
    print()
    print("Success.")

LineMatch = namedtuple("LineMatch", ("text", "lineNo", "colors"))

@unique
class ColorRegex(Enum):
    hex = "(?:^|\W)(\#[a-fA-F0-9]{6})(?!\w)"
    rgb = "(?:^|\W)(\#\d{1,3} \d{1,3} \d{1,3})(?!\w)"
    decimal = "(?:^|\W)(\#d{1,3})(?!\w)"

@unique
class ColorType(Enum):
    dark = "dark"
    light = "light"

class ColorList(object):
    def __init__(self, colors):
        self.index = 0
        self.colors = colors

    def next(self):
        currentColor = self.colors[self.index]
        self.index += 1
        if self.index == len(self.colors):
            self.index = 0
        return currentColor

class Line(object): 
    def __init__(self, lineNumber, useCursorColor = False, useBackgroundColor = False, useForegroundColor = False):
        self.lineNumber = lineNumber
        self.colorStrings = []
        self.useCursorColor = useCursorColor
        self.useBackgroundColor = useBackgroundColor
        self.useForegroundColor = useForegroundColor

class ColorString(object):
    def __init__(self, indeces, color, colorType):
        self.indeces = indeces
        self.color = color
        self.colorType = colorType

    def toDict(self):
        return { "indeces": self.indeces, "color": self.color, "colorType": self.colorType.value }

    @staticmethod
    def fromDict(colorStringDict):
        return ColorString(colorStringDict["indeces"], colorStringDict["color"], ColorType[colorStringDict["colorType"]])

class Theme(object):
    def __init__(self, wallpaperFile, lightColors, darkColors, foreground, background, cursor):
        self.wallpaperFile = wallpaperFile
        self.lightColors = ColorList(lightColors)
        self.darkColors = ColorList(darkColors)
        self.foreground = foreground
        self.background = background
        self.cursor = cursor

    @classmethod
    def fromConfig(cls, name):
        themeConfig = cls.getThemeConfig(name)
        wallpaperFile = themeConfig["wallpaperFile"]
        lightColors = themeConfig["lightColors"]
        darkColors = themeConfig["darkColors"]
        foreground = themeConfig["foreground"]
        background = themeConfig["background"]
        cursor = themeConfig["cursor"]
        return cls(wallpaperFile, lightColors, darkColors, foreground, background, cursor)

    @staticmethod
    def loadWallpaper(themeName):
        themeConfig = ConfigObj(getFilePath(themeName, "themeConfig.ini"), unrepr = True)
        command = Config["wallpaperCmd"].strip() + " " + themeConfig["wallpaperFile"]
        callCommand(command)

    @staticmethod
    def load(name):
        Theme.loadWallpaper(name)
        sourceDestPairs = [(getFilePath(name, rule.appName), rule.filePath) for rule in Rules]
        copyFiles(sourceDestPairs)

    def nextColor(self, line, colorString):
        if line.useBackgroundColor:
            return self.background

        if line.useForegroundColor:
            return self.foreground

        if line.useCursorColor:
            return self.cursor

        if colorString.colorType == ColorType.light:
            return self.lightColors.next()

        return self.darkColors.next()

    def shuffleColors(self):
        random.shuffle(lightColors)
        random.shuffle(darkColors)

    def updateConfigFile(self, name, rule):
        colorIndex = 0
        with open(rule.filePath, "r") as f:
            configLines = [line for line in f]
        for line in rule.lines:
            editLine = configLines[line.lineNumber]
            newLine = editLine
            for colorString in line.colorStrings:
                newLine = self.changeLine(newLine, colorString.indeces, self.nextColor(line, colorString))
            configLines[line.lineNumber] = newLine
        writeArrayToFile(configLines, getFilePath(name, rule.appName))

    def updateConfigFiles(self, name):
        for rule in Rules:
            self.updateConfigFile(name, rule)
    
    @staticmethod
    def getThemeConfig(name):
        return ConfigObj(getFilePath(name, "themeConfig.ini"), indent_type = "\t", unrepr = True)

    def writeThemeConfig(self, name):
        themeConfig = Theme.getThemeConfig(name)
        themeConfig["wallpaperFile"] = self.wallpaperFile
        themeConfig["lightColors"] = self.lightColors.colors
        themeConfig["darkColors"] = self.darkColors.colors
        themeConfig["foreground"] = self.foreground
        themeConfig["background"] = self.background
        themeConfig["cursor"] = self.cursor
        themeConfig.write()
 
    def create(self, name):
        callCommand("mkdir " + getFilePath(name))
        self.updateConfigFiles(name)
        self.writeThemeConfig(name)

    def changeLine(self, line, indeces, newValue):
        start = indeces[0]
        end = indeces[1]
        return line[:start] + newValue + line[end:]

class Rule(object):
    config = ConfigObj(CONFIG_FILE_PATH, indent_type = "\t", unrepr = True)

    def __init__(self, filePath, appName, inputFormat):
        self.filePath = os.path.expanduser(filePath.strip())
        self.appName = appName
        self.mode = ColorRegex[inputFormat]
        self.lines = []

    def create(self, autodetect, manualBg, manualFg, manualCursor, defaultColorType):
        lines = []
        lineNo = 0
        search = re.compile(self.mode.value)
        linesFound = []
        lines = []
        if autodetect:
            print("Possible lines to modify found:")
            with open(self.filePath, "r") as f:
                for line in f:
                    matches = search.findall(line)
                    if len(matches) > 0:
                        textLine = Line(lineNumber = lineNo,
                                useCursorColor = (True if manualCursor and "cursor" in line else False),
                                useBackgroundColor = (True if manualBg and "background" in line else False),
                                useForegroundColor = (True if manualFg and "foreground" in line else False))
                        lines.append(LineMatch(line.strip(), lineNo, matches))
                        start = 0
                        for match in matches:
                            indeces = self.getIndeces(start, match, line)
                            textLine.colorStrings.append(ColorString(indeces, match, defaultColorType))
                            start = indeces[1]
                        linesFound.append(textLine)
                    lineNo += 1
            self.printLines(lines)
        else:
            pass
            #TODO: function to get manual lines
        modifyLines = input("Enter which lines you wish to modify. Enter nothing to modify all lines. Example: 2-5,8,10 ").replace(" ", "")
        modifyAll = (True if len(modifyLines) == 0 else False)
        if modifyAll:
            self.lines = linesFound
        else:
            modifyList = lineStringToList(linesToModify)
            for i in range(len(linesFound)):
                if i in modifyList:
                    self.lines.append(linesFound[i])
        print()
        self.printLinesAndColors(lines)
        nonDefaultColorType = (ColorType.light if defaultColorType == ColorType.dark else ColorType.dark)
        nonDefaultLines = input("Enter which lines should use {0} colors. Enter nothing to use {1} colors for all lines. ".format(nonDefaultColorType.name, defaultColorType.name)).strip()
        nonDefaultList = lineStringToList(nonDefaultLines)
        colorList = [colorString for line in self.lines for colorString in line.colorStrings]
        for lineNumber in nonDefaultList:
            colorList[lineNumber - 1].colorType = nonDefaultColorType
        self.save()

    @staticmethod
    def serializeColorStrings(colorStrings):
        return [colorString.toDict() for colorString in colorStrings]
    
    @staticmethod
    def deserializeColorStrings(colorStringDict):
        return [ColorString.fromDict(colorString) for colorString in colorStringDict]

    def getIndeces(self, start, match, line):
        for i in range(start, len(line) - len(match)):
            if line[i:i + len(match)] == match:
                return (i, i + len(match))
        return None

    def printLines(self, lines):
        for i in range(len(lines)):
            print("{0}. (Line {1}) {2}".format(i + 1, lines[i].lineNo + 1, lines[i].text))

    def printLinesAndColors(self, lines):
        colorIndex = 1
        for line in lines:
            print("(Line {0}) {1}".format(line.lineNo + 1, line.text))
            for color in line.colors:
                print("\t{0}. {1}".format(colorIndex, color)) 
                colorIndex += 1
            print()

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
            if line.useCursorColor:
                lineConfig["cursor"] = True
            elif line.useBackgroundColor:
                lineConfig["background"] = True
            elif line.useForegroundColor:
                lineConfig["foreground"] = True

            lineConfig["substringsToEdit"] = Rule.serializeColorStrings(line.colorStrings)

        Rule.config.write()

    @staticmethod
    def loadAll():
        rules = []
        for appName, values in Rule.config.items():
            rules.append(Rule.load(appName))
        return rules
        
    @staticmethod
    def load(appName):
        values = Rule.config[appName]
        rule = Rule(values["filePath"], appName, values["mode"])
        rule.appName = appName
        rule.filePath = values["filePath"]
        rule.mode = values["mode"]

        for key, lineValues in Rule.getLineNumberItems(appName):
            line = Line(lineNumber = lineValues["lineNumber"])
            line.useCursorColor = lineValues.get("cursor", False)
            line.useBackgroundColor = lineValues.get("background", False)
            line.useForegroundColor = lineValues.get("foreground", False)
            line.colorStrings = Rule.deserializeColorStrings(lineValues["substringsToEdit"])
            rule.lines.append(line) 

        return rule

    @staticmethod
    def getLineNumberItems(appName):
        return [(key, value) for key, value in Rule.config[appName].items() if key.startswith("line ")]

def main():
    parseArgs()

Rules = Rule.loadAll()
Config = ConfigObj(getFilePath("config.ini"), unrepr = True)

Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))

def getPoints(img):
    lights = []
    darks = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        if isLight(color):
            lights.append(Point(color, 3, 1))
        elif isDark(color):
            darks.append(Point(color, 3, 1))
    return lights, darks

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
    main()
    #img = Image.open("/home/aschey/Pictures/wallpapers/city.png")
    #img.thumbnail((200, 200))

    #points = getPoints(img)
    #print([rgbToHex(map(int, cluster.center.coords)) for cluster in kmeans(points, 16, 50)])
