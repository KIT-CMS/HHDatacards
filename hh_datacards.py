import os
import CombineHarvester.CombineTools.ch as ch
import argparse

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ntuple-tag", default=os.environ.get("NTUPLETAG"))
    p.add_argument("--tag", default=os.environ.get("TAG"))
    p.add_argument("--era", default=os.environ.get("ERA"))
    return p.parse_args()

def main():
    args = parse_args()
    cb = ch.CombineHarvester()

    cmssw_base = os.environ.get("CMSSW_BASE")
    shapes_dir = f"{cmssw_base}/src/HHDatacards/shapes/equal-events-1"

    ntupelTag = args.ntuple_tag
    tag = args.tag
    era = args.era

    print(f"[INFO] ntuple tag: {ntupelTag}, tag: {tag}, era: {era}")

    output_dir = f"/work/sdaigler/smhtt_ul/output/datacards/{ntupelTag}-{tag}"

    # Defining analysis-specific configuration
    final_states = ["mt", "et", "tt"]
    backgrounds = [
        "W",
        "EWK",
        "ZTT", "ZL", "ZJ",
        "TTT", "TTL", "TTJ",
        "VVJ", "VVT", "VVL",
        "VVV-VVVJ", "VVV-VVVT", "VVV-VVVL",
        "ST-STT", "ST-STJ", "ST-STL",
        "TTV-TTVJ", "TTV-TTVL", "TTV-TTVT",
        "ggH_htt125", "qqH_htt125", "ttH_htt125", "VH125",
    ]
    signal = "HH2B2Tau"

    categories = {}

    # Declaring categories, processes and extracting their shapes
    for fs in final_states:
        categories[fs] = [
            ( 1, f"{fs}_HH2B2Tau"),
            ( 2, f"{fs}_DY"),
            ( 3, f"{fs}_ST"),
            ( 4, f"{fs}_TT"),
            ( 5, f"{fs}_VV"),
            ( 6, f"{fs}_Other"),
        ]
        cb.AddObservations(["*"], ["htt"], [era], [fs], categories[fs])
        cb.AddProcesses(["*"], ["htt"], [era], [fs], backgrounds, categories[fs], signal=False)
        cb.AddProcesses([""], ["htt"], [era], [fs], [signal], categories[fs], signal=True)
        cb.cp().channel([fs]).ExtractShapes(f"{shapes_dir}/htt_{fs}.inputs-sm-Run{era}-ML.root", "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC")

    # Adding systematic uncertainties
    cb.cp().AddSyst(cb,"eff_m","lnN",ch.SystMap()(1.03)) # Example uncertainty

    # Removing processes with yield smaller or equal to 0
    cb.FilterProcs(lambda p : p.rate() <= 0.0)

    # Running an autorebinning: https://github.com/cms-analysis/CombineHarvester/blob/main/CombineTools/src/AutoRebin.cc
    rebinner = ch.AutoRebin().SetBinThreshold(1.0).SetBinUncertFraction(0.9).SetRebinMode(1).SetPerformRebin(True).SetVerbosity(1)
    rebinner.Rebin(cb,cb)

    # Adjust naming scheme of categories
    ch.SetStandardBinNames(cb, "$ANALYSIS_$CHANNEL_$BINID_$ERA")

    # Add bin-by-bin (Barlow-Beeston light)
    cb.SetAutoMCStats(cb, 10.0)

    # Write datacards
    writer = ch.CardWriter(f"{output_dir}/$TAG/$BIN.txt", f"{output_dir}/$TAG/common/htt_input_{era}.root")
    writer.SetVerbosity(1)
    writer.WriteCards("cmb", cb) # "cmb" is $TAG in this context

    # Printout content of combine harvester workspace
    cb.PrintAll()

if __name__ == "__main__":
    main()