import json

import pandas as pd

from netsentinel.services.flow_payloads import dataframe_to_flow_payloads
from netsentinel.services.packet_capture import packets_to_flow_records
from netsentinel.services.sample_data import generate_synthetic_network_flows


def test_dataframe_to_flow_payloads_normalizes_common_csv_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "Timestamp": "2026-05-28T10:00:00",
                "Flow Duration": 0.25,
                "Protocol": "6",
                "Source Port": 49152,
                "Destination Port": "22",
                "Total Fwd Packets": 12,
                "Total Backward Packets": 3,
                "Total Length of Fwd Packets": 2400,
                "Total Length of Bwd Packets": 350,
                "Flow Bytes/s": 11000,
                "Flow Packets/s": 60,
            }
        ]
    )

    payloads = dataframe_to_flow_payloads(df)

    assert payloads == [
        {
            "timestamp": "2026-05-28T10:00:00",
            "duration": 0.25,
            "protocol": "TCP",
            "src_port": 49152,
            "dst_port": 22,
            "src_bytes": 2400.0,
            "dst_bytes": 350.0,
            "src_packets": 12,
            "dst_packets": 3,
            "flow_bytes_per_sec": 11000.0,
            "flow_packets_per_sec": 60.0,
        }
    ]


def test_dataframe_to_flow_payloads_makes_sample_data_json_safe() -> None:
    sample = generate_synthetic_network_flows(20, seed=123).drop(columns=["label", "attack_type"])

    payloads = dataframe_to_flow_payloads(sample)

    json.dumps({"flows": payloads})
    assert len(payloads) == 20
    assert isinstance(payloads[0]["timestamp"], str)


def test_tshark_packets_are_aggregated_into_bidirectional_flows() -> None:
    packets = pd.DataFrame(
        [
            {
                "frame.time_epoch": 100.0,
                "ip.src": "10.0.0.10",
                "ip.dst": "10.0.0.20",
                "ip.proto": 6,
                "frame.len": 100,
                "tcp.srcport": 49152,
                "tcp.dstport": 22,
                "udp.srcport": None,
                "udp.dstport": None,
                "tcp.flags": "0x00000002",
            },
            {
                "frame.time_epoch": 100.5,
                "ip.src": "10.0.0.20",
                "ip.dst": "10.0.0.10",
                "ip.proto": 6,
                "frame.len": 80,
                "tcp.srcport": 22,
                "tcp.dstport": 49152,
                "udp.srcport": None,
                "udp.dstport": None,
                "tcp.flags": "0x00000010",
            },
        ]
    )

    flows = packets_to_flow_records(packets)

    assert len(flows) == 1
    assert flows[0]["protocol"] == "TCP"
    assert flows[0]["src_port"] == 49152
    assert flows[0]["dst_port"] == 22
    assert flows[0]["src_packets"] == 1
    assert flows[0]["dst_packets"] == 1
    assert flows[0]["src_bytes"] == 100.0
    assert flows[0]["dst_bytes"] == 80.0
    assert flows[0]["duration"] == 0.5
    assert flows[0]["tcp_flags"] == 18


def test_tshark_aggregation_skips_unsupported_ip_protocols() -> None:
    packets = pd.DataFrame(
        [
            {
                "frame.time_epoch": 100.0,
                "ip.src": "10.0.0.10",
                "ip.dst": "224.0.0.1",
                "ip.proto": 2,
                "frame.len": 64,
                "tcp.srcport": None,
                "tcp.dstport": None,
                "udp.srcport": None,
                "udp.dstport": None,
                "tcp.flags": None,
            }
        ]
    )

    assert packets_to_flow_records(packets) == []
