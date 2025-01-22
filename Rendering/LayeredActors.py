#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkProperty,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def generate_and_display_cube_and_axes():
    colors = vtkNamedColors()

    # Make the slab and axes actors.
    cube_source = vtkCubeSource()
    cube_source.SetXLength(4.0)
    cube_source.SetYLength(9.0)
    cube_source.SetZLength(1.0)
    cube_source.SetCenter(0.0, 0.0, 0.0)

    cube_mapper = vtkPolyDataMapper()
    cube_mapper.SetInputConnection(cube_source.GetOutputPort())

    back = vtkProperty()
    back.SetColor(colors.GetColor3d('Sienna'))

    cube_actor = vtkActor()
    cube_actor.GetProperty().SetDiffuseColor(colors.GetColor3d('BurlyWood'))
    cube_actor.SetMapper(cube_mapper)
    cube_actor.GetProperty().EdgeVisibilityOn()
    cube_actor.GetProperty().SetLineWidth(2.0)
    cube_actor.GetProperty().SetEdgeColor(colors.GetColor3d('PapayaWhip'))
    cube_actor.SetBackfaceProperty(back)

    transform = vtkTransform()
    transform.Translate(0.0, 0.0, 0.0)

    axes = vtkAxesActor()
    # The axes can be positioned with a user transform.
    axes.SetUserTransform(transform)

    # The renderers, render window and interactor.
    renderers = list()
    ren_win = vtkRenderWindow()
    ren_win.SetSize(800, 800)
    ren_win.SetWindowName('LayeredActors')

    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    # Define the renderers and allocate them to layers.
    for i in range(0, 2):
        renderers.append(vtkRenderer())
        ren_win.AddRenderer(renderers[i])
        renderers[i].SetLayer(i)

    # Layer 0 - background not transparent.
    renderers[0].SetBackground(colors.GetColor3d('DarkSlateGray'))
    renderers[0].AddActor(cube_actor)
    renderers[0].SetLayer(0)
    # Layer 1 - the background is transparent,
    #           so we only see the layer 0 background color
    renderers[1].AddActor(axes)
    renderers[1].SetBackground(colors.GetColor3d('MidnightBlue'))
    renderers[1].SetLayer(1)

    # Set a common camera view for each layer.
    for renderer in renderers:
        camera = renderer.GetActiveCamera()
        camera.Elevation(-30)
        camera.Azimuth(-30)
        renderer.ResetCamera()

    #  We have two layers.
    ren_win.SetNumberOfLayers(len(renderers))

    ren_win.Render()

    iren.AddObserver('KeyPressEvent', select_layer)
    iren.AddObserver('EndInteractionEvent', orient_layer)

    iren.Start()


def select_layer(caller, ev):
    """
    Select the layer to manipulate.
    :param caller:
    :param ev:
    :return:
    """
    iren = caller
    renderers = iren.GetRenderWindow().GetRenderers()
    if renderers.GetNumberOfItems() < 2:
        print('We need at least two renderers, we have only', renderers.GetNumberOfItems())
        return
    renderers.InitTraversal()
    # Top item.
    ren0 = renderers.GetNextItem()
    # Bottom item.
    ren1 = renderers.GetNextItem()

    key = iren.GetKeySym()

    if key in ['0', 'KP_0']:
        print('Selected layer:', key)
        iren.GetRenderWindow().GetInteractor().GetInteractorStyle().SetDefaultRenderer(ren0)
        ren0.InteractiveOn()
        ren1.InteractiveOff()
    if key in ['1', 'KP_1']:
        print('Selected layer:', key)
        iren.GetRenderWindow().GetInteractor().GetInteractorStyle().SetDefaultRenderer(ren1)
        ren0.InteractiveOff()
        ren1.InteractiveOn()


def orient_layer(caller, ev):
    """
    Orient layer 0 based on the camera orientation in layer 1 or vice versa.

    :param caller:
    :param ev:
    :return:
    """

    iren = caller
    renderers = iren.GetRenderWindow().GetRenderers()
    if renderers.GetNumberOfItems() < 2:
        print('We need at least two renderers, we have only', renderers.GetNumberOfItems())
        return
    renderers.InitTraversal()
    # Top item.
    ren0 = renderers.GetNextItem()
    # Bottom item.
    ren1 = renderers.GetNextItem()

    if ren1.GetInteractive():
        orient1 = get_orientation(ren1)
        set_orientation(ren0, orient1)
        ren0.ResetCamera()
    else:
        orient0 = get_orientation(ren0)
        set_orientation(ren1, orient0)
        ren1.ResetCamera()


def get_orientation(ren):
    """
    Get the camera orientation.
    :param ren: The renderer.
    :return: The orientation parameters.
    """
    p = dict()
    camera = ren.GetActiveCamera()
    p['position'] = camera.GetPosition()
    p['focal point'] = camera.GetFocalPoint()
    p['view up'] = camera.GetViewUp()
    p['distance'] = camera.GetDistance()
    p['clipping range'] = camera.GetClippingRange()
    p['orientation'] = camera.GetOrientation()
    return p


def set_orientation(ren, p):
    """
    Set the orientation of the camera.
    :param ren: The renderer.
    :param p: The orientation parameters.
    :return:
    """
    camera = ren.GetActiveCamera()
    camera.SetPosition(p['position'])
    camera.SetFocalPoint(p['focal point'])
    camera.SetViewUp(p['view up'])
    camera.SetDistance(p['distance'])
    camera.SetClippingRange(p['clipping range'])


def main():
    generate_and_display_cube_and_axes()


if __name__ == '__main__':
    main()
