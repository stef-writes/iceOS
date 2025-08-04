from __future__ import annotations

"""Generate Prometheus rule file from MetricName enum.

Outputs YAML compatible with Prometheus rule files under docs/generated/.
"""

from pathlib import Path

import yaml  # type: ignore

from ice_core.models.enums import MetricName


def main() -> None:
    rules = []
    for metric in MetricName:
        rules.append(
            {
                "alert": f"{metric.value}_absent",
                "expr": f"absent({metric.value})",
                "for": "15m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": f"Metric {metric.value} missing"},
            }
        )

    rule_file = {
        "groups": [
            {
                "name": "iceos-generated",
                "rules": rules,
            }
        ]
    }

    out_path = Path("docs/generated/metric_rules.yaml")
    out_path.write_text(yaml.dump(rule_file, sort_keys=False))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
