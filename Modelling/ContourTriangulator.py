#!/usr/bin/env python3


# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkMarchingSquares
from vtkmodules.vtkFiltersGeneral import vtkContourTriangulator
from vtkmodules.vtkIOImage import vtkPNGReader
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def get_program_parameters():
    import argparse
    description = 'Create a contour from a structured point set (image) and triangulate it.'
    epilogue = '''
    Try with different iso values e.g. -i1000.
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue)
    parser.add_argument('file_name', help='The path to the image file to use e.g fullhead15.png.')
    parser.add_argument('-i', '--iso_value', help='The contour value for generating the isoline.', default=500,
                        type=int)
    args = parser.parse_args()
    return args.file_name, args.iso_value


def main():
    file_name, iso_value = get_program_parameters()

    colors = vtkNamedColors()

    reader = vtkPNGReader()
    if not reader.CanReadFile(file_name):
        print('Error: Could not read', file_name)
        return
    reader.SetFileName(file_name)
    reader.Update()

    iso = vtkMarchingSquares()
    iso.SetInputConnection(reader.GetOutputPort())
    iso.SetValue(0, iso_value)

    iso_mapper = vtkDataSetMapper()
    iso_mapper.SetInputConnection(iso.GetOutputPort())
    iso_mapper.ScalarVisibilityOff()

    iso_actor = vtkActor()
    iso_actor.SetMapper(iso_mapper)
    iso_actor.GetProperty().SetColor(
        colors.GetColor3d('MediumOrchid'))

    poly = vtkContourTriangulator()
    poly.SetInputConnection(iso.GetOutputPort())

    poly_mapper = vtkDataSetMapper()
    poly_mapper.SetInputConnection(poly.GetOutputPort())
    poly_mapper.ScalarVisibilityOff()

    poly_actor = vtkActor()
    poly_actor.SetMapper(poly_mapper)
    poly_actor.GetProperty().SetColor(colors.GetColor3d('Gray'))

    # Standard rendering classes.
    renderer = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.SetMultiSamples(0)
    ren_win.AddRenderer(renderer)
    ren_win.SetWindowName('ContourTriangulator')

    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    renderer.AddActor(poly_actor)
    renderer.AddActor(iso_actor)
    renderer.SetBackground(colors.GetColor3d('DarkSlateGray'))
    ren_win.SetSize(300, 300)

    camera = renderer.GetActiveCamera()
    renderer.ResetCamera()
    camera.Azimuth(180)

    ren_win.Render()
    iren.Initialize()
    iren.Start()


if __name__ == '__main__':
    main()
