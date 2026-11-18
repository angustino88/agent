"""MDF (Measurement Data Format) file reader."""
from __future__ import annotations

from asammdf import MDF, Signal


class MDFReader:
    """Read and query MDF measurement files via *asammdf*."""

    def __init__(self, mdf_file: str):
        self.mdf = MDF(mdf_file)

    def num_groups(self) -> int:
        """Return the number of groups in the MDF file."""
        return int(self.mdf.info()['groups'])

    def num_channels_in_group(self, group_idx: int) -> int:
        """Return the number of channels in a specific group."""
        return int(self.mdf.info()[f'group {group_idx}']['channels count'])

    def channel_names_in_group(self, group_idx: int) -> list[str]:
        """Return a list of channel names in a specific group."""
        num_channels = self.num_channels_in_group(group_idx)
        return [self.mdf.get_channel_name(group_idx, ch_idx) for ch_idx in range(num_channels)]

    def total_num_channels(self) -> int:
        """Return the total number of channels in the MDF file."""
        return sum(self.num_channels_in_group(g) for g in range(self.num_groups()))

    def all_channel_names(self) -> list[str]:
        """Return a list of all channel names in the MDF file."""
        names = []
        for group_idx in range(self.num_groups()):
            names.extend(self.channel_names_in_group(group_idx))
        return names

    def read_signals(
        self,
        signal_names: list[str],
        raw: bool = False,
        fmt: str = 'Dec'
    ) -> list[tuple[str, list, list]]:
        """
        Read signals by name, with optional raw and format options.
        Returns a list of tuples: (signal_name, samples, timestamps)
        """
        sig_data_list = []
        raw_sig_data_list = self.mdf.select(signal_names, raw=raw)

        for raw_sig_data in raw_sig_data_list:
            try:
                samples = raw_sig_data.samples.tolist()
                if raw:
                    if fmt == 'Hex':
                        sig_samples = [
                            x.decode('utf-8') if isinstance(x, bytes)
                            else hex(x) if isinstance(x, int)
                            else x for x in samples
                        ]
                    elif fmt == 'Bin':
                        sig_samples = [
                            x.decode('utf-8') if isinstance(x, bytes)
                            else bin(x) if isinstance(x, int)
                            else x for x in samples
                        ]
                    else:
                        sig_samples = [
                            x.decode('utf-8') if isinstance(x, bytes)
                            else x for x in samples
                        ]
                else:
                    sig_samples = [
                        x.decode('utf-8') if isinstance(x, bytes)
                        else x for x in samples
                    ]
            except Exception:
                # If can't decode data with utf-8, try ISO-8859-1
                sig_samples = [
                    x.decode('ISO-8859-1') if isinstance(x, bytes)
                    else x for x in raw_sig_data.samples.tolist()
                ]

            sig_data_list.append(
                (
                    raw_sig_data.name,
                    sig_samples,
                    raw_sig_data.timestamps.tolist()
                )
            )

        return sig_data_list

    def get_signal(self, signal_name: str, group: int = 0) -> Signal:
        """Return the Signal object for a given signal name and group."""
        return self.mdf.get(signal_name, group=group)

    def get_signal_samples(self, signal_name: str, group: int = 0) -> list:
        """Return the samples for a given signal."""
        sig = self.get_signal(signal_name, group)
        return sig.samples.tolist()

    def get_signal_timestamps(self, signal_name: str, group: int = 0) -> list:
        """Return the timestamps for a given signal."""
        sig = self.get_signal(signal_name, group)
        return sig.timestamps.tolist()

    def get_signal_info(self, signal_name: str, group: int = 0) -> dict:
        """Return metadata/info for a given signal."""
        sig = self.get_signal(signal_name, group)
        return {
            "name": sig.name,
            "unit": sig.unit,
            "samples_count": len(sig.samples),
            "timestamps_count": len(sig.timestamps),
            "comment": getattr(sig, "comment", ""),
            "source": getattr(sig, "source", ""),
        }

    def export_signal_to_csv(self, signal_name: str, csv_path: str, group: int = 0) -> None:
        """Export a signal's samples and timestamps to a CSV file."""
        import csv
        sig = self.get_signal(signal_name, group)
        with open(csv_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sample"])
            for t, s in zip(sig.timestamps, sig.samples):
                writer.writerow([t, s])

    def close(self):
        """Close the MDF file (if needed)."""
        self.mdf.close()
