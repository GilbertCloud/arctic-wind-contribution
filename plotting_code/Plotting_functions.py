import numpy as np
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as colors
from cartopy.mpl.gridliner import Gridliner
from scipy import stats
import matplotlib.path as mpath
import xarray as xr
from typing import List, Tuple
from matplotlib.colors import Colormap, BoundaryNorm, ListedColormap
from matplotlib.colorbar import Colorbar
from matplotlib.axes import Axes

## Functions for plotting secondary axis with wavenumber/wavelength
def wvn2wvl(x):
    return 10000/x

def wvl2wvn(x):
    return 10000/x

## Functions for plotting secondary axis with height/pressure
H = 8000 # m
p0 = 1013.25 # hPa
def p2z(x):
    return -1*H*np.log(x/p0)

def z2p(x):
    return p0*np.exp(-1*x/H)

def t_test_two_means(m1: float|np.ndarray|xr.DataArray, m2: float|np.ndarray|xr.DataArray,
                     std1: float|np.ndarray|xr.DataArray, std2: float|np.ndarray|xr.DataArray,
                     n1: float|np.ndarray|xr.DataArray, n2: float|np.ndarray|xr.DataArray,
                     test_type: int|float, diff: float|np.ndarray|xr.DataArray) -> np.ndarray:
    '''
    This function calculates the p-values for a small sample test for the difference between two means. 
    Assumes null hypothesis can be:
    • µ1 - µ2 ≤ ∆
    • µ1 - µ2 ≥ ∆
    • µ1 - µ2 = ∆

    INPUT:
    m1: sample 1 mean(s) 
    m2: sample 2 mean(s)
    std1: sample 1 standard deviation(s)
    std2: sample 2 standard deviation(s)
    n1: sample 1 size(s)
    n2: sample 2 size(s)
    test_type: whether the test is one (1) or two tailed (2)
    diff: diff between population means (∆)

    OUTPUT:
    pvalue: p values
    '''

    if (test_type != 1) and (test_type != 2):
        raise ValueError('\'test_type\' value  must be 1 or 2')

    # Calculate t-statistic
    tstat = (m1-m2-diff)/np.sqrt(((std1**2)/n1)+((std2**2)/n2))

    # Calculate degrees of freedom and round down
    df = ((((std1**2)/n1)+((std2**2)/n2))**2)/(((((std1**2)/n1)**2)/(n1-1))+((((std2**2)/n2)**2)/(n2-1)))
    df = np.floor(df)

    # Calculate & return p-value
    pvalue = stats.t.sf(abs(tstat),df=df)*test_type
    return pvalue

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
    k = np.where(d>0)[0][0]

    # Find p-critical value & return it
    pcrit = 0.0 if k == 0 else pvalues_fl[k-1]
    return pcrit

def CustomCmap(levels: List[float]|np.ndarray, colorlist: List|Colormap, extremes: List, list: bool=True) -> Tuple[Colormap, BoundaryNorm]:
    '''
    Creates a custom colormap and normalization from a list of colors or a cmap

    INPUT:
    levels: numpy array of levels for colormap
    colorlist: list of colors (named, 4value, or a mix of the two) or Colormap object. list must be length(levels)-1
    extremes: list of two colors that are the under and over extremes [under, over]
    list: (optional) boolean describes whether colorlist is a list of colors (True) 
          or a colormap object to pull colors from (False). defaults to True

    OUTPUT:
    cmap: custom colormap
    norm: custom normalization
    '''

    # Create custom cmap from list of colors
    if list:
        cmap = (ListedColormap(colorlist).with_extremes(under=extremes[0], over=extremes[-1]))

    # Create custom cmap from linearly spaced list of cmap colors
    else:
        mapped_colors = colorlist(np.linspace(0,1,len(levels)-1))
        cmap = (ListedColormap(mapped_colors).with_extremes(under=colorlist.get_under(), over=colorlist.get_over()))

    # Create custom normalization
    norm = BoundaryNorm(levels, cmap.N)

    return cmap, norm

def draw_circle(ax: Axes, grdln_x_maj: List[float]|np.ndarray=np.arange(-180,181,30), grdln_y_maj: List[float]|np.ndarray=np.arange(-90,91,10),
                draw_circ: bool=True, draw_major: bool=True, draw_major_labels: bool=True, draw_minor: bool=False,
                grdln_x_min: List[float]|np.ndarray=np.arange(-180,181,15), grdln_y_min: List[float]|np.ndarray=np.arange(-90,91,5),
                draw_minor_labels: bool=False) -> None|Gridliner|Tuple[Gridliner,Gridliner]:
    '''
    Draw circle and gridlines on an axis for a polar (Arctic or Antarctic plot)

    INPUT:
    ax: matplotlib axis object to modify
    grdln_x_maj: (optional) longitude major gridline values. defaults to every 30 degrees
    grdln_y_maj: (optional) latitude major gridline values. defaults to every 10 degrees
    draw_circ: (optional) draw circle. defaults to True
    draw_major: (optional) draw major gridlines. defaults to True
    draw_major_labels: (optional) draw labels for major gridlines. defaults to True
    draw_minor: (optional) draw minor gridlines. defaults to False
    grdln_x_min: (optional) longitude minor gridline values. defaults to every 15 degrees
    grdln_y_min: (optional) latitude minor gridline values. defaults to every 5 degrees
    draw_minor_labels: (optional) draw labels for minor gridlines. defaults to False

    OUTPUT: 
    maj_gl: major gridlines object
    min_gl: (optional) minor gridlines object
    '''
    
    if draw_circ:
        # Get unit circle
        circle_path = mpath.Path.unit_circle()
        
        # Get circle path for this axis and set as boundary
        circle_path_ax_0 = mpath.Path(circle_path.vertices.copy()*ax.get_ylim()[1]*0.9, circle_path.codes.copy())
        ax.set_boundary(circle_path_ax_0)

    # Draw major gridlines
    if draw_major:
       maj_gl = ax.gridlines(crs=ccrs.PlateCarree(),zorder=10, # Transform to projection, layer order
                linewidth=0.5,color='#d8dcd6',linestyle='--', # Line width, color, style
                xlocs=grdln_x_maj,ylocs=grdln_y_maj, # x, y label range
                draw_labels=draw_major_labels) # Draw labels 
    
    # Draw minor gridlines
    if draw_minor:
        min_gl = ax.gridlines(crs=ccrs.PlateCarree(),zorder=10, # Transform to projection, layer order
                linewidth=0.5,color='#d8dcd6',linestyle='--', # Line width, color, style
                xlocs=grdln_x_min,ylocs=grdln_y_min, # x, y label range
                draw_labels=draw_minor_labels) # Draw labels
        
    # Return appropriate gridlines
    if draw_major and draw_minor:
        return maj_gl, min_gl
    elif draw_major and ~draw_minor:
        return maj_gl
    elif ~draw_major and draw_minor:
        return min_gl
    else:
        return None
    

# Variables for this function
ens_dict1 = {'Mean': '', 'All_members': 'ensemble_member'}
ens_dict2 = {'Mean': (), 'All_members': ('ensemble_member',)}
time_dict = {0: 'month', 1: 'year', 2: 'season', 3: ''}


def CalcStatSig(control_data_avg: xr.Dataset, control_data_std: xr.Dataset, control_data_n: xr.Dataset, 
                optics_data_avg: xr.Dataset, optics_data_std: xr.Dataset, optics_data_n: xr.Dataset,
                var: str, sig: str, ens_type: str, time_avg: int) -> xr.Dataset:
    '''
    Calculate the p-values and p-critical value (according Wilks) from a t-test between the optics and control averages.
    This function will only do the t-test for a single variable. Assumes alpha = 0.05.

    INPUT:
    control_data_avg: variable average for the control run
    control_data_std: variable standard deviation for the control run
    control_data_n: variable count (n) for the control run
    optics_data_avg: variable average for the optics run
    optics_data_std: variable standard deviation for the optics run
    optics_data_n: variable count (n) for the optics run
    var: variable string
    sig: how to evaluate the significance of p-values using 'Wilks' or 'No_Wilks'. 'No_Wilks' assumes alpha = 0.05.
    ens_type: Whether the data variable is an ensemble mean ('Mean') or all the ensemble members ('All_members')
    time_avg: Integer describing how the data was averaged [by season: 2, by month: 0, entire dataset: 3, by year: 1]

    OUTPUT:
    optics_data_avg: variable average for the optics run with the p-values and p-critical values added as variables
    '''
    # Get appropriate values from ens_dict and time_dict
    e_dim = ens_dict1[ens_type]
    t_dim = time_dict[time_avg]

    # Set up dimensions list for p-critical values
    pcdims = (e_dim,t_dim)

    # Set up dimensions list for p-values
    pdims = ens_dict2[ens_type]+(t_dim,'lat','lon') if time_avg != 3 else ens_dict2[ens_type]+('lat','lon')

    # Set up index list based on ensemble type
    ens_list = np.arange(1) if ens_type == 'Mean' else np.arange(control_data_avg.sizes['ensemble_member'])

    # Set up index list based on time averaging
    time_list = np.arange(1) if time_avg == 3 else np.arange(control_data_avg.sizes[t_dim])

    # If variable is FLUT or FLDS do 1-sided t-test, otherwise 2-sided t-test
    if np.logical_or(var == 'FLDS',var == 'FLUT'):
        alt = 1
    else:
        alt = 2

    # Calculate p-vals and load into dataset
    pvals = t_test_two_means(optics_data_avg[var],control_data_avg[var],
                                     optics_data_std[var],control_data_std[var],
                                     optics_data_n[var],control_data_n[var],alt,0.)

    optics_data_avg['pvals_'+var] = (pdims,pvals)

    if sig == 'Wilks':
        # Calculate Wilks p-critical
        siglevel = 0.05
        pcrit = np.zeros([len(ens_list),len(time_list)])

        # Loop through all months/years & ensemble members
        for i in time_list:
            # Set time part of index
            index = dict() if time_avg == 3 else {t_dim: i}
            for j in ens_list:
                # Set time/ensemble index
                index = index.update({e_dim: j}) if ens_type == 'All_members' else index

                # Calculate p-critical
                pcrit[j,i] = Wilks_pcrit(optics_data_avg['pvals_'+var][index].values,siglevel)

        optics_data_avg['pcrit_'+var] = (pcdims,pcrit)

    return optics_data_avg