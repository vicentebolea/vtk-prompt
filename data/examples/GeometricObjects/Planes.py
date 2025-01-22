#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingFreeType
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import (
    vtkPlanes,
    vtkPolyData
)
from vtkmodules.vtkFiltersCore import vtkHull
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkCamera,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
    vtkTextMapper,
    vtkTextProperty
)


def main():
    colors = vtkNamedColors()

    planes = list()
    titles = list()

    # Using frustum planes.
    titles.append('Using frustum planes')
    camera = vtkCamera()
    planes_array = [0] * 24
    camera.GetFrustumPlanes(1, planes_array)
    planes.append(vtkPlanes())
    planes[0].SetFrustumPlanes(planes_array)

    # Using bounds.
    titles.append('Using bounds')
    sphere_source = vtkSphereSource()
    sphere_source.Update()
    bounds = [0] * 6
    sphere_source.GetOutput().GetBounds(bounds)
    planes.append(vtkPlanes())
    planes[1].SetBounds(bounds)

    # At this point we have the planes created by both of the methods above.
    # You can do whatever you want with them.

    # For visualisation we will produce an n-sided convex hull
    # and visualise it.

    # Create a common text property.
    text_property = vtkTextProperty()
    text_property.SetFontSize(16)
    text_property.SetJustificationToCentered()

    ren_win = vtkRenderWindow()
    ren_win.SetSize(600, 600)
    ren_win.SetWindowName('Planes')

    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    hulls = list()
    pds = list()
    mappers = list()
    actors = list()
    renderers = list()
    text_mappers = list()
    text_actors = list()
    for i in range(0, len(planes)):
        hulls.append(vtkHull())
        hulls[i].SetPlanes(planes[i])

        pds.append(vtkPolyData())

        # To generate the convex hull we supply a vtkPolyData object and a bounding box.
        # We define the bounding box to be where we expect the resulting polyhedron to lie.
        # Make it a generous fit as it is only used to create the initial
        # polygons that are eventually clipped.
        hulls[i].GenerateHull(pds[i], -200, 200, -200, 200, -200, 200)

        mappers.append(vtkPolyDataMapper())
        mappers[i].SetInputData(pds[i])

        actors.append(vtkActor())
        actors[i].SetMapper(mappers[i])
        actors[i].GetProperty().SetColor(colors.GetColor3d('Moccasin'))
        actors[i].GetProperty().SetSpecular(0.8)
        actors[i].GetProperty().SetSpecularPower(30)

        renderers.append(vtkRenderer())
        renderers[i].AddActor(actors[i])

        text_mappers.append(vtkTextMapper())
        text_mappers[i].SetInput(titles[i])
        text_mappers[i].SetTextProperty(text_property)

        text_actors.append(vtkActor2D())
        text_actors[i].SetMapper(text_mappers[i])
        text_actors[i].SetPosition(100, 10)
        renderers[i].AddViewProp(text_actors[i])

        ren_win.AddRenderer(renderers[i])

    # Setup the viewports
    x_grid_dimensions = 2
    y_grid_dimensions = 1
    renderer_size = 300
    ren_win.SetSize(renderer_size * x_grid_dimensions, renderer_size * y_grid_dimensions)
    for row in range(0, y_grid_dimensions):
        for col in range(0, x_grid_dimensions):
            index = row * x_grid_dimensions + col

            # (xmin, ymin, xmax, ymax)
            viewport = [float(col) / x_grid_dimensions,
                        float(y_grid_dimensions - (row + 1)) / y_grid_dimensions,
                        float(col + 1) / x_grid_dimensions,
                        float(y_grid_dimensions - row) / y_grid_dimensions]

            if index > (len(actors) - 1):
                # Add a renderer even if there is no actor.
                # This makes the render window background all the same color.
                ren = vtkRenderer()
                ren.SetBackground(colors.GetColor3d('DarkSlateGray'))
                ren.SetViewport(viewport)
                ren_win.AddRenderer(ren)
                continue

            renderers[index].SetViewport(viewport)
            renderers[index].SetBackground(colors.GetColor3d('DarkSlateGray'))
            renderers[index].ResetCamera()
            renderers[index].GetActiveCamera().Azimuth(30)
            renderers[index].GetActiveCamera().Elevation(-30)
            renderers[index].ResetCameraClippingRange()

    iren.Initialize()
    ren_win.Render()
    iren.Start()


if __name__ == '__main__':
    main()
