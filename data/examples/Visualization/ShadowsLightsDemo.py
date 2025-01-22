#!/usr/bin/env python3

"""
The scene consists of:
1) four actors: a rectangle, a box, a cone and a sphere.
   The box, the cone and the sphere are above the rectangle.
2) Two spotlights, one in the direction of the box, another one in the
   direction of the sphere.
   Both lights are above the box, the cone and  the sphere.
"""

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
from vtkmodules.vtkFiltersSources import (
    vtkConeSource,
    vtkCubeSource,
    vtkPlaneSource,
    vtkSphereSource
)
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkLight,
    vtkLightActor,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor
)
from vtkmodules.vtkRenderingOpenGL2 import (
    vtkCameraPass,
    vtkOpaquePass,
    vtkOpenGLRenderer,
    vtkRenderPassCollection,
    vtkSequencePass,
    vtkShadowMapPass
)


def main():
    iren = vtkRenderWindowInteractor()

    renwin = vtkRenderWindow()
    renwin.SetSize(400, 400)
    renwin.SetMultiSamples(0)

    renwin.SetAlphaBitPlanes(1)
    iren.SetRenderWindow(renwin)

    renderer = vtkOpenGLRenderer()
    renwin.AddRenderer(renderer)
    renwin.SetSize(640, 480)

    seq = vtkSequencePass()

    passes = vtkRenderPassCollection()

    shadows = vtkShadowMapPass()
    passes.AddItem(shadows.GetShadowMapBakerPass())
    passes.AddItem(shadows)

    opaque = vtkOpaquePass()
    passes.AddItem(opaque)

    seq.SetPasses(passes)

    camera_p = vtkCameraPass()
    camera_p.SetDelegatePass(seq)

    # Tell the renderer to use our render pass pipeline.
    renderer.SetPass(camera_p)

    colors = vtkNamedColors()
    box_color = colors.GetColor3d('Tomato')
    rectangle_color = colors.GetColor3d('Beige')
    cone_color = colors.GetColor3d('Peacock')
    sphere_color = colors.GetColor3d('Banana')

    rectangle_source = vtkPlaneSource()
    rectangle_source.SetOrigin(-5.0, 0.0, 5.0)
    rectangle_source.SetPoint1(5.0, 0.0, 5.0)
    rectangle_source.SetPoint2(-5.0, 0.0, -5.0)
    rectangle_source.SetResolution(100, 100)

    rectangle_mapper = vtkPolyDataMapper()
    rectangle_mapper.SetInputConnection(rectangle_source.GetOutputPort())

    rectangle_mapper.SetScalarVisibility(0)

    rectangle_actor = vtkActor()
    rectangle_actor.SetMapper(rectangle_mapper)
    rectangle_actor.VisibilityOn()
    rectangle_actor.GetProperty().SetColor(rectangle_color)

    box_source = vtkCubeSource()
    box_source.SetXLength(2.0)

    box_normals = vtkPolyDataNormals()
    box_normals.SetInputConnection(box_source.GetOutputPort())
    box_normals.ComputePointNormalsOff()
    box_normals.ComputeCellNormalsOn()
    box_normals.Update()
    box_normals.GetOutput().GetPointData().SetNormals(None)

    box_mapper = vtkPolyDataMapper()
    box_mapper.SetInputConnection(box_normals.GetOutputPort())
    box_mapper.ScalarVisibilityOff()

    box_actor = vtkActor()
    box_actor.SetMapper(box_mapper)
    box_actor.VisibilityOn()
    box_actor.SetPosition(-2.0, 2.0, 0.0)
    box_actor.GetProperty().SetColor(box_color)

    cone_source = vtkConeSource()
    cone_source.SetResolution(24)
    cone_source.SetDirection(1.0, 1.0, 1.0)

    cone_mapper = vtkPolyDataMapper()
    cone_mapper.SetInputConnection(cone_source.GetOutputPort())
    cone_mapper.SetScalarVisibility(0)

    cone_actor = vtkActor()
    cone_actor.SetMapper(cone_mapper)
    cone_actor.VisibilityOn()
    cone_actor.SetPosition(0.0, 1.0, 1.0)
    cone_actor.GetProperty().SetColor(cone_color)

    sphere_source = vtkSphereSource()
    sphere_source.SetThetaResolution(32)
    sphere_source.SetPhiResolution(32)

    sphere_mapper = vtkPolyDataMapper()
    sphere_mapper.SetInputConnection(sphere_source.GetOutputPort())
    sphere_mapper.ScalarVisibilityOff()

    sphere_actor = vtkActor()
    sphere_actor.SetMapper(sphere_mapper)

    sphere_actor.VisibilityOn()
    sphere_actor.SetPosition(2.0, 2.0, -1.0)
    sphere_actor.GetProperty().SetColor(sphere_color)

    renderer.AddViewProp(rectangle_actor)
    renderer.AddViewProp(box_actor)
    renderer.AddViewProp(cone_actor)
    renderer.AddViewProp(sphere_actor)

    # Spotlights.

    # Lighting the box.
    l1 = vtkLight()
    l1.SetPosition(-4.0, 4.0, -1.0)
    l1.SetFocalPoint(box_actor.GetPosition())
    l1.SetColor(colors.GetColor3d('White'))
    l1.PositionalOn()
    renderer.AddLight(l1)
    l1.SwitchOn()

    # Lighting the sphere.
    l2 = vtkLight()
    l2.SetPosition(4.0, 5.0, 1.0)
    l2.SetFocalPoint(sphere_actor.GetPosition())
    l2.SetColor(colors.GetColor3d('Magenta'))
    l2.PositionalOn()
    renderer.AddLight(l2)
    l2.SwitchOn()

    # For each spotlight, add a light frustum wireframe representation and a cone
    # wireframe representation, colored with the light color.
    angle = l1.GetConeAngle()
    if l1.LightTypeIsSceneLight() and l1.GetPositional() and angle < 180.0:  # spotlight
        la = vtkLightActor()
        la.SetLight(l1)
        renderer.AddViewProp(la)
    angle = l2.GetConeAngle()
    if l2.LightTypeIsSceneLight() and l2.GetPositional() and angle < 180.0:  # spotlight
        la = vtkLightActor()
        la.SetLight(l2)
        renderer.AddViewProp(la)

    renderer.SetBackground2(colors.GetColor3d('Black'))
    renderer.SetBackground(colors.GetColor3d('Silver'))
    renderer.SetGradientBackground(True)

    renwin.Render()
    renwin.SetWindowName('ShadowsLightsDemo')

    renderer.ResetCamera()

    camera = renderer.GetActiveCamera()
    camera.Azimuth(40.0)
    camera.Elevation(10.0)

    renwin.Render()

    iren.Start()


if __name__ == '__main__':
    main()
