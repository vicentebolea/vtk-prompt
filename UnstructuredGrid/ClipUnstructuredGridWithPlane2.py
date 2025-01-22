#!/usr/bin/env python

import collections

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import (
    vtkCellTypes,
    vtkPlane
)
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkClipDataSet
from vtkmodules.vtkIOLegacy import vtkUnstructuredGridReader
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def get_program_parameters():
    import argparse
    description = 'Use a vtkClipDataSet to clip a vtkUnstructuredGrid..'
    epilogue = '''
 Use a vtkClipDataSet to clip a vtkUnstructuredGrid..
 The resulting output and clipped output are presented in yellow and red respectively.
 To illustrate the clipped interfaces, the example uses a vtkTransform to rotate each
    output about their centers.
 Note: This clipping filter does not retain the original cells if they are not clipped.
   '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename', help='treemesh.vtk')
    parser.add_argument('-o', action='store_false',
                        help='Output using the original code.')
    args = parser.parse_args()
    return args.filename, args.o


def main():
    filename, correct_output = get_program_parameters()

    # Create the reader for the data.
    reader = vtkUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()

    bounds = reader.GetOutput().GetBounds()
    center = reader.GetOutput().GetCenter()

    colors = vtkNamedColors()
    renderer = vtkRenderer()
    renderer.SetBackground(colors.GetColor3d('Wheat'))
    renderer.UseHiddenLineRemovalOn()

    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindow.SetSize(640, 480)

    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderWindow)

    xnorm = [-1.0, -1.0, 1.0]

    clipPlane = vtkPlane()
    clipPlane.SetOrigin(reader.GetOutput().GetCenter())
    clipPlane.SetNormal(xnorm)

    if correct_output:
        clipper = vtkClipDataSet()
        clipper.SetClipFunction(clipPlane)
        clipper.SetInputData(reader.GetOutput())
        clipper.SetValue(0.0)
        clipper.GenerateClippedOutputOff()
        clipper.Update()

        # Set inside out, generate the clipped output and
        #  use the clipped output for the clipped mapper.
        # If this is done a similar image to
        # ClipUnstructuredGridWithPlane is created.
        clipper1 = vtkClipDataSet()
        clipper1.SetClipFunction(clipPlane)
        clipper1.SetInputData(reader.GetOutput())
        clipper1.SetValue(0.0)
        clipper1.InsideOutOn()
        clipper1.GenerateClippedOutputOn()
        clipper1.Update()

    else:
        clipper = vtkClipDataSet()
        clipper.SetClipFunction(clipPlane)
        clipper.SetInputData(reader.GetOutput())
        clipper.SetValue(0.0)
        clipper.GenerateClippedOutputOn()
        clipper.Update()

        clipper1 = None

    insideMapper = vtkDataSetMapper()
    insideMapper.SetInputData(clipper.GetOutput())
    insideMapper.ScalarVisibilityOff()

    insideActor = vtkActor()
    insideActor.SetMapper(insideMapper)
    insideActor.GetProperty().SetDiffuseColor(colors.GetColor3d('Banana'))
    insideActor.GetProperty().SetAmbient(0.3)
    insideActor.GetProperty().EdgeVisibilityOn()

    clippedMapper = vtkDataSetMapper()
    if correct_output:
        clippedMapper.SetInputData(clipper1.GetClippedOutput())
    else:
        clippedMapper.SetInputData(clipper.GetClippedOutput())
    clippedMapper.ScalarVisibilityOff()

    clippedActor = vtkActor()
    clippedActor.SetMapper(clippedMapper)
    clippedActor.GetProperty().SetDiffuseColor(colors.GetColor3d('tomato'))
    insideActor.GetProperty().SetAmbient(0.3)
    clippedActor.GetProperty().EdgeVisibilityOn()

    # Create transforms to make a better visualization
    insideTransform = vtkTransform()
    insideTransform.Translate(-(bounds[1] - bounds[0]) * 0.75, 0, 0)
    insideTransform.Translate(center[0], center[1], center[2])
    insideTransform.RotateY(-120.0)
    insideTransform.Translate(-center[0], -center[1], -center[2])
    insideActor.SetUserTransform(insideTransform)

    clippedTransform = vtkTransform()
    clippedTransform.Translate((bounds[1] - bounds[0]) * 0.75, 0, 0)
    clippedTransform.Translate(center[0], center[1], center[2])
    if correct_output:
        clippedTransform.RotateY(60.0)
    else:
        clippedTransform.RotateY(-120.0)
    clippedTransform.Translate(-center[0], -center[1], -center[2])
    clippedActor.SetUserTransform(clippedTransform)

    renderer.AddViewProp(clippedActor)
    renderer.AddViewProp(insideActor)

    renderer.ResetCamera()
    renderer.GetActiveCamera().Dolly(1.4)
    renderer.ResetCameraClippingRange()
    renderWindow.Render()
    renderWindow.SetWindowName('ClipUnstructuredGridWithPlane2')
    renderWindow.Render()

    interactor.Start()

    # Generate a report
    numberOfCells = clipper.GetOutput().GetNumberOfCells()
    print('------------------------')
    print('The inside dataset contains a \n', clipper.GetOutput().GetClassName(), ' that has ', numberOfCells, ' cells')
    cellMap = dict()
    for i in range(0, numberOfCells):
        cellMap.setdefault(clipper.GetOutput().GetCellType(i), 0)
        cellMap[clipper.GetOutput().GetCellType(i)] += 1
    # Sort by key and put into an OrderedDict.
    # An OrderedDict remembers the order in which the keys have been inserted.
    for k, v in collections.OrderedDict(sorted(cellMap.items())).items():
        print('\tCell type ', vtkCellTypes.GetClassNameFromTypeId(k), ' occurs ', v, ' times.')

    print('------------------------')
    outsideCellMap = dict()
    if correct_output:
        number_of_cells = clipper1.GetClippedOutput().GetNumberOfCells()
        print('The clipped dataset contains a \n', clipper1.GetClippedOutput().GetClassName(), ' that has ',
              numberOfCells,
              ' cells')
        for i in range(0, number_of_cells):
            outsideCellMap.setdefault(clipper1.GetClippedOutput().GetCellType(i), 0)
            outsideCellMap[clipper1.GetClippedOutput().GetCellType(i)] += 1
    else:
        number_of_cells = clipper.GetClippedOutput().GetNumberOfCells()
        print('The clipped dataset contains a \n', clipper.GetClippedOutput().GetClassName(), ' that has ',
              numberOfCells,
              ' cells')
        for i in range(0, number_of_cells):
            outsideCellMap.setdefault(clipper.GetClippedOutput().GetCellType(i), 0)
            outsideCellMap[clipper.GetClippedOutput().GetCellType(i)] += 1
    for k, v in collections.OrderedDict(sorted(outsideCellMap.items())).items():
        print(f' Cell type {vtkCellTypes.GetClassNameFromTypeId(k)} occurs {v} times.')


if __name__ == '__main__':
    main()
