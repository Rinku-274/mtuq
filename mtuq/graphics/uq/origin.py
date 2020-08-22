
#
# graphics/uq/origin.py - uncertainty quantification of source origin
#

import numpy as np
import subprocess

from matplotlib import pyplot
from pandas import DataFrame
from xarray import DataArray
from mtuq.graphics._gmt import exists_gmt, gmt_not_found_warning,\
    _parse_filetype, _parse_title
from mtuq.grid_search import MTUQDataArray, MTUQDataFrame
from mtuq.util import fullpath, warn
from mtuq.util.math import closed_interval, open_interval


def plot_misfit_xy(filename, ds, origins, sources, title='', labeltype='latlot',
    add_colorbar=False, add_marker=True):
    """ Plots misfit versus depth


    .. rubric :: Input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    data structure containing moment tensors and corresponding misfit values

    ``title`` (`str`):
    Optional figure title


    .. rubric :: Usage

    Moment tensors and corresponding misfit values must be given in the format
    returned by `mtuq.grid_search` (in other words, as a `DataArray` or 
    `DataFrame`.)

    """
    x, y = _get_xy(origins)

    _check(ds)
    ds = ds.copy()


    if issubclass(type(ds), DataArray):
        values, indices = _min_dataarray(ds)
        best_sources = _get_sources(sources, indices)


    elif issubclass(type(ds), DataFrame):
        values, indices = _min_dataframe(ds)
        best_sources = _get_sources(sources, indices)


    _plot_xy(filename, x, y, values, title, labeltype)

    try:
        _plot_xy_mt_gmt(filename, x, y, best_sources, labeltype)
    except:
        warn('_plot_xy_mt_gmt failed')
        _plot_xy_mt_gmt(filename+'_mt', x, y, best_sources, labeltype) # debugging- get traceback



def plot_misfit_depth(filename, ds, origins, sources, title=''):
    """ Plots misfit versus depth


    .. rubric :: Input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    data structure containing moment tensors and corresponding misfit values

    ``title`` (`str`):
    Optional figure title


    .. rubric :: Usage

    Moment tensors and corresponding misfit values must be given in the format
    returned by `mtuq.grid_search` (in other words, as a `DataArray` or 
    `DataFrame`.)

    """
    depths = _get_depths(origins)

    _check(ds)
    ds = ds.copy()


    if issubclass(type(ds), DataArray):
        values, indices = _min_dataarray(ds)
        best_sources = _get_sources(sources, indices)


    elif issubclass(type(ds), DataFrame):
        values, indices = _min_dataframe(ds)
        best_sources = _get_sources(sources, indices)


    _plot_depth(filename, depths, values, indices,
        title, xlabel='auto', ylabel='Misfit')



def plot_likelihood_depth(filename, ds, origins, sources, sigma=None, title=''):
    """ Plots marginal likelihood versus depth


    .. rubric :: Input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    data structure containing moment tensors and corresponding misfit values

    ``title`` (`str`):
    Optional figure title


    .. rubric :: Usage

    Moment tensors and corresponding misfit values must be given in the format
    returned by `mtuq.grid_search` (in other words, as a `DataArray` or 
    `DataFrame`.)

    """
    assert sigma is not None

    depths = _get_depths(origins)

    _check(ds)
    ds = ds.copy()


    if issubclass(type(ds), DataArray):
        ds.values = np.exp(-ds.values/(2.*sigma**2))
        ds.values /= ds.values.sum()

        values, indices = _min_dataarray(ds)
        best_sources = _get_sources(sources, indices)


    elif issubclass(type(ds), DataFrame):
        ds = np.exp(-ds/(2.*sigma**2))
        ds /= ds.sum()

        values, indices = _min_dataframe(ds)
        best_sources = _get_sources(sources, indices)

    values /= values.sum()

    _plot_depth(filename, depths, values, indices, 
        title=title, xlabel='auto', ylabel='Likelihood')



def plot_marginal_depth(filename, ds, origins, sources, sigma=None, title=''):
    """ Plots marginal likelihoods on `v-w` rectangle


    .. rubric :: Input arguments

    ``filename`` (`str`):
    Name of output image file

    ``ds`` (`DataArray` or `DataFrame`):
    data structure containing moment tensors and corresponding misfit values

    ``title`` (`str`):
    Optional figure title


    .. rubric :: Usage

    Moment tensors and corresponding misfit values must be given in the format
    returned by `mtuq.grid_search` (in other words, as a `DataArray` or 
    `DataFrame`.)


    """
    assert sigma is not None

    depths = _get_depths(origins)

    _check(ds)
    ds = ds.copy()


    if issubclass(type(ds), DataArray):
        ds = np.exp(-ds/(2.*sigma**2))
        ds /= ds.sum()

        values, indices = _max_dataarray(ds)
        best_sources = _get_sources(sources, indices)

    elif issubclass(type(ds), DataFrame):
        raise NotImplementedError
        ds = np.exp(-ds/(2.*sigma**2))
        ds /= ds.sum()

        values, indices = _min_dataframe(ds)
        best_sources = _get_sources(sources, indices)

    values /= values.sum()

    _plot_depth(filename, depths, values, indices, 
        title=title, xlabel='auto', ylabel='Likelihood')



#
# utility functions
#

def _check(ds):
    """ Checks data structures
    """
    if type(ds) not in (DataArray, DataFrame, MTUQDataArray, MTUQDataFrame):
        raise TypeError("Unexpected grid format")


def _get_depths(origins):
    depths = []
    for origin in origins:
        depths += [float(origin.depth_in_m)]
    return np.array(depths)


def _get_xy(origins):
    x, y = [], []
    for origin in origins:
        x += [float(origin.offset_x_in_m)]
        y += [float(origin.offset_y_in_m)]
    return np.array(x), np.array(y)


def _get_sources(sources, indices):
    return [sources.get(index) for index in indices]


def _min_dataarray(ds):
    values, indices = [], []
    for _i in range(ds.shape[-1]):
        sliced = ds[:,:,:,:,:,:,_i]
        values += [sliced.min()]
        indices += [int(sliced.argmin())]
    return np.array(values), indices


def _max_dataarray(ds):
    values, indices = [], []
    for _i in range(ds.shape[-1]):
        sliced = ds[:,:,:,:,:,:,_i]
        values += [sliced.max()]
        indices += [int(sliced.argmax())]
    return np.array(values), indices


def _sum_dataarray(ds):
    raise NotImplementedError

def _min_dataframe(ds):
    raise NotImplementedError

def _max_dataframe(ds):
    raise NotImplementedError

def _sum_dataframe(ds):
    raise NotImplementedError


#
# pyplot wrappers
#

def _plot_depth(filename, depths, values, best_sources, title='',
    xlabel='auto', ylabel='', show_magnitudes=False, show_beachballs=False):

    if xlabel=='auto' and ((depths.max()-depths.min()) < 10000.):
       xlabel = 'Depth (m)'

    if xlabel=='auto' and ((depths.max()-depths.min()) >= 10000.):
       depths /= 1000.
       xlabel = 'Depth (km)'

    figsize = (6., 4.)
    pyplot.figure(figsize=figsize)

    pyplot.plot(depths, values, 'k-')

    if show_magnitudes:
        raise NotImplementedError

    if show_beachballs:
        raise NotImplementedError

    if xlabel:
         pyplot.xlabel(xlabel)

    if ylabel:
         pyplot.ylabel(ylabel)

    if title:
        pyplot.title(title)

    pyplot.savefig(filename)


def _plot_xy(filename, x, y, values, title='', labeltype='latlot',
    add_colorbar=False, add_marker=True, cmap='hot'):

    xlabel, ylabel = _get_labeltype(x, y, labeltype)

    assert len(x)==len(y)==len(values), ValueError

    ux = np.unique(x)
    uy = np.unique(y)
    if len(ux)*len(uy)!=len(values):
        warn('Irregular x-y misfit grid')

    figsize = (6., 6.)
    pyplot.figure(figsize=figsize)

    pyplot.tricontourf(x, y, values, 100, cmap=cmap)

    if add_marker:
        idx = values.argmin()
        coords = x[idx], y[idx]

        pyplot.scatter(*coords, s=250,
            marker='o',
            facecolors='none',
            edgecolors=[0,1,0],
            linewidths=1.75,
            )

    if xlabel:
         pyplot.xlabel(xlabel)

    if ylabel:
         pyplot.ylabel(ylabel)

    if title:
        pyplot.title(title)

    pyplot.gca().axis('square')

    pyplot.savefig(filename)


#
# gmt wrappers
#

def _plot_xy_mt_gmt(filename, x, y, sources, title='',
    labeltype='latlon', show_magnitudes=False, show_beachballs=True):

    filetype = _parse_filetype(filename)
    title, subtitle = _parse_title(title)
    xlabel, ylabel = _get_labeltype(x, y, labeltype)

    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()


    assert len(x)==len(y)==len(sources), ValueError

    ux = np.unique(x)
    uy = np.unique(y)
    if len(ux)*len(uy)!=len(sources):
        warn('Irregular x-y grid')

    mw_array = None
    if show_magnitudes:
        mw_array = np.zeros((len(sources), 3))
        for _i, source in enumerate(sources):
            mw_array[_i, 0] = x[_i]
            mw_array[_i, 1] = y[_i]
            mw_array = source.magnitude()

    mt_array = None
    if show_beachballs:
        mt_array = np.zeros((len(sources), 9))
        for _i, source in enumerate(sources):
            mt_array[_i, 0] = x[_i]
            mt_array[_i, 1] = y[_i]
            mt_array[_i, 3:] = source.as_vector()

    if mt_array is not None:
        mt_file = 'tmp_mt_'+filename+'.txt'
        np.savetxt(mt_file, mt_array)
    else:
        mt_file = "''"

    if mw_array is not None:
        mw_file = 'tmp_mw_'+filename+'.txt'
        np.savetxt(mw_file, mw_array)
    else:
        mw_file = "''"

    # call bash script
    if exists_gmt():
        subprocess.call("%s %s %s %s %s %s %f %f %f %f %s %s" %
           (fullpath('mtuq/graphics/_gmt/plot_xy_mt'),
            filename,
            filetype,
            mt_file,
            mw_file,
            '0',
            xmin, xmax,
            ymin, ymax,
            title,
            subtitle
            ),
            shell=True)
    else:
        gmt_not_found_warning(
            ascii_data)


def _get_labeltype(x,y,labeltype):
    if labeltype=='latlon':
       xlabel = None
       ylabel = None

    if labeltype=='offset' and ((x.max()-x.min()) >= 10000.):
       x /= 1000.
       y /= 1000.
       xlabel = 'X offset (km)'
       ylabel = 'Y offset (km)'
    elif labeltype=='offset' and ((x.max()-x.min()) < 10000.):
       xlabel = 'X offset (m)'
       ylabel = 'Y offset (m)'

    return xlabel,ylabel

