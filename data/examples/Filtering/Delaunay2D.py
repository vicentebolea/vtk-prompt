#!/usr/bin/python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import vtkDelaunay2D
from vtkmodules.vtkFiltersGeneral import vtkVertexGlyphFilter
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def main():
    colors = vtkNamedColors()

    # Create a set of heights on a grid.
    # This is often called a "terrain map".
    points = vtkPoints()

    grid_size = 10
    for x in range(grid_size):
        for y in range(grid_size):
            points.InsertNextPoint(x, y, int((x + y) / (y + 1)))

    # Add the grid points to a polydata object.
    polydata = vtkPolyData()
    polydata.SetPoints(points)

    delaunay = vtkDelaunay2D()
    delaunay.SetInputData(polydata)

    # Visualize
    mesh_mapper = vtkPolyDataMapper()
    mesh_mapper.SetInputConnection(delaunay.GetOutputPort())

    mesh_actor = vtkActor()
    mesh_actor.SetMapper(mesh_mapper)
    mesh_actor.GetProperty().SetColor(colors.GetColor3d('LightGoldenrodYellow'))
    mesh_actor.GetProperty().EdgeVisibilityOn()
    mesh_actor.GetProperty().SetEdgeColor(colors.GetColor3d('CornflowerBlue'))
    mesh_actor.GetProperty().SetLineWidth(3)
    mesh_actor.GetProperty().RenderLinesAsTubesOn()

    glyph_filter = vtkVertexGlyphFilter()
    glyph_filter.SetInputData(polydata)

    point_mapper = vtkPolyDataMapper()
    point_mapper.SetInputConnection(glyph_filter.GetOutputPort())

    point_actor = vtkActor()
    point_actor.SetMapper(point_mapper)
    point_actor.GetProperty().SetColor(colors.GetColor3d('DeepPink'))
    point_actor.GetProperty().SetPointSize(10)
    point_actor.GetProperty().RenderPointsAsSpheresOn()

    renderer = vtkRenderer()
    renderer.SetBackground(colors.GetColor3d('PowderBlue'))
    render_window = vtkRenderWindow()
    render_window.SetSize(600, 600)
    render_window.SetWindowName('Delaunay2D')
    render_window.AddRenderer(renderer)
    render_window_interactor = vtkRenderWindowInteractor()
    render_window_interactor.SetRenderWindow(render_window)

    renderer.AddActor(mesh_actor)
    renderer.AddActor(point_actor)

    render_window_interactor.Initialize()
    render_window.Render()
    render_window_interactor.Start()


if __name__ == '__main__':
    main()
