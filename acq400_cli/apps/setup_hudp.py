#!/usr/bin/env python3

"""
Setup HUDP for UUTs
"""

from acq400_cli import ArgParser, Carrier, CAPTURE_STATE
import logging

INVALID = ('NONE', 'PC')
MTU = 9038 - 66


def main(args):

    tx_uut = Carrier(args.tx_uutname) if args.tx_uutname and args.tx_uutname.upper() not in INVALID else None
    rx_uut = Carrier(args.rx_uutname) if args.rx_uutname and args.rx_uutname.upper() not in INVALID else None


    if tx_uut:
        print(f"TX UUT: {tx_uut.hostname}")

        if tx_uut.capture_state != CAPTURE_STATE.IDLE:
            logging.error(f"ERROR: {tx_uut.hostname} is {tx_uut.capture_state.name}, abort capture first")
            exit()

        if tx_uut.ai_master.knob_exists('pack24'):
            if args.pack24: tx_uut.ai_master.pack24 = '1'
            else: tx_uut.ai_master.pack24 = '1'

        if args.run0 is not None: tx_uut.s0.run0 = args.run0

        tx_uut.hudp.init(args.tx_ip, args.gw or args.rx_ip, args.netmask)
        tx_uut.hudp.set_disco(args.disco)
        tx_uut.hudp.config_tx(args.rx_ip, args.port, args.port, args.decim, args.broadcast, args.netmask)

        if args.hudp_relay is None:
            tx_uut.hudp.udp_data_src = 0
            tx_ssb = int(tx_uut.s0.ssb)
        else:
            tx_ssb = tx_uut.hudp.config_relay(args.hudp_relay)

        if args.tx_ssb is not None: tx_ssb = args.tx_ssb

        tx_uut.hudp.tx_sample_sz = tx_ssb
        tx_uut.hudp.tx_spp = args.spp
        tx_packet_size = tx_ssb * args.spp

        if tx_packet_size > MTU:
            logging.error(f"ERROR: packet length ({tx_packet_size}) exceeds MTU ({MTU})")
            return

        tx_uut.hudp.enable()
        tx_uut.hudp.init_arp_req()

        tx_actual_packet_size = int(tx_uut.hudp.tx_calc_pkt_sz)
        if tx_packet_size != tx_actual_packet_size:
            print(f"ERROR: set tx packet size {tx_packet_size} tx actual packet size {tx_actual_packet_size}")

        spad0_column = None if int(tx_uut.s0.ssb) == int(tx_uut.s0.spadstart) else int(tx_uut.s0.spadstart) // 4

        print(f"TX configured: ssb: {tx_ssb} spp: {args.spp} packet size: {tx_packet_size} spad0: {spad0_column} datarate: {tx_uut.data_rate / args.decim:.2f} MBs")
        print(f"CMD: sudo ./udprx -R 40 -p {args.port} --spp {args.spp} --ssb {tx_ssb}" + (f" -c {spad0_column}" if spad0_column else ''))

    if rx_uut:
        print(f"RX UUT: {rx_uut.hostname}")
        if rx_uut.capture_state != CAPTURE_STATE.IDLE:
            logging.error(f"ERROR: {rx_uut.hostname} is {rx_uut.capture_state.name}, abort capture first")
            exit()

        if args.play0 is not None: rx_uut.s0.play0 = args.play0

        rx_uut.s0.distributor = 'comms=U off'
        rx_uut.s0.distributor = 'on'

        rx_uut.hudp.init(args.rx_ip, args.gw or args.rx_ip, args.netmask)
        rx_uut.hudp.set_disco(args.disco)
        rx_uut.hudp.config_rx(args.tx_ip, args.port)
        rx_uut.hudp.enable()


def get_parser():
    parser = ArgParser(description='Setup HUDP for UUTs')

    parser.add_argument("--netmask", default='255.255.255.0', help='netmask')

    parser.add_argument("--tx_ip", default='10.12.198.128', help='tx ip address')
    parser.add_argument("--rx_ip", default='10.12.198.129', help='rx ip address')

    parser.add_argument("--gw", default=None, help='gateway')
    parser.add_argument("--port", default='53676', help='port')

    parser.add_argument("--run0", default=None, help="set tx sites+spad")
    parser.add_argument("--play0", default=None, help="set rx sites+spad")

    parser.add_argument("--broadcast", action='store_true', help="broadcast the data")
    parser.add_argument("--disco", default=None, type=int, help="enable discontinuity check at index x")
    parser.add_argument("--pack24", action='store_true', help="enable pack 24 mode")

    parser.add_argument("--hudp_relay", default=None, type=int, help="relay LLC VI out HUDP txt offset")
    parser.add_argument("--spp", default=1, type=int, help="samples per packet")

    parser.add_argument("--decim", default=1, type=int, help="hudp decimation, 1..16")
    parser.add_argument("--tx_ssb", default=None, type=int, help="Override TX SSB")

    parser.add_argument('tx_uutname', nargs='?', help="transmit UUT or None")
    parser.add_argument('rx_uutname', nargs='?', help="receive UUT or None")
    return parser


if __name__ == '__main__':
    main(get_parser().parse_args())
