import pandas as pd

from netsentinel.services.real_dataset import CSECICIDS2018Service


def test_prepare_cse_cic_ids2018_style_file(tmp_path) -> None:
    raw_path = tmp_path / "sample_cse.csv"
    pd.DataFrame(
        [
            {
                "Dst Port": 22,
                "Protocol": 6,
                "Timestamp": "14/02/2018 10:00:00",
                "Flow Duration": 120000,
                "Tot Fwd Pkts": 50,
                "Tot Bwd Pkts": 8,
                "TotLen Fwd Pkts": 8000,
                "TotLen Bwd Pkts": 900,
                "Flow Byts/s": 74166.6,
                "Flow Pkts/s": 483.3,
                "Pkt Len Mean": 153.4,
                "Pkt Len Std": 22.5,
                "SYN Flag Cnt": 4,
                "ACK Flag Cnt": 7,
                "Label": "SSH-Bruteforce",
            },
            {
                "Dst Port": 443,
                "Protocol": 6,
                "Timestamp": "14/02/2018 10:01:00",
                "Flow Duration": 900000,
                "Tot Fwd Pkts": 12,
                "Tot Bwd Pkts": 14,
                "TotLen Fwd Pkts": 2500,
                "TotLen Bwd Pkts": 5200,
                "Flow Byts/s": 8555.5,
                "Flow Pkts/s": 28.8,
                "Pkt Len Mean": 296.1,
                "Pkt Len Std": 35.0,
                "SYN Flag Cnt": 1,
                "ACK Flag Cnt": 2,
                "Label": "Benign",
            },
        ]
    ).to_csv(raw_path, index=False)

    prepared, report = CSECICIDS2018Service(tmp_path / "raw", tmp_path / "processed").prepare_files(
        [raw_path],
        output_path=tmp_path / "processed" / "prepared.csv",
        max_rows=None,
    )

    assert len(prepared) == 2
    assert set(prepared["label"]) == {0, 1}
    assert report.attack_type_counts["SSH-Bruteforce"] == 1
