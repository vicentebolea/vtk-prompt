### Description

This example loads a CSV file, edits it and visualises the result.

It demonstrates the use of [pandas](https://pandas.pydata.org/) to read and edit the CSV input file, then use [numpy](https://numpy.org/) and the vtk-numpy interface for building the resultant vtkPolyData object based on the options selected.

The key thing about `pandas` is it can read/write data in various formats: CSV and text files, Microsoft Excel, SQL databases, and the fast HDF5 format. It is highly optimized for performance and the DataFrame object allows for extensive row/column manipulation. So we can edit the data, creating new columns, and, finally, select only relevant columns for further analysis by VTK.

In this case we select columns using numpy to create the three-dimensional point data array data. The numpy objects are then converted to vtk data structures and integrated into a vtkPolyData object.

The process is this:

``` text
CSV->pandas(read/edit/select)->numpy->numpy_to_vtk->vtkPolyData
```

Note how easy it is the get the three-dimensional coordinates using numpy.

The files used to generate the example are:

``` text
<DATA>/LakeGininderra.csv
<DATA>/LakeGininderra.kmz
```

Where:

- `<DATA>` is the path to `?vtk-?examples/src/Testing/Data`
- `LakeGininderra.csv` is the CSV file used by this program.
- `LakeGininderra.kmz` can be loaded into Google Earth to display the track.

The parameters for typical usage are something like this:

``` text
<DATA>/LakeGininderra.csv -u -c -pResults
```

<figure>
  <img style="float:middle" src="https://raw.githubusercontent.com/Kitware/vtk-examples/gh-pages/src/SupplementaryData/Python/IO/LakeGininderra.jpg">
  <figcaption>A Google Earth image of the track.</figcaption>
</figure>

Further information:

- [Easy Data Conversion to VTK with Python](https://www.kitware.com/easy-data-conversion-to-vtk-with-python/).
- [Installing pandas](https://pandas.pydata.org/docs/getting_started/install.html).
- [VTK Examples - New CSV Examples](https://discourse.vtk.org/t/vtk-examples-new-csv-examples/11632)
