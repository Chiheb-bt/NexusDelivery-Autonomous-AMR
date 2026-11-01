#!/usr/bin/env python3
"""
tools/generate_bom_table.py
Reads BOM.csv (the single source of truth) and generates:
1. Mathematical validation of all line items (Quantity * Unit Cost == Extended Cost).
2. Clean Markdown table representation for README.md.
"""
import csv
import os
import sys

def parse_bom(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"BOM file not found: {csv_path}")

    items = []
    summary_rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subsystem = row['Subsystem'].strip()
            if subsystem.startswith('Total') or 'Tunisie' in subsystem:
                summary_rows.append(row)
            else:
                qty = int(row['Quantity'])
                unit_cost = float(row['Unit Cost USD'])
                ext_cost = float(row['Extended Cost USD'])
                expected_ext = round(qty * unit_cost, 2)
                if abs(ext_cost - expected_ext) > 0.01:
                    raise ValueError(
                        f"Arithmetic mismatch on {row['Component']}: "
                        f"{qty} * {unit_cost} = {expected_ext}, but got {ext_cost}"
                    )
                items.append({
                    'subsystem': subsystem,
                    'component': row['Component'].strip(),
                    'part_number': row['Part Number'].strip(),
                    'specs': row['Key Specifications'].strip(),
                    'quantity': qty,
                    'unit_cost': unit_cost,
                    'extended_cost': ext_cost,
                    'status': row['Status'].strip(),
                    'source': row['Source / Link'].strip()
                })

    computed_parts_total = round(sum(i['extended_cost'] for i in items), 2)
    return items, computed_parts_total, summary_rows

def generate_markdown_table(csv_path):
    items, parts_total, _ = parse_bom(csv_path)

    # Standard Tunisia freight + customs estimate (approx 30% of CIF value + air freight)
    freight_customs_tn = 580.00
    landed_tn = round(parts_total + freight_customs_tn, 2)

    md = []
    md.append("| Sous-systeme | Composant | Reference / Specifications | Qte | Cout unitaire (USD) | Total poste (USD) | Statut preuve |")
    md.append("|:---|:---|:---|:---:|:---:|:---:|:---:|")

    for it in items:
        source_link = f"[{it['component']}]({it['source']})" if it['source'].startswith('http') else it['component']
        md.append(
            f"| **{it['subsystem']}** | {source_link} | {it['specs']} | {it['quantity']} | ${it['unit_cost']:.2f} | ${it['extended_cost']:.2f} | {it['status']} |"
        )

    md.append(f"| **Total pieces brutes** | NexusDelivery AMR (16 postes) | Composants bruts sortie usine | - | - | **${parts_total:.2f} USD** | CALCULÉ |")
    md.append(f"| *Fret et douane Tunisie* | Transport aerien (15kg) + Droits douane/TVA (~30%) | Transit et dedouanement indicatif | - | - | *${freight_customs_tn:.2f} USD* | ESTIMATION - A VERIFIER |")
    md.append(f"| **Total rendu Tunisie** | NexusDelivery Landed Cost | Cout total indicatif d approvisionnement | - | - | **${landed_tn:.2f} USD** | ESTIMATION - A VERIFIER |")

    return "\n".join(md), parts_total, landed_tn

if __name__ == '__main__':
    default_csv = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'delivery_robot_sim', 'web_dashboard', 'downloads', 'BOM.csv'
    )
    csv_file = sys.argv[1] if len(sys.argv) > 1 else default_csv
    table_md, parts_tot, landed_tot = generate_markdown_table(csv_file)
    print(f"BOM verified mathematically. Parts Total: ${parts_tot:.2f} USD | Landed TN: ${landed_tot:.2f} USD\n")
    print(table_md)
