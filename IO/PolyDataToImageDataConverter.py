#!/usr/bin/env python

from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkIOImage import vtkMetaImageWriter
from vtkmodules.vtkImagingStencil import (
    vtkImageStencil,
    vtkPolyDataToImageStencil
)


def get_program_parameters():
    import argparse
    parser = argparse.ArgumentParser(description='Converts the polydata to imagedata.')
    parser.add_argument('filename', help='A filename e.g. headMesh.stl')
    args = parser.parse_args()
    return args.filename


def main():
    mesh_filename = get_program_parameters()

    reader = vtkSTLReader()
    reader.SetFileName(mesh_filename)
    reader.Update()
    mesh = reader.GetOutput()
    bounds = mesh.GetBounds()

    spacing1 = 0.1
    pixel_padding = 5
    origin_shift = pixel_padding * spacing1
    spacing = [spacing1, spacing1, spacing1]
    origin = [bounds[0] - origin_shift, bounds[2] - origin_shift, bounds[4] - origin_shift]
    extent = [0, int((bounds[1] - bounds[0]) / spacing1) + 2 * pixel_padding, 0,
              int((bounds[3] - bounds[2]) / spacing1) + 2 * pixel_padding, 0,
              int((bounds[5] - bounds[4]) / spacing1) + 2 * pixel_padding]

    blank_image = vtkImageData()
    blank_image.SetExtent(extent)
    blank_image.AllocateScalars(3, 1)  # VTK_UNSIGNED_CHAR, 1 component
    blank_image.GetPointData().GetScalars().Fill(0)
    blank_image.SetSpacing(spacing)
    blank_image.SetOrigin(origin)

    dataToStencil = vtkPolyDataToImageStencil()
    dataToStencil.SetInputData(mesh)
    dataToStencil.SetOutputSpacing(spacing)
    dataToStencil.SetOutputOrigin(origin)

    stencil = vtkImageStencil()
    stencil.SetInputData(blank_image)
    stencil.SetStencilConnection(dataToStencil.GetOutputPort())
    stencil.ReverseStencilOn()
    stencil.SetBackgroundValue(255)
    stencil.Update()
    mask = stencil.GetOutput()

    writer = vtkMetaImageWriter()
    writer.SetFileName("output.mha")
    writer.SetInputData(mask)
    writer.Write()


if __name__ == '__main__':
    main()
