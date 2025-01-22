#!/usr/bin/env python3

import json
from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import (
    vtkCommand,
    vtkLookupTable
)
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import (
    vtkCameraOrientationWidget,
    vtkOrientationMarkerWidget,
    vtkSliderRepresentation2D,
    vtkSliderWidget
)
from vtkmodules.vtkRenderingAnnotation import (
    vtkAxesActor,
    vtkAnnotatedCubeActor,
)
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkPropAssembly,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)


def get_program_parameters(argv):
    import argparse
    description = 'View surfaces of a segmented frog dataset using preprocessed VTK tissue files.'
    epilogue = '''
Sliders are provided to control the opacity of the displayed tissues.
Up to fifteen different surfaces may be viewed.

Note:
   If you want to use brainbin (the brain with no gaussian smoothing),
    instead of brain, then request it with -t brainbin
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', action='store_const', dest='view', const='a',
                       help='The view corresponds to Fig 12-9a in the VTK Textbook')
    group.add_argument('-b', action='store_const', dest='view', const='b',
                       help='The view corresponds to Fig 12-9b in the VTK Textbook')
    group.add_argument('-c', action='store_const', dest='view', const='c',
                       help='The view corresponds to Fig 12-9c in the VTK Textbook')
    group.add_argument('-d', action='store_const', dest='view', const='d',
                       help='The view corresponds to Fig 12-9d in the VTK Textbook')
    group.add_argument('-l', action='store_const', dest='view', const='l',
                       help='The view corresponds to looking down on the anterior surface')
    group.add_argument('-p', action='store_const', dest='view', const='p',
                       help='The view corresponds to looking down on the posterior surface (the default)')
    parser.set_defaults(type=None)

    parser.add_argument('file_name', help='The path to the JSON file e.g. Frog_vtk.json.')
    parser.add_argument('-n', action='store_true', dest='omit_sliders', help='No sliders.')
    parser.add_argument('-t', nargs='+', dest='tissues', action='append', help='Select one or more tissues.')
    args = parser.parse_args()
    return args.file_name, args.view, args.omit_sliders, args.tissues


def main(fn, select_figure, no_sliders, chosen_tissues):
    if not select_figure:
        select_figure = 'p'

    fn_path = Path(fn)
    if not fn_path.suffix:
        fn_path = fn_path.with_suffix(".json")
    if not fn_path.is_file():
        print('Unable to find: ', fn_path)
    parsed_ok, parameters = parse_json(fn_path)
    if not parsed_ok:
        print('Unable to parse the JSON file.')
        return

    color_lut = create_tissue_lut(parameters['indices'], parameters['colors'])

    tissues = parameters['names']
    if select_figure:
        if select_figure == 'b':
            # No skin.
            tissues = parameters['fig12-9b']
        if select_figure in ['c', 'd']:
            # No skin, blood and skeleton.
            tissues = parameters['fig12-9cd']

    if chosen_tissues:
        chosen_tissues = [x.lower() for x in chosen_tissues[0]]
        res = list()
        has_brainbin = False
        if 'brainbin' in chosen_tissues:
            print('Using brainbin instead of brain.')
            res.append('brainbin')
            parameters['indices'].pop('brain', None)
            parameters['indices']['brainbin'] = 2
            parameters['colors'].pop('brain', None)
            parameters['colors']['brainbin'] = 'beige'
            has_brainbin = True
        for ct in chosen_tissues:
            if has_brainbin and ct in ['brain', 'brainbin']:
                continue
            if ct in tissues:
                res.append(ct)
            else:
                print(f'Tissue: {ct} is not available.')
                print(f'Available tissues are: {", ".join(tissues)} and brainbin')
                return
        if len(res) == 1 and 'skin' in res:
            parameters['opacity']['skin'] = 1.0
        tissues = res

    colors = vtkNamedColors()
    colors.SetColor("ParaViewBkg", [82, 87, 110, 255])

    # Setup render window, renderers, and interactor.
    ren = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)
    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    sliders = dict()
    left_step_size = 1.0 / 9
    left_pos_y = 0.275
    left_pos_x0 = 0.02
    left_pos_x1 = 0.18
    right_step_size = 1.0 / 9
    right_pos_y = 0.05
    right_pos_x0 = 0.8 + 0.02
    right_pos_x1 = 0.8 + 0.18

    slider_count = 0

    color_size = len(max(parameters['colors'].values(), key=len))
    name_size = len(max(parameters['names'], key=len))
    int_size = 2
    line = '-' * (7 + name_size + color_size)
    res = [line,
           f'{"Tissue":<{name_size}s}{" Label "}{"Color"}',
           line]

    for tissue in tissues:
        reader = vtkPolyDataReader()
        reader.SetFileName(parameters['vtk_files'][tissue])
        reader.Update()

        trans = SliceOrder().get(parameters['orientation'][tissue])
        trans.Scale(1, -1, -1)

        tf = vtkTransformPolyDataFilter()
        tf.SetInputConnection(reader.GetOutputPort())
        tf.SetTransform(trans)
        tf.SetInputConnection(reader.GetOutputPort())

        normals = vtkPolyDataNormals()
        normals.SetInputConnection(tf.GetOutputPort())
        normals.SetFeatureAngle(60.0)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)

        actor.GetProperty().SetOpacity(parameters['opacity'][tissue])
        actor.GetProperty().SetDiffuseColor(color_lut.GetTableValue(parameters['indices'][tissue])[:3])
        actor.GetProperty().SetSpecular(0.2)
        actor.GetProperty().SetSpecularPower(10)

        ren.AddActor(actor)

        if not no_sliders:
            slider_properties = SliderProperties()
            slider_properties.value_initial = parameters['opacity'][tissue]
            slider_properties.title = tissue

            # Screen coordinates.
            if slider_count < 7:
                slider_properties.p1 = [left_pos_x0, left_pos_y]
                slider_properties.p2 = [left_pos_x1, left_pos_y]
                left_pos_y += left_step_size
            else:
                slider_properties.p1 = [right_pos_x0, right_pos_y]
                slider_properties.p2 = [right_pos_x1, right_pos_y]
                right_pos_y += right_step_size

            slider_widget = make_slider_widget(slider_properties, color_lut, parameters['indices'][tissue])
            slider_widget.SetInteractor(iren)
            slider_widget.SetAnimationModeToAnimate()
            slider_widget.EnabledOn()

            cb = SliderCallback(actor.GetProperty())
            slider_widget.AddObserver(vtkCommand.InteractionEvent, cb)
            sliders[tissue] = slider_widget
            slider_count += 1

        res.append(
            f'{tissue:<{name_size}s} {parameters["indices"][tissue]:{int_size + 3}d}'
            f' {parameters["colors"][tissue]:<{color_size}s}')

    res.append(line)
    print('\n'.join(res))

    if no_sliders:
        ren_win.SetSize(1024, 1024)
    else:
        ren_win.SetSize(1024 + 400, 1024)
    ren_win.SetWindowName('FroggieView')

    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))

    #  Final view.
    camera = ren.GetActiveCamera()
    # Superior Anterior Left
    labels = 'sal'
    if select_figure == 'a':
        # Fig 12-9a in the VTK Textbook
        camera.SetPosition(495.722368, -447.474954, -646.308030)
        camera.SetFocalPoint(137.612066, -40.962376, -195.171023)
        camera.SetViewUp(-0.323882, -0.816232, 0.478398)
        camera.SetDistance(704.996499)
        camera.SetClippingRange(319.797039, 1809.449285)
    elif select_figure == 'b':
        # Fig 12-9b in the VTK Textbook
        camera.SetPosition(478.683494, -420.477744, -643.112038)
        camera.SetFocalPoint(135.624874, -36.478435, -210.614440)
        camera.SetViewUp(-0.320495, -0.820148, 0.473962)
        camera.SetDistance(672.457328)
        camera.SetClippingRange(307.326771, 1765.990822)
    elif select_figure == 'c':
        # Fig 12-9c in the VTK Textbook
        camera.SetPosition(201.363313, -147.260834, -229.885066)
        camera.SetFocalPoint(140.626206, -75.857216, -162.352531)
        camera.SetViewUp(-0.425438, -0.786048, 0.448477)
        camera.SetDistance(115.534047)
        camera.SetClippingRange(7.109870, 854.091718)
    elif select_figure == 'd':
        # Fig 12-9d in the VTK Textbook
        camera.SetPosition(115.361727, -484.656410, -6.193827)
        camera.SetFocalPoint(49.126343, 98.501094, 1.323317)
        camera.SetViewUp(-0.649127, -0.083475, 0.756086)
        camera.SetDistance(586.955116)
        camera.SetClippingRange(360.549218, 866.876230)
    elif select_figure == 'l':
        # Orient so that we look down on the anterior surface and
        #   the superior surface faces the top of the screen.
        #  Left Superior Anterior
        labels = 'lsa'
        transform = vtkTransform()
        transform.SetMatrix(camera.GetModelTransformMatrix())
        transform.RotateY(90)
        transform.RotateZ(90)
        camera.SetModelTransformMatrix(transform.GetMatrix())
        ren.ResetCamera()
    else:
        # The default.
        # Orient so that we look down on the posterior surface and
        #   the superior surface faces the top of the screen.
        # Right Superior Posterior
        labels = 'rsp'
        transform = vtkTransform()
        transform.SetMatrix(camera.GetModelTransformMatrix())
        transform.RotateY(-90)
        transform.RotateZ(90)
        camera.SetModelTransformMatrix(transform.GetMatrix())
        ren.ResetCamera()

    cow = vtkCameraOrientationWidget()
    cow.SetParentRenderer(ren)
    if no_sliders:
        # Turn off if you do not want it.
        cow.On()
        cow.EnabledOn()
    else:
        cow.Off()
        cow.EnabledOff()

    axes = make_cube_actor(labels, colors)
    om = vtkOrientationMarkerWidget()
    om.SetOrientationMarker(axes)
    # Position upper left in the viewport.
    # om.SetViewport(0.0, 0.8, 0.2, 1.0)
    # Position lower left in the viewport.
    om.SetViewport(0, 0, 0.2, 0.2)
    om.SetInteractor(iren)
    om.EnabledOn()
    om.InteractiveOn()

    ren_win.Render()

    slider_toggle = SliderToggleCallback(sliders)
    iren.AddObserver('KeyPressEvent', slider_toggle)

    iren.Start()


def parse_json(fn_path):
    """
    Parse the JSON file selecting the components that we want.

    We also check that the file paths are valid.

    :param fn_path: The path the JSON file.
    :return: A dictionary of the parameters that we require.
    """
    with open(fn_path) as data_file:
        json_data = json.load(data_file)
    paths_ok = True
    parameters = dict()
    for k, v in json_data.items():
        if k == 'files':
            if 'root' in v:
                root = Path(v['root'])
                if not root.exists():
                    print(f'Bad path: {root}')
                    paths_ok = False
                else:
                    if 'vtk_files' not in v:
                        print('Expected vtk files.')
                        paths_ok = False
                        continue
                    for kk in v:
                        if kk == 'vtk_files':
                            if len(v[kk]) != 17:
                                print(f'Expected seventeen file names.')
                                paths_ok = False
                            # The stem of the file path becomes the key.
                            path_map = dict()
                            for p in list(map(lambda pp: root / pp, v[kk])):
                                path_map[p.stem] = p
                                if not p.is_file():
                                    paths_ok = False
                                    print(f'Not a file {p}')
                            if paths_ok:
                                parameters[kk] = path_map
            else:
                paths_ok = False
                print('Missing the key "root" and/or the key "files" for the files.')
        else:
            if k in ['tissues', 'figures']:
                for kk, vv in v.items():
                    parameters[kk] = vv
    return paths_ok, parameters


class SliceOrder:
    """
    These transformations permute image and other geometric data to maintain proper
     orientation regardless of the acquisition order. After applying these transforms with
    vtkTransformFilter, a view up of 0, -1, 0 will result in the body part
    facing the viewer.
    NOTE: some transformations have a -1 scale factor for one of the components.
          To ensure proper polygon orientation and normal direction, you must
          apply the vtkPolyDataNormals filter.

    Naming (the nomenclature is medical):
    si - superior to inferior (top to bottom)
    is - inferior to superior (bottom to top)
    ap - anterior to posterior (front to back)
    pa - posterior to anterior (back to front)
    lr - left to right
    rl - right to left
    """

    def __init__(self):
        self.si_mat = vtkMatrix4x4()
        self.si_mat.Zero()
        self.si_mat.SetElement(0, 0, 1)
        self.si_mat.SetElement(1, 2, 1)
        self.si_mat.SetElement(2, 1, -1)
        self.si_mat.SetElement(3, 3, 1)

        self.is_mat = vtkMatrix4x4()
        self.is_mat.Zero()
        self.is_mat.SetElement(0, 0, 1)
        self.is_mat.SetElement(1, 2, -1)
        self.is_mat.SetElement(2, 1, -1)
        self.is_mat.SetElement(3, 3, 1)

        self.lr_mat = vtkMatrix4x4()
        self.lr_mat.Zero()
        self.lr_mat.SetElement(0, 2, -1)
        self.lr_mat.SetElement(1, 1, -1)
        self.lr_mat.SetElement(2, 0, 1)
        self.lr_mat.SetElement(3, 3, 1)

        self.rl_mat = vtkMatrix4x4()
        self.rl_mat.Zero()
        self.rl_mat.SetElement(0, 2, 1)
        self.rl_mat.SetElement(1, 1, -1)
        self.rl_mat.SetElement(2, 0, 1)
        self.rl_mat.SetElement(3, 3, 1)

        """
        The previous transforms assume radiological views of the slices
         (viewed from the feet).
        Other modalities such as physical sectioning may view from the head.
        The following transforms modify the original with a 180° rotation about y
        """

        self.hf_mat = vtkMatrix4x4()
        self.hf_mat.Zero()
        self.hf_mat.SetElement(0, 0, -1)
        self.hf_mat.SetElement(1, 1, 1)
        self.hf_mat.SetElement(2, 2, -1)
        self.hf_mat.SetElement(3, 3, 1)

        self.transform = dict()

        si_trans = vtkTransform()
        si_trans.SetMatrix(self.si_mat)
        self.transform['si'] = si_trans

        is_trans = vtkTransform()
        is_trans.SetMatrix(self.is_mat)
        self.transform['is'] = is_trans

        ap_trans = vtkTransform()
        ap_trans.Scale(1, -1, 1)
        self.transform['ap'] = ap_trans

        pa_trans = vtkTransform()
        pa_trans.Scale(1, -1, -1)
        self.transform['pa'] = pa_trans

        lr_trans = vtkTransform()
        lr_trans.SetMatrix(self.lr_mat)
        self.transform['lr'] = lr_trans

        rl_trans = vtkTransform()
        rl_trans.SetMatrix(self.rl_mat)
        self.transform['rl'] = rl_trans

        hf_trans = vtkTransform()
        hf_trans.SetMatrix(self.hf_mat)
        self.transform['hf'] = hf_trans

        hf_si_trans = vtkTransform()
        hf_si_trans.SetMatrix(self.hf_mat)
        hf_si_trans.Concatenate(self.si_mat)
        self.transform['hfsi'] = hf_si_trans

        hf_is_trans = vtkTransform()
        hf_is_trans.SetMatrix(self.hf_mat)
        hf_is_trans.Concatenate(self.is_mat)
        self.transform['hfis'] = hf_is_trans

        hf_ap_trans = vtkTransform()
        hf_ap_trans.SetMatrix(self.hf_mat)
        hf_ap_trans.Scale(1, -1, 1)
        self.transform['hfap'] = hf_ap_trans

        hf_pa_trans = vtkTransform()
        hf_pa_trans.SetMatrix(self.hf_mat)
        hf_pa_trans.Scale(1, -1, -1)
        self.transform['hfpa'] = hf_pa_trans

        hf_lr_trans = vtkTransform()
        hf_lr_trans.SetMatrix(self.hf_mat)
        hf_lr_trans.Concatenate(self.lr_mat)
        self.transform['hflr'] = hf_lr_trans

        hf_rl_trans = vtkTransform()
        hf_rl_trans.SetMatrix(self.hf_mat)
        hf_rl_trans.Concatenate(self.rl_mat)
        self.transform['hfrl'] = hf_rl_trans

        # Identity
        self.transform['I'] = vtkTransform()

        # Zero
        z_trans = vtkTransform()
        z_trans.Scale(0, 0, 0)
        self.transform['Z'] = z_trans

    def print_transform(self, order):
        """
        Print the homogenous matrix corresponding to the slice order.
        :param order: The slice order.
        :return:
        """
        print(order)
        m = self.transform[order].GetMatrix()
        for i in range(0, 4):
            row = list()
            for j in range(0, 4):
                row.append(f'{m.GetElement(i, j):6.2g}')
            print(' '.join(row))

    def print_all_transforms(self):
        """
        Print all the homogenous matrices corresponding to the slice orders.
        :return:
        """
        for k in self.transform.keys():
            self.print_transform(k)

    def get(self, order):
        """
        Returns the vtkTransform corresponding to the slice order.

        :param order: The slice order.
        :return: The vtkTransform to use.
        """
        if order in self.transform.keys():
            return self.transform[order]
        else:
            s = 'No such transform "{:s}" exists.'.format(order)
            raise Exception(s)


def create_tissue_lut(indices, colors):
    """
    Create the lookup table for the frog tissues.

    Each table value corresponds the color of one of the frog tissues.

    :param indices: The tissue name and index.
    :param colors: The tissue name and color.
    :return: The lookup table.
    """
    lut = vtkLookupTable()
    lut.SetNumberOfColors(len(colors))
    lut.SetTableRange(0, len(colors) - 1)
    lut.Build()

    nc = vtkNamedColors()

    for k in indices.keys():
        lut.SetTableValue(indices[k], nc.GetColor4d(colors[k]))

    return lut


def make_axes_actor(scale, xyz_labels):
    """
    :param scale: Sets the scale and direction of the axes.
    :param xyz_labels: Labels for the axes.
    :return: The axes actor.
    """
    axes = vtkAxesActor()
    axes.SetScale(scale)
    axes.SetShaftTypeToCylinder()
    axes.SetXAxisLabelText(xyz_labels[0])
    axes.SetYAxisLabelText(xyz_labels[1])
    axes.SetZAxisLabelText(xyz_labels[2])
    axes.SetCylinderRadius(0.5 * axes.GetCylinderRadius())
    axes.SetConeRadius(1.025 * axes.GetConeRadius())
    axes.SetSphereRadius(1.5 * axes.GetSphereRadius())
    tprop = axes.GetXAxisCaptionActor2D().GetCaptionTextProperty()
    tprop.ItalicOn()
    tprop.ShadowOn()
    tprop.SetFontFamilyToTimes()
    # Use the same text properties on the other two axes.
    axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    return axes


def make_annotated_cube_actor(cube_labels, colors):
    """
    :param cube_labels: The labels for the cube faces.
    :param colors: Used to determine the cube color.
    :return: The annotated cube actor.
    """
    # A cube with labeled faces.
    cube = vtkAnnotatedCubeActor()
    cube.SetXPlusFaceText(cube_labels[0])
    cube.SetXMinusFaceText(cube_labels[1])
    cube.SetYPlusFaceText(cube_labels[2])
    cube.SetYMinusFaceText(cube_labels[3])
    cube.SetZPlusFaceText(cube_labels[4])
    cube.SetZMinusFaceText(cube_labels[5])
    cube.SetFaceTextScale(0.5)
    cube.GetCubeProperty().SetColor(colors.GetColor3d('Gainsboro'))

    cube.GetTextEdgesProperty().SetColor(colors.GetColor3d('LightSlateGray'))

    # Change the vector text colors.
    cube.GetXPlusFaceProperty().SetColor(colors.GetColor3d('Tomato'))
    cube.GetXMinusFaceProperty().SetColor(colors.GetColor3d('Tomato'))
    cube.GetYPlusFaceProperty().SetColor(colors.GetColor3d('DeepSkyBlue'))
    cube.GetYMinusFaceProperty().SetColor(colors.GetColor3d('DeepSkyBlue'))
    cube.GetZPlusFaceProperty().SetColor(colors.GetColor3d('SeaGreen'))
    cube.GetZMinusFaceProperty().SetColor(colors.GetColor3d('SeaGreen'))
    return cube


def make_cube_actor(label_selector, colors):
    """
    :param label_selector: The selector used to define labels for the axes and cube.
    :param colors: Used to set the colors of the cube faces.
    :return: The combined axes and annotated cube prop.
    """
    if label_selector == 'sal':
        # xyz_labels = ['S', 'A', 'L']
        xyz_labels = ['+X', '+Y', '+Z']
        cube_labels = ['S', 'I', 'A', 'P', 'L', 'R']
        scale = [1.5, 1.5, 1.5]
    elif label_selector == 'rsp':
        # xyz_labels = ['R', 'S', 'P']
        xyz_labels = ['+X', '+Y', '+Z']
        cube_labels = ['R', 'L', 'S', 'I', 'P', 'A']
        scale = [1.5, 1.5, 1.5]
    elif label_selector == 'lsa':
        # xyz_labels = ['R', 'S', 'P']
        xyz_labels = ['+X', '+Y', '+Z']
        cube_labels = ['L', 'R', 'S', 'I', 'A', 'P']
        scale = [1.5, 1.5, 1.5]
    else:
        xyz_labels = ['+X', '+Y', '+Z']
        cube_labels = ['+X', '-X', '+Y', '-Y', '+Z', '-Z']
        scale = [1.5, 1.5, 1.5]

    # We are combining a vtkAxesActor and a vtkAnnotatedCubeActor
    # into a vtkPropAssembly
    cube = make_annotated_cube_actor(cube_labels, colors)
    axes = make_axes_actor(scale, xyz_labels)

    # Combine orientation markers into one with an assembly.
    assembly = vtkPropAssembly()
    assembly.AddPart(axes)
    assembly.AddPart(cube)
    return assembly


class SliderProperties:
    tube_width = 0.004
    slider_length = 0.015
    slider_width = 0.008
    end_cap_length = 0.008
    end_cap_width = 0.02
    title_height = 0.02
    label_height = 0.02

    value_minimum = 0.0
    value_maximum = 1.0
    value_initial = 1.0

    p1 = [0.02, 0.1]
    p2 = [0.18, 0.1]

    title = None

    title_color = 'Black'
    label_color = 'Black'
    value_color = 'DarkSlateGray'
    slider_color = 'BurlyWood'
    selected_color = 'Lime'
    bar_color = 'Black'
    bar_ends_color = 'Indigo'


def make_slider_widget(properties, lut, idx):
    """
    Make the slider widget.

    :param properties: The slider properties.
    :param lut: The color lookup table.
    :param idx: The tissue index.
    :return: The slider widget.
    """
    slider = vtkSliderRepresentation2D()

    slider.SetMinimumValue(properties.value_minimum)
    slider.SetMaximumValue(properties.value_maximum)
    slider.SetValue(properties.value_initial)
    slider.SetTitleText(properties.title)

    slider.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
    slider.GetPoint1Coordinate().SetValue(properties.p1[0], properties.p1[1])
    slider.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
    slider.GetPoint2Coordinate().SetValue(properties.p2[0], properties.p2[1])

    slider.SetTubeWidth(properties.tube_width)
    slider.SetSliderLength(properties.slider_length)
    slider.SetSliderWidth(properties.slider_width)
    slider.SetEndCapLength(properties.end_cap_length)
    slider.SetEndCapWidth(properties.end_cap_width)
    slider.SetTitleHeight(properties.title_height)
    slider.SetLabelHeight(properties.label_height)

    colors = vtkNamedColors()
    # Set the colors of the slider components.
    # Change the color of the bar.
    slider.GetTubeProperty().SetColor(colors.GetColor3d(properties.bar_color))
    # Change the color of the ends of the bar.
    slider.GetCapProperty().SetColor(colors.GetColor3d(properties.bar_ends_color))
    # Change the color of the knob that slides.
    slider.GetSliderProperty().SetColor(colors.GetColor3d(properties.slider_color))
    # Change the color of the knob when the mouse is held on it.
    slider.GetSelectedProperty().SetColor(colors.GetColor3d(properties.selected_color))
    # Change the color of the text displaying the value.
    slider.GetLabelProperty().SetColor(colors.GetColor3d(properties.value_color))
    #  Use the one color for the labels.
    # slider.GetTitleProperty().SetColor(colors.GetColor3d(properties.label_color))
    # Change the color of the text indicating what the slider controls
    if idx in range(0, 16):
        slider.GetTitleProperty().SetColor(lut.GetTableValue(idx)[:3])
        slider.GetTitleProperty().ShadowOff()
    else:
        slider.GetTitleProperty().SetColor(colors.GetColor3d(properties.title_color))

    slider_widget = vtkSliderWidget()
    slider_widget.SetRepresentation(slider)

    return slider_widget


class SliderCallback:
    def __init__(self, actor_property):
        self.actor_property = actor_property

    def __call__(self, caller, ev):
        slider_widget = caller
        value = slider_widget.GetRepresentation().GetValue()
        self.actor_property.SetOpacity(value)


class SliderToggleCallback:
    def __init__(self, sliders):
        self.sliders = sliders

    def __call__(self, caller, ev):
        if caller.GetKeyCode() == "n":
            for k, v in self.sliders.items():
                if v.GetEnabled():
                    v.Off()
                else:
                    v.On()


if __name__ == '__main__':
    import sys

    data_folder, view, omit_sliders, selected_tissues = get_program_parameters(sys.argv)
    main(data_folder, view, omit_sliders, selected_tissues)
