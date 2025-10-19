import os
import CombineHarvester.CombineTools.ch as ch
import argparse

lumi_base = 59.83
# lumi_target = 137.66 # Run 2 full
lumi_target = 430.8 # Run 2 + Run 3
lumi_sf = lumi_target / lumi_base
USE_LUMI_SF = False

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ntuple-tag", default=os.environ.get("NTUPLETAG"))
    p.add_argument("--tag", default=os.environ.get("TAG")) # nn_tag
    p.add_argument("--era", default=os.environ.get("ERA"))
    p.add_argument("--final-state", default="all", choices=["et", "mt", "tt", "all"])
    p.add_argument("--output-dir")
    p.add_argument("--systematics", action="store_true", help="Add systematic uncertainties to datacard")
    return p.parse_args()

def get_synced_shapes_dir(era, channel, ntuple_tag, tag):
    return f"output/{era}-{channel}-{ntuple_tag}-{tag}/synced/htt_{channel}.inputs-sm-Run{era}-ML.root"

def main():
    args = parse_args()
    cb = ch.CombineHarvester()

    ntupelTag = args.ntuple_tag
    tag = args.tag
    era = args.era
    use_systematics = args.systematics
    output_dir = args.output_dir if args.output_dir else f"/work/sdaigler/smhtt_ul/output/datacards/{ntupelTag}/{tag}/{args.final_state}"

    print(f"[INFO] ntuple tag: {ntupelTag}, tag: {tag}, era: {era}")

    # Defining analysis-specific configuration
    final_states = ["mt", "et", "tt"] if args.final_state == "all" else [args.final_state]
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
        "QCD"
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
        synced_shapes_dir = get_synced_shapes_dir(era, fs, ntupelTag, tag)
        print(f"[INFO] Using synced shapes from: {synced_shapes_dir}")
        cb.cp().channel([fs]).ExtractShapes(synced_shapes_dir, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC")

    # Adding luminosity scale factor
    if USE_LUMI_SF:
        cb.cp().ForEachProc(lambda pr: pr.set_rate(pr.rate() * lumi_sf))
        print(f"[INFO] Scaled MC rates by x{lumi_sf:.3f} to target luminosity {lumi_target} fb^-1 (base {lumi_base} fb^-1).")


    # Adding systematic uncertainties
    if use_systematics:
        print("[INFO] Adding systematic uncertainties to datacard")
        cb.cp().channel(["et"]).AddSyst(cb,"eff_e","lnN",ch.SystMap()(1.02))
        cb.cp().channel(["mt"]).AddSyst(cb,"eff_m","lnN",ch.SystMap()(1.02))

        # eff_t only for IDvsEle and IDvsMu, 
        T_VS_LEP = 1.01
        cb.cp().channel(["et","mt"]).AddSyst(cb,"eff_t_vsLep_$CHANNEL_$ERA","lnN",ch.SystMap()(T_VS_LEP))
        cb.cp().channel(["tt"]).AddSyst(cb,"eff_t_vsLep_$CHANNEL_$ERA","lnN",ch.SystMap()(T_VS_LEP * T_VS_LEP))

        # eff_t for IDvsJet (normally as shapes)
        T_VS_JET = 1.02 # Only a guess
        cb.cp().channel(["et","mt"]).AddSyst(cb,"eff_t_vsJet_$CHANNEL_$ERA","lnN",ch.SystMap()(T_VS_JET))
        cb.cp().channel(["tt"]).AddSyst(cb,"eff_t_vsJet_$CHANNEL_$ERA","lnN",ch.SystMap()(T_VS_JET * T_VS_JET))

        # https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2
        cb.cp().AddSyst(cb, "lumi_13TeV_$ERA", "lnN", ch.SystMap()(1.025))

        # Uncertainty: Background normalizations
        # VV 
        cb.cp().process(["VVT", "VVJ", "VVL"]).AddSyst(cb, "htt_vvXsec", "lnN", ch.SystMap()(1.05))
        
        # ST 
        cb.cp().process(["ST-STT", "ST-STJ", "ST-STL"]).AddSyst(cb, "htt_stXsec", "lnN", ch.SystMap()(1.05))

        # TT
        cb.cp().process(["TTT", "TTL", "TTJ"]).AddSyst(cb, "htt_tjXsec", "lnN", ch.SystMap()(1.06))
        
        # W
        cb.cp().process(["W"]).AddSyst(cb, "htt_wjXsec", "lnN", ch.SystMap()(1.04))

        # Z
        cb.cp().process(["ZTT", "ZL", "ZJ"]).AddSyst(cb, "htt_zjXsec", "lnN", ch.SystMap()(1.02))
        
        # ttH
        cb.cp().process(["ttH_htt125"]).AddSyst(cb, "QCDscale_ttH", "lnN", ch.SystMap()((1.058, 0.908)))
        cb.cp().process(["ttH_htt125"]).AddSyst(cb, "pdf_ttH",      "lnN", ch.SystMap()(1.030))
        cb.cp().process(["ttH_htt125"]).AddSyst(cb, "alphaS_ttH",   "lnN", ch.SystMap()(1.020))

        # ggH
        cb.cp().process(["ggH_htt125"]).AddSyst(cb, "QCDscale_ggH", "lnN", ch.SystMap()(1.039))
        cb.cp().process(["ggH_htt125"]).AddSyst(cb, "pdf_ggH",      "lnN", ch.SystMap()(1.019))
        cb.cp().process(["ggH_htt125"]).AddSyst(cb, "alphaS_ggH",   "lnN", ch.SystMap()(1.026))

        # qqH
        cb.cp().process(["qqH_htt125"]).AddSyst(cb, "QCDscale_qqH", "lnN", ch.SystMap()((1.004, 0.997)))
        cb.cp().process(["qqH_htt125"]).AddSyst(cb, "pdf_qqH",      "lnN", ch.SystMap()(1.021))
        cb.cp().process(["qqH_htt125"]).AddSyst(cb, "alphaS_qqH",   "lnN", ch.SystMap()(1.005))

        # VH (kombiniert WH + ZH): QCDscale (envelope), pdf (max), alphaS (gemeinsam)
        cb.cp().process(["VH125"]).AddSyst(cb, "QCDscale_VH", "lnN", ch.SystMap()((1.038, 0.970)))
        cb.cp().process(["VH125"]).AddSyst(cb, "pdf_VH",      "lnN", ch.SystMap()(1.017))
        cb.cp().process(["VH125"]).AddSyst(cb, "alphaS_VH",   "lnN", ch.SystMap()(1.009))

        # QCD from AN resolved_2b 
        # Not for et because no QCD estimated by ABCD method in this channel
        cb.cp().channel(["et"]).bin_id([2,3,5]).process(["QCD"]).AddSyst(cb, "QCDNorm_$CHANNEL_$ERA", "lnN", ch.SystMap()(1.108))
        cb.cp().channel(["mt"]).process(["QCD"]).AddSyst(cb, "QCDNorm_$CHANNEL_$ERA", "lnN", ch.SystMap()(1.108))
        cb.cp().channel(["tt"]).process(["QCD"]).AddSyst(cb, "QCDNorm_$CHANNEL_$ERA", "lnN", ch.SystMap()(1.216))

        # Signal
        # QCD Scale
        cb.cp().process([signal]).AddSyst(cb, "QCDscale_HH", "lnN", ch.SystMap()((1.022, 0.95)))

        # PDF+alphaS (gemeinsam, ±3%) – falls getrennt gewünscht, aufsplitten
        cb.cp().process([signal]).AddSyst(cb, "PDF_alphas_HH", "lnN", ch.SystMap()(1.03))

        # m_top Effekt (±2.6%)
        cb.cp().process([signal]).AddSyst(cb, "mtop_HH", "lnN", ch.SystMap()(1.026))

        # Branching Fractions für H→bb und H→ττ
        cb.cp().process([signal]).AddSyst(cb, "BR_h_bb",      "lnN", ch.SystMap()((1.0125, 0.9873)))
        cb.cp().process([signal]).AddSyst(cb, "BR_h_tautau",  "lnN", ch.SystMap()(1.0165))
        print(f"[INFO] Added systematic uncertainties to the datacard")
    else:
        print("[INFO] Not adding systematic uncertainties to datacard")


    # Removing processes with yield smaller or equal to 0
    cb.FilterProcs(lambda p : p.rate() <= 0.0)

    # Running an autorebinning: https://github.com/cms-analysis/CombineHarvester/blob/main/CombineTools/src/AutoRebin.cc
    rebinner = ch.AutoRebin().SetBinThreshold(1.0).SetBinUncertFraction(0.9).SetRebinMode(1).SetPerformRebin(True).SetVerbosity(1)
    rebinner.Rebin(cb,cb)

    # Adjust naming scheme of categories
    ch.SetStandardBinNames(cb, "$ANALYSIS_$CHANNEL_$BINID_$ERA")

    # Add bin-by-bin (Barlow-Beeston light)
    cb.SetAutoMCStats(cb, 0.0)

    # Write datacards
    writer = ch.CardWriter(f"{output_dir}/$TAG/$BIN.txt", f"{output_dir}/$TAG/common/htt_input_{era}.root")
    writer.SetVerbosity(1)
    writer.WriteCards("cmb", cb) # "cmb" is $TAG in this context

    # Printout content of combine harvester workspace
    cb.PrintAll()

if __name__ == "__main__":
    main()