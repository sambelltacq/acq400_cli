

import os
import logging

class AFHBA404:
    @staticmethod
    def connections():

        connections = {}
        lports=[]
        for devnum in range(16):
            path = f"/dev/rtm-t.{devnum}.ctrl/acq_ident_port"
            if not os.path.isfile(path): continue
            lports.append(devnum)
            with open(path) as f:
                hostname, rport, status = f.read().strip().split()
            if len(hostname.split('_')[-1]) != 3:
                continue
            connections[int(devnum)] = {
                "hostname": hostname,
                "rport": rport,
                "status": status,
            }
        if not lports:
            raise RuntimeError("Driver Not enabled")
        missing = set(range(len(lports))) - set(lports)
        if missing:
            logging.error(f"Missing devices detected ({missing})")

        return connections

    @staticmethod
    def get_root():
        """Get AFHBA404 Root dir"""

        expected_location = os.path.join(os.path.expanduser("~"), "PROJECTS", "AFHBA404")
        root = os.environ.get("AFHBA404_DIR", expected_location)
        
        if os.path.isdir(root): return root
        logging.error(f"Unable to locate AFHAB404 dir specify with 'AFHBA404_DIR='")
        raise RuntimeError(f"AFHAB404 dir not found")
