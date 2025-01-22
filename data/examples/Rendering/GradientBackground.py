#!/usr/bin/env python

# Based on:
#  https://gitlab.kitware.com/vtk/vtk/-/blob/master/Rendering/Core/Testing/Cxx/TestGradientBackground.cxx?ref_type=heads
# See:
#  [New in VTK 9.3: Radial Gradient Background](https://www.kitware.com/new-in-vtk-9-3-radial-gradient-background/)

from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingFreeType
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkPolyData,
    vtkPolyLine
)
from vtkmodules.vtkFiltersSources import (
    vtkConeSource,
    vtkSphereSource
)
from vtkmodules.vtkIOGeometry import (
    vtkBYUReader,
    vtkOBJReader,
    vtkSTLReader
)
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from vtkmodules.vtkIOPLY import vtkPLYReader
from vtkmodules.vtkIOXML import vtkXMLPolyDataReader
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkCoordinate,
    vtkPolyDataMapper,
    vtkPolyDataMapper2D,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
    vtkTextMapper,
    vtkTextProperty,
    vtkViewport
)


def get_program_parameters(argv):
    import argparse
    description = 'Demonstrates the background shading options.'
    epilogue = '''
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-f', '--file_name', default=None,
                        help='An optional file name, e.g. star-wars-vader-tie-fighter.obj.')
    args = parser.parse_args()
    return args.file_name


def main(fn):
    if fn:
        fp = Path(fn)
        if not fp.is_file():
            print(f'The path: {fp} does not exist.')
            return
    else:
        fp = None

    pd = read_polydata_(fp)

    ren_win = vtkRenderWindow()
    ren_win.SetWindowName('GradientBackground')

    iren = vtkRenderWindowInteractor()
    renderers = []

    # For each gradient specify the mode.
    modes = [
        vtkViewport.GradientModes.VTK_GRADIENT_VERTICAL,
        vtkViewport.GradientModes.VTK_GRADIENT_HORIZONTAL,
        vtkViewport.GradientModes.VTK_GRADIENT_RADIAL_VIEWPORT_FARTHEST_SIDE,
        vtkViewport.GradientModes.VTK_GRADIENT_RADIAL_VIEWPORT_FARTHEST_CORNER,
    ]

    colors = vtkNamedColors()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(pd)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d('Honeydew'))
    actor.GetProperty().SetSpecular(0.3)
    actor.GetProperty().SetSpecularPower(60.0)

    ren_width = 640
    ren_height = 480

    # The bounds for each view port.
    xmins = [0.0, 0.5, 0.0, 0.5]
    ymins = [0.0, 0.0, 0.5, 0.5]
    xmaxs = [0.5, 1.0, 0.5, 1.0]
    ymaxs = [0.5, 0.5, 1.0, 1.0]

    # Here we select and name the colors.
    # Feel free to change colors.
    bottom_color = colors.GetColor3d('Gold')
    top_color = colors.GetColor3d('OrangeRed')
    left_color = colors.GetColor3d('Gold')
    right_color = colors.GetColor3d('OrangeRed')
    center_color = colors.GetColor3d('Gold')
    side_color = colors.GetColor3d('OrangeRed')
    corner_color = colors.GetColor3d('OrangeRed')

    viewport_title = ["Vertical",
                      "Horizontal",
                      "Radial Farthest Side",
                      "Radial Farthest Corner",
                      ]

    # Create one text property for all.
    text_property = vtkTextProperty()
    text_property.SetJustificationToCentered()
    text_property.SetFontSize(ren_height // 12)
    text_property.SetColor(colors.GetColor3d('MidnightBlue'))

    text_mappers = []
    text_actors = []

    # Define borders for the viewports  = [top, left, bottom, right].
    lb = [False, True, True, False]
    lbr = [False, True, True, True]
    tlb = [True, True, True, False]
    tlbr = [True, True, True, True]
    border_color = 'DarkGreen'
    border_width = 4.0

    for i in range(0, 4):
        text_mappers.append(vtkTextMapper())
        text_mappers[i].SetInput(viewport_title[i])
        text_mappers[i].SetTextProperty(text_property)

        text_actors.append(vtkActor2D())
        text_actors[i].SetMapper(text_mappers[i])
        text_actors[i].SetPosition(ren_width / 2, 8)

        renderers.append(vtkRenderer())
        renderers[i].AddActor(text_actors[i])
        renderers[i].AddActor(actor)
        renderers[i].GradientBackgroundOn()
        renderers[i].SetGradientMode(modes[i])

        renderers[i].SetViewport(xmins[i], ymins[i], xmaxs[i], ymaxs[i])

        if i == 1:
            # Horizontal
            renderers[i].SetBackground(left_color)
            renderers[i].SetBackground2(right_color)
            viewport_border(renderers[i], lbr, border_color, border_width)
        elif i == 2:
            # Radial Farthest Side
            renderers[i].SetBackground(center_color)
            renderers[i].SetBackground2(side_color)
            viewport_border(renderers[i], tlb, border_color, border_width)
        elif i == 3:
            # Radial Farthest Corner
            renderers[i].SetBackground(center_color)
            renderers[i].SetBackground2(corner_color)
            viewport_border(renderers[i], tlbr, border_color, border_width)
        else:
            # Vertical
            renderers[i].SetBackground(bottom_color)
            renderers[i].SetBackground2(top_color)
            viewport_border(renderers[i], lb, border_color, border_width)

        ren_win.AddRenderer(renderers[i])

    ren_win.SetInteractor(iren)
    ren_win.Render()

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    iren.Initialize()
    iren.UpdateSize(ren_width * 2, ren_height * 2)

    iren.Start()


def read_polydata_(path):
    """
    Read from a file containing vtkPolyData.

    If the path is empty a cone is returned.
    If the extension is unknown a sphere is returned.
    
    :param path: The path to the file.
    :return: The vtkPolyData.
    """

    poly_data = vtkPolyData()

    if path is None:
        # Default to a cone if the path is empty.
        source = vtkConeSource()
        source.SetResolution(25)
        source.SetDirection(0, 1, 0)
        source.SetHeight(1)
        source.Update()
        poly_data.DeepCopy(source.GetOutput())
        return poly_data

    valid_suffixes = ['.g', '.obj', '.stl', '.ply', '.vtk', '.vtp']
    ext = path.suffix.lower()
    if path.suffix not in valid_suffixes:
        print('Warning:', path, 'unknown extension, using a sphere instead.')
        source = vtkSphereSource()
        source.SetPhiResolution(50)
        source.SetThetaResolution(50)
        source.Update()
        poly_data.DeepCopy(source.GetOutput())
    else:
        if ext == '.ply':
            reader = vtkPLYReader()
            reader.SetFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())
        elif ext == '.vtp':
            reader = vtkXMLPolyDataReader()
            reader.SetFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())
        elif ext == '.obj':
            reader = vtkOBJReader()
            reader.SetFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())
        elif ext == '.stl':
            reader = vtkSTLReader()
            reader.SetFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())
        elif ext == '.vtk':
            reader = vtkPolyDataReader()
            reader.SetFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())
        elif ext == '.g':
            reader = vtkBYUReader()
            reader.SetGeometryFileName(file_name)
            reader.Update()
            poly_data.DeepCopy(reader.GetOutput())

    return poly_data


def viewport_border(renderer, sides, border_color, border_width):
    """
    Set a border around a viewport.

    :param renderer: The renderer corresponding to the viewport.
    :param sides: An array of boolean corresponding to [top, left, bottom, right]
    :param border_color: The color of the border.
    :param border_width: The width of the border.
    :return:
    """
    colors = vtkNamedColors()

    # Points start at upper right and proceed anti-clockwise.
    points = vtkPoints()
    points.SetNumberOfPoints(4)
    points.InsertPoint(0, 1, 1, 0)
    points.InsertPoint(1, 0, 1, 0)
    points.InsertPoint(2, 0, 0, 0)
    points.InsertPoint(3, 1, 0, 0)

    cells = vtkCellArray()
    cells.Initialize()

    if sides[0]:
        # Top
        top = vtkPolyLine()
        top.GetPointIds().SetNumberOfIds(2)
        top.GetPointIds().SetId(0, 0)
        top.GetPointIds().SetId(1, 1)
        cells.InsertNextCell(top)
    if sides[1]:
        # Left
        left = vtkPolyLine()
        left.GetPointIds().SetNumberOfIds(2)
        left.GetPointIds().SetId(0, 1)
        left.GetPointIds().SetId(1, 2)
        cells.InsertNextCell(left)
    if sides[2]:
        # Bottom
        bottom = vtkPolyLine()
        bottom.GetPointIds().SetNumberOfIds(2)
        bottom.GetPointIds().SetId(0, 2)
        bottom.GetPointIds().SetId(1, 3)
        cells.InsertNextCell(bottom)
    if sides[3]:
        # Right
        right = vtkPolyLine()
        right.GetPointIds().SetNumberOfIds(2)
        right.GetPointIds().SetId(0, 3)
        right.GetPointIds().SetId(1, 0)
        cells.InsertNextCell(right)

    # Now make the polydata and display it.
    poly = vtkPolyData()
    poly.Initialize()
    poly.SetPoints(points)
    poly.SetLines(cells)

    # Use normalized viewport coordinates since
    # they are independent of window size.
    coordinate = vtkCoordinate()
    coordinate.SetCoordinateSystemToNormalizedViewport()

    mapper = vtkPolyDataMapper2D()
    mapper.SetInputData(poly)
    mapper.SetTransformCoordinate(coordinate)

    actor = vtkActor2D()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d(border_color))

    # Line width should be at least 2 to be visible at extremes.
    actor.GetProperty().SetLineWidth(border_width)

    renderer.AddViewProp(actor)


if __name__ == '__main__':
    import sys

    file_name = get_program_parameters(sys.argv)
    main(file_name)
