""" Generate scattering covariance dataset from Mars waveforms. """
import argparse
import h5py
import obspy
import numpy as np
import os
from tqdm import tqdm

from scatcov.frontend import analyze
from facvae.utils import datadir, is_night_time_event

MARS_PATH = datadir('mars')


def windows(x, window_size, stride, offset):
    """ Separate x into windows on last axis, discard any residual.
    """
    num_window = (x.shape[-1] - window_size - offset) // stride + 1
    windowed_x = np.stack([
        x[..., i * stride + offset:window_size + i * stride + offset]
        for i in range(num_window)
    ], -2)  # (C) x nb_w x w

    return windowed_x


def setup_hdf5_file(path, scat_cov_filename):
    """
    Setting up an HDF5 file to write scattering covariances.
    """
    # Path to the file.
    file_path = os.path.join(path, scat_cov_filename)

    # Horizons file
    file = h5py.File(file_path, 'a')
    file.close()


def update_hdf5_file(path, scat_cov_filename, filename, waveform,
                     scat_covariances, window_times):
    """
    Update the HDF5 file by writing new scattering covariances.
    """
    # Path to the file.
    file_path = os.path.join(path, scat_cov_filename)

    # HDF5 file.
    file = h5py.File(file_path, 'r+')

    # Group for the given file.
    file_group = file.create_group(filename)

    # HDF5 dataset for waveform.
    file_group.create_dataset('waveform', data=waveform, dtype=np.float32)

    # HDF5 dataset for waveform.
    file_group.create_dataset('scat_cov',
                              data=scat_covariances,
                              dtype=np.float32)
    file_group.create_dataset(
        'window_times',
        data=[str(event_time) for event_time in window_times],
        dtype=h5py.string_dtype())
    file.close()


def compute_scat_cov(args):

    waveform_path = datadir(os.path.join(MARS_PATH, 'waveforms'))
    scat_cov_path = datadir(os.path.join(MARS_PATH, 'scat_covs_h5'))
    raw_data_files = os.listdir(waveform_path)

    setup_hdf5_file(scat_cov_path, args.scat_cov_filename)
    discarded_files = 0
    with tqdm(raw_data_files,
              unit='file',
              colour='#B5F2A9',
              dynamic_ncols=True) as pb:
        for i, file in enumerate(pb):
            if os.stat(os.path.join(waveform_path, file)).st_size > 0:
                # Read data into a stream format.
                data_stream = obspy.read(os.path.join(waveform_path, file))

                # Only keep files that do not have gaps.
                if len(data_stream.get_gaps()) == 0:

                    # The following line although will not do interpolation —
                    # because there are not gaps — but will combine different
                    # streams into one.
                    data_stream = data_stream.merge(method=1,
                                                    fill_value="interpolate")

                    # Trimming all the components to the same length.
                    data_stream = data_stream.trim(
                        starttime=max(
                            [tr.meta.starttime for tr in data_stream]),
                        endtime=min([tr.meta.endtime for tr in data_stream]))

                    # Turn the trace to a batch of windowed data with size
                    # `window_size`.
                    windowed_data = list(
                        data_stream.slide(
                            (args.window_size - 1) /
                            data_stream[0].meta.sampling_rate,
                            args.window_size /
                            data_stream[0].meta.sampling_rate // 2,
                            offset=0))

                    window_times = []
                    batched_window = []
                    for window in windowed_data:
                        window_times.append(
                            (window[0].meta.starttime, window[0].meta.endtime))
                        batched_window.append(
                            np.stack([tr.data for tr in window]))
                    batched_window = np.stack(batched_window)
                    batched_window = batched_window.reshape(
                        batched_window.shape[0] * batched_window.shape[1],
                        batched_window.shape[2])

                    # Compute scattering covariance. RX is a
                    # DescribedTensor.
                    # RX.y is a tensor of size B x nb_coeff x T x 2

                    # RX.info is a dataframe with nb_coeff rows that
                    # describes each RX.y[:, i_coeff, :, :] for 0 <=
                    # i_coeff < nb_coeff
                    RX = analyze(batched_window,
                                 J=args.num_oct,
                                 Q1=args.q1,
                                 Q2=args.q2,
                                 moments='cov',
                                 cuda=args.cuda,
                                 normalize=True,
                                 nchunks=48)
                    if not args.use_power_spectrum:
                        mask_power_spectrum = RX.descri.where(
                            q=2, r=1)  # where is the power spectrum
                        RX = RX.reduce(mask=~mask_power_spectrum)
                    RX.y = RX.y.reshape(len(windowed_data), 3, -1, 2)

                    # Compute the average of the scattering covariance
                    # over the time axis.
                    for b in range(len(windowed_data)):

                        # CASE 1: keep real and imag parts by considering
                        # it as different real coefficients
                        y = RX.y[b, ...].numpy()
                        scat_covariances = np.transpose(y, (0, 2, 1)).reshape(
                            3 * 2, -1)

                        # scat_covariances = [
                        #     torch.cat(
                        #         [RX.y[b, :, 0].real,
                        #          RX.y[b, :, 0].imag]).numpy()
                        #     for i in range(3)
                        # ]
                        # scat_covariances = np.transpose(
                        #     np.stack(scat_covariances), (1, 0, 2))

                        # CASE 2: only keeps the modulus of the scattering
                        # covariance, hence discarding time asymmetry info
                        # scat_covariances = np.abs(cplx.to_np(y))

                        # CASE 3: only keep the phase, which looks at time
                        # asymmetry in the data y =
                        # RX.reduce(m_type=['m01', 'm11'], re=False).y[0,
                        # :, 0].numpy() y_phase = np.angle(y)
                        # y_phase[np.abs(y) < 1e-2] = 0.0  # rules phase
                        # instability scat_covariances = y_phase

                        filename = file + '_' + str(b)
                        event_start, event_end = window_times[b]
                        if args.use_day_data or is_night_time_event(
                                event_start, event_end):

                            update_hdf5_file(
                                scat_cov_path, args.scat_cov_filename,
                                filename, batched_window[3 * b:3 * (b + 1),
                                                         ...],
                                scat_covariances, window_times[b])
                        pb.set_postfix({
                            'shape':
                            scat_covariances.shape,
                            'discarded':
                            f'{discarded_files/(i + 1):.4f}'
                        })

                else:
                    discarded_files += 1


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--window_size',
                        dest='window_size',
                        type=int,
                        default=2**12,
                        help='Window size of raw waveforms')
    parser.add_argument('--num_oct',
                        dest='num_oct',
                        type=int,
                        default=8,
                        help='Number of octaves in the scattering transform')
    parser.add_argument('--q1', dest='q1', type=int, default=2)
    parser.add_argument('--q2', dest='q2', type=int, default=4)
    parser.add_argument('--cuda',
                        dest='cuda',
                        type=int,
                        default=1,
                        help='set to 1 for running on GPU, 0 for CPU')
    parser.add_argument('--use_day_data',
                        dest='use_day_data',
                        type=int,
                        default=1,
                        help='set to 0 for extracting only night time data')
    parser.add_argument('--use_power_spectrum',
                        dest='use_power_spectrum',
                        type=int,
                        default=1,
                        help='set to 0 for extracting only night time data')
    parser.add_argument(
        '--scat_cov_filename',
        dest='scat_cov_filename',
        type=str,
        default='scat_covs_mc_w-size-2e12_q1-2_q2-4_nighttime.h5',
        help='filname to be created')
    args = parser.parse_args()

    compute_scat_cov(args)
