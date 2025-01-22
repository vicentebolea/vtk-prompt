#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkConeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDiscretizableColorTransferFunction,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def main():
    colors = vtkNamedColors()
    colors.SetColor('ParaViewBkg', 82, 87, 110, 255)

    ren = vtkRenderer()
    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))
    ren_win = vtkRenderWindow()
    ren_win.SetSize(640, 480)
    ren_win.SetWindowName('ColorMapToLUT')
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    sphere = vtkSphereSource()
    sphere.SetThetaResolution(64)
    sphere.SetPhiResolution(32)

    cone = vtkConeSource()
    cone.SetResolution(6)
    cone.SetDirection(0, 1, 0)
    cone.SetHeight(1)
    cone.Update()
    bounds = cone.GetOutput().GetBounds()

    elevation_filter = vtkElevationFilter()
    elevation_filter.SetLowPoint(0, bounds[2], 0)
    elevation_filter.SetHighPoint(0, bounds[3], 0)
    elevation_filter.SetInputConnection(cone.GetOutputPort())
    # elevation_filter.SetInputConnection(sphere.GetOutputPort())

    ctf = get_ctf()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(elevation_filter.GetOutputPort())
    mapper.SetLookupTable(ctf)
    mapper.SetColorModeToMapScalars()
    mapper.InterpolateScalarsBeforeMappingOn()

    actor = vtkActor()
    actor.SetMapper(mapper)

    ren.AddActor(actor)

    ren_win.Render()
    iren.Start()


def get_ctf():
    # name: Fast, creator: Francesca Samsel and Alan W. Scott
    # interpolationspace: RGB, space: rgb
    # file name: Fast.json

    ctf = vtkDiscretizableColorTransferFunction()

    ctf.SetColorSpaceToRGB()
    ctf.SetScaleToLinear()

    ctf.SetNanColor(0.0, 0.0, 0.0)

    ctf.AddRGBPoint(0, 0.05639999999999999, 0.05639999999999999, 0.47)
    ctf.AddRGBPoint(0.17159223942480895, 0.24300000000000013, 0.4603500000000004, 0.81)
    ctf.AddRGBPoint(0.2984914818394138, 0.3568143826543521, 0.7450246485363142, 0.954367702893722)
    ctf.AddRGBPoint(0.4321287371255907, 0.6882, 0.93, 0.9179099999999999)
    ctf.AddRGBPoint(0.5, 0.8994959551205902, 0.944646394975174, 0.7686567142818399)
    ctf.AddRGBPoint(0.5882260353170073, 0.957107977357604, 0.8338185108985666, 0.5089156299842102)
    ctf.AddRGBPoint(0.7061412605695164, 0.9275207599610714, 0.6214389091739178, 0.31535705838676426)
    ctf.AddRGBPoint(0.8476395308725272, 0.8, 0.3520000000000001, 0.15999999999999998)
    ctf.AddRGBPoint(1, 0.59, 0.07670000000000013, 0.11947499999999994)

    ctf.SetNumberOfValues(9)
    ctf.DiscretizeOff()

    return ctf


if __name__ == '__main__':
    main()
