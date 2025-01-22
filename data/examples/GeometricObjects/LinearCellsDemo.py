# !/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import (
    vtkPoints,
    VTK_VERSION_NUMBER,
    vtkVersion
)
from vtkmodules.vtkCommonDataModel import (
    VTK_TETRA,
    vtkCellArray,
    vtkHexagonalPrism,
    vtkHexahedron,
    vtkLine,
    vtkPentagonalPrism,
    vtkPixel,
    vtkPolyLine,
    vtkPolyVertex,
    vtkPolygon,
    vtkPyramid,
    vtkQuad,
    vtkTetra,
    vtkTriangle,
    vtkTriangleStrip,
    vtkUnstructuredGrid,
    vtkVertex,
    vtkVoxel,
    vtkWedge
)
from vtkmodules.vtkFiltersSources import (
    vtkCubeSource,
    vtkSphereSource
)
from vtkmodules.vtkInteractionWidgets import (
    vtkCameraOrientationWidget,
    vtkOrientationMarkerWidget
)
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkDataSetMapper,
    vtkGlyph3DMapper,
    vtkLightKit,
    vtkPolyDataMapper,
    vtkProperty,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
    vtkTextMapper,
    vtkTextProperty
)
from vtkmodules.vtkRenderingLabel import vtkLabeledDataMapper


def get_program_parameters():
    import argparse
    description = 'Demonstrate the linear cell types found in VTK.'
    epilogue = '''
         The numbers define the ordering of the points making the cell.
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-w', '--wireframe', action='store_true',
                        help='Render a wireframe.')
    group1.add_argument('-b', '--backface', action='store_true',
                        help='Display the back face in a different colour.')

    parser.add_argument('-o', '--object_number', type=int, default=None,
                        help='The number corresponding to the object.')
    parser.add_argument('-n', '--no_plinth', action='store_true',
                        help='Remove the plinth.')
    args = parser.parse_args()
    return args.wireframe, args.backface, args.object_number, args.no_plinth


def main():
    wireframe_on, backface_on, object_num, plinth_off = get_program_parameters()

    objects = specify_objects()
    # The order here should match the order in specify_objects().
    object_order = list(objects.keys())

    # Check for a single object.
    single_object = None
    if object_num:
        if object_num in object_order:
            single_object = True
        else:
            print('Object not found.\nPlease enter the number corresponding to the object.')
            print('Available objects are:')
            for obj in object_order:
                print(f'{objects[obj]} (={str(obj)})')
            return

    colors = vtkNamedColors()

    # Create one sphere for all.
    sphere = vtkSphereSource()
    sphere.SetPhiResolution(21)
    sphere.SetThetaResolution(21)
    sphere.SetRadius(0.04)

    cells = get_unstructured_grids()
    # The text to be displayed in the viewport.
    names = list()
    # The keys of the objects selected for display.
    keys = list()
    if single_object:
        names.append(f'{objects[object_num]} (={str(object_num)})')
        keys.append(object_num)
    else:
        for obj in object_order:
            names.append(f'{objects[obj]} (={str(obj)})')
            keys.append(obj)

    add_plinth = (10, 11, 12, 13, 14, 15, 16,)
    lines = (3, 4)

    # Set up the viewports.
    grid_column_dimensions = 4
    grid_row_dimensions = 4
    renderer_size = 300
    if single_object:
        grid_column_dimensions = 1
        grid_row_dimensions = 1
        renderer_size = 1200
    window_size = (grid_column_dimensions * renderer_size, grid_row_dimensions * renderer_size)

    viewports = dict()
    blank = len(cells)
    blank_viewports = list()

    for row in range(0, grid_row_dimensions):
        if row == grid_row_dimensions - 1:
            last_row = True
        for col in range(0, grid_column_dimensions):
            if col == grid_column_dimensions - 1:
                last_col = True
            index = row * grid_column_dimensions + col
            # Set the renderer's viewport dimensions (xmin, ymin, xmax, ymax) within the render window.
            # Note that for the Y values, we need to subtract the row index from grid_rows
            #  because the viewport Y axis points upwards, and we want to draw the grid from top to down.
            viewport = (float(col) / grid_column_dimensions,
                        float(grid_row_dimensions - (row + 1)) / grid_row_dimensions,
                        float(col + 1) / grid_column_dimensions,
                        float(grid_row_dimensions - row) / grid_row_dimensions)

            if index < blank:
                viewports[keys[index]] = viewport
            else:
                s = f'vp_{col:d}_{row:d}'
                viewports[s] = viewport
                blank_viewports.append(s)

    ren_win = vtkRenderWindow()
    ren_win.SetSize(window_size)
    ren_win.SetWindowName('LinearCellsDemo')

    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)
    # Since we always import vtkmodules.vtkInteractionStyle we can do this
    # because vtkInteractorStyleSwitch is automatically imported:
    iren.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    renderers = dict()

    # Create and link the mappers, actors and renderers together.
    single_object_key = None
    for idx, key in enumerate(keys):
        print('Creating:', names[idx])

        if single_object:
            single_object_key = key

        text_property = get_text_property()
        if single_object:
            text_property.SetFontSize(renderer_size // 28)
        else:
            text_property.SetFontSize(renderer_size // 24)

        text_mapper = vtkTextMapper()
        text_mapper.SetTextProperty(text_property)
        text_mapper.SetInput(names[idx])
        text_actor = vtkActor2D()
        text_actor.SetMapper(text_mapper)
        text_actor.SetPosition(renderer_size / 2.0, 8)

        mapper = vtkDataSetMapper()
        mapper.SetInputData(cells[key][0])
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.SetProperty(get_actor_property())

        if wireframe_on or key in lines:
            actor.GetProperty().SetRepresentationToWireframe()
            actor.GetProperty().SetLineWidth(2)
            actor.GetProperty().SetOpacity(1)
            actor.GetProperty().SetColor(colors.GetColor3d('Black'))
        else:
            if backface_on:
                actor.SetBackfaceProperty(get_back_face_property())

        # Label the points.
        label_property = get_label_property()
        if single_object:
            label_property.SetFontSize(renderer_size // 36)
        else:
            label_property.SetFontSize(renderer_size // 16)

        label_mapper = vtkLabeledDataMapper()
        label_mapper.SetInputData(cells[key][0])
        label_mapper.SetLabelTextProperty(label_property)

        label_actor = vtkActor2D()
        label_actor.SetMapper(label_mapper)

        # Glyph the points.
        point_mapper = vtkGlyph3DMapper()
        point_mapper.SetInputData(cells[key][0])
        point_mapper.SetSourceConnection(sphere.GetOutputPort())
        point_mapper.ScalingOn()
        point_mapper.ScalarVisibilityOff()

        point_actor = vtkActor()
        point_actor.SetMapper(point_mapper)
        point_actor.SetProperty(get_point_actor_property())

        renderer = vtkRenderer()
        renderer.SetBackground(colors.GetColor3d('LightSteelBlue'))
        renderer.SetViewport(viewports[key])

        light_kit = vtkLightKit()
        light_kit.AddLightsToRenderer(renderer)

        renderer.AddActor(text_actor)
        renderer.AddActor(actor)
        renderer.AddActor(label_actor)
        renderer.AddActor(point_actor)
        if not plinth_off:
            # Add a plinth.
            if key in add_plinth:
                tile_actor = make_tile(cells[key][0].GetBounds(),
                                       expansion_factor=0.5, thickness_ratio=0.01, shift_y=-0.05)
                tile_actor.SetProperty(get_tile_property())
                renderer.AddActor(tile_actor)

        renderer.ResetCamera()
        renderer.GetActiveCamera().Azimuth(cells[key][1])
        renderer.GetActiveCamera().Elevation(cells[key][2])
        renderer.GetActiveCamera().Dolly(cells[key][3])
        renderer.ResetCameraClippingRange()

        renderers[key] = renderer
        ren_win.AddRenderer(renderers[key])

    for name in blank_viewports:
        viewport = viewports[name]
        renderer = vtkRenderer()
        renderer.SetBackground = colors.GetColor3d('LightSteelBlue')
        renderer.SetViewport(viewport)

        renderers[name] = renderer
        ren_win.AddRenderer(renderers[name])

    if single_object:
        if vtk_version_ok(9, 0, 20210718):
            try:
                cam_orient_manipulator = vtkCameraOrientationWidget()
                cam_orient_manipulator.SetParentRenderer(renderers[single_object_key])
                cam_orient_manipulator.SetInteractor(iren)
                # Enable the widget.
                cam_orient_manipulator.On()
            except AttributeError:
                pass
        else:
            axes = vtkAxesActor()
            widget = vtkOrientationMarkerWidget()
            rgba = [0.0, 0.0, 0.0, 0.0]
            colors.GetColor("Carrot", rgba)
            widget.SetOutlineColor(rgba[0], rgba[1], rgba[2])
            widget.SetOrientationMarker(axes)
            widget.SetInteractor(iren)
            widget.SetViewport(0.0, 0.0, 0.2, 0.2)
            widget.EnabledOn()
            widget.InteractiveOn()

    ren_win.Render()
    iren.Initialize()
    iren.Start()


def specify_objects():
    """
    Link the unstructured grid number to the unstructured grid name.

    :return: A dictionary: {index number: unstructured grid name}.
    """
    return {
        1: 'VTK_VERTEX',
        2: 'VTK_POLY_VERTEX',
        3: 'VTK_LINE',
        4: 'VTK_POLY_LINE',
        5: 'VTK_TRIANGLE',
        6: 'VTK_TRIANGLE_STRIP',
        7: 'VTK_POLYGON',
        8: 'VTK_PIXEL',
        9: 'VTK_QUAD',
        10: 'VTK_TETRA',
        11: 'VTK_VOXEL',
        12: 'VTK_HEXAHEDRON',
        13: 'VTK_WEDGE',
        14: 'VTK_PYRAMID',
        15: 'VTK_PENTAGONAL_PRISM',
        16: 'VTK_HEXAGONAL_PRISM',
    }


def get_unstructured_grids():
    """
    Get the unstructured grid names, the unstructured grid and initial orientations.

    :return: A dictionary: {index number: (unstructured grid, azimuth, elevation and dolly)}.
    """
    return {
        1: (make_vertex(), 30, -30, 0.1),
        2: (make_poly_vertex(), 30, -30, 0.8),
        3: (make_line(), 30, -30, 0.4),
        4: (make_polyline(), 30, -30, 1.0),
        5: (make_triangle(), 30, -30, 0.7),
        6: (make_triangle_strip(), 30, -30, 1.1),
        7: (make_polygon(), 0, -45, 1.0),
        8: (make_pixel(), 0, -45, 1.0),
        9: (make_quad(), 0, -45, 1.0),
        10: (make_tetra(), 20, 20, 1.0),
        11: (make_voxel(), -22.5, 15, 0.95),
        12: (make_hexahedron(), -22.5, 15, 0.95),
        13: (make_wedge(), -30, 15, 1.0),
        14: (make_pyramid(), -60, 15, 1.0),
        15: (make_pentagonal_prism(), -60, 10, 1.0),
        16: (make_hexagonal_prism(), -60, 15, 1.0)
    }


# These functions return an vtkUnstructured grid corresponding to the object.

def make_vertex():
    # A vertex is a cell that represents a 3D point.
    number_of_vertices = 1

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)

    vertex = vtkVertex()
    for i in range(0, number_of_vertices):
        vertex.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(vertex.GetCellType(), vertex.GetPointIds())

    return ug


def make_poly_vertex():
    # A polyvertex is a cell that represents a set of 0D vertices.
    number_of_vertices = 6

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, 0, 0)
    points.InsertNextPoint(0, 1, 0)
    points.InsertNextPoint(0, 0, 1)
    points.InsertNextPoint(1, 0, 0.4)
    points.InsertNextPoint(0, 1, 0.6)

    poly_vertex = vtkPolyVertex()
    poly_vertex.GetPointIds().SetNumberOfIds(number_of_vertices)

    for i in range(0, number_of_vertices):
        poly_vertex.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(poly_vertex.GetCellType(), poly_vertex.GetPointIds())

    return ug


def make_line():
    # A line is a cell that represents a 1D point.
    number_of_vertices = 2

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(0.5, 0.5, 0)

    line = vtkLine()
    for i in range(0, number_of_vertices):
        line.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(line.GetCellType(), line.GetPointIds())

    return ug


def make_polyline():
    # A polyline is a cell that represents a set of 1D lines.
    number_of_vertices = 5

    points = vtkPoints()
    points.InsertNextPoint(0, 0.5, 0)
    points.InsertNextPoint(0.5, 0, 0)
    points.InsertNextPoint(1, 0.3, 0)
    points.InsertNextPoint(1.5, 0.4, 0)
    points.InsertNextPoint(2.0, 0.4, 0)

    polyline = vtkPolyLine()
    polyline.GetPointIds().SetNumberOfIds(number_of_vertices)

    for i in range(0, number_of_vertices):
        polyline.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(polyline.GetCellType(), polyline.GetPointIds())

    return ug


def make_triangle():
    # A triangle is a cell that represents a triangle.
    number_of_vertices = 3

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(0.5, 0.5, 0)
    points.InsertNextPoint(.2, 1, 0)

    triangle = vtkTriangle()
    for i in range(0, number_of_vertices):
        triangle.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(triangle.GetCellType(), triangle.GetPointIds())

    return ug


def make_triangle_strip():
    # A triangle strip is a cell that represents a triangle strip.
    number_of_vertices = 10

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, -.1, 0)
    points.InsertNextPoint(0.5, 1, 0)
    points.InsertNextPoint(2.0, -0.1, 0)
    points.InsertNextPoint(1.5, 0.8, 0)
    points.InsertNextPoint(3.0, 0, 0)
    points.InsertNextPoint(2.5, 0.9, 0)
    points.InsertNextPoint(4.0, -0.2, 0)
    points.InsertNextPoint(3.5, 0.8, 0)
    points.InsertNextPoint(4.5, 1.1, 0)

    triangle_strip = vtkTriangleStrip()
    triangle_strip.GetPointIds().SetNumberOfIds(number_of_vertices)
    for i in range(0, number_of_vertices):
        triangle_strip.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(triangle_strip.GetCellType(), triangle_strip.GetPointIds())

    return ug


def make_polygon():
    # A polygon is a cell that represents a polygon.
    number_of_vertices = 6

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, -0.1, 0)
    points.InsertNextPoint(0.8, 0.5, 0)
    points.InsertNextPoint(1, 1, 0)
    points.InsertNextPoint(0.6, 1.2, 0)
    points.InsertNextPoint(0, 0.8, 0)

    polygon = vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(number_of_vertices)
    for i in range(0, number_of_vertices):
        polygon.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(polygon.GetCellType(), polygon.GetPointIds())

    return ug


def make_pixel():
    # A pixel is a cell that represents a pixel
    number_of_vertices = 4

    pixel = vtkPixel()
    pixel.GetPoints().SetPoint(0, 0, 0, 0)
    pixel.GetPoints().SetPoint(1, 1, 0, 0)
    pixel.GetPoints().SetPoint(2, 0, 1, 0)
    pixel.GetPoints().SetPoint(3, 1, 1, 0)

    for i in range(0, number_of_vertices):
        pixel.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(pixel.GetPoints())
    ug.InsertNextCell(pixel.GetCellType(), pixel.GetPointIds())

    return ug


def make_quad():
    # A quad is a cell that represents a quad
    number_of_vertices = 4

    quad = vtkQuad()
    quad.GetPoints().SetPoint(0, 0, 0, 0)
    quad.GetPoints().SetPoint(1, 1, 0, 0)
    quad.GetPoints().SetPoint(2, 1, 1, 0)
    quad.GetPoints().SetPoint(3, 0, 1, 0)

    for i in range(0, number_of_vertices):
        quad.point_ids.SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(quad.GetPoints())
    ug.InsertNextCell(quad.GetCellType(), quad.GetPointIds())

    return ug


def make_tetra():
    # Make a tetrahedron.
    number_of_vertices = 4

    points = vtkPoints()
    # points.InsertNextPoint(0, 0, 0)
    # points.InsertNextPoint(1, 0, 0)
    # points.InsertNextPoint(1, 1, 0)
    # points.InsertNextPoint(0, 1, 1)

    # Rotate the above points -90° about the X-axis.
    points.InsertNextPoint((0.0, 0.0, 0.0))
    points.InsertNextPoint((1.0, 0.0, 0.0))
    points.InsertNextPoint((1.0, 0.0, -1.0))
    points.InsertNextPoint((0.0, 1.0, -1.0))

    tetra = vtkTetra()
    for i in range(0, number_of_vertices):
        tetra.GetPointIds().SetId(i, i)

    cell_array = vtkCellArray()
    cell_array.InsertNextCell(tetra)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.SetCells(VTK_TETRA, cell_array)

    return ug


def make_voxel():
    # A voxel is a representation of a regular grid in 3-D space.
    number_of_vertices = 8

    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, 0, 0)
    points.InsertNextPoint(0, 1, 0)
    points.InsertNextPoint(1, 1, 0)
    points.InsertNextPoint(0, 0, 1)
    points.InsertNextPoint(1, 0, 1)
    points.InsertNextPoint(0, 1, 1)
    points.InsertNextPoint(1, 1, 1)

    voxel = vtkVoxel()
    for i in range(0, number_of_vertices):
        voxel.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(voxel.GetCellType(), voxel.GetPointIds())

    return ug


def make_hexahedron():
    """
    A regular hexagon (cube) with all faces square and three squares
     around each vertex is created below.

    Set up the coordinates of eight points, (the two faces must be
     in counter-clockwise order as viewed from the outside).

    :return:
    """

    number_of_vertices = 8

    # Create the points.
    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, 0, 0)
    points.InsertNextPoint(1, 1, 0)
    points.InsertNextPoint(0, 1, 0)
    points.InsertNextPoint(0, 0, 1)
    points.InsertNextPoint(1, 0, 1)
    points.InsertNextPoint(1, 1, 1)
    points.InsertNextPoint(0, 1, 1)

    # Create a hexahedron from the points.
    hexahedron = vtkHexahedron()
    for i in range(0, number_of_vertices):
        hexahedron.GetPointIds().SetId(i, i)

    # Add the points and hexahedron to an unstructured grid
    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(hexahedron.GetCellType(), hexahedron.GetPointIds())

    return ug


def make_wedge():
    # A wedge consists of two triangular ends and three rectangular faces.

    number_of_vertices = 6

    points = vtkPoints()

    # points.InsertNextPoint(0, 1, 0)
    # points.InsertNextPoint(0, 0, 0)
    # points.InsertNextPoint(0, 0.5, 0.5)
    # points.InsertNextPoint(1, 1, 0)
    # points.InsertNextPoint(1, 0.0, 0.0)
    # points.InsertNextPoint(1, 0.5, 0.5)

    # Rotate the above points -90° about the X-axis
    #  and translate -1 along the Y-axis.
    points.InsertNextPoint(0.0, 0.0, 0.0)
    points.InsertNextPoint(0.0, 0, 1.0)
    points.InsertNextPoint(0.0, 0.5, 0.5)
    points.InsertNextPoint(1.0, 0.0, 0.0)
    points.InsertNextPoint(1.0, 0, 1.0)
    points.InsertNextPoint(1.0, 0.5, 0.5)

    wedge = vtkWedge()
    for i in range(0, number_of_vertices):
        wedge.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(wedge.GetCellType(), wedge.GetPointIds())

    return ug


def make_pyramid():
    # Make a regular square pyramid.
    number_of_vertices = 5

    points = vtkPoints()

    # p0 = [1.0, 1.0, 0.0]
    # p1 = [-1.0, 1.0, 0.0]
    # p2 = [-1.0, -1.0, 0.0]
    # p3 = [1.0, -1.0, 0.0]
    # p4 = [0.0, 0.0, 1.0]

    # Rotate the above points -90° about the X-axis.
    p0 = (1.0, 0, -1.0)
    p1 = (-1.0, 0, -1.0)
    p2 = (-1.0, 0, 1.0)
    p3 = (1.0, 0, 1.0)
    p4 = (0.0, 2.0, 0)

    points.InsertNextPoint(p0)
    points.InsertNextPoint(p1)
    points.InsertNextPoint(p2)
    points.InsertNextPoint(p3)
    points.InsertNextPoint(p4)

    pyramid = vtkPyramid()
    for i in range(0, number_of_vertices):
        pyramid.GetPointIds().SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(points)
    ug.InsertNextCell(pyramid.GetCellType(), pyramid.GetPointIds())

    return ug


def make_pentagonal_prism():
    number_of_vertices = 10

    pentagonal_prism = vtkPentagonalPrism()

    scale = 2.0
    pentagonal_prism.GetPoints().SetPoint(0, 11 / scale, 10 / scale, 10 / scale)
    pentagonal_prism.GetPoints().SetPoint(1, 13 / scale, 10 / scale, 10 / scale)
    pentagonal_prism.GetPoints().SetPoint(2, 14 / scale, 12 / scale, 10 / scale)
    pentagonal_prism.GetPoints().SetPoint(3, 12 / scale, 14 / scale, 10 / scale)
    pentagonal_prism.GetPoints().SetPoint(4, 10 / scale, 12 / scale, 10 / scale)
    pentagonal_prism.GetPoints().SetPoint(5, 11 / scale, 10 / scale, 14 / scale)
    pentagonal_prism.GetPoints().SetPoint(6, 13 / scale, 10 / scale, 14 / scale)
    pentagonal_prism.GetPoints().SetPoint(7, 14 / scale, 12 / scale, 14 / scale)
    pentagonal_prism.GetPoints().SetPoint(8, 12 / scale, 14 / scale, 14 / scale)
    pentagonal_prism.GetPoints().SetPoint(9, 10 / scale, 12 / scale, 14 / scale)

    for i in range(0, number_of_vertices):
        pentagonal_prism.point_ids.SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(pentagonal_prism.GetPoints())
    ug.InsertNextCell(pentagonal_prism.GetCellType(), pentagonal_prism.GetPointIds())

    return ug


def make_hexagonal_prism():
    number_of_vertices = 12

    hexagonal_prism = vtkHexagonalPrism()

    scale = 2.0
    hexagonal_prism.GetPoints().SetPoint(0, 11 / scale, 10 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(1, 13 / scale, 10 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(2, 14 / scale, 12 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(3, 13 / scale, 14 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(4, 11 / scale, 14 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(5, 10 / scale, 12 / scale, 10 / scale)
    hexagonal_prism.GetPoints().SetPoint(6, 11 / scale, 10 / scale, 14 / scale)
    hexagonal_prism.GetPoints().SetPoint(7, 13 / scale, 10 / scale, 14 / scale)
    hexagonal_prism.GetPoints().SetPoint(8, 14 / scale, 12 / scale, 14 / scale)
    hexagonal_prism.GetPoints().SetPoint(9, 13 / scale, 14 / scale, 14 / scale)
    hexagonal_prism.GetPoints().SetPoint(10, 11 / scale, 14 / scale, 14 / scale)
    hexagonal_prism.GetPoints().SetPoint(11, 10 / scale, 12 / scale, 14 / scale)

    for i in range(0, number_of_vertices):
        hexagonal_prism.point_ids.SetId(i, i)

    ug = vtkUnstructuredGrid()
    ug.SetPoints(hexagonal_prism.GetPoints())
    ug.InsertNextCell(hexagonal_prism.GetCellType(), hexagonal_prism.GetPointIds())

    return ug


def make_tile(bounds, expansion_factor=0.5, thickness_ratio=0.05, shift_y=-0.05):
    """
    Make a tile slightly larger or smaller than the bounds in the
      X and Z directions and thinner or thicker in the Y direction.

    A thickness_ratio of zero reduces the tile to an XZ plane.

    :param bounds: The bounds for the tile.
    :param expansion_factor: The expansion factor in the XZ plane.
    :param thickness_ratio: The thickness ratio in the Y direction, >= 0.
    :param shift_y: Used to shift the centre of the plinth in the Y-direction.
    :return: An actor corresponding to the tile.
    """

    d_xyz = (
        bounds[1] - bounds[0],
        bounds[3] - bounds[2],
        bounds[5] - bounds[4]
    )
    thickness = d_xyz[2] * abs(thickness_ratio)
    center = ((bounds[1] + bounds[0]) / 2.0,
              bounds[2] - thickness / 2.0 + shift_y,
              (bounds[5] + bounds[4]) / 2.0)
    x_length = bounds[1] - bounds[0] + (d_xyz[0] * expansion_factor)
    z_length = bounds[5] - bounds[4] + (d_xyz[2] * expansion_factor)
    plane = vtkCubeSource()
    plane.SetCenter(center)
    plane.SetXLength(x_length)
    plane.SetYLength(thickness)
    plane.SetZLength(z_length)

    plane_mapper = vtkPolyDataMapper()
    plane_mapper.SetInputConnection(plane.GetOutputPort())

    tile_actor = vtkActor()
    tile_actor.SetMapper(plane_mapper)

    return tile_actor


def get_text_property():
    colors = vtkNamedColors()

    pty = vtkTextProperty()
    pty.BoldOn()
    pty.SetJustificationToCentered()
    pty.SetColor(colors.GetColor3d('Black'))
    return pty


def get_label_property():
    colors = vtkNamedColors()

    pty = vtkTextProperty()
    pty.BoldOn()
    pty.ShadowOn()
    pty.SetJustificationToCentered()
    pty.SetColor(colors.GetColor3d('DeepPink'))
    return pty


def get_back_face_property():
    colors = vtkNamedColors()

    pty = vtkProperty()
    pty.SetAmbientColor(colors.GetColor3d('LightSalmon'))
    pty.SetDiffuseColor(colors.GetColor3d('OrangeRed'))
    pty.SetSpecularColor(colors.GetColor3d('White'))
    pty.SetSpecular(0.2)
    pty.SetDiffuse(1.0)
    pty.SetAmbient(0.2)
    pty.SetSpecularPower(20.0)
    pty.SetOpacity(1.0)
    return pty


def get_actor_property():
    colors = vtkNamedColors()

    pty = vtkProperty()
    pty.SetAmbientColor(colors.GetColor3d('DarkSalmon'))
    pty.SetDiffuseColor(colors.GetColor3d('Seashell'))
    pty.SetSpecularColor(colors.GetColor3d('White'))
    pty.SetSpecular(0.5)
    pty.SetDiffuse(0.7)
    pty.SetAmbient(0.5)
    pty.SetSpecularPower(20.0)
    pty.SetOpacity(0.8)
    pty.EdgeVisibilityOn()
    pty.SetLineWidth(3)
    return pty


def get_point_actor_property():
    colors = vtkNamedColors()

    pty = vtkProperty()
    pty.SetAmbientColor(colors.GetColor3d('Gold'))
    pty.SetDiffuseColor(colors.GetColor3d('Yellow'))
    pty.SetSpecularColor(colors.GetColor3d('White'))
    pty.SetSpecular(0.5)
    pty.SetDiffuse(0.7)
    pty.SetAmbient(0.5)
    pty.SetSpecularPower(20.0)
    pty.SetOpacity(1.0)
    return pty


def get_tile_property():
    colors = vtkNamedColors()

    pty = vtkProperty()
    pty.SetAmbientColor(colors.GetColor3d('SteelBlue'))
    pty.SetDiffuseColor(colors.GetColor3d('LightSteelBlue'))
    pty.SetSpecularColor(colors.GetColor3d('White'))
    pty.SetSpecular(0.5)
    pty.SetDiffuse(0.7)
    pty.SetAmbient(0.5)
    pty.SetSpecularPower(20.0)
    pty.SetOpacity(0.8)
    pty.EdgeVisibilityOn()
    pty.SetLineWidth(1)
    return pty


def vtk_version_ok(major, minor, build):
    """
    Check the VTK version.

    :param major: Major version.
    :param minor: Minor version.
    :param build: Build version.
    :return: True if the requested VTK version is greater or equal to the actual VTK version.
    """
    needed_version = 10000000000 * int(major) + 100000000 * int(minor) + int(build)
    try:
        vtk_version_number = VTK_VERSION_NUMBER
    except AttributeError:  # as error:
        ver = vtkVersion()
        vtk_version_number = 10000000000 * ver.GetVTKMajorVersion() + 100000000 * ver.GetVTKMinorVersion() \
                             + ver.GetVTKBuildVersion()
    if vtk_version_number >= needed_version:
        return True
    else:
        return False


if __name__ == '__main__':
    main()
