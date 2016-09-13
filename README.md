# Synchronicity

Synchronicity is a command-line utility for creating and maintaining unified colorschemes for all your Linux applications.

Synchronicity uses two major concepts: rules and themes.

**Rules** are stored in `~/.synchronicity/rules.ini`. The purpose of a rule is to determine which parts of a configuration file are responsible for setting the colors of the application that the coniguration file corresponds to.

**Themes** each have their own directory (`~/.synchronicity/themeName`). When a theme is created, it takes each original configuration file, replaces its colors with the colors generated for the theme, and places the newly created copy in the theme's directory. When the theme is loaded, it replaces the actual configuration files with the ones in the theme's directory. Themes also have their own configuration files (`~/.synchronicity/themeName/themeConfig.ini`) which contain data on the theme's colors and where the image used to generate the theme is located.

## Documentation
Synchronicity responds to the following commands:

`synchronicity theme name filename lights darks`

* Creates a new theme

* **name:** What the theme will be called

* **filename:** Path to the image file to create the colorscheme from

* **lights:** Number of light colors to use in the scheme

* **darks:** Number of dark colors to use in the scheme

* Example: `synchronicity theme diamonds ~/pictures/diamonds.jpg 18 5`

* After running this command, the user will be prompted to choose the cursor, background, and foreground colors from the list of available colors. It is recommended to use at least 18 light colors (16 colors for terminal colorscheme plus foreground color and cursor color) and 3 - 5 dark colors (to have a few choices for a background color) for a light-on-dark colorscheme, or 18 dark colors and 3 - 5 light colors for a dark-on-light colorscheme.

`synchronicity rule appName filename [-c] [-d] [--auto-fg] [--auto-bg] [--auto-cursor]`

* Creates a new rule

* **appName:** Alias to use for the application that the configuration file corresponds to

* **filename:** Path to the configuration file to create a rule for

* optional arguments:

    * **-c {hex, rgb, numeric} default: hex** Color format that the configuration file uses for colors. (hex: #000000, RGB: 00,00,00, numeric: 00)

    * **-d {dark, light} default: light** Default color type to use. The user will have to manually select the lines in the configuration file that should not use the default color type.

    * **--auto-bg** Use the designated background color for the theme where the configuration file contains a line like "background #000000"

    * **--auto-fg** Use the designated foreground color for the theme where the configuration file contains a line like "foreground #000000"

    * **--auto-cursor** Use the designated cursor color for the theme where the configuration file contains a line like "cursor #000000"

* Example: `synchronicity rule i3 ~/.i3/config -c rgb -d dark --auto-fg --auto-bg --auto-cursor`

`synchronicity backup`

* Backs up the all of the configuration files which have a rule configured for them. Backup files will be placed in `~/.synchronicity/appName.backup`. This allows the user to try out new themes without losing their current configuration if it is not currently stored in its own theme.

`synchonicity load themeName`

* Loads a theme

* **themeName:** Name of the theme to load

* Example: `synchronicity load diamonds`

`synchronicity revert`

* Reverts all config files to the copies stored in `~/.synchronicity/{appName}.backup`

* This is used to restore all config files saved by running `synchonicity backup`

`synchronicity rm-rule appName`

* Deletes the rule from `rules.ini`

* Example: `synchronicity rm-rule i3`

`synchonicity rm-theme themeName`

* Deletes the theme

* Example: `synchronicity rm-theme diamonds`

`synchonicity reconfigure appName themeName`

* Shuffles the order of the colors in a particular rule. Use this option if you like the overall colorscheme for the theme but one app has colors that don't look right together.

* **appName:** Name of the app to reconfigure

* **themeName:** Name of the theme to reconfigure the app for

* Example: `reconfigure i3 diamonds`

* Note: If you run `synchronicity reconfigure` on the current theme, you will have to run `synchronicity load` to see the changes.

`synchronicity startup`

* Place this command in `~/.xinitrc` or some equivalent in order to load the image file on startup.

## Screenshots

![Dots](http://i.imgur.com/OyIpFHc.png)
![Triangles](http://i.imgur.com/KtO5onC.png)
![Arch](http://i.imgur.com/xHpnxf2.png)
