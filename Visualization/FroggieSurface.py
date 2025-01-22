#!/usr/bin/env python3

import copy
import json
from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersCore import (
    vtkDecimatePro,
    vtkFlyingEdges3D,
    vtkMarchingCubes,
    vtkPolyDataNormals,
    vtkStripper,
    vtkWindowedSincPolyDataFilter
)
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkIOImage import vtkMetaImageReader
from vtkmodules.vtkImagingCore import (
    vtkImageShrink3D,
    vtkImageThreshold
)
from vtkmodules.vtkImagingGeneral import vtkImageGaussianSmooth
from vtkmodules.vtkImagingMorphological import vtkImageIslandRemoval2D
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import (
    vtkCameraOrientationWidget,
    vtkOrientationMarkerWidget
)
from vtkmodules.vtkRenderingAnnotation import (
    vtkAnnotatedCubeActor,
    vtkAxesActor
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
    description = 'Construct surfaces from a segmented frog dataset.'
    epilogue = '''
Up to fifteen different surfaces may be extracted.

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

    parser.add_argument('file_name', help='The path to the JSON file e.g. Frog_mhd.json.')
    parser.add_argument('-t', nargs='+', dest='tissues', action='append', help='Select one or more tissues.')
    parser.add_argument('-m', action='store_false', dest='flying_edges',
                        help='Use flying edges by default, marching cubes if set.')
    # -o: obliterate a synonym for decimation.
    parser.add_argument('-o', action='store_true', dest='decimation', help='Decimate if set.')
    args = parser.parse_args()
    return args.file_name, args.view, args.tissues, args.flying_edges, args.decimation


def main(fn, select_figure, chosen_tissues, flying_edges, decimate):
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

    tissues = list()
    indices = dict()
    for n in parameters['names']:
        if n != 'brainbin':
            tissues.append(n)
            indices[n] = parameters[n]['tissue']
    color_lut = create_tissue_lut(indices, parameters['colors'])

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
            indices.pop('brain', None)
            indices['brainbin'] = 2
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
            parameters['skin']['opacity'] = 1.0
        tissues = res

    colors = vtkNamedColors()
    colors.SetColor("ParaViewBkg", [82, 87, 110, 255])

    # Setup render window, renderer, and interactor.
    ren = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)
    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    color_size = len(max(parameters['colors'].values(), key=len))
    name_size = len(max(parameters['names'], key=len))
    int_size = 2
    line = '-' * (7 + name_size + color_size)
    res = [line,
           f'{"Tissue":<{name_size}s}{" Label "}{"Color"}',
           line]

    so = SliceOrder()

    for name in tissues:
        actor = create_tissue_actor(name, parameters[name], parameters['mhd_files'], flying_edges, decimate,
                                    color_lut, so)
        ren.AddActor(actor)
        res.append(f'{name:<{name_size}s} {indices[name]:{int_size + 3}d} {parameters["colors"][name]:<{color_size}s}')

    res.append(line)
    print('\n'.join(res))

    ren_win.SetSize(1024, 1024)
    ren_win.SetWindowName('FroggieSurface')

    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))

    #  Final view.
    camera = ren.GetActiveCamera()
    # Superior Anterior Left
    labels = 'sal'
    if select_figure == 'a':
        # Fig 12-9a in the VTK Textbook
        camera.SetPosition(742.731237, -441.329635, -877.192015)
        camera.SetFocalPoint(247.637687, 120.680880, -253.487473)
        camera.SetViewUp(-0.323882, -0.816232, 0.478398)
        camera.SetDistance(974.669585)
        camera.SetClippingRange(311.646383, 1803.630763)
    elif select_figure == 'b':
        # Fig 12-9b in the VTK Textbook
        camera.SetPosition(717.356065, -429.889054, -845.381584)
        camera.SetFocalPoint(243.071719, 100.996487, -247.446340)
        camera.SetViewUp(-0.320495, -0.820148, 0.473962)
        camera.SetDistance(929.683631)
        camera.SetClippingRange(293.464446, 1732.794957)
    elif select_figure == 'c':
        # Fig 12-9c in the VTK Textbook
        camera.SetPosition(447.560023, -136.611491, -454.753689)
        camera.SetFocalPoint(253.142277, 91.949451, -238.583973)
        camera.SetViewUp(-0.425438, -0.786048, 0.448477)
        camera.SetDistance(369.821187)
        camera.SetClippingRange(0.829116, 829.115939)
    elif select_figure == 'd':
        # Fig 12-9d in the VTK Textbook
        camera.SetPosition(347.826249, -469.633647, -236.234262)
        camera.SetFocalPoint(296.893207, 89.307704, -225.156581)
        camera.SetViewUp(-0.687345, -0.076948, 0.722244)
        camera.SetDistance(561.366478)
        camera.SetClippingRange(347.962064, 839.649856)
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
    # Turn off if you do not want it.
    cow.On()
    cow.EnabledOn()

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
    # The names of the tissues as a list.
    parameters['names'] = list()
    for k, v in json_data.items():
        if k == 'files':
            if 'root' in v:
                root = Path(v['root'])
                if not root.exists():
                    print(f'Bad path: {root}')
                    paths_ok = False
                else:
                    if 'mhd_files' not in v:
                        print('Expected mhd files.')
                        paths_ok = False
                        continue
                    for kk in v:
                        if kk == 'mhd_files':
                            if len(v[kk]) != 2:
                                print(f'Expected two file names.')
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
            if k == "tissue_parameters":
                # Assemble the parameters for each tissue.
                # Create the base parameters.
                bp = dict()
                for kk, vv in v['default'].items():
                    bp[kk.lower()] = vv
                frog = copy.deepcopy(bp)
                for kk, vv in v['frog'].items():
                    frog[kk.lower()] = vv
                for kk, vv in v.items():
                    if kk not in ['default', 'frog', 'parameter types']:
                        if kk == 'skin':
                            parameters[kk] = copy.deepcopy(bp)
                        else:
                            parameters[kk] = copy.deepcopy(frog)
                        for kkk, vvv in vv.items():
                            parameters[kk][kkk.lower()] = vvv
                            if kkk == 'NAME':
                                parameters['names'].append(vvv)
    return paths_ok, parameters


def create_tissue_actor(name, tissue, files, flying_edges, decimate, lut, so):
    """
    Create the actor for a specific tissue.

    :param name: The tissue name.
    :param tissue: The tissue parameters.
    :param files: The path to the tissue files.
    :param flying_edges: If true use flying edges.
    :param decimate: If true decimate.
    :param lut: The color lookup table for the tissues.
    :param so: The transforms corresponding to the slice order.
    :return: The actor.
    """

    pixel_size = tissue['pixel_size']
    spacing = tissue['spacing']
    start_slice = tissue['start_slice']
    data_spacing = [pixel_size, pixel_size, spacing]
    columns = tissue['columns']
    rows = tissue['rows']
    data_origin = [-(columns / 2.0) * pixel_size, -(rows / 2.0) * pixel_size, start_slice * spacing]

    voi = [
        tissue['start_column'],
        tissue['end_column'],
        tissue['start_row'],
        tissue['end_row'],
        tissue['start_slice'],
        tissue['end_slice'],
    ]
    # Adjust y bounds for PNM coordinate system.
    tmp = voi[2]
    voi[2] = rows - voi[3] - 1
    voi[3] = rows - tmp - 1

    if name == 'skin':
        fn = files['frog']
    else:
        fn = files['frogtissue']

    reader = vtkMetaImageReader()
    reader.SetFileName(str(fn))
    reader.SetDataSpacing(data_spacing)
    reader.SetDataOrigin(data_origin)
    reader.SetDataExtent(voi)
    reader.Update()

    last_connection = reader

    if not name == 'skin':
        if tissue['island_replace'] >= 0:
            island_remover = vtkImageIslandRemoval2D()
            island_remover.SetAreaThreshold(tissue['island_area'])
            island_remover.SetIslandValue(tissue['island_replace'])
            island_remover.SetReplaceValue(tissue['tissue'])
            island_remover.SetInput(last_connection.GetOutput())
            island_remover.Update()
            last_connection = island_remover

        select_tissue = vtkImageThreshold()
        select_tissue.ThresholdBetween(tissue['tissue'], tissue['tissue'])
        select_tissue.SetInValue(255)
        select_tissue.SetOutValue(0)
        select_tissue.SetInputConnection(last_connection.GetOutputPort())
        last_connection = select_tissue

    sample_rate = [
        tissue['sample_rate_column'],
        tissue['sample_rate_row'],
        tissue['sample_rate_slice'],
    ]

    shrinker = vtkImageShrink3D()
    shrinker.SetInputConnection(last_connection.GetOutputPort())
    shrinker.SetShrinkFactors(sample_rate)
    shrinker.AveragingOn()
    last_connection = shrinker

    gsd = [
        tissue['gaussian_standard_deviation_column'],
        tissue['gaussian_standard_deviation_row'],
        tissue['gaussian_standard_deviation_slice'],
    ]

    if not all(v == 0 for v in gsd):
        grf = [
            tissue['gaussian_radius_factor_column'],
            tissue['gaussian_radius_factor_row'],
            tissue['gaussian_radius_factor_slice'],
        ]

        gaussian = vtkImageGaussianSmooth()
        gaussian.SetStandardDeviation(*gsd)
        gaussian.SetRadiusFactors(*grf)
        gaussian.SetInputConnection(shrinker.GetOutputPort())
        last_connection = gaussian

    iso_value = tissue['value']
    if flying_edges:
        iso_surface = vtkFlyingEdges3D()
        iso_surface.SetInputConnection(last_connection.GetOutputPort())
        iso_surface.ComputeScalarsOff()
        iso_surface.ComputeGradientsOff()
        iso_surface.ComputeNormalsOff()
        iso_surface.SetValue(0, iso_value)
        iso_surface.Update()
    else:
        iso_surface = vtkMarchingCubes()
        iso_surface.SetInputConnection(last_connection.GetOutputPort())
        iso_surface.ComputeScalarsOff()
        iso_surface.ComputeGradientsOff()
        iso_surface.ComputeNormalsOff()
        iso_surface.SetValue(0, iso_value)
        iso_surface.Update()

    transform = so.get(tissue['slice_order'])
    tf = vtkTransformPolyDataFilter()
    tf.SetTransform(transform)
    tf.SetInputConnection(iso_surface.GetOutputPort())
    last_connection = tf

    if decimate:
        decimator = vtkDecimatePro()
        decimator.SetInputConnection(last_connection.GetOutputPort())
        decimator.SetFeatureAngle(tissue['decimate_angle'])
        decimator.PreserveTopologyOn()
        decimator.SetErrorIsAbsolute(1)
        decimator.SetAbsoluteError(tissue['decimate_error'])
        decimator.SetTargetReduction(tissue['decimate_reduction'])
        last_connection = decimator

    smooth_iterations = tissue['smooth_iterations']
    if smooth_iterations != 0:
        smoother = vtkWindowedSincPolyDataFilter()
        smoother.SetInputConnection(last_connection.GetOutputPort())
        smoother.BoundarySmoothingOff()
        smoother.FeatureEdgeSmoothingOff()
        smoother.SetFeatureAngle(tissue['smooth_angle'])
        smoother.SetPassBand(tissue['smooth_factor'])
        smoother.NonManifoldSmoothingOn()
        smoother.NormalizeCoordinatesOff()
        last_connection = smoother

    normals = vtkPolyDataNormals()
    normals.SetInputConnection(last_connection.GetOutputPort())
    normals.SetFeatureAngle(tissue['feature_angle'])

    stripper = vtkStripper()
    stripper.SetInputConnection(normals.GetOutputPort())

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(stripper.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetOpacity(tissue['opacity'])
    actor.GetProperty().SetDiffuseColor(lut.GetTableValue(tissue['tissue'])[:3])
    actor.GetProperty().SetSpecular(0.5)
    actor.GetProperty().SetSpecularPower(10)

    return actor


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
        # xyz_labels = ['L', 'S', 'A']
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


if __name__ == '__main__':
    import sys

    data_folder, view, selected_tissues, use_flying_edges, use_decimate = get_program_parameters(sys.argv)
    main(data_folder, view, selected_tissues, use_flying_edges, use_decimate)
