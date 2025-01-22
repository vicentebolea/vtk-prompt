#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingFreeType
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkCylinderSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkDiscretizableColorTransferFunction,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
    vtkTextMapper,
    vtkTextProperty
)


def main():
    colors = vtkNamedColors()
    colors.SetColor('ParaViewBkg', 82, 87, 110, 255)

    ren_win = vtkRenderWindow()
    ren_win.SetSize(640 * 2, 480 * 2)
    ren_win.SetWindowName('RescaleReverseLUT')
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    ctf = list()
    ctf.append(get_ctf(False))
    ctf.append(rescale_ctf(ctf[0], 0, 1, False))
    ctf.append(rescale_ctf(ctf[0], *ctf[0].GetRange(), True))
    ctf.append(rescale_ctf(ctf[0], 0, 1, True))

    # Define viewport ranges.
    xmins = [0.0, 0.0, 0.5, 0.5]
    xmaxs = [0.5, 0.5, 1.0, 1.0]
    ymins = [0.5, 0.0, 0.5, 0.0]
    ymaxs = [1.0, 0.5, 1.0, 0.5]

    # Define titles.
    titles = ['Original', 'Rescaled', 'Reversed', 'Rescaled and Reversed']

    # Create a common text property.
    text_property = vtkTextProperty()
    text_property.SetFontSize(36)
    text_property.SetJustificationToCentered()
    text_property.SetColor(colors.GetColor3d('LightGoldenrodYellow'))

    sources = list()
    elevation_filters = list()
    mappers = list()
    actors = list()
    scalar_bars = list()
    renderers = list()
    text_mappers = list()
    text_actors = list()

    for i in range(0, 4):
        cylinder = vtkCylinderSource()
        cylinder.SetCenter(0.0, 0.0, 0.0)
        cylinder.SetResolution(6)
        cylinder.Update()
        bounds = cylinder.GetOutput().GetBounds()
        sources.append(cylinder)

        elevation_filter = vtkElevationFilter()
        elevation_filter.SetScalarRange(0, 1)
        elevation_filter.SetLowPoint(0, bounds[2], 0)
        elevation_filter.SetHighPoint(0, bounds[3], 0)
        elevation_filter.SetInputConnection(sources[i].GetOutputPort())
        elevation_filters.append(elevation_filter)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(elevation_filters[i].GetOutputPort())
        mapper.SetLookupTable(ctf[i])
        mapper.SetColorModeToMapScalars()
        mapper.InterpolateScalarsBeforeMappingOn()
        mappers.append(mapper)

        actor = vtkActor()
        actor.SetMapper(mappers[i])
        actors.append(actor)

        # Add a scalar bar.
        scalar_bar = vtkScalarBarActor()
        scalar_bar.SetLookupTable(ctf[i])
        scalar_bars.append(scalar_bar)

        text_mappers.append(vtkTextMapper())
        text_mappers[i].SetInput(titles[i])
        text_mappers[i].SetTextProperty(text_property)

        text_actors.append(vtkActor2D())
        text_actors[i].SetMapper(text_mappers[i])
        # Note: The position of an Actor2D is specified in display coordinates.
        text_actors[i].SetPosition(300, 16)

        ren = vtkRenderer()
        ren.SetBackground(colors.GetColor3d('ParaViewBkg'))
        ren.AddActor(actors[i])
        ren.AddActor(scalar_bars[i])
        ren.AddActor(text_actors[i])
        ren.SetViewport(xmins[i], ymins[i], xmaxs[i], ymaxs[i])
        renderers.append(ren)

        ren_win.AddRenderer(renderers[i])

    ren_win.Render()
    iren.Start()


def get_ctf(modern=False):
    """
    Generate the color transfer function.

    The seven colors corresponding to the colors that Isaac Newton labelled
        when dividing the spectrum of visible light in 1672 are used.

    The modern variant of these colors can be selected and used instead.

    See: [Rainbow](https://en.wikipedia.org/wiki/Rainbow)

    :param modern: Selects either Newton's original seven colors or modern version.
    :return: The color transfer function.
    """

    # name: Rainbow, creator: Andrew Maclean
    # interpolationspace: RGB, space: rgb
    # file name:

    ctf = vtkDiscretizableColorTransferFunction()

    ctf.SetColorSpaceToRGB()
    ctf.SetScaleToLinear()
    ctf.SetNanColor(0.5, 0.5, 0.5)
    ctf.SetBelowRangeColor(0.0, 0.0, 0.0)
    ctf.UseBelowRangeColorOn()
    ctf.SetAboveRangeColor(1.0, 1.0, 1.0)
    ctf.UseAboveRangeColorOn()

    if modern:
        ctf.AddRGBPoint(-1.0, 1.0, 0.0, 0.0)  # Red
        ctf.AddRGBPoint(-2.0 / 3.0, 1.0, 128.0 / 255.0, 0.0)  # Orange #ff8000
        ctf.AddRGBPoint(-1.0 / 3.0, 1.0, 1.0, 0.0)  # Yellow
        ctf.AddRGBPoint(0.0, 0.0, 1.0, 0.0)  # Green #00ff00
        ctf.AddRGBPoint(1.0 / 3.0, 0.0, 1.0, 1.0)  # Cyan
        ctf.AddRGBPoint(2.0 / 3.0, 0.0, 0.0, 1.0)  # Blue
        ctf.AddRGBPoint(1.0, 128.0 / 255.0, 0.0, 1.0)  # Violet #8000ff
    else:
        ctf.AddRGBPoint(-1.0, 1.0, 0.0, 0.0)  # Red
        ctf.AddRGBPoint(-2.0 / 3.0, 1.0, 165.0 / 255.0, 0.0)  # Orange #00a500
        ctf.AddRGBPoint(-1.0 / 3.0, 1.0, 1.0, 0.0)  # Yellow
        ctf.AddRGBPoint(0.0, 0.0, 125.0 / 255.0, 0.0)  # Green #008000
        ctf.AddRGBPoint(1.0 / 3.0, 0.0, 153.0 / 255.0, 1.0)  # Blue #0099ff
        ctf.AddRGBPoint(2.0 / 3.0, 68.0 / 255.0, 0, 153.0 / 255.0)  # Indigo #4400ff
        ctf.AddRGBPoint(1.0, 153.0 / 255.0, 0.0, 1.0)  # Violet #9900ff

    ctf.SetNumberOfValues(7)
    ctf.DiscretizeOn()

    return ctf


def generate_new_ctf(old_ctf, new_x, new_rgb, reverse=False):
    """
    Generate a new color transfer function from the old one,
    adding in the new x and rgb values.

    :param old_ctf: The old color transfer function.
    :param new_x: The new color x-values.
    :param new_rgb: The color RGB values.
    :param reverse: If true, reverse the colors.
    :return: The new color transfer function.
    """
    new_ctf = vtkDiscretizableColorTransferFunction()
    new_ctf.SetScale(old_ctf.GetScale())
    new_ctf.SetColorSpace(old_ctf.GetColorSpace())
    new_ctf.SetNanColor(old_ctf.GetNanColor())
    if not reverse:
        new_ctf.SetBelowRangeColor(old_ctf.GetBelowRangeColor())
        new_ctf.SetUseBelowRangeColor(old_ctf.GetUseBelowRangeColor())
        new_ctf.SetAboveRangeColor(old_ctf.GetAboveRangeColor())
        new_ctf.SetUseAboveRangeColor(old_ctf.GetUseAboveRangeColor())
    else:
        new_ctf.SetBelowRangeColor(old_ctf.GetAboveRangeColor())
        new_ctf.SetUseBelowRangeColor(old_ctf.GetUseAboveRangeColor())
        new_ctf.SetAboveRangeColor(old_ctf.GetBelowRangeColor())
        new_ctf.SetUseAboveRangeColor(old_ctf.GetUseBelowRangeColor())
    new_ctf.SetNumberOfValues(len(new_x))
    new_ctf.SetDiscretize(old_ctf.GetDiscretize())
    if not reverse:
        for i in range(0, len(new_x)):
            new_ctf.AddRGBPoint(new_x[i], *new_rgb[i])
    else:
        sz = len(new_x)
        for i in range(0, sz):
            j = sz - (i + 1)
            new_ctf.AddRGBPoint(new_x[i], *new_rgb[j])
    new_ctf.Build()
    return new_ctf


def rescale(values, new_min=0, new_max=1):
    """
    Rescale the values.

    See: https://stats.stackexchange.com/questions/25894/changing-the-scale-of-a-variable-to-0-100

    :param values: The values to be rescaled.
    :param new_min: The new minimum value.
    :param new_max: The new maximum value.
    :return: The rescaled values.
    """
    res = list()
    old_min, old_max = min(values), max(values)
    for v in values:
        new_v = (new_max - new_min) / (old_max - old_min) * (v - old_min) + new_min
        # new_v1 = (new_max - new_min) / (old_max - old_min) * (v - old_max) + new_max
        res.append(new_v)
    return res


def rescale_ctf(ctf, new_min=0, new_max=1, reverse=False):
    """
    Rescale and, optionally, reverse the colors in the color transfer function.

    :param ctf: The color transfer function to rescale.
    :param new_min: The new minimum value.
    :param new_max: The new maximum value.
    :param reverse: If true, reverse the colors.
    :return: The rescaled color transfer function.
    """
    if new_min > new_max:
        r0 = new_max
        r1 = new_min
    else:
        r0 = new_min
        r1 = new_max

    xv = list()
    rgbv = list()
    nv = [0] * 6
    for i in range(0, ctf.GetNumberOfValues()):
        ctf.GetNodeValue(i, nv)
        x = nv[0]
        rgb = nv[1:4]
        xv.append(x)
        rgbv.append(rgb)
    xvr = rescale(xv, r0, r1)

    return generate_new_ctf(ctf, xvr, rgbv, reverse=reverse)


if __name__ == '__main__':
    main()
