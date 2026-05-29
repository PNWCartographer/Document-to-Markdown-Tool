"""
Targeted stress test re-run — verifies fixes for findings from the initial run.

Only runs:
  CS4  — Caption association + image refs (verify image refs now appear in markdown)
  CS8  — Large CSV → all formats (verify find_output false positive is fixed)
  CS11 — Cancel during searchable PDF (verify cancel fires with larger PDF)
  CS13 — AI-Ready Chunks on large PDF (never ran in initial suite)
  CS14 — Each small file with Quality preset (never ran)
  CS15 — Confidence validation (never ran)

Run:  python stress_rerun.py
"""
import os
import sys
import importlib

# Reuse everything from the comprehensive suite
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import stress_comprehensive as sc

# Override output root so we don't clobber the previous run
sc.OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "_stress_output_rerun")

# Reset counters
sc.PASS = 0
sc.FAIL = 0
sc.WARN = 0
sc.FINDINGS = []
sc.results_log = []
sc._run_id = 0

import time
import shutil
import traceback


def main():
    start = time.time()

    sc.log("╔══════════════════════════════════════════════════════════╗")
    sc.log("║  Targeted Stress Test Re-Run (Fix Verification)         ║")
    sc.log("╚══════════════════════════════════════════════════════════╝")
    sc.log(f"\nTest files:  {sc.TEST_FILES}")
    sc.log(f"Output dir:  {sc.OUTPUT_ROOT}")
    sc.log(f"Time:        {time.strftime('%Y-%m-%d %H:%M:%S')}")
    sc.log("")

    # Clean output
    if os.path.exists(sc.OUTPUT_ROOT):
        shutil.rmtree(sc.OUTPUT_ROOT, ignore_errors=True)
    os.makedirs(sc.OUTPUT_ROOT, exist_ok=True)

    # Only the suites we need to re-verify
    suites = [
        ("CS4",  sc.cs4_caption_association),
        ("CS8",  sc.cs8_csv_formats),
        ("CS11", sc.cs11_cancel_searchable_pdf),
        ("CS13", sc.cs13_rag_chunks_large),
        ("CS14", sc.cs14_quality_preset_each),
        ("CS15", sc.cs15_confidence_validation),
    ]

    for label, fn in suites:
        try:
            fn()
        except Exception as e:
            sc.log(f"\n  ✗ {label} CRASHED: {e}")
            traceback.print_exc()
            sc.FINDINGS.append(("CRASH", label, str(e)))
            sc.FAIL += 1

    elapsed = time.time() - start

    # Summary
    sc.log(f"\n{'='*60}")
    sc.log(f"RESULTS:  {sc.PASS} passed  |  {sc.FAIL} failed  |  {sc.WARN} warnings")
    sc.log(f"Elapsed:  {elapsed:.1f}s ({elapsed/60:.1f} min)")
    sc.log(f"{'='*60}")

    if sc.FINDINGS:
        sc.log(f"\n{'─'*60}")
        sc.log("FINDINGS REPORT")
        sc.log(f"{'─'*60}")

        fails = [f for f in sc.FINDINGS if f[0] == "FAIL"]
        warns = [f for f in sc.FINDINGS if f[0] == "WARN"]
        crashes = [f for f in sc.FINDINGS if f[0] == "CRASH"]
        notes = [f for f in sc.FINDINGS if f[0] == "NOTE"]

        if crashes:
            sc.log(f"\n🔴 CRASHES ({len(crashes)}):")
            for _, suite, msg in crashes:
                sc.log(f"  [{suite}] {msg}")
        if fails:
            sc.log(f"\n🔴 FAILURES ({len(fails)}):")
            for _, suite, msg in fails:
                sc.log(f"  [{suite}] {msg}")
        if warns:
            sc.log(f"\n🟡 WARNINGS ({len(warns)}):")
            for _, suite, msg in warns:
                sc.log(f"  [{suite}] {msg}")
        if notes:
            sc.log(f"\n🔵 OBSERVATIONS ({len(notes)}):")
            for _, suite, msg in notes:
                sc.log(f"  [{suite}] {msg}")
    else:
        sc.log("\n✅ All checks passed — no findings.")

    # Write report
    report_path = os.path.join(sc.OUTPUT_ROOT, "stress_rerun_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(sc.results_log))
    sc.log(f"\nFull report: {report_path}")

    try:
        sc._ROOT.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    main()
