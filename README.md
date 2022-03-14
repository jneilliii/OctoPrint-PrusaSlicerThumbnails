# Slicer Thumbnails

![GitHub Downloads](https://badgen.net/github/assets-dl/jneilliii/OctoPrint-PrusaSlicerThumbnails/)

This plugin will extract embedded thumbnails from gcode files created from [PrusaSlicer](#PrusaSlicer), [SuperSlicer](#SuperSlicer), [Cura](#Cura), or [Simplify3D](#Simplify3D).

The preview thumbnail can be shown in OctoPrint from the files list by clicking the newly added image button.

![button](screenshot_button.png)

The thumbnail will open in a modal window.

![thumbnail](screenshot_thumbnail.png)

If enabled in settings the thumbnail can also be embedded as an inline thumbnail within the file list itself. If you use this option it's highly recommended to also set the option to set file list height or position inline image to the left.

![thumbnail](screenshot_inline_thumbnail.png)

## Configuration

### PrusaSlicer

Available via the UI since version 2.3, requires expert mode to be enabled in the upper right corner of the program to see the setting.

![PrusaSlicer](screenshot_prusaslicer.png)

**Warning**: the higher the resolution of the thumbnail you use in this setting the larger your gcode file will be when sliced.

### SuperSlicer

Available via the UI since version 2.2.53, requires expert mode to be enabled in the upper right corner of the program to see the setting.

![SuperSlicer](screenshot_superslicer.png)

**Warning**: the higher the resolution of the thumbnail you use in this setting the larger your gcode file will be when sliced.

### Cura

A post-processing script has been bundled since version 4.9. For older versions you can manually add the post-processing script as described [here](https://gist.github.com/jneilliii/4034c84d1ec219c68c8877d0e794ec4e).

![Cura](screenshot_cura.png)

### Simplify3D

Available as a post-processing script for [windows](https://github.com/boweeble/s3d-thumbnail-generator),  [linux](https://github.com/NotExpectedYet/s3d-thumbnail-generator), or [macos](https://github.com/idcrook/s3d-thumbnail-generator-macos) thanks to [@boweeble](https://github.com/boweeble/), [@NotExpectedYet](https://github.com/NotExpectedYet/), and [@idcrook](https://github.com/idcrook/).

## Get Help

If you experience issues with this plugin or need assistance please use the issue tracker by clicking issues above.

### Additional Plugins

Check out my other plugins [here](https://plugins.octoprint.org/by_author/#jneilliii)

### Sponsors
- Andreas Lindermayr
- [@Mearman](https://github.com/Mearman)
- [@TheTuxKeeper](https://github.com/thetuxkeeper)
- [@tideline3d](https://github.com/tideline3d/)
- [SimplyPrint](https://simplyprint.dk/)
- [Andrew Beeman](https://github.com/Kiendeleo)
- [Calanish](https://github.com/calanish)
- [Will O](https://github.com/4wrxb)
- [Lachlan Bell](https://lachy.io/)
- [Johnny Bergdal](https://github.com/bergdahl)
- [Leigh Johnson](https://github.com/leigh-johnson)
- [Stephen Berry](https://github.com/berrystephenw)
- [Guyot François](https://github.com/iFrostizz)
- César Romero
- [Steve Dougherty](https://github.com/Thynix)
- [Kyle Menigoz](https://menigoz.me)
## Support My Efforts
I, jneilliii, programmed this plugin for fun and do my best effort to support those that have issues with it, please return the favor and leave me a tip or become a Patron if you find this plugin helpful and want me to continue future development.

[![Patreon](patreon-with-text-new.png)](https://www.patreon.com/jneilliii) [![paypal](paypal-with-text.png)](https://paypal.me/jneilliii)

<small>No paypal.me? Send funds via PayPal to jneilliii&#64;gmail&#46;com</small>
