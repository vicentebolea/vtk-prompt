### Description

This example loads a CSV file, edits it and visualises the result.

It demonstrates the use of [pandas](https://pandas.pydata.org/) to read and edit the CSV input file, then create a temporary file containing the desired columns. This temporary file is subsequently read and parsed using vtkDelimitedTextReader.

The key thing about `pandas` is it can read/write data in various formats: CSV and text files, Microsoft Excel, SQL databases, and the fast HDF5 format. It is highly optimized for performance and the DataFrame object allows for extensive row/column manipulation. So we can edit the data, creating new columns, and, finally, select only relevant columns for further analysis by VTK.

In this case we create a temporary CSV file of selected columns and read this with vtkDelimitedTextReader.

The process is this:

``` text
CSV->pandas(read/edit/select)->CSV->vtkDelimitedTextReader->vtkPolyData
```

By going down this route we don't overload the delimited text reader with the effort of processing any unneeded columns of data.

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
<DATA>/LakeGininderra.csv -e -c -pResults
```

<figure>
  <img style="float:middle" src="https://raw.githubusercontent.com/Kitware/vtk-examples/gh-pages/src/SupplementaryData/Python/IO/LakeGininderra.jpg">
  <figcaption>A Google Earth image of the track.</figcaption>
</figure>

Further information:

- [Easy Data Conversion to VTK with Python](https://www.kitware.com/easy-data-conversion-to-vtk-with-python/).
- [Installing pandas](https://pandas.pydata.org/docs/getting_started/install.html).
- [VTK Examples - New CSV Examples](https://discourse.vtk.org/t/vtk-examples-new-csv-examples/11632)
