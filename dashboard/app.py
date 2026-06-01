"""Streamlit dashboard for NetSentinel-ML."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from netsentinel.services.flow_payloads import dataframe_to_flow_payloads, normalize_flow_dataframe
from netsentinel.services.packet_capture import (
    DEFAULT_CAPTURE_FILTER,
    interface_value,
    list_tshark_interfaces,
    packet_preview,
    packets_to_flow_records,
    run_tshark_capture,
)

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("NETSENTINEL_API_KEY", "dev-netsentinel-key")
MAX_BATCH_SIZE = 500
DEFAULT_TSHARK_PATH = (
    r"C:\Program Files\Wireshark\tshark.exe"
    if Path(r"C:\Program Files\Wireshark\tshark.exe").exists()
    else "tshark"
)

st.set_page_config(page_title="NetSentinel-ML", layout="wide")


def get_json(path: str) -> dict:
    response = requests.get(f"{API_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def post_json(path: str, payload: dict, protected: bool = False, timeout: int = 15) -> dict:
    headers = {"x-api-key": API_KEY} if protected else {}
    response = requests.post(f"{API_URL}{path}", json=payload, headers=headers, timeout=timeout)
    if response.status_code >= 400:
        detail = response.text[:800]
        raise requests.HTTPError(f"{response.status_code} error from {path}: {detail}", response=response)
    return response.json()


def post_batch_predictions(flows: list[dict]) -> pd.DataFrame:
    predictions: list[dict] = []
    for start in range(0, len(flows), MAX_BATCH_SIZE):
        batch = flows[start : start + MAX_BATCH_SIZE]
        response = post_json("/api/v1/predict/batch", {"flows": batch}, timeout=60)
        predictions.extend(response["predictions"])
    return pd.DataFrame(predictions)


def risk_color(prediction: str) -> str:
    return "#b42318" if prediction == "malicious" else "#067647"


@st.cache_data(show_spinner=False, ttl=30)
def cached_interfaces(tshark_path: str) -> list[str]:
    return list_tshark_interfaces(tshark_path)


st.title("NetSentinel-ML")
st.caption("Network intrusion detection with explainability, drift monitoring, and model lifecycle controls.")

tabs = st.tabs(["Operations", "Prediction", "Capture", "Models", "Drift", "Runbooks"])

with tabs[0]:
    try:
        health = get_json("/api/v1/health")
        performance = get_json("/api/v1/performance")
        metrics = performance["metrics"]
        active_model = health.get("active_model") or {}

        cols = st.columns(5)
        cols[0].metric("Active model", active_model.get("name", "none"))
        cols[1].metric("F1", f"{active_model.get('metrics', {}).get('f1', 0):.3f}")
        cols[2].metric("P95 latency", f"{metrics['latency_p95_ms']:.2f} ms")
        cols[3].metric("Throughput", f"{metrics['throughput_rps']:.3f} rps")
        cols[4].metric("Drift score", f"{metrics['drift_score']:.3f}")

        alerts = pd.DataFrame(performance.get("alerts", []))
        if not alerts.empty:
            st.subheader("Alerts")
            st.dataframe(alerts, width="stretch", hide_index=True)
        else:
            st.info("No active alerts.")

        latency_frame = pd.DataFrame(
            {
                "metric": ["P50", "P95", "P99"],
                "latency_ms": [
                    metrics["latency_p50_ms"],
                    metrics["latency_p95_ms"],
                    metrics["latency_p99_ms"],
                ],
            }
        )
        st.plotly_chart(
            px.bar(latency_frame, x="metric", y="latency_ms", color="metric", title="Latency Percentiles"),
            width="stretch",
        )
    except Exception as exc:
        st.error(f"API unavailable at {API_URL}: {exc}")

with tabs[1]:
    left, right = st.columns([1, 1])
    with left:
        with st.form("prediction_form"):
            protocol = st.selectbox("Protocol", ["TCP", "UDP", "ICMP"], index=0)
            dst_port = st.number_input("Destination port", 0, 65535, 22)
            duration = st.number_input("Duration", 0.01, 600.0, 0.18)
            src_bytes = st.number_input("Source bytes", 0.0, 10_000_000.0, 8420.0)
            dst_bytes = st.number_input("Destination bytes", 0.0, 10_000_000.0, 920.0)
            src_packets = st.number_input("Source packets", 0, 1_000_000, 52)
            dst_packets = st.number_input("Destination packets", 0, 1_000_000, 9)
            tcp_flags = st.number_input("TCP flags", 0, 128, 12)
            submitted = st.form_submit_button("Predict")

        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "duration": duration,
            "protocol": protocol,
            "src_port": 49152,
            "dst_port": int(dst_port),
            "src_bytes": src_bytes,
            "dst_bytes": dst_bytes,
            "src_packets": int(src_packets),
            "dst_packets": int(dst_packets),
            "tcp_flags": int(tcp_flags),
        }

    with right:
        if submitted:
            try:
                prediction = post_json("/api/v1/predict", payload)
                title = prediction["prediction"].title()
                color = risk_color(prediction["prediction"])
                st.markdown(
                    f"<h2 style='color:{color};'>{title}</h2>",
                    unsafe_allow_html=True,
                )
                st.metric("Confidence", f"{prediction['confidence']:.2%}")
                st.metric("Latency", f"{prediction['latency_ms']:.2f} ms")

                explanation = pd.DataFrame(prediction["explanation"])
                st.subheader("Top feature contributions")
                st.plotly_chart(
                    px.bar(
                        explanation,
                        x="contribution",
                        y="feature",
                        orientation="h",
                        color="direction",
                    ),
                    width="stretch",
                )
                st.subheader("Counterfactual changes")
                st.dataframe(pd.DataFrame(prediction["counterfactual"]), width="stretch", hide_index=True)
            except Exception as exc:
                st.error(f"Prediction failed: {exc}")
        else:
            st.info("Submit a flow to see its risk score and explanation.")

    st.divider()
    st.subheader("CSV batch scoring")
    uploaded_csv = st.file_uploader("Upload network-flow CSV", type=["csv"])
    if uploaded_csv is not None:
        try:
            csv_frame = pd.read_csv(uploaded_csv)
            if csv_frame.empty:
                st.warning("Uploaded CSV has no rows.")
            else:
                max_rows = st.number_input(
                    "Rows to score",
                    min_value=1,
                    max_value=min(5000, len(csv_frame)),
                    value=min(500, len(csv_frame)),
                    step=100,
                )
                normalized_preview = normalize_flow_dataframe(csv_frame).head(int(max_rows))
                st.dataframe(normalized_preview, width="stretch", hide_index=True)

                if st.button("Score uploaded CSV"):
                    flows = dataframe_to_flow_payloads(csv_frame, limit=int(max_rows))
                    if not flows:
                        st.warning("No usable rows found in the uploaded CSV.")
                    else:
                        predictions = post_batch_predictions(flows)
                        source = pd.DataFrame(flows).reset_index(drop=True)
                        scored = pd.concat([source, predictions], axis=1)
                        counts = predictions["prediction"].value_counts().rename_axis("prediction").reset_index(
                            name="count"
                        )

                        cols = st.columns(3)
                        cols[0].metric("Rows scored", len(scored))
                        cols[1].metric("Malicious", int((predictions["prediction"] == "malicious").sum()))
                        cols[2].metric("Benign", int((predictions["prediction"] == "benign").sum()))

                        st.plotly_chart(
                            px.bar(counts, x="prediction", y="count", color="prediction", title="CSV predictions"),
                            width="stretch",
                        )
                        st.dataframe(scored, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"CSV scoring failed: {exc}")

with tabs[2]:
    st.subheader("Live packet capture")

    tshark_path = st.text_input("tshark path", DEFAULT_TSHARK_PATH)
    try:
        interface_rows = cached_interfaces(tshark_path)
    except Exception as exc:
        interface_rows = []
        st.error(f"Unable to list capture interfaces: {exc}")

    if interface_rows:
        selected_interface = st.selectbox(
            "Capture interface",
            interface_rows,
            index=next((idx for idx, row in enumerate(interface_rows) if "Wi-Fi" in row), 0),
        )
        capture_interface = interface_value(selected_interface)
    else:
        capture_interface = st.text_input("Capture interface", "4")

    c1, c2, c3 = st.columns(3)
    window_seconds = c1.number_input("Capture window", min_value=3, max_value=60, value=10, step=1)
    packet_limit = c2.number_input("Packet limit", min_value=0, max_value=5000, value=0, step=100)
    max_flows = c3.number_input("Max flows to analyze", min_value=1, max_value=1000, value=500, step=50)
    capture_filter = st.text_input("Capture filter", DEFAULT_CAPTURE_FILTER)

    if st.button("Capture and analyze", type="primary"):
        try:
            with st.spinner("Capturing packets and scoring flows..."):
                packets = run_tshark_capture(
                    tshark_path=tshark_path,
                    interface=capture_interface,
                    window_seconds=int(window_seconds),
                    packet_limit=int(packet_limit) or None,
                    capture_filter=capture_filter,
                )
                flow_records = packets_to_flow_records(packets)[: int(max_flows)]
                payloads = dataframe_to_flow_payloads(pd.DataFrame(flow_records))

                if payloads:
                    predictions = post_batch_predictions(payloads)
                    flow_frame = pd.DataFrame(flow_records).head(len(payloads)).reset_index(drop=True)
                    scored = pd.concat([flow_frame, predictions], axis=1)
                else:
                    predictions = pd.DataFrame()
                    scored = pd.DataFrame()

            cols = st.columns(4)
            cols[0].metric("Packets captured", int(len(packets)))
            cols[1].metric("Flows analyzed", int(len(scored)))
            cols[2].metric(
                "Malicious",
                int((predictions["prediction"] == "malicious").sum()) if not predictions.empty else 0,
            )
            cols[3].metric(
                "Benign",
                int((predictions["prediction"] == "benign").sum()) if not predictions.empty else 0,
            )

            if packets.empty:
                st.warning("No packets were captured in this window.")
            else:
                st.subheader("Captured packet preview")
                st.dataframe(packet_preview(packets), width="stretch", hide_index=True)

            if scored.empty:
                st.warning("No supported TCP, UDP, or ICMP flows were available for analysis.")
            else:
                prediction_counts = predictions["prediction"].value_counts().rename_axis("prediction").reset_index(
                    name="count"
                )
                st.plotly_chart(
                    px.bar(
                        prediction_counts,
                        x="prediction",
                        y="count",
                        color="prediction",
                        title="Live capture predictions",
                    ),
                    width="stretch",
                )
                st.subheader("Analyzed flows")
                st.dataframe(scored, width="stretch", hide_index=True)
                st.download_button(
                    "Download analyzed capture CSV",
                    scored.to_csv(index=False),
                    file_name="netsentinel_capture_predictions.csv",
                    mime="text/csv",
                )
        except Exception as exc:
            st.error(f"Capture analysis failed: {exc}")

with tabs[3]:
    try:
        models = pd.DataFrame(get_json("/api/v1/models")["models"])
        if not models.empty:
            model_metrics = pd.json_normalize(models.to_dict(orient="records"))
            st.dataframe(model_metrics, width="stretch", hide_index=True)
            chart_cols = [col for col in model_metrics.columns if col.startswith("metrics.")]
            if chart_cols:
                selected = st.multiselect("Metrics", chart_cols, default=chart_cols[:4])
                if selected:
                    melted = model_metrics.melt(id_vars=["model_id"], value_vars=selected)
                    st.plotly_chart(
                        px.bar(melted, x="model_id", y="value", color="variable", barmode="group"),
                        width="stretch",
                    )
        else:
            st.info("No models registered yet.")
    except Exception as exc:
        st.error(f"Unable to load model catalog: {exc}")

with tabs[4]:
    st.subheader("Drift simulation")
    rows = st.slider("Rows", 20, 1000, 200, step=20)
    drifted = st.toggle("Shift incoming distribution", value=True)
    if st.button("Run drift check"):
        from netsentinel.services.sample_data import generate_synthetic_network_flows

        sample = generate_synthetic_network_flows(rows, seed=123, drift=drifted)
        flows = dataframe_to_flow_payloads(sample.drop(columns=["label", "attack_type"]))
        try:
            report = post_json("/api/v1/drift/check", {"flows": flows}, protected=True)
            status_label = "Drift detected" if report["drifted"] else "No drift"
            cols = st.columns(3)
            cols[0].metric("Status", status_label)
            cols[1].metric("Drift score", f"{report['drift_score']:.3f}")
            cols[2].metric("Threshold", f"{report['threshold']:.3f}")

            feature_scores = pd.DataFrame(report["features"])
            if not feature_scores.empty:
                top_features = feature_scores.head(10)
                st.plotly_chart(
                    px.bar(
                        top_features,
                        x="drift_score",
                        y="feature",
                        orientation="h",
                        color="drifted",
                        title="Top changed features",
                    ),
                    width="stretch",
                )
                st.dataframe(feature_scores, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Drift check failed: {exc}")

with tabs[5]:
    st.subheader("Incident response runbooks")
    st.markdown(
        """
        **Performance degradation**

        1. Confirm the drop in `/api/v1/performance`.
        2. Review recent drift scores and top changed features.
        3. Run a holdout validation job before switching models.
        4. Roll back to the previous production model if precision or recall drops.

        **Data drift**

        1. Inspect PSI, KL divergence, and KS results.
        2. Validate whether the shift is expected business traffic or an attack pattern.
        3. Trigger retraining with recent data and promote only if holdout F1 improves.

        **High error rate**

        1. Check request schema failures and model artifact availability.
        2. Verify registry metadata and active model path.
        3. Restart the API container after confirming artifacts are present.
        """
    )
