import logging
import time

from acq400_cli.utils import run_on_all_uuts


class HDMI:
    @staticmethod
    def enable_direct_out(uut):
        """Enable HDMI DO"""
        uut.s0.SIG__SYNC_OUT__CLK = 0
        uut.s0.SIG__SYNC_OUT__TRG = 0
        uut.s0.SIG__SYNC_OUT__SYNC = 0
        uut.s0.SIG__SYNC_OUT__GPIO = 0

    @staticmethod
    def disable_direct_out(uut):
        """Disable HDMI DO"""
        uut.s0.SIG__SYNC_OUT__CLK = 2
        uut.s0.SIG__SYNC_OUT__TRG = 2
        uut.s0.SIG__SYNC_OUT__SYNC = 2

    @staticmethod
    def write_nibble(uut, nibble):
        """Write nibble to HDMI"""
        uut.s0.SIG__SYNC_BUS_OUT__CLK  = (nibble >> 3) & 1
        uut.s0.SIG__SYNC_BUS_OUT__TRG  = (nibble >> 2) & 1
        uut.s0.SIG__SYNC_BUS_OUT__SYNC = (nibble >> 1) & 1
        uut.s0.SIG__SYNC_BUS_OUT__GPIO = (nibble >> 0) & 1

    @staticmethod
    def read_nibble(uut):
        """Read nibble from HDMI"""
        return (
            (int(uut.s0.SIG__SYNC_BUS__IN__CLK == 'ON')  << 3) |
            (int(uut.s0.SIG__SYNC_BUS__IN__TRG == 'ON')  << 2) |
            (int(uut.s0.SIG__SYNC_BUS__IN__SYNC == 'ON') << 1) |
            (int(uut.s0.SIG__SYNC_BUS__IN__GPIO == 'ON') << 0)
        )


class CarrierTree(HDMI, dict):
    """Create HDMI connections map; the instance is the root hostname -> subtree dict."""

    def __init__(self, uuts):
        super().__init__()
        logging.debug("Detecting HDMI connections")

        uutnames = [uut.hostname for uut in uuts]
        uut_state = run_on_all_uuts(self.__save_and_setup_trg)(uuts)
        time.sleep(1)
        try:
            self.__pulse_triggers(uuts)
            time.sleep(2)
            counts = run_on_all_uuts(self.__get_trg_count)(uuts)
            parents = self.__find_parents(uutnames, counts)
            for device, parent in parents.items():
                if parent is None:
                    self[device] = self.__build_tree(device, parents)
            self.tree = self.__dict_to_tree(self)
        finally:
            run_on_all_uuts(self.__restore_trigger_state)(uuts, uut_state)

    def __str__(self):
        return self.tree

    def __save_and_setup_trg(self, uut):
        state = {
            'prev_trigger_0': uut.s0.SIG__SRC__TRG__0,
            'prev_trigger_1': uut.s0.SIG__SRC__TRG__1,
            'prev_trg_out': uut.s0.SIG__SYNC_OUT__TRG,
            'prev_trg_out_dx': uut.s0.SIG__SYNC_OUT__TRG__DX,
        }
        uut.s0.SIG__SRC__TRG__0 = 1
        uut.s0.SIG__SRC__TRG__1 = 0
        uut.s0.SIG__SYNC_OUT__TRG = 2
        uut.s0.SIG__SYNC_OUT__TRG__DX = 1
        uut.s0.SIG__TRG_EXT__RESET = 1
        return state

    def __restore_trigger_state(self, uut, uut_state):
        state = uut_state[uut.hostname]
        uut.s0.SIG__SRC__TRG__0 = state['prev_trigger_0']
        uut.s0.SIG__SRC__TRG__1 = state['prev_trigger_1']
        uut.s0.SIG__SYNC_OUT__TRG = state['prev_trg_out']
        uut.s0.SIG__SYNC_OUT__TRG__DX = state['prev_trg_out_dx']

    @staticmethod
    def __get_trg_count(uut):
        return int(uut.s0.SIG__TRG_EXT__COUNT)

    def __pulse_triggers(self, uuts):
        for idx, uut in enumerate(uuts):
            logging.debug("%s soft trigger x%s", uut.hostname, idx + 1)
            for _ in range(idx + 1):
                uut.s0.soft_trigger = 1

    def __find_parents(self, uutnames, counts):
        parents = {}
        for uutname, count in counts.items():
            if count == 0:
                parents[uutname] = None
            elif 1 <= count <= len(uutnames):
                parents[uutname] = uutnames[count - 1]
            else:
                logging.warning(
                    "Invalid TRG_EXT count %s for %s; treating as root",
                    count, uutname,
                )
                parents[uutname] = None
        return parents

    def __build_tree(self, parent, parents):
        tree = {}
        for device, p in parents.items():
            if p == parent:
                tree[device] = self.__build_tree(device, parents)
        return tree

    def __dict_to_tree(self, branch, prefix="", depth=0):
        lines = []
        keys = list(branch.keys())

        for i, k in enumerate(keys):
            is_last = i == len(keys) - 1
            if depth == 0:
                lines.append(prefix + k)
            else:
                connector = "└── " if is_last else "├── "
                lines.append(prefix + connector + k)

            child_prefix = prefix + ("    " if is_last else "│   ")
            if isinstance(branch[k], dict) and branch[k]:
                lines.append(self.__dict_to_tree(branch[k], child_prefix, depth + 1))

        return "\n".join(lines)

    def partition(self, depth=0):
        
        def walk(branch, level=0):
            for hostname, subtree in branch.items():
                yield hostname, level
                if subtree:
                    yield from walk(subtree, level + 1)

        above, below = [], []
        for hostname, level in walk(self):
            if level == depth:
                above.append(hostname)
            elif level > depth:
                below.append(hostname)
        return above, below


