#!/usr/bin/env python3

import json
import sys
from pathlib import Path

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkElevationFilter
from vtkmodules.vtkFiltersSources import vtkConeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer
)
from vtkmodules.vtkRenderingCore import (
    vtkDiscretizableColorTransferFunction
)


def get_program_parameters(argv):
    import argparse
    description = 'Take a JSON description of a colormap and convert it to a VTK colormap.'
    epilogue = '''
    A color transfer function in C++ or Python can be optionally generated.
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('file_name', help='The path to the JSONL file e.g Fast.xml.')
    parser.add_argument('-d', action='store_true', dest='discretize', help='Discretize the colormap.')
    parser.add_argument('-n', dest='name', default=None, type=str,
                        help='Specify the name of the colormap,'
                             ' needed if there is more than one colormap in the JSON file.')
    parser.add_argument('-s', dest='size', default=None, type=int,
                        help='Specify the size of the colormap.')
    parser.add_argument('-g', dest='generate_function', default=None,
                        help='Generate code for the color transfer function,'
                             ' specify the desired language one of: Cxx, Python.')

    args = parser.parse_args()
    return args.file_name, args.discretize, args.name, args.size, args.generate_function


def main(file_name, discretize, colormap_name, table_size, generate_function):
    if file_name:
        fn_path = Path(file_name)
        if not fn_path.suffix:
            fn_path = fn_path.with_suffix(".json")
        if not fn_path.is_file():
            print('Unable to find: ', fn_path)
            return
    else:
        print('Please enter a path to the JSON file.')
        return
    parameters = parse_json(fn_path)
    if len(parameters) == 0:
        print('No named colormaps found.')
        return
    if len(parameters) == 1:
        colormap_name = list(parameters.keys())[0]
    else:
        names = list(parameters.keys())
        if len(parameters) > 1 and colormap_name is None:
            print(f'A colormap name is required, choose one of:\n{layout(sorted(names), order="row")}')
            return
        if colormap_name not in names:
            print(f'Unknown colormap name {colormap_name}, choose one of:\n{layout(sorted(names), order="row")}')
            return

    if generate_function is not None:
        generate_function = generate_function.lower()
        available_languages = {k.lower(): k for k in ['Cxx', 'Python']}
        available_languages.update({'cpp': 'Cxx', 'c++': 'Cxx', 'py': 'Python'})
        if generate_function not in available_languages:
            print(f'The language: {generate_function} is not available.')
            tmp = ', '.join(sorted([lang for lang in set(available_languages.values())]))
            print(f'Choose one of these: {tmp}.')
            return
        else:
            language = available_languages[generate_function]
    else:
        language = None

    ctf = make_ctf(parameters[colormap_name], discretize, table_size)

    # Generate code for Python or C++ if needed.
    if language is not None and language in ['Cxx', 'Python']:
        if language == 'Python':
            generate_ctf_python(parameters[colormap_name], discretize, table_size)
        else:
            generate_ctf_cpp(parameters[colormap_name], discretize, table_size)

    colors = vtkNamedColors()
    colors.SetColor('ParaViewBkg', 82, 87, 110, 255)

    sphere = vtkSphereSource()
    sphere.SetThetaResolution(64)
    sphere.SetPhiResolution(32)
    sphere.SetRadius(0.5)
    sphere.Update()

    cone = vtkConeSource()
    cone.SetResolution(6)
    cone.SetDirection(0, 1, 0)
    cone.SetHeight(1)
    cone.Update()

    # bounds = sphere.GetOutput().GetBounds()
    bounds = cone.GetOutput().GetBounds()

    elevation_filter = vtkElevationFilter()
    elevation_filter.SetLowPoint(0, bounds[2], 0)
    elevation_filter.SetHighPoint(0, bounds[3], 0)
    # elevation_filter.SetInputConnection(sphere.GetOutputPort())
    elevation_filter.SetInputConnection(cone.GetOutputPort())

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(elevation_filter.GetOutputPort())
    mapper.SetLookupTable(ctf)
    mapper.SetColorModeToMapScalars()
    mapper.InterpolateScalarsBeforeMappingOn()

    actor = vtkActor()
    actor.SetMapper(mapper)

    # Visualize
    ren = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(ren)
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    ren.AddActor(actor)
    ren.SetBackground(colors.GetColor3d('ParaViewBkg'))

    ren_win.SetSize(640, 480)
    ren_win.SetWindowName('ColorMapToLUT_JSON')

    ren_win.Render()
    iren.Start()


def parse_json(fn_path):
    """
    Parse the exported ParaView JSON file of a colormap.
    :param fn_path: The path to the JSON file.
    :return: A dict of colormaps indexed by name.
    """
    with open(fn_path) as data_file:
        json_data = json.load(data_file)

    def extract(d):
        """
        Pull out the data we need.

        :param d: The parsed JSON data.
        :return: The extracted data.
        """
        data_values = list()
        color_values = list()
        opacity_values = list()
        color_map_details = dict()
        nan = None
        above = None
        below = None
        for k, v in d.items():
            if 'Points' in k:
                n = 4
                data_color = [v[i * n:(i + 1) * n] for i in range((len(v) + n - 1) // n)]
                for dc in data_color:
                    if len(dc) == 4:
                        data_values.append(dc[0])
                        color_values.append(tuple(dc[1:]))
                if 'hsv' in k.lower():
                    color_map_details['space'] = 'hsv'
                else:
                    color_map_details['space'] = 'rgb'

            if k == 'ColorSpace':
                color_map_details['interpolationspace'] = v
            if k == 'Creator':
                color_map_details['creator'] = v
            if k == 'Name':
                color_map_details['name'] = v
            if k == 'NanColor':
                nan = tuple(v[0:3])
        return {'color_map_details': color_map_details, 'data_values': data_values,
                'color_values': color_values, 'opacity_values': opacity_values, 'NaN': nan, 'Above': above,
                'Below': below}

    res = dict()
    for jd in json_data:
        if 'ColorSpace' in jd:
            parameters = extract(jd)
            parameters['path'] = fn_path.name
            cm_name = parameters['color_map_details']['name']
            # Do some checks.
            if cm_name is not None:
                if len(parameters['data_values']) != len(parameters['color_values']):
                    sys.exit(f'{parameters["path"]}: The data values length must be the same as colors.')
                if len(parameters['opacity_values']) > 0:
                    if len(parameters['opacity_values']) != len(parameters['color_values']):
                        sys.exit(f'{parameters["path"]}: The opacity values length must be the same as colors.')
                res[cm_name] = parameters
    return res


def layout(targets, columns=None, width=120, order='column'):
    """
    Layout a sorted list of targets into columns.

    :param targets: A list of targets.
    :param columns: The number of columns, if None, then the width is used.
    :param width: Width of the page, used if the number of columns is zero or None.
    :param order: Ordering either by row or column (default).
    :return A list of lists of available targets.
    """

    order = order.lower()
    if order not in ['row', 'column']:
        print('The order must be either row or column, row is the default.')
        return

    def fmt_v(v):
        return f'{v:<{max_len}s}'

    max_len = max(map(len, targets))
    # Split into rows.
    if columns:
        number_of_columns = columns
    else:
        number_of_columns = width // max_len
    step_size = divmod(len(targets), number_of_columns)
    step = step_size[0]
    if step_size[1] != 0:
        step += 1
    if order == 'row':
        rows = [targets[i:i + number_of_columns] for i in range(0, len(targets), number_of_columns)]
    else:
        rows = list()
        for i in range(step):
            row = list()
            for j in range(number_of_columns):
                idx = j * step + i
                if idx < len(targets):
                    row.append(targets[idx])
            rows.append(row)
    res = list()
    for row in rows:
        res.append(' '.join(map(fmt_v, row)))
    return '\n'.join(res)


def make_ctf(parameters, discretize, table_size=None):
    """
    Generate the discretizable color transfer function
    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """

    ctf = vtkDiscretizableColorTransferFunction()

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            ctf.SetColorSpaceToHSV()
        elif interp_space == 'lab':
            ctf.SetColorSpaceToLab()
        elif interp_space == 'cielab':
            ctf.SetColorSpaceToLab()
        elif interp_space == 'ciede2000':
            ctf.SetColorSpaceToLabCIEDE2000()
        elif interp_space == 'diverging':
            ctf.SetColorSpaceToDiverging()
        elif interp_space == 'step':
            ctf.SetColorSpaceToStep()
        else:
            ctf.SetColorSpaceToRGB()
    else:
        ctf.SetColorSpaceToRGB()

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            ctf.SetScaleToLog10()
        else:
            ctf.SetScaleToLinear()
    else:
        ctf.SetScaleToLinear()

    if parameters['NaN'] is not None:
        ctf.SetNanColor(*parameters['NaN'])

    if parameters['Above'] is not None:
        ctf.SetAboveRangeColor(*parameters['Above'])
        ctf.UseAboveRangeColorOn()

    if parameters['Below'] is not None:
        ctf.SetBelowRangeColor(*parameters['Below'])
        ctf.UseBelowRangeColorOn()

    space = parameters['color_map_details']['space'].lower()
    ctf_sz = len(parameters["data_values"])
    for i in range(0, ctf_sz):
        idx = parameters['data_values'][i]
        rgb = parameters['color_values'][i]
        if space == 'hsv':
            ctf.AddHSVPoint(idx, *rgb)
        else:
            ctf.AddRGBPoint(idx, *rgb)

    if table_size is not None:
        ctf.SetNumberOfValues(max(table_size, ctf_sz))
    else:
        ctf.SetNumberOfValues(ctf_sz)

    if discretize:
        ctf.DiscretizeOn()
    else:
        ctf.DiscretizeOff()

    return ctf


def generate_ctf_python(parameters, discretize, table_size=None):
    """
    Generate a function for the ctf.

    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """
    indent = ' ' * 4

    comment = f'{indent}#'
    if 'name' in parameters['color_map_details']:
        comment += f' name: {parameters["color_map_details"]["name"]},'
    if 'creator' in parameters['color_map_details']:
        comment += f' creator: {parameters["color_map_details"]["creator"]}'
    if 'interpolationspace' in parameters['color_map_details']:
        comment += f'\n{indent}# interpolationspace: {parameters["color_map_details"]["interpolationspace"]},'
    if 'interpolationtype' in parameters['color_map_details']:
        comment += f' interpolationtype: {parameters["color_map_details"]["interpolationtype"]},'
    if 'space' in parameters['color_map_details']:
        comment += f' space: {parameters["color_map_details"]["space"]}'
    comment += f'\n{indent}# file name: {parameters["path"]}\n'

    s = ['', f'def get_ctf():', comment, f'{indent}ctf = vtkDiscretizableColorTransferFunction()', '']

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            s.append(f'{indent}ctf.SetColorSpaceToHSV()')
        elif interp_space == 'lab':
            s.append(f'{indent}ctf.SetColorSpaceToLab()')
        elif interp_space == 'cielab':
            s.append(f'{indent}ctf.SetColorSpaceToLab()')
        elif interp_space == 'ciede2000':
            s.append(f'{indent}ctf.SetColorSpaceToLabCIEDE2000()')
        elif interp_space == 'diverging':
            s.append(f'{indent}ctf.SetColorSpaceToDiverging()')
        elif interp_space == 'step':
            s.append(f'{indent}ctf.SetColorSpaceToStep()')
        else:
            s.append(f'{indent}ctf.SetColorSpaceToRGB()')
    else:
        s.append(f'{indent}ctf.SetColorSpaceToRGB()')

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            s.append(f'{indent}ctf.SetScaleToLog10()')
        else:
            s.append(f'{indent}ctf.SetScaleToLinear()')
    else:
        s.append(f'{indent}ctf.SetScaleToLinear()')
    s.append('')

    if parameters['NaN'] is not None:
        color = ', '.join(list(map(str, parameters['NaN'])))
        s.append(f'{indent}ctf.SetNanColor({color})')

    if parameters['Above'] is not None:
        color = ', '.join(list(map(str, parameters['Above'])))
        s.append(f'{indent}ctf.SetAboveRangeColor({color})')
        s.append(f'{indent}ctf.UseAboveRangeColorOn()')

    if parameters['Below'] is not None:
        color = ', '.join(list(map(str, parameters['Below'])))
        s.append(f'{indent}ctf.SetBelowRangeColor({color})')
        s.append(f'{indent}ctf.UseBelowRangeColorOn()')
    s.append('')

    space = parameters['color_map_details']['space'].lower()
    ctf_sz = len(parameters["data_values"])
    for i in range(0, ctf_sz):
        rgb = ', '.join(list(map(str, parameters['color_values'][i])))
        idx = parameters['data_values'][i]
        if space == 'hsv':
            s.append(f'{indent}ctf.AddHSVPoint({idx}, {rgb})')
        else:
            s.append(f'{indent}ctf.AddRGBPoint({idx}, {rgb})')
    s.append('')

    if table_size is not None:
        s.append(f'{indent}ctf.SetNumberOfValues({max(table_size, ctf_sz)})')
    else:
        s.append(f'{indent}ctf.SetNumberOfValues({ctf_sz})')

    if discretize:
        s.append(f'{indent}ctf.DiscretizeOn()')
    else:
        s.append(f'{indent}ctf.DiscretizeOff()')
    s.append('')

    s.append(f'{indent}return ctf')
    s.append('')

    print('\n'.join(s))


def generate_ctf_cpp(parameters, discretize, table_size=None):
    """
    Generate a function for the ctf.

    :param parameters: The parameters.
    :param discretize: True if the values are to be mapped after discretization.
    :param table_size: The table size.
    :return: The discretizable color transfer function.
    """
    indent = ' ' * 2

    comment = f'{indent}//'
    if 'name' in parameters['color_map_details']:
        comment += f' name: {parameters["color_map_details"]["name"]},'
    if 'creator' in parameters['color_map_details']:
        comment += f' creator: {parameters["color_map_details"]["creator"]}'
    if 'interpolationspace' in parameters['color_map_details']:
        comment += f'\n{indent}// interpolationspace: {parameters["color_map_details"]["interpolationspace"]},'
    if 'interpolationtype' in parameters['color_map_details']:
        comment += f' interpolationtype: {parameters["color_map_details"]["interpolationtype"]},'
    if 'space' in parameters['color_map_details']:
        comment += f' space: {parameters["color_map_details"]["space"]}'
    comment += f'\n{indent}// file name: {parameters["path"]}\n'

    s = ['', f'vtkNew<vtkDiscretizableColorTransferFunction> GetCTF()', '{', comment,
         f'{indent}vtkNew<vtkDiscretizableColorTransferFunction> ctf;', '']

    interp_space = parameters['color_map_details'].get('interpolationspace', None)
    if interp_space:
        interp_space = interp_space.lower()
        if interp_space == 'hsv':
            s.append(f'{indent}ctf->SetColorSpaceToHSV();')
        elif interp_space == 'lab':
            s.append(f'{indent}ctf->SetColorSpaceToLab();')
        elif interp_space == 'cielab':
            s.append(f'{indent}ctf->SetColorSpaceToLab();')
        elif interp_space == 'ciede2000':
            s.append(f'{indent}ctf->SetColorSpaceToLabCIEDE2000();')
        elif interp_space == 'diverging':
            s.append(f'{indent}ctf->SetColorSpaceToDiverging();')
        elif interp_space == 'step':
            s.append(f'{indent}ctf->SetColorSpaceToStep();')
        else:
            s.append(f'{indent}ctf->SetColorSpaceToRGB();')
    else:
        s.append(f'{indent}ctf->SetColorSpaceToRGB();')

    scale = parameters['color_map_details'].get('interpolationtype', None)
    if scale:
        scale = scale.lower()
        if scale == 'log10':
            s.append(f'{indent}ctf->SetScaleToLog10();')
        else:
            s.append(f'{indent}ctf->SetScaleToLinear();')
    else:
        s.append(f'{indent}ctf->SetScaleToLinear();')
    s.append('')

    if parameters['NaN'] is not None:
        color = ', '.join(list(map(str, parameters['NaN'])))
        s.append(f'{indent}ctf->SetNanColor({color});')

    if parameters['Above'] is not None:
        color = ', '.join(list(map(str, parameters['Above'])))
        s.append(f'{indent}ctf->SetAboveRangeColor({color});')
        s.append(f'{indent}ctf->UseAboveRangeColorOn();')

    if parameters['Below'] is not None:
        color = ', '.join(list(map(str, parameters['Below'])))
        s.append(f'{indent}ctf->SetBelowRangeColor({color});')
        s.append(f'{indent}ctf->UseBelowRangeColorOn();')
    s.append('')

    space = parameters['color_map_details']['space'].lower()
    ctf_sz = len(parameters["data_values"])
    for i in range(0, ctf_sz):
        rgb = ', '.join(list(map(str, parameters['color_values'][i])))
        idx = parameters['data_values'][i]
        if space == 'hsv':
            s.append(f'{indent}ctf->AddHSVPoint({idx}, {rgb});')
        else:
            s.append(f'{indent}ctf->AddRGBPoint({idx}, {rgb});')
    s.append('')

    if table_size is not None:
        s.append(f'{indent}ctf->SetNumberOfValues({max(table_size, ctf_sz)});')
    else:
        s.append(f'{indent}ctf->SetNumberOfValues({ctf_sz});')

    if discretize:
        s.append(f'{indent}ctf->DiscretizeOn();')
    else:
        s.append(f'{indent}ctf->DiscretizeOff();')
    s.append('')

    s.append(f'{indent}return ctf;')
    s.append('}')
    s.append('')

    print('\n'.join(s))


if __name__ == '__main__':
    file, discretise, name, size, generate = get_program_parameters(sys.argv)
    main(file, discretise, name, size, generate)
