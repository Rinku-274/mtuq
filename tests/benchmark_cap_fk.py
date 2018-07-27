
import os
import sys
import numpy as np

from os.path import basename, join
from mtuq.dataset import sac
from mtuq.greens_tensor import fk
from mtuq.grid_search import DoubleCoupleGridRandom
from mtuq.grid_search import grid_search_serial
from mtuq.misfit.cap import Misfit
from mtuq.process_data.cap import ProcessData
from mtuq.util.cap_util import remove_unused_stations, trapezoid_rise_time, Trapezoid
from mtuq.util.plot import plot_beachball, plot_data_synthetics
from mtuq.util.util import cross, path_mtuq



if __name__=='__main__':
    #
    # Given four "fundamental" moment tensor, generates MTUQ synthetics and
    # compares with corresponding CAP/FK synthetics
    #
    # This script is similar to examples/GridSearch.DoubleCouple3.Serial.py,
    # except here we consider only four grid points rather than an entire
    # grid, and here the final plots are a comparison of MTUQ and CAP/FK 
    # synthetics rather than a comparison of data and synthetics
    #
    # Note that CAP works with dyne/cm and MTUQ works with N/m, so to make
    # comparisons we convert CAP output from the former to the latter
    #
    # The CAP/FK synthetics used in the comparison were generated by 
    # uafseismo/capuaf:46dd46bdc06e1336c3c4ccf4f99368fe99019c88
    # using the following commands
    #
    # explosion source:
    # cap.pl -H0.02 -P1/15/60 -p1 -S2/10/0 -T15/150 -D1/1/0.5 -C0.1/0.333/0.025/0.0625 -Y1 -Zweight_test.dat -Mscak_34 -m4.5 -I1 -R0/1.178/90/45/90 20090407201255351
    #
    # double-couple source #1:
    # cap.pl -H0.02 -P1/15/60 -p1 -S2/10/0 -T15/150 -D1/1/0.5 -C0.1/0.333/0.025/0.0625 -Y1 -Zweight_test.dat -Mscak_34 -m4.5 -I1 -R0/0/90/90/90 20090407201255351
    #
    # double-couple source #2:
    # cap.pl -H0.02 -P1/15/60 -p1 -S2/10/0 -T15/150 -D1/1/0.5 -C0.1/0.333/0.025/0.0625 -Y1 -Zweight_test.dat -Mscak_34 -m4.5 -I1 -R0/0/90/0/0 20090407201255351
    #
    # double-couple source #3:
    # cap.pl -H0.02 -P1/15/60 -p1 -S2/10/0 -T15/150 -D1/1/0.5 -C0.1/0.333/0.025/0.0625 -Y1 -Zweight_test.dat -Mscak_34 -m4.5 -I1 -R0/0/0/90/180 20090407201255351
    #


    path_ref = []
    path_ref += [join(path_mtuq(), 'data/tests/benchmark_cap_fk/20090407201255351/0')]
    path_ref += [join(path_mtuq(), 'data/tests/benchmark_cap_fk/20090407201255351/1')]
    path_ref += [join(path_mtuq(), 'data/tests/benchmark_cap_fk/20090407201255351/2')]
    path_ref += [join(path_mtuq(), 'data/tests/benchmark_cap_fk/20090407201255351/3')]
    # For now this path exists only in my personal environment.  Eventually, 
    # we need to include it in the repository or make it available for download
    path_greens=  join(os.getenv('CENTER1'), 'data/wf/FK_SYNTHETICS/scak')


    path_data=    join(path_mtuq(), 'data/examples/20090407201255351')
    path_weights= join(path_mtuq(), 'data/tests/benchmark_cap_fk/20090407201255351/weights.dat')
    path_picks=   join(path_mtuq(), 'data/examples/20090407201255351/picks.dat')
    event_name=   '20090407201255351'
    model=        'scak'


    process_bw = ProcessData(
        filter_type='Bandpass',
        freq_min= 0.1,
        freq_max= 0.333,
        pick_type='from_pick_file',
        pick_file=path_picks,
        window_type='cap_bw',
        window_length=15.,
        padding_length=0,
        weight_type='cap_bw',
        cap_weight_file=path_weights,
        )

    process_sw = ProcessData(
        filter_type='Bandpass',
        freq_min=0.025,
        freq_max=0.0625,
        pick_type='from_pick_file',
        pick_file=path_picks,
        window_type='cap_sw',
        window_length=150.,
        padding_length=0,
        weight_type='cap_sw',
        cap_weight_file=path_weights,
        )

    process_data = {
       'body_waves': process_bw,
       'surface_waves': process_sw,
       }


    misfit_bw = Misfit(
        time_shift_max=0.,
        time_shift_groups=['ZR'],
        )

    misfit_sw = Misfit(
        time_shift_max=0.,
        time_shift_groups=['ZR','T'],
        )

    misfit = {
        'body_waves': misfit_bw,
        'surface_waves': misfit_sw,
        }


    #
    # Next we specify the source parameter grid
    #

    grid = [
       # Mrr, Mtt, Mpp, Mrt, Mrp, Mtp
       np.sqrt(1./3.)*np.array([1., 1., 1., 0., 0., 0.]), # explosion
       np.sqrt(1./2.)*np.array([0., 0., 0., 1., 0., 0.]), # double-couple #1
       np.sqrt(1./2.)*np.array([0., 0., 0., 0., 1., 0.]), # double-couple #2
       np.sqrt(1./2.)*np.array([0., 0., 0., 0., 0., 1.]), # double-couple #3
       ]

    Mw = 4.5
    M0 = 10.**(1.5*Mw + 9.1) # units: N-m
    for mt in grid:
        mt *= M0
        # ad hoc factor
        mt *= np.sqrt(2.)

    rise_time = trapezoid_rise_time(Mw=4.5)
    wavelet = Trapezoid(rise_time)


    #
    # The benchmark starts now
    #

    print 'Reading data...\n'
    data = sac.reader(path_data, wildcard='*.[zrt]', id=event_name,
        tags=['cm', 'velocity']) 
    remove_unused_stations(data, path_weights)
    data.sort_by_distance()

    stations  = []
    for stream in data:
        stations += [stream.meta]
    origin = data.get_origin()


    print 'Processing data...\n'
    processed_data = {}
    for key in ['body_waves', 'surface_waves']:
        processed_data[key] = data.map(process_data[key])
    data = processed_data


    print 'Reading Greens functions...\n'
    factory = fk.GreensTensorFactory(path_greens)
    greens = factory(stations, origin)

    print 'Processing Greens functions...\n'
    greens.convolve(wavelet)
    processed_greens = {}
    for key in ['body_waves', 'surface_waves']:
        processed_greens[key] = greens.map(process_data[key])
    greens = processed_greens

    print 'Plotting waveforms...'
    from copy import deepcopy
    from mtuq.util.cap_util import get_synthetics_cap, get_synthetics_mtuq
    from mtuq.util.cap_util import get_data_cap

    for _i, mt in enumerate(grid):
        print ' %d of %d' % (_i+1, len(grid)+1)
        synthetics_cap = get_synthetics_cap(deepcopy(data), path_ref[_i])
        synthetics_mtuq = get_synthetics_mtuq(greens, mt)
        filename = 'cap_fk_'+str(_i)+'.png'
        plot_data_synthetics(filename, synthetics_cap, synthetics_mtuq)

    # generates "bonus" figure comparing how CAP processes observed data with
    # how MTUQ processes observed data
    print ' %d of %d' % (_i+2, len(grid)+1)
    data_mtuq = data
    data_cap = get_data_cap(deepcopy(data), path_ref[0])
    filename = 'cap_fk_data.png'
    plot_data_synthetics(filename, data_cap, data_mtuq, normalize=False)


