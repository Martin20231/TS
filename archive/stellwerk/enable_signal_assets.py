"""Fuegt Kuju RailSimulator + TrainTeamBerlin AS_Common zum Szenario RequiredSet hinzu."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: enable_signal_assets.py <scenario_dir>")
        return 1

    scenario_dir = Path(sys.argv[1])
    xml_path = scenario_dir / "ScenarioProperties.xml"
    if not xml_path.exists():
        print(f"[FEHLER] Nicht gefunden: {xml_path}")
        return 1

    text = xml_path.read_text(encoding="utf-8")
    additions = [
        ("Kuju", "RailSimulator"),
        ("TrainTeamBerlin", "AS_Common"),
    ]

    for i, (provider, product) in enumerate(additions):
        token = f">{provider}</Provider>"
        product_token = f">{product}</Product>"
        if token in text and product_token in text:
            # Grobe Pruefung ob Paar im RequiredSet vorkommt
            chunk = text[text.find("<RequiredSet>") : text.find("</RequiredSet>")]
            if provider in chunk and product in chunk:
                print(f"[OK] Bereits vorhanden: {provider} / {product}")
                continue

        block = (
            f'\t\t<iBlueprintLibrary-cBlueprintSetID d:id="661077{i}">\n'
            f'\t\t\t<Provider d:type="cDeltaString">{provider}</Provider>\n'
            f'\t\t\t<Product d:type="cDeltaString">{product}</Product>\n'
            f"\t\t</iBlueprintLibrary-cBlueprintSetID>"
        )
        marker = "\t</RequiredSet>"
        if marker not in text:
            print("[FEHLER] RequiredSet nicht gefunden")
            return 1
        text = text.replace(marker, block + "\n" + marker, 1)
        print(f"[OK] Hinzugefuegt: {provider} / {product}")

    bak = xml_path.with_suffix(".xml.bak_stellwerk")
    if not bak.exists():
        bak.write_text(xml_path.read_text(encoding="utf-8"), encoding="utf-8")

    xml_path.write_text(text, encoding="utf-8")
    md5 = xml_path.with_name("ScenarioProperties.xml.MD5")
    if md5.exists():
        md5.unlink()
        print("[OK] Alte MD5 entfernt")

    print()
    print("Szenario im Editor NEU oeffnen -> Signal-Symbol -> Taste M -> S ModSig SH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
