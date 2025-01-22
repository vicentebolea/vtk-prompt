#!/usr/bin/env python3

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingContextOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOImage import vtkDICOMImageReader
from vtkmodules.vtkInteractionImage import vtkImageViewer2
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage
from vtkmodules.vtkRenderingCore import (
    vtkActor2D,
    vtkRenderWindowInteractor,
    vtkTextMapper,
    vtkTextProperty
)


# Helper class to format slice status message
class StatusMessage:
    @staticmethod
    def format(slice: int, max_slice: int):
        return f'Slice Number {slice + 1}/{max_slice + 1}'


# Define own interaction style
class MyVtkInteractorStyleImage(vtkInteractorStyleImage):
    def __init__(self, parent=None):
        super().__init__()
        self.AddObserver('KeyPressEvent', self.key_press_event)
        self.AddObserver('MouseWheelForwardEvent', self.mouse_wheel_forward_event)
        self.AddObserver('MouseWheelBackwardEvent', self.mouse_wheel_backward_event)
        self.image_viewer = None
        self.status_mapper = None
        self.slice = 0
        self.min_slice = 0
        self.max_slice = 0

    def set_image_viewer(self, image_viewer):
        self.image_viewer = image_viewer
        self.min_slice = image_viewer.GetSliceMin()
        self.max_slice = image_viewer.GetSliceMax()
        self.slice = self.min_slice
        print(f'Slicer: Min = {self.min_slice}, Max= {self.max_slice}')

    def set_status_mapper(self, status_mapper):
        self.status_mapper = status_mapper

    def move_slice_forward(self):
        if self.slice < self.max_slice:
            self.slice += 1
            print(f'MoveSliceForward::Slice = {self.slice}')
            self.imageviewer.SetSlice(self.slice)
            msg = StatusMessage.format(self.slice, self.max_slice)
            self.status_mapper.SetInput(msg)
            self.imageviewer.Render()

    def move_slice_backward(self):
        if self.slice > self.min_slice:
            self.slice -= 1
            print(f'MoveSliceBackward::Slice = {self.slice}')
            self.imageviewer.SetSlice(self.slice)
            msg = StatusMessage.format(self.slice, self.max_slice)
            self.status_mapper.SetInput(msg)
            self.imageviewer.Render()

    def key_press_event(self, obj, event):
        key = self.GetInteractor().GetKeySym()
        if key == 'Up':
            self.move_slice_forward()
        elif key == 'Down':
            self.move_slice_backward()

    def mouse_wheel_forward_event(self, obj, event):
        self.move_slice_forward()

    def mouse_wheel_backward_event(self, obj, event):
        self.move_slice_backward()


# Read all the DICOM files in the specified directory.
def get_program_parameters():
    import argparse
    description = 'Read DICOM series data'
    epilogue = ''''''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dirname', help='DicomTestImages.zip')
    args = parser.parse_args()
    return args.dirname


def main():
    colors = vtkNamedColors()
    reader = vtkDICOMImageReader()
    folder = get_program_parameters()
    # Read DICOM files in the specified directory
    reader.SetDirectoryName(folder)
    reader.Update()

    # Visualilze
    image_viewer = vtkImageViewer2()
    image_viewer.SetInputConnection(reader.GetOutputPort())
    # Slice status message
    slice_text_prop = vtkTextProperty()
    slice_text_prop.SetFontFamilyToCourier()
    slice_text_prop.SetFontSize(20)
    slice_text_prop.SetVerticalJustificationToBottom()
    slice_text_prop.SetJustificationToLeft()
    # Slice status message
    slice_text_mapper = vtkTextMapper()
    msg = StatusMessage.format(image_viewer.GetSliceMin(), image_viewer.GetSliceMax())
    slice_text_mapper.SetInput(msg)
    slice_text_mapper.SetTextProperty(slice_text_prop)

    slice_text_actor = vtkActor2D()
    slice_text_actor.SetMapper(slice_text_mapper)
    slice_text_actor.SetPosition(15, 10)

    # Usage hint message
    usage_text_prop = vtkTextProperty()
    usage_text_prop.SetFontFamilyToCourier()
    usage_text_prop.SetFontSize(14)
    usage_text_prop.SetVerticalJustificationToTop()
    usage_text_prop.SetJustificationToLeft()
    usage_text_mapper = vtkTextMapper()
    usage_text_mapper.SetInput(
        'Slice with mouse wheel\n  or Up/Down-Key\n- Zoom with pressed right\n '
        ' mouse button while dragging'
    )
    usage_text_mapper.SetTextProperty(usage_text_prop)

    usage_text_actor = vtkActor2D()
    usage_text_actor.SetMapper(usage_text_mapper)
    usage_text_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
    usage_text_actor.GetPositionCoordinate().SetValue(0.05, 0.95)

    # Create an interactor with our own style (inherit from
    # vtkInteractorStyleImage in order to catch mousewheel and key events.
    render_window_interactor = vtkRenderWindowInteractor()
    my_interactor_style = MyVtkInteractorStyleImage()

    # Make imageviewer2 and sliceTextMapper visible to our interactorstyle
    # to enable slice status message updates when  scrolling through the slices.
    my_interactor_style.set_image_viewer(image_viewer)
    my_interactor_style.set_status_mapper(slice_text_mapper)

    # Make the interactor use our own interactor style
    # because SetupInteractor() is defining it's own default interator style
    # this must be called after SetupInteractor().
    # renderWindowInteractor.SetInteractorStyle(myInteractorStyle);
    image_viewer.SetupInteractor(render_window_interactor)
    render_window_interactor.SetInteractorStyle(my_interactor_style)
    render_window_interactor.Render()

    # Add slice status message and usage hint message to the renderer.
    image_viewer.GetRenderer().AddActor2D(slice_text_actor)
    image_viewer.GetRenderer().AddActor2D(usage_text_actor)

    # Initialize rendering and interaction.
    image_viewer.Render()
    image_viewer.GetRenderer().ResetCamera()
    image_viewer.GetRenderer().SetBackground(colors.GetColor3d('SlateGray'))
    image_viewer.GetRenderWindow().SetSize(800, 800)
    image_viewer.GetRenderWindow().SetWindowName('ReadDICOMSeries')
    image_viewer.Render()
    render_window_interactor.Start()


if __name__ == '__main__':
    main()
