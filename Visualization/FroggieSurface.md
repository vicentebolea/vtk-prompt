### Description

Construct surfaces from a segmented frog dataset. Up to fifteen different surfaces may be extracted. The example, `FroggieView` is similar to this example and uses sliders to control the opacities of the tissues.

By default the frog is oriented so that we look down on the dorsal (posterior) surface and the superior surface faces the top of the screen. The frog is rendered with the skin being translucent so that you can see the internal organs.

In the lower left of the image there is a prop assembly with labelled XYZ axes and a cube labelled with anatomical orientations:

- **Sagittal plane**
  - L - left
  - R - right
- **Coronal plane**
  - A - anterior
  - P - posterior
- **Transverse plane**
  - S - superior  
  - I - inferior

This prop assembly can be moved and resized.

Individual tissues can be specified by using the "**-t**" option e.g. "**-t skin skeleton**".

We use vtkFlyingEdges3D to take the 3D structured point set and generate the iso-surfaces. However, if desired, you can specify vtkMarchingCubes instead, use the option "**-m**".

The parameters used to generate the example image are loaded from a JSON file containing the data needed to access and generate the actors for each tissue along with other supplementary data such as the data file names. This means that the user need only load this one file in order to generate the data for rendering. This file is called:

``` text
<DATA>/Frog_mhd.json
```

Where `<DATA>` is the path to `?vtk-?examples/src/Testing/Data`.

For information about the parameters in the JSON file, please see [Frog_mhd_format](../../Documentation/Frog_mhd_format.md).

The code uses a general way of specifying transformations that can permute image and other geometric data in order to maintain proper orientation regardless of the acquisition order. See the class `SliceOrder`.

The dataset was prepared at the Lawrence Berkeley National Laboratories and is included with their permission. The data was acquired by physically slicing the frog and photographing the slices. The original segmented data is in the form of tissue masks with one file per tissue. There are 136 slices per tissue and 15 different tissues. Each slice is 470 by 500 pixels.

To accommodate the volume readers in VTK, the mask files were processed and combined into one vtkMetaImageReader file, called `frogtissue.mhd`. Integer numbers 1-15 are used to represent the 15 tissues. A similar process was done for the frog skin with the result being stored in a file called `frog.mhd`.

Further information:

- [VTK Examples - FroggieSurface and FroggieView](https://discourse.vtk.org/t/vtk-examples-froggiesurface-and-froggieview/11952)


!!! info
    Mutually exclusive options "**-a, -b, -c, -d**" are provided to let you generate approximations to the following figures: [Figure 12-9a](../../../VTKBook/12Chapter12/#Figure%2012-9a), [Figure 12-9b](../../../VTKBook/12Chapter12/#Figure%2012-9b), [Figure 12-9c](../../../VTKBook/12Chapter12/#Figure%2012-9c), and [Figure 12-9d](../../../VTKBook/12Chapter12/#Figure%2012-9d) in [Chapter 12](../../../VTKBook/12Chapter12) of the [VTK Textbook](../../../VTKBook/01Chapter1).
