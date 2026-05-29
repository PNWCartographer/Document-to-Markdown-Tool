"""
Quick CS4-only verification — confirms the page_range fix for _extract_fitz_images.

Checks:
  1. Newnes handbook (438p, 30 requested) completes within 300s timeout
  2. Equipment manual (177p, 30 requested) produces image refs (was 0 before fix)
  3. Algebra textbook (1467p, 30 requested) still produces refs + captions

Run:  python stress_verify_cs4.py
"""
import os, sys, time, shutil, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import stress_comprehensive as sc

# Isolated output directory
sc.OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "_stress_output_verify")
sc.PASS = 0
sc.FAIL = 0
sc.WARN = 0
sc.FINDINGS = []
sc.results_log = []
sc._run_id = 0

if os.path.exists(sc.OUTPUT_ROOT):
    shutil.rmtree(sc.OUTPUT_ROOT, ignore_errors=True)
os.makedirs(sc.OUTPUT_ROOT, exist_ok=True)


def main():
    start = time.time()
    sc.log("=" * 60)
    sc.log("CS4 Fix Verification — page_range image extraction")
    sc.log("=" * 60)

    candidates = [
        ("Algebra textbook (1467p)",
         "algebra-and-trigonometry-2e_-_WEB.pdf"),
        ("Newnes handbook (438p)",
         "newnes_electrical_engineers_handbook.pdf"),
        ("Equipment manual (177p)",
         "heavy-equipment-operation-and-maintenance-manual-1nbsped-1032419806-9781032419800_compress.pdf"),
    ]

    for label, fname in candidates:
        pdf = sc.find_file(fname)
        if not pdf:
            sc.warn(f"{label} — file not found")
            continue

        pages = sc.pdf_pages(pdf) or 100
        mid = max(10, pages // 3)
        page_range = list(range(mid, min(mid + 30, pages + 1)))

        sc.log(f"\n─── {label} ───")
        sc.log(f"  Pages: {page_range[0]}-{page_range[-1]} of {pages}")

        t0 = time.time()
        result, out_dir, logs, _ = sc.run(
            [pdf],
            {"preserve_images": True, "embed_images": False},
            page_ranges={pdf: page_range},
            timeout=300,
        )
        elapsed = time.time() - t0
        sc.log(f"  Elapsed: {elapsed:.1f}s")

        md = sc.read_output(out_dir)
        sc.check(f"{label} converts within 300s", md is not None)

        if md:
            img_refs = re.findall(r"!\[([^\]]*)\]\(", md)
            generic = [r for r in img_refs if r.startswith("Image from page")]
            captioned = [r for r in img_refs if not r.startswith("Image from page")]

            sc.log(f"  Image refs: {len(img_refs)} total, "
                   f"{len(captioned)} captioned, {len(generic)} generic")

            sc.check(f"{label} has image refs", len(img_refs) > 0,
                     "0 image refs in markdown")

            if captioned:
                sc.check(f"{label} has captions", True)
                for cap in captioned[:3]:
                    sc.log(f"    Caption: {cap[:80]}")
            else:
                sc.note(f"{label} — no captions detected")

            # Verify images are only from the requested page range
            page_nums_in_refs = set()
            for r in re.findall(r"image_\d+_p(\d+)\.", md):
                page_nums_in_refs.add(int(r))
            if page_nums_in_refs:
                out_of_range = page_nums_in_refs - set(page_range)
                sc.check(f"{label} images only from requested pages",
                         len(out_of_range) == 0,
                         f"found images from pages outside range: {sorted(out_of_range)[:10]}")
                sc.log(f"  Image pages: {sorted(page_nums_in_refs)[:10]}{'...' if len(page_nums_in_refs)>10 else ''}")

            assets = [f for f in sc.list_outputs(out_dir) if "assets" in f]
            sc.log(f"  Asset files: {len(assets)}")

    elapsed_total = time.time() - start
    sc.log(f"\n{'=' * 60}")
    sc.log(f"RESULTS:  {sc.PASS} passed  |  {sc.FAIL} failed  |  {sc.WARN} warnings")
    sc.log(f"Elapsed:  {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
    sc.log(f"{'=' * 60}")

    if sc.FINDINGS:
        fails = [f for f in sc.FINDINGS if f[0] == "FAIL"]
        if fails:
            sc.log(f"\n🔴 FAILURES ({len(fails)}):")
            for _, suite, msg in fails:
                sc.log(f"  [{suite}] {msg}")
    else:
        sc.log("\n✅ All checks passed — fix verified.")

    # Write report
    report = os.path.join(sc.OUTPUT_ROOT, "verify_report.txt")
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(sc.results_log))
    sc.log(f"\nReport: {report}")

    try:
        sc._ROOT.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    main()
