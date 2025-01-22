### Description

Generate a VTK colormap from a ParaView JSON description of a colormap.

This script will let you choose a colormap by name from [ParaView Default Colormaps](https://gitlab.kitware.com/paraview/paraview/-/blob/master/Remoting/Views/ColorMaps.json).

A cone is rendered to demonstrate the resultant colormap.

 C++ and Python functions can also be generated which implement the colormap. You can copy/paste these directly into your code. Or they can replace the existing function in:

 - [ColorMapToLUT.py](../ColorMapToLUT)
 - [ColorMapToLUT.cxx](../../../Cxx/Utilities/ColorMapToLUT)

This program was inspired by this discussion: [Replacement default color map and background palette](https://discourse.paraview.org/t/replacement-default-color-map-and-background-palette/12712), the **Fast** colormap from this discussion is used as test data here.

A good initial source for color maps is: [SciVisColor](https://sciviscolor.org/) -- this will provide you with plenty of XML examples.

Further information:

- [VTK Examples - Some ColorMap to LookupTable tools]()
- [How to export ParaView colormap into a format that could be read by matplotlib](https://discourse.paraview.org/t/how-to-export-paraview-colormap-into-a-format-that-could-be-read-by-matplotlib/2436)
- [How to export ParaView colormap into a format that could be read by matplotlib?](https://discourse.paraview.org/t/how-to-export-paraview-colormap-into-a-format-that-could-be-read-by-matplotlib/2394)
- [Color map advice and resources](https://discourse.paraview.org/t/color-map-advice-and-resources/6452/4)
