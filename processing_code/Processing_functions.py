# Packages
import numpy as np
import xarray as xr
import pandas as pd
from scipy import stats
import warnings
warnings.simplefilter('ignore', UserWarning)
warnings.filterwarnings('ignore')
import datetime as dt
from datetime import timedelta
from cartopy.util import add_cyclic_point
from typing import List, Tuple
import pop_tools
from xgcm import Grid

def Wilks_pcrit(pvalues: np.ndarray, siglevel: float) -> float:
    '''
    This function calcules the p-critical level for the Wilks significance test

    INPUT:
    pvalues: array of p-values
    siglevel: significance level (i.e. 0.01 or 1%, 0.05 or 5%, ...)
    
    OUTPUT:
    pcrit: Wilks p-critical value (i.e. any p-value less than this is significant)
    '''

    # Calculate false detection rate
    alpha_fdr = 2*siglevel

    # Flatten p-values into 1D array & sort
    pvalues_fl = pvalues.flatten()
    pvalues_fl = np.sort(pvalues_fl)

    # Generate arrays to calculate differences
    x = np.arange(1,len(pvalues_fl)+1,1)
    x = x.astype(float)
    y = (x/len(x))*alpha_fdr

    # Calculate differences
    d = pvalues_fl-y

    # Grab index of first p-value where p-value > y
    w_out = np.where(d>0.0)
    k = -1 if w_out[0].size == 0 else w_out[0][0]

    # Find p-critical value & return it
    # None of the p-values are significant
    if k == 0:
        pcrit = 0.0
    # All p-values are significant
    elif k == -1:
        pcrit = pvalues_fl[-1]
    # Some p-values are significant
    else:
        pcrit = pvalues_fl[k-1]
        
    return pcrit

def InterPlevels(ds, var):
    '''
    Interpolates 3D from model levels to standard pressure levels
    INPUT:
    ds: xarray DataArray
    var: variable name

    OUTPUT:
    varout: modified xarray DataArray
    '''
    
    # Calculate the pressure at every time, lev, lat, lon
    p = (ds['hyam']*ds['P0'] + ds['hybm']*ds['PS'])/100
    
    # Assign it as a variable in the dataset
    ds = ds.assign({'p': np.log(p)})
    
    # Create an xgcm Grid object with a Z coordinate given by 'lev'
    grid = Grid(ds, coords={'Z': {'center': 'lev'}}, periodic=False)
    
    # Give the array of pressures to interpolate to
    p_target = np.array([10., 20., 30., 50., 70., 100., 150., 200., 250.,
                         300., 400., 500., 600., 650., 700., 750., 800., 850.,
                         900., 925., 950., 1000.])
    
    # Use the transform method to interpolate to constant pressure given the target pressures above
    # The target_data parameter tells it what variable to use to base the transformation on. 
    # In our case, we're using the model pressure at every point calculated above
    varout = grid.transform(ds[var], 'Z', np.log(p_target), target_data=ds.p)
    
    # Rename the new dimension and assign the coordinate as the target pressures above
    varout = varout.rename({'p': 'plev'})
    varout = varout.assign_coords({'plev': p_target})
    
    return varout.squeeze()

def AddCyclic(da: xr.DataArray) -> xr.DataArray:
    # Add cyclic point
    cyclic_data, cyclic_lon = add_cyclic_point(da.data, coord=da['lon'])
    cyclic_coords = {dim: da.coords[dim] for dim in da.dims}
    cyclic_coords['lon'] = cyclic_lon

    da = xr.DataArray(cyclic_data, dims=da.dims, coords=cyclic_coords, attrs=da.attrs, name=da.name)
    return da

def FixLongitude(da: xr.DataArray, add_cyclic: bool) -> xr.DataArray:
    '''
    Fixes CESM longitude 
    INPUT:
    da: xarray DataArray

    OUTPUT:
    da: modified xarray DataArray
    '''
    # Switch longitude from 0-360 to -180-180
    da = da.assign_coords(dict(lon=(((da.lon+180) % 360)-180)))

    # Sort longitude to fix plotting problems
    da = da.sortby('lon','ascending')

    if add_cyclic:
         da = AddCyclic(da)
    
    return da

def FixGrid(da: xr.DataArray, grid: str) -> xr.DataArray:
    '''
    Transforms CICE grid into lat/lon (0-360)
    INPUT:
    da: xarray DataArray

    OUTPUT:
    da: modified xarray DataArray
    '''

    # Get CICE grid from pop_tools
    grid = pop_tools.get_grid('POP_'+grid)

    # Change tarea to m2 instead of km2
    with xr.set_options(keep_attrs=True):
        grid['TAREA'] = grid['TAREA']/(1e4)
    grid['TAREA'].attrs['units'] = 'm^2'

    # Add lat, lon, and tarea coordinates
    da.coords['lat'] = (('nj','ni'),grid['TLAT'].values)
    da.coords['lon'] = (('nj','ni'),grid['TLONG'].values)
    da.coords['tarea'] = (('nj','ni'),grid['TAREA'].values)

    return da

    

def FixTime(da: xr.DataArray) -> xr.DataArray:
    '''
    Fixes CESM time coordinate for monthly data
    INPUT:
    da: xarray DataArray

    OUTPUT:
    da: modified xarray DataArray
    '''

    # Subtract 15 days to fix monthly timestamp
    da = da.assign_coords(dict(time=(da.time-timedelta(days=15))))

    return da

def CalcStatforDim(da: xr.DataArray, grpdim: str, dims: str|List[str]) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    '''
    Calculates mean, standard deviation, n for the DataArray over dimension(s)
    INPUT: 
    da: xarray DataArray
    dims: list of dimension(s)

    OUTPUT:
    da_avg: DataArray mean over dimension(s) 
    da_std: DataArray standard deviation over dimension(s)
    da_n: DataArray count over dimension(s)
    '''
    # Check if lat is one of average dimensions
    if 'lat' in dims:
        weights = np.cos(np.deg2rad(da.lat))
        da = da.weighted(weights)

    if grpdim == '':
        da_avg = da.mean(dims, skipna=True)
        da_std = da.std(dims, skipna=True, ddof=1)
        da_n = da.count(dims)
    else:
        # Calculate statistics over dimension(s)
        da_avg = da.groupby(grpdim).mean(dims, skipna=True)
        da_std = da.groupby(grpdim).std(dims, skipna=True, ddof=1)
        da_n = da.groupby(grpdim).count(dims)

    da_avg.compute()
    da_std.compute()
    da_n.compute()

    return da_avg, da_std, da_n



def CalcStatbyGrpDim(da: xr.DataArray, grpdim1: str, grpdim2: str, concatdim: str, avgdim: str, avgdim2: str|List[str]) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    '''
    Calculates mean, standard deviation, n for the DataArray over dimension(s) by a grouped by dimension
    INPUT: 
    da: xarray DataArray
    grpdim1: dimension to group data by
    grpdim2: second dimension to group data by
    concatdim: dimension to concatenate ungrouped data
    avgdims: dimension(s) to calculate statistics over group of data

    OUTPUT:
    da_avg: DataArray mean over dimension(s) 
    da_std: DataArray standard deviation over dimension(s)
    da_n: DataArray count over dimension(s)
    '''
    # Check if lat is in average dimension
    if 'lat' in avgdim:
        weights = np.cos(np.deg2rad(da.lat))
        da = da.weighted(weights)

    # Group dataArray
    da_grp = da.groupby(grpdim1)

    # Initialize lists
    da_avg_list = []
    lbl_list = []

    
    # Loop over all groups in grouped dataArray
    for sub, dss in da_grp:
        if grpdim2 != '':
            # Calculate mean for group
            dss_avg = dss.groupby(grpdim2).mean(avgdim, skipna=True)
        else:
            dss_avg = dss.mean(avgdim, skipna=True)

        # Add to lists
        da_avg_list.append(dss_avg)
        lbl_list.append(sub)

    # Calculate statistics over group
    da_avg_grp = xr.concat(da_avg_list,pd.Index(lbl_list,name=concatdim))   
    da_avg_grp.compute()
    
    da_avg = da_avg_grp.mean(avgdim2,skipna=True)
    da_std = da_avg_grp.std(avgdim2,skipna=True,ddof=1)
    da_n = da_avg_grp.count(avgdim2)

    da_avg.compute()
    da_std.compute()
    da_n.compute()

    return da_avg, da_std, da_n
    
def Ensemble(da_list, ens_index: pd.Index, return_mean=False, stat='avg') -> xr.DataArray:
    '''
    Takes list of DataArrarys, one for each ensemble member, and turns them into a single DataArray
    with a dimension of 'ensemble_member'. Optionally returns ensemble mean instead. If returning
    ensemble mean, stat is required
    INPUT:
    da_list: list of DataArrays, length is number of ensemble members
    ens_index: pandas Index with name 'ensemble_member'
    return_mean: (optional) boolean for returning ensemble mean. default is False
    stat: (optional) string describing statistic that ensemble mean will be calculated for. default is 'avg'
          must be one of 'avg', 'std', 'n' 

    OUTPUT:
    da_ens: DataArray containing ensemble
    da_ensmean: DataArray containing ensemble mean
    '''
    # Concatenate list with pandas index of ensemble members
    da_ens = xr.concat(da_list, ens_index)

    # Chunk data
    da_ens = da_ens.chunk({'ensemble_member': -1})
    da_ens.compute()

    # If returning ensemble mean
    if return_mean:
        # If statistic is average
        if stat == 'avg':
            da_ensmean = da_ens.mean('ensemble_member', skipna=True)
        
        # Else if statistic is standard deviation
        elif stat == 'std':
            num_em = da_ens.sizes['ensemble_member']
            da_ensmean = np.sqrt((da_ens**2).sum('ensemble_member', skipna=True)/num_em)

        # Else if statistic is count
        elif stat == 'n':
            da_ensmean = da_ens.sum('ensemble_member', skipna=True)
        
        # Else if stat is not the right value
        else:
            raise ValueError('\'stat\' value  must be one of \'avg\', \'std\', \'n\'')
        
        da_ensmean.compute()

        return da_ensmean
    
    # Else only return ensemble
    else:
        return da_ens