"""Run the whole sheet-only chain for one size/style.

Usage: python -I run_size.py <config.json>

config keys:
  name        short id, e.g. "gp_roman" (work dirs are work/<name>_*)
  family      e.g. "Caslon 1734 Great Primer"
  style       "Roman" | "Italic"
  trans       transcription file, or {"0": file, "1": file} when the copies are
              different settings (the Berner sheets of 1592 and 1622 are)
  boxes       {"0": [x0,y0,x1,y1], "1": [...], "2": [...]} on work/page<p>.png (or on prepared images, see 'images')
  images      optional {"0": "work/x_p0.png", ...}: prepared (e.g. deslanted) block images; boxes then refer to them
  ntext       number of running-text lines before the alphabet line
  borrow      optional --borrow spec used in alignment round 1 (e.g. "Q!:work/english_avg7:1.21")
  borrow_all  optional --borrow spec used in every round (e.g. a letter that never gets its own good template)
  synth       optional --synth spec for round 1
  rounds      alignment rounds (default 3)
  skip_segment  true to start straight from borrowed templates (italics), with 'start_avg'
  start_avg   template dir for round 1 when skip_segment
  slant       italic slant in degrees (0 for roman)
  descent     shared descent for the family (optional)
  pitch       body in px; if omitted, measured from the baselines
  fonts_dir   optional: where the fonts go (default "fonts"), e.g. a candidate folder
  sheet_drop  optional: list of sheet labels that are mis-cuts; their sheet impressions are
              ignored in the book merge (average.py, merge_metrics.py), so the books supply them
  tag         optional: suffix for the result json and upright build, so a trial run
              leaves the current work/<name>_result.json alone
"""
import sys, os, json, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np

S = os.path.dirname(os.path.abspath(__file__))
PY = [sys.executable, "-I", "-X", "utf8"]
sys.path.insert(0, S)
import typelib_profile as _prof  # noqa: E402   per-project settings (N:\Claude Work\_typelib)
JOBS = int(_prof.get("align_jobs"))   # copies segmented/aligned at once (env COLINES_JOBS)


def each(fn, items):
    # the copies are independent (own output dirs), so they can run side by side
    if JOBS <= 1:
        return [fn(i) for i in items]
    with ThreadPoolExecutor(JOBS) as ex:
        return list(ex.map(fn, items))


def run(args, quiet=True):
    r = subprocess.run(PY + args, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:]); raise SystemExit("step failed: " + " ".join(args[:2]))
    return r.stdout


def main():
    C = json.load(open(sys.argv[1], encoding="utf-8"))
    os.environ["GARAMONT_SHEET_DROP"] = ",".join(C.get("sheet_drop", []))   # read by average.py, merge_metrics.py
    reuse = "--reuse" in sys.argv      # keep existing alignment; redo merge, spacing, build
    # (--reuse --respace also keeps the book-merged averages in <name>_avgS: metrics and builds only)
    nm = C["name"]; W = "work"
    imgs = C.get("images") or {p: f"{W}/page{p}.png" for p in C["boxes"]}
    copies = sorted(C["boxes"])
    TR = C["trans"] if isinstance(C["trans"], dict) else {p: C["trans"] for p in copies}
    rounds = C.get("rounds", 3)
    # round 0: gap-based segmentation (romans) or borrowed templates (italics)
    if reuse:
        tpl = f"{W}/{nm}_avg{rounds}"
    elif not C.get("skip_segment"):
        each(lambda p: run([f"{S}/segment.py", imgs[p], *map(str, C["boxes"][p]), TR[p], f"{W}/{nm}_seg_p{p}"]), copies)
        run([f"{S}/average.py", f"{W}/{nm}_avg0"] + [f"{W}/{nm}_seg_p{p}" for p in copies])
        tpl = f"{W}/{nm}_avg0"
    else:
        tpl = C["start_avg"]
    for r in ([] if reuse else range(1, rounds + 1)):
        extra = []
        spec = ",".join(x for x in [C.get("borrow") if r == 1 else None, C.get("borrow_all")] if x)
        if spec:
            extra.append("--borrow=" + spec)
        if r == 1 and C.get("synth"):
            extra.append("--synth=" + C["synth"])
        def align(p):
            out = f"{W}/{nm}_al_p{p}"
            shutil.rmtree(out, ignore_errors=True)
            return run([f"{S}/segment_align.py", imgs[p], *map(str, C["boxes"][p]), TR[p], tpl, out] + extra)
        for p, o in zip(copies, each(align, copies)):
            for ln in o.splitlines()[1:]:
                if "all words aligned" not in ln:
                    print(f"  round {r} copy {p}: {ln}")
        tpl = f"{W}/{nm}_avg{r}"
        shutil.rmtree(tpl, ignore_errors=True)
        run([f"{S}/average.py", tpl] + [f"{W}/{nm}_al_p{p}" for p in copies])
    # alphabet line(s): capitals are letterspaced, so gap-based segmentation
    # separates them reliably; alignment is kept for the running text
    if not C.get("no_alpha_merge"):
        merged = []
        # first pass: which copies have a clean (unrepaired) gap-cut alphabet line?
        clean = {}
        for p in copies:
            seg = f"{W}/{nm}_aseg_p{p}"
            shutil.rmtree(seg, ignore_errors=True)
            subprocess.run(PY + [f"{S}/segment.py", imgs[p], *map(str, C["boxes"][p]), TR[p], seg], capture_output=True)
            if os.path.exists(f"{seg}/instances.json"):
                clean[p] = [i for i in json.load(open(f"{seg}/instances.json", encoding="utf-8"))["instances"] if i["line"] >= C["ntext"]]
        # a copy's gap-cut alphabet line is trusted when every glyph's width agrees
        # with the other copies (labels shifted by a bad split would not agree)
        widths = {}
        alph = dict(clean)
        for p, a_ in clean.items():
            for i in a_:
                widths.setdefault((i["line"], i["pos"], i["ch"]), []).append(i["x1"] - i["x0"])
        dev_ = {}; fallback_copy = None
        rat_p = os.path.join(W, "width_ratios.json")
        RAT = json.load(open(rat_p, encoding="utf-8"))["ratio"] if os.path.exists(rat_p) else {}
        for p, a_ in list(clean.items()):
            ok = bool(a_) and len(clean) >= 2
            # each capital must also have roughly its expected proportions (two
            # copies can make the identical mistake, e.g. S and T merged)
            hs_ = [i["y1"] - i["y0"] for i in a_ if i["ch"] in "EFHILT"]
            if hs_ and RAT:
                h_ = float(np.median(hs_))
                for i in a_:
                    r_ = RAT.get(i["ch"])
                    if r_ and i["ch"] not in "QJ" and abs((i["x1"] - i["x0"]) / (r_ * h_) - 1) > 0.35:
                        ok = False
            for i in a_:
                ws = widths[(i["line"], i["pos"], i["ch"])]
                if len(ws) < 2 or abs((i["x1"] - i["x0"]) / np.median(ws) - 1) > 0.15:
                    ok = False
            clean[p] = ok
            dev_[p] = float(np.mean([abs((i["x1"] - i["x0"]) / (RAT[i["ch"]] * h_) - 1) for i in a_
                                     if RAT.get(i["ch"]) and i["ch"] not in "QJ"])) if (a_ and hs_ and RAT) else 9.0
        any_clean = any(clean.values())
        if not any_clean and dev_:
            # no copy passes the strict test: fall back to the single copy whose
            # capital proportions fit best, if they fit reasonably
            bp = min(dev_, key=dev_.get)
            if dev_[bp] < 0.15:
                clean[bp] = True; any_clean = True
                fallback_copy = bp
                print(f"  fallback: alphabet line from copy {bp} (mean proportion deviation {dev_[bp]:.2f})")
        print("  alphabet line clean per copy:", clean)

        def rel_x(lst):
            # glyph centre as a fraction of its line's span, per (line, pos, ch)
            span = {}
            for i in lst:
                a, b = span.get(i["line"], (1e9, -1e9)); span[i["line"]] = (min(a, i["x0"]), max(b, i["x1"]))
            return {(i["line"], i["pos"], i["ch"]): ((i["x0"] + i["x1"]) / 2 - span[i["line"]][0]) / max(1, span[i["line"]][1] - span[i["line"]][0]) for i in lst}
        ref_x = {}
        for p, ok in clean.items():
            if ok:
                for k, v in rel_x(alph[p]).items():
                    ref_x.setdefault(k, []).append(v)

        def glyph_ok(i, rx, h2):
            # a single capital from an untrusted line: where every trusted copy has
            # the same letter, and with its expected proportions
            k = (i["line"], i["pos"], i["ch"])
            if k not in ref_x or abs(rx[k] - float(np.median(ref_x[k]))) > 0.01:
                return False
            r_ = RAT.get(i["ch"])
            return not r_ or i["ch"] in "QJ" or abs((i["x1"] - i["x0"]) / (r_ * h2) - 1) <= 0.2
        for p in copies:
            seg = f"{W}/{nm}_aseg_p{p}"
            alj = json.load(open(f"{W}/{nm}_al_p{p}/instances.json", encoding="utf-8"))
            if os.path.exists(f"{seg}/instances.json"):
                sgj = json.load(open(f"{seg}/instances.json", encoding="utf-8"))
                alpha = [i for i in sgj["instances"] if i["line"] >= C["ntext"]]
                # trust gap-cut capitals only when no split/merge repair was needed:
                # a repaired line can shift every later label by one letter
                bad_lines = set() if clean.get(p) else {i["line"] for i in alpha}
                if bad_lines and any_clean and RAT:
                    hs2 = [i["y1"] - i["y0"] for i in alpha if i["ch"] in "EFHILT"]
                    rx = rel_x(alpha)
                    alpha = [i for i in alpha if hs2 and glyph_ok(i, rx, float(np.median(hs2)))]
                    print(f"  copy {p}: {len(alpha)} single capitals kept from its untrusted alphabet line")
                else:
                    alpha = [i for i in alpha if i["line"] not in bad_lines]
                if p == fallback_copy and RAT:
                    # fallback copy: keep only capitals whose own proportions fit
                    hs2 = [i["y1"] - i["y0"] for i in alpha if i["ch"] in "EFHILT"]
                    if hs2:
                        h2 = float(np.median(hs2))
                        alpha = [i for i in alpha if not RAT.get(i["ch"]) or i["ch"] in "J"
                                 or abs((i["x1"] - i["x0"]) / (RAT[i["ch"]] * h2) - 1) <= 0.25]
                if bad_lines and not any_clean:
                    keep_al = [i for i in alj["instances"] if i["line"] in bad_lines]
                    alpha = alpha + [dict(i, _src="al") for i in keep_al]
                if bad_lines and any_clean and not alpha:
                    # drop this copy's alphabet line, keep its running text
                    out = f"{W}/{nm}_fin_p{p}"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
                    inst = []
                    for i in [i for i in alj["instances"] if i["line"] < C["ntext"]]:
                        fn = f"{len(inst):05d}.png"; shutil.copy(f"{W}/{nm}_al_p{p}/{i['file']}", f"{out}/{fn}"); inst.append(dict(i, file=fn))
                    json.dump(dict(alj, instances=inst), open(f"{out}/instances.json", "w", encoding="utf-8"), ensure_ascii=False)
                    merged.append(out); continue
                if alpha:
                    out = f"{W}/{nm}_fin_p{p}"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
                    inst = []
                    for src, items in ((f"{W}/{nm}_al_p{p}", [i for i in alj["instances"] if i["line"] < C["ntext"]]), (seg, alpha)):
                        for i in items:
                            sd = f"{W}/{nm}_al_p{p}" if i.get("_src") == "al" else src
                            fn = f"{len(inst):05d}.png"; shutil.copy(f"{sd}/{i['file']}", f"{out}/{fn}")
                            inst.append({k: v for k, v in dict(i, file=fn).items() if k != "_src"})
                    json.dump(dict(alj, instances=inst), open(f"{out}/instances.json", "w", encoding="utf-8"), ensure_ascii=False)
                    merged.append(out); continue
            merged.append(f"{W}/{nm}_al_p{p}")
        # large sizes: take every cleanly gap-cut word from segmentation, keep
        # alignment only for words that needed repair (touching letters)
        if C.get("prefer_seg"):
            # letter layouts (centres relative to the word's span) of every cleanly
            # cut word, from any copy: an aligned word whose letters sit elsewhere
            # has had its labels shifted, and is dropped
            def layout(ws):
                ws = sorted(ws, key=lambda i: i["pos"]); a, b = ws[0]["x0"], ws[-1]["x1"]
                return [((i["x0"] + i["x1"]) / 2 - a) / max(1, b - a) for i in ws]
            ref = {}
            for p in copies:
                if os.path.exists(f"{W}/{nm}_aseg_p{p}/instances.json"):
                    words = {}
                    for i in json.load(open(f"{W}/{nm}_aseg_p{p}/instances.json", encoding="utf-8"))["instances"]:
                        words.setdefault((i["line"], i["word"]), []).append(i)
                    for k, ws in words.items():
                        if len(ws) >= 3 and not any(i.get("repaired", True) for i in ws):
                            ref.setdefault(k, []).append(layout(ws))
            ndrop = 0
            for idx, p in enumerate(copies):
                seg = f"{W}/{nm}_aseg_p{p}"
                if not os.path.exists(f"{seg}/instances.json"):
                    continue
                sg = json.load(open(f"{seg}/instances.json", encoding="utf-8"))["instances"]
                good = {(i["line"], i["word"]) for i in sg if not i.get("repaired", True)}
                good -= {(i["line"], i["word"]) for i in sg if i.get("repaired", True)}
                src = merged[idx]
                cur = json.load(open(f"{src}/instances.json", encoding="utf-8"))
                words = {}
                for i in cur["instances"]:
                    if (i["line"], i["word"]) not in good:
                        words.setdefault((i["line"], i["word"]), []).append(i)
                shifted = set()
                for k, ws in words.items():
                    if k in ref and len(ws) >= 3:
                        lo = layout(ws)
                        if all(len(r) == len(lo) and max(abs(x - y) for x, y in zip(r, lo)) > 0.12 for r in ref[k]):
                            shifted.add(k)
                ndrop += len(shifted)
                cur = dict(cur, instances=[i for i in cur["instances"] if (i["line"], i["word"]) not in shifted])
                out = f"{W}/{nm}_pfs_p{p}"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
                inst = []
                for d_, items in ((src, [i for i in cur["instances"] if (i["line"], i["word"]) not in good]),
                                  (seg, [i for i in sg if (i["line"], i["word"]) in good])):
                    for i in items:
                        fn = f"{len(inst):05d}.png"; shutil.copy(f"{d_}/{i['file']}", f"{out}/{fn}"); inst.append(dict(i, file=fn))
                json.dump(dict(cur, instances=inst), open(f"{out}/instances.json", "w", encoding="utf-8"), ensure_ascii=False)
                merged[idx] = out
            print("  prefer_seg: clean gap-cut words used where available;", ndrop, "aligned words dropped as label-shifted")
        if True:   # always re-average the final instance set
            tpl = f"{W}/{nm}_avgF"; shutil.rmtree(tpl, ignore_errors=True)
            run([f"{S}/average.py", tpl] + merged)
        al = merged
    else:
        al = [f"{W}/{nm}_al_p{p}" for p in copies]
    if C.get("relabel"):
        # a sheet line whose labels slid after a bad split (Brevier roman: on the
        # alphabet line S and T merged, so each later capital took the previous
        # letter's label). "relabel": {"line": n, "map": "S>T,T>V", "drop": "Z,QR"}
        # - "S>T" = the glyph labelled S is really T; drop = labels to discard
        # (a fragment, a fused pair). Applied to the sheet copies before averaging.
        rl = C["relabel"]
        mp = dict(x.split(">") for x in rl["map"].split(",") if x)
        drop = set(x for x in rl.get("drop", "").split(",") if x)
        for d in al:
            meta = json.load(open(f"{d}/instances.json", encoding="utf-8"))
            if meta.get("relabelled"):
                continue
            keep = []
            for i in meta["instances"]:
                if i["line"] == rl["line"]:
                    if i["ch"] in drop:
                        continue
                    i["ch"] = mp.get(i["ch"], i["ch"])
                keep.append(i)
            meta["instances"] = keep; meta["relabelled"] = rl
            json.dump(meta, open(f"{d}/instances.json", "w", encoding="utf-8"), ensure_ascii=False)
        tpl = f"{W}/{nm}_avgF"; shutil.rmtree(tpl, ignore_errors=True)
        run([f"{S}/average.py", tpl] + al)
    # body = line pitch, unless given
    if "pitch" in C:
        pitch = float(C["pitch"])
    else:
        P = []
        for d in al:
            I = json.load(open(f"{d}/instances.json", encoding="utf-8"))["instances"]
            bl = {}
            for i in I:
                bl.setdefault(i["line"], []).append(i["baseline"])
            b = [np.median(v) for k, v in sorted(bl.items())]
            P += list(np.diff(b)[:max(1, C["ntext"] - 1)])
        pitch = float(np.median(P))
    if C.get("specimen"):
        # Caslon's later specimen books printed from the same cuts (matched at the
        # same size, scripts/titling_match.py): their impressions count like the
        # sheet's copies, for shapes and for spacing
        import glob as _g
        spec = sorted(d for pat in C["specimen"].split(",") for d in _g.glob(pat) if os.path.exists(f"{d}/instances.json"))
        al = al + spec
        tpl = f"{W}/{nm}_avgP"; shutil.rmtree(tpl, ignore_errors=True)
        run([f"{S}/average.py", tpl] + al)
    sp = run([f"{S}/spacing.py", tpl, str(C["ntext"])] + al).splitlines()[0]
    if C.get("supp"):
        # supplementary book sources: used only for glyphs the sheet lacks; book
        # spacing is mapped onto the sheet's metrics (merge_metrics.py)
        import glob as _g, shutil as _sh
        supp = sorted(d for pat in C["supp"].split(",") for d in _g.glob(pat) if os.path.exists(f"{d}/instances.json"))
        avgS = f"{W}/{nm}_avgS"
        # --respace: keep the averaged glyphs and the measured book spacing in avgS,
        # redo only the merge of the metrics and the builds
        if not ("--respace" in sys.argv and os.path.exists(f"{avgS}/metrics_book.json")):
            shutil.rmtree(avgS, ignore_errors=True)
            lst = f"{W}/{nm}_sources.txt"
            open(lst, "w").write(chr(10).join(al + ["+" + d for d in supp]))
            run([f"{S}/average.py", avgS, "@" + lst])
            _sh.copy(f"{tpl}/metrics.json", f"{avgS}/metrics_1734.json")
            lst2 = f"{W}/{nm}_supp.txt"; open(lst2, "w").write(chr(10).join("+" + d for d in supp))
            run([f"{S}/spacing.py", avgS, str(C["ntext"]), "@" + lst2])
            _sh.copy(f"{avgS}/metrics.json", f"{avgS}/metrics_book.json")
        m_ = run([f"{S}/merge_metrics.py", avgS, str(pitch), ",".join(al), str(C["ntext"])])
        if _prof.get("fix_degenerate"):
            # Caslon: glyphs the solver could not measure (one or two pairs) get estimated spacing
            ref_ = _prof.get("fix_degenerate").format(style=C["style"].lower(), n="4" if C["style"] == "Roman" else "11")
            run([f"{S}/fix_degenerate_spacing.py", avgS, ref_])
        tpl = avgS
        sp += " | supplements: " + str(len(supp)) + " dirs; " + m_.strip().splitlines()[-1]
    fam = C["family"]; style = C["style"]
    slant = C.get("slant", 0)
    common = [f"--family={fam}", f"--style={style}"] + ([f"--slant={slant}"] if slant else []) + \
             ([f"--descent={C['descent']}"] if "descent" in C else []) +              ([f"--extra={C['extra']}"] if C.get("extra") and os.path.exists(f"{C['extra']}/metrics.json") else [])
    base = fam.replace(" ", "")
    outs = []
    for v, sfx in (("clean", ""), ("impression", "Impression")):
        fn = f"{C.get('fonts_dir', 'fonts')}/{base}{sfx}-{style}.otf"
        run([f"{S}/build.py", tpl, v, str(pitch), fn] + common); outs.append(fn)
    # fidelity on an upright build
    run([f"{S}/build.py", tpl, "clean", str(pitch), f"{W}/{nm}_upright{C.get('tag', '')}.otf", f"--family={fam}", f"--style={style}"])
    fid = run([f"{S}/fidelity.py", f"{W}/{nm}_upright{C.get('tag', '')}.otf", str(pitch)] + al).strip().splitlines()
    res = dict(name=nm, pitch_px=round(pitch, 1), pitch_in=round(pitch / 600, 4), spacing=sp, fidelity=fid, fonts=outs, templates=tpl)
    if _prof.get("check_build") and os.path.exists(f"{S}/check_build.py"):
        # stale seeds, unfitted spacing, lost glyphs (against the last backup, if C names one), thin glyphs
        res["checks"] = subprocess.run(PY + [f"{S}/check_build.py", tpl] + ([C["previous"]] if C.get("previous") else []),
                                       capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()
    if _prof.get("check_glyphs") and os.path.exists(f"{S}/check_glyphs.py"):
        # is each glyph the letter its label says: class, cross-source and agreement checks
        refs_ = ",".join(_prof.get("check_refs").get(style, []))
        g_ = subprocess.run(PY + [f"{S}/check_glyphs.py", tpl, "--ref=" + refs_] + (["--italic"] if slant else []),
                            capture_output=True, text=True, encoding="utf-8")
        res["glyph_checks"] = (g_.stdout.strip().splitlines() or [g_.stderr.strip()[-300:]])[-1]
    json.dump(res, open(f"{W}/{nm}_result{C.get('tag', '')}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
