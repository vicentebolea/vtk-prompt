### Description

This example shows how to adjust a colormap so that the colormap scalar range matches the scalar range on the object. This is done by adjusting the colormap so that the colormap scalar range matches the scalar range of the object by rescaling the control points and, optionally, reversing the order of the colors.

Of course, if you are generating the scalars, it may be easier to just change the scalar range of your filter. However, this may not be possible in some cases.

Here, we generate the original Color Transfer Function (CTF) corresponding to the seven colors that Isaac Newton labeled when dividing the spectrum of visible light in 1672. There are seven colors and the scalar range is [-1, 1].

The cylinder has a vtkElevationFilter applied to it with a scalar range of [0, 1].

There are four images:

- Original -  The cylinder is colored by only the top four colors from the CTF. This is because the elevation scalar range on the cylinder is [0, 1] and the CTF scalar range is [-1, 1]. So the coloring is green->violet.
- Reversed - We have reversed the colors from the original CTF and the lower four colors in the original CTF are now the top four colors used to color the cylinder. The coloring is now green->red.
- Rescaled - The original CTF is rescaled to the range [0, 1] to match the scalar range of the elevation filter. The coloring is red->violet.
- Rescaled and Reversed - The original CTF is rescaled to the range [0, 1] and the colors reversed. The coloring is violet->red.
