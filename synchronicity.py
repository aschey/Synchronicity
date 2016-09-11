#! /usr/bin/env python

#TODO:
    # random theme on startup
    # warn about backup when changing theme
    # warn when any files have been changed
    # allow user to disable autodetect
    # create install script
    # allow user to save current config to a theme
    # allow manual choosing of background, foreground, cursor colors

from PIL import Image
from collections import namedtuple
from math import sqrt
from sys import argv, exit
from numpy import array
from enum import Enum, unique
from configobj import ConfigObj
from argparse import ArgumentParser
import random
import subprocess
import os
import re
import kmeans

CONFIG_DIR = os.path.expanduser("~/.synchronicity")
CONFIG_FILE_PATH = CONFIG_DIR + "/rules.ini"

def createClusters(points, numColors, filename):
    minDistance = Config["minDistance"]

    rgbs = [list(map(int, cluster.center.coords)) for cluster in kmeans.cluster(points, numColors, minDistance)]
    # Create image file so the user can choose colors
    writeToPPM(rgbs, filename, numColors)
    return list(map(rgbToHex, rgbs))

# convert the decimal color values to a hex string
def rgbToHex(rgb):
    return "#" + "".join("{0:02x}".format(val) for val in rgb).upper()

def callCommand(command):
    retCode = subprocess.call(command, shell = True)
    
    # Don't let commands fail silently
    checkForError(retCode != 0, "command {0} failed with error code {1}".format(command, retCode), retCode)

def checkForError(condition, message, errorCode = 1):
    if condition:
        print(message)
        exit(errorCode)

def getFilePath(*args):
    pathElements = [CONFIG_DIR] + list(args)
    return "/".join(pathElements)

def errorIfNoTheme(themeName):
    checkForError(not os.path.isdir(getFilePath(themeName)), "Error: theme does not exist")

def writeToPPM(rgbs, filename, numColors):
    COLORWIDTH = 54
    with open(filename, 'w') as f:
        # Write the header
        f.write('P3\n')
        f.write(str(numColors * COLORWIDTH) + " " + str(COLORWIDTH) + "\n")
        f.write('255\n')

        # Draw colors in a numColors * COLORWIDTH by COLORWIDTH block
        for i in range(COLORWIDTH):
            for rgb in rgbs:
                for j in range(COLORWIDTH):
                    for val in rgb:
                        f.write(str(val) + " ")
                    f.write("\n")

def getColorFormatString(numColors):
    formatString = ""
    # Make room to display the colors
    formatString += formatString.join(["\\n" for i in range(6)])
    formatString += "   "
    # Display colors with enough space between them
    formatString += "".join(["%2d       " for i in range(numColors)])
    return formatString


def numbersToString(start, end):
    return " ".join([str(i) for i in range(start, end)])

def copyFiles(sourceDestPairs):
    command = ""
    
    # copy all files from their source to their destination
    for sourceDestPair in sourceDestPairs:
        command += "cp {0} {1};".format(sourceDestPair[0], sourceDestPair[1])

    callCommand(command)

def printToScreen(numLights, numDarks):
    numColors = numDarks + numLights
    lightFormat = getColorFormatString(numLights)
    darkFormat = getColorFormatString(numDarks)
    lightVals = numbersToString(1, numLights + 1)
    darkVals = numbersToString(numLights + 1, numColors + 1)

    # Display light colors then dark colors
    command = ("./drawimage.sh lightColors.ppm 60; " +
            "./drawimage.sh darkColors.ppm 140; " + 
            "printf \"{0}\n\" {1}; printf \"{2}\n\" {3};").format(lightFormat, lightVals, darkFormat, darkVals)

    callCommand(command)

def createTheme(args):
    numLights = args.lights
    numDarks = args.darks

    img = Image.open(args.filename)
    # Extract light and dark colors from the image
    lights, darks = kmeans.getPoints(img)
    checkForError(len(lights) < numLights, "Error: image does not contain enough light colors")
    checkForError(len(darks) < numDarks, "Error: image does not contain enough dark colors")

    print("Calculating colors...")
    lightRgbs = createClusters(lights, numLights, "lightColors.ppm")
    darkRgbs = createClusters(darks, numDarks, "darkColors.ppm")
    allRgbs = lightRgbs + darkRgbs

    callCommand("clear")
    printToScreen(numLights, numDarks)
    
    backgroundIndex = int(input("Which color do you want to be the background? "))
    foregroundIndex = int(input("Which color do you want to be the foreground? "))
    cursorIndex = int(input("Which color do you want to be the cursor? "))

    # Determine if the scheme should be dark on light or light on dark
    palette, backgrounds = ((lightRgbs, darkRgbs) if backgroundIndex > numLights else (darkRgbs, lightRgbs))
    # User-inputted indeces are one-based
    background = allRgbs[backgroundIndex - 1]
    foreground = allRgbs[foregroundIndex - 1]
    cursor = allRgbs[cursorIndex - 1]

    palette.remove(foreground)
    palette.remove(cursor)
    backgrounds.remove(background)

    # Don't need image files anymore
    callCommand("rm lightColors.ppm; rm darkColors.ppm")

    Theme(args.filename, lightRgbs, darkRgbs, foreground, background, cursor).create(args.name)

def backup(args):
    sourceDestPairs = [(rule.filePath, getFilePath(rule.appName + ".backup")) for rule in Rules]
    copyFiles(sourceDestPairs)

def createRule(args):
    defaultColorType = ColorType[args.d]
    autoBg = args.auto_bg
    autoFg = args.auto_fg
    autoCursor = args.auto_cursor

    Rule(args.filename, args.appName, args.c).create(autoBg, autoFg, autoCursor, defaultColorType)

def loadTheme(args):
    Theme.load(args.themeName)

def revert(args):
    sourceDestPairs = [(getFilePath(rule.appName + ".backup"), rule.filePath) for rule in Rules]
    copyFiles(sourceDestPairs)

def rmRule(args):
    del Rule.config[args.appName]
    Rule.config.write()

def rmTheme(args):
    themePath = getFilePath(args.themeName)
    callCommand("rm -r " + themePath)

def reconfigure(args):
    theme = Theme.fromConfig(args.themeName)
    rule = Rule.load(args.appName)
    theme.shuffleColors()
    theme.createAppConfigFile(args.themeName, rule)

def startup(args):
    themeName = Config["currentTheme"]
    Theme.loadWallpaper(themeName)

def parseArgs():
    argParser = ArgumentParser()
    subparsers = argParser.add_subparsers()

    themeParser = subparsers.add_parser("theme", help = "create a new theme")
    themeParser.add_argument("name", help = "theme name")
    themeParser.add_argument("filename", help = "image file to load the theme from")
    themeParser.add_argument("lights", type = int, help = "number of light colors to use")
    themeParser.add_argument("darks", type = int, help = "number of dark colors to use")
    themeParser.set_defaults(func = createTheme)

    ruleParser = subparsers.add_parser("rule", help = "create a new rule")
    ruleParser.add_argument("appName", help = "name of the app the filename is used for")
    ruleParser.add_argument("filename", help = "config file to create the rule for")
    ruleParser.add_argument("-c", choices = ["hex", "rgb", "numeric"], default = "hex", 
            help = "(default: 'hex') color format the config file stores colors as")
    ruleParser.add_argument("-d", choices = ["dark", "light"], default = "light", 
            help = "(default: 'light') default color type to use")
    ruleParser.add_argument("--auto-bg", action = "store_true", 
            help = "use the background color designated for the theme")
    ruleParser.add_argument("--auto-fg", action = "store_true", 
            help = "use the foreground color designated for the theme")
    ruleParser.add_argument("--auto-cursor", action = "store_true", 
            help = "use the cursor color designated for the theme")
    ruleParser.set_defaults(func = createRule)

    backupParser = subparsers.add_parser("backup", help = "backup existing configuration")
    backupParser.set_defaults(func = backup)

    loadParser = subparsers.add_parser("load", help = "load a theme")
    loadParser.add_argument("themeName")
    loadParser.set_defaults(func = loadTheme)

    revertParser = subparsers.add_parser("revert", help = "revert config files to their backup copy")
    revertParser.set_defaults(func = revert)

    rmRuleParser = subparsers.add_parser("rm-rule", help = "remove a rule from the rule config file")
    rmRuleParser.add_argument("appName")
    rmRuleParser.set_defaults(func = rmRule)

    rmThemeParser = subparsers.add_parser("rm-theme", help = "delete a theme")
    rmThemeParser.add_argument("themeName")
    rmThemeParser.set_defaults(func = rmTheme)

    reconfigureParser = subparsers.add_parser("reconfigure", 
            help = "generate a new colorscheme for one app using the colors for the specified theme")
    reconfigureParser.add_argument("appName")
    reconfigureParser.add_argument("themeName")
    reconfigureParser.set_defaults(func = reconfigure)

    startupParser = subparsers.add_parser("startup", 
            help = "use this option to load the theme wallpaper at startup")
    startupParser.set_defaults(func = startup)

    args = argParser.parse_args()
    if hasattr(args, "themeName"):
        errorIfNoTheme(args.themeName)

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
        # Start from the first color if all colors have been used
        if self.index == len(self.colors):
            self.index = 0
        return currentColor

    def shuffle(self):
        random.shuffle(self.colors)

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

    # For serialization
    def toDict(self):
        return { "indeces": self.indeces, "color": self.color, "colorType": self.colorType.value }

    # For deserialization
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
        # Call the command located in the config file to load the specified wallpaper
        command = Config["wallpaperCmd"].strip() + " " + themeConfig["wallpaperFile"]
        callCommand(command)

    @staticmethod
    def load(name):
        if not os.path.isdir(getFilePath(name)):
            print("Error: Theme {0} does not exist".format(name))
            exit(1)

        Theme.loadWallpaper(name)
        # Copy the files from the theme folder to their actual config paths
        sourceDestPairs = [(getFilePath(name, rule.appName), rule.filePath) for rule in Rules]
        copyFiles(sourceDestPairs)

        # Update the config to reflect the theme change
        Config["currentTheme"] = name
        Config.write()

    def shuffleColors(self):
        self.lightColors.shuffle()
        self.darkColors.shuffle()

    def createAppConfigFile(self, name, rule):
        # Load the whole config file for easier editing
        with open(rule.filePath, "r") as f:
            configLines = [line for line in f]

        for line in rule.lines:
            editLine = configLines[line.lineNumber]
            newLine = editLine
            for colorString in line.colorStrings:
                # Edit the line one color at a time
                newLine = self._changeLine(newLine, colorString.indeces, self._nextColor(line, colorString))

            configLines[line.lineNumber] = newLine
        
        # Create the new config file in the current theme's directory
        self._writeArrayToFile(configLines, getFilePath(name, rule.appName))

    def createAppConfigFiles(self, name):
        for rule in Rules:
            self.createAppConfigFile(name, rule)
    
    @staticmethod
    def getThemeConfig(name):
        return ConfigObj(getFilePath(name, "themeConfig.ini"), indent_type = "\t", unrepr = True)

    def create(self, name):
        callCommand("mkdir " + getFilePath(name))
        self.createAppConfigFiles(name)
        self._writeThemeConfig(name)

    def _writeThemeConfig(self, name):
        themeConfig = Theme.getThemeConfig(name)
        themeConfig["wallpaperFile"] = self.wallpaperFile
        themeConfig["lightColors"] = self.lightColors.colors
        themeConfig["darkColors"] = self.darkColors.colors
        themeConfig["foreground"] = self.foreground
        themeConfig["background"] = self.background
        themeConfig["cursor"] = self.cursor
        themeConfig.write()


    def _changeLine(self, line, indeces, newValue):
        start = indeces[0]
        end = indeces[1]
        return line[:start] + newValue + line[end:]

    def _writeArrayToFile(self, fileLines, newFileName):
        # Note: Assumes newlines are already included
        with open(newFileName, "w") as f:
            for line in fileLines:
                f.write(line)

    def _nextColor(self, line, colorString):
        if line.useBackgroundColor:
            return self.background

        if line.useForegroundColor:
            return self.foreground

        if line.useCursorColor:
            return self.cursor

        if colorString.colorType == ColorType.light:
            return self.lightColors.next()

        return self.darkColors.next()

class Rule(object):
    config = ConfigObj(CONFIG_FILE_PATH, indent_type = "\t", unrepr = True)

    def __init__(self, filePath, appName, inputFormat):
        self.filePath = os.path.expanduser(filePath.strip())
        self.appName = appName
        self.mode = ColorRegex[inputFormat]
        self.lines = []

    @staticmethod
    def serializeColorStrings(colorStrings):
        return [colorString.toDict() for colorString in colorStrings]
    
    @staticmethod
    def deserializeColorStrings(colorStringDict):
        return [ColorString.fromDict(colorString) for colorString in colorStringDict]

    def create(self, autoBg, autoFg, autoCursor, defaultColorType):
        linesFound, linesToDisplay = self._autodetectLines(autoBg, autoFg, autoCursor, defaultColorType)

        modifyLines = input("Enter which lines you wish to modify. " + 
                "Enter nothing to modify all lines. Example: 2-5,8,10 ").replace(" ", "")
        modifyAll = (True if len(modifyLines) == 0 else False)

        if modifyAll:
            self.lines = linesFound
        else:
            modifyList = self._lineStringToList(linesToModify)
            for i in range(len(linesFound)):
                if i in modifyList:
                    self.lines.append(linesFound[i])
        print()
        # Print the lines and all of their colors to allow the user to choose light and dark colors
        self._printLinesAndColors(linesToDisplay)

        nonDefaultColorType = (ColorType.light if defaultColorType == ColorType.dark else ColorType.dark)
        nonDefaultLines = input(("Enter which lines should use {0} colors. " + 
                "Enter nothing to use {1} colors for all lines. ").format(nonDefaultColorType.name, 
                    defaultColorType.name)).strip()

        nonDefaultList = self._lineStringToList(nonDefaultLines)
        colorList = [colorString for line in self.lines for colorString in line.colorStrings]
        # Update the substrings that should not use the default color type
        for lineNumber in nonDefaultList:
            colorList[lineNumber - 1].colorType = nonDefaultColorType

        # Write the rule to the config file
        self.save()

    def save(self):
        if not os.path.isdir(CONFIG_DIR):
            callCommand("mkdir " + CONFIG_DIR)

        # Create a new section in the config file for this rule
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
            
            # ConfigObj can't store user-defined objects, so serialize to dict
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

        for key, lineValues in Rule._getLineNumberItems(appName):
            line = Line(lineNumber = lineValues["lineNumber"])
            line.useCursorColor = lineValues.get("cursor", False)
            line.useBackgroundColor = lineValues.get("background", False)
            line.useForegroundColor = lineValues.get("foreground", False)
            # Convert dictionaries into ColorString objects
            line.colorStrings = Rule.deserializeColorStrings(lineValues["substringsToEdit"])
            rule.lines.append(line) 

        return rule

    def _autodetectLines(self, autoBg, autoFg, autoCursor, defaultColorType):
        lineNo = 0
        textLines = []
        lines = []
        search = re.compile(self.mode.value)

        print("Possible lines to modify found:")
        with open(self.filePath, "r") as f:
            for textLine in f:
                # Search for substrings in the line that match the color regex
                matches = search.findall(textLine)
                if len(matches) > 0:
                    line = Line(lineNumber = lineNo,
                            useCursorColor = (True if autoCursor and "cursor" in textLine else False),
                            useBackgroundColor = (True if autoBg and "background" in textLine else False),
                            useForegroundColor = (True if autoFg and "foreground" in textLine else False))
                    textLines.append(LineMatch(textLine.strip(), lineNo, matches))
                    start = 0
                    for match in matches:
                        indeces = self._getIndeces(start, match, textLine)
                        line.colorStrings.append(ColorString(indeces, match, defaultColorType))
                        start = indeces[1]
                    lines.append(line)
                lineNo += 1
        # Display the lines found to the user so the user can choose which lines to modify
        self._printLines(textLines)

        return lines, textLines
    
    def _getIndeces(self, start, match, line):
        try:
            start = line.index(match, start)
            end = start + len(match)
            return (start, end)
        except ValueError:
            return None

    def _lineStringToList(self, lineString):
        if len(lineString) == 0:
            return []
        modifyIndeces = []
        splitLine = lineString.split(",")
        for lineNumber in splitLine:
            try:
                lineNumber = int(lineNumber)
                modifyIndeces.append(lineNumber)
            except ValueError:
                # Number is formatted like '1-5' instead of just '1'
                start = int(lineNumber[0])
                end = int(lineNumber[2])

                # Include the whole range of numbers
                for i in range(start, end + 1):
                    modifyIndeces.append(i)

        # Sort in case user entered numbers out of order
        return sorted(modifyIndeces)


    def _printLines(self, lines):
        for i in range(len(lines)):
            # Indeces displayed to user are one-based instead of zero-based
            print("{0}. (Line {1}) {2}".format(i + 1, lines[i].lineNo + 1, lines[i].text))

    def _printLinesAndColors(self, lines):
        colorIndex = 1
        for line in lines:
            print("(Line {0}) {1}".format(line.lineNo + 1, line.text))
            for color in line.colors:
                print("\t{0}. {1}".format(colorIndex, color)) 
                colorIndex += 1
            print()

    @staticmethod
    def _getLineNumberItems(appName):
        # Return all config data for lines formatted like "[[line xxx]]"
        return [(key, value) for key, value in Rule.config[appName].items() if key.startswith("line ")]

    
    
def main():
    parseArgs()

Rules = Rule.loadAll()
Config = ConfigObj(getFilePath("config.ini"), unrepr = True)

if __name__ == "__main__":
    main()
