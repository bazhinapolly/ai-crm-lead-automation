"""Evaluate deterministic or optional OpenAI lead priority on synthetic labeled cases."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from lead_ai import analyze_lead  # noqa: E402
from openai_provider import OpenAIProvider  # noqa: E402

def metrics(cases,predictions):
    rows=[{"id":case["id"],"expected":case["expected"],"predicted":predicted} for case,predicted in zip(cases,predictions,strict=True)]; per_label={}
    for label in ("Hot","Warm","Cold"):
        tp=sum(row["expected"]==label and row["predicted"]==label for row in rows); fp=sum(row["expected"]!=label and row["predicted"]==label for row in rows); fn=sum(row["expected"]==label and row["predicted"]!=label for row in rows)
        per_label[label]={"precision":round(tp/(tp+fp),4) if tp+fp else None,"recall":round(tp/(tp+fn),4) if tp+fn else None,"true_positive":tp,"false_positive":fp,"false_negative":fn}
    correct=sum(row["expected"]==row["predicted"] for row in rows); return {"accuracy":round(correct/len(rows),4),"total":len(rows),"per_label":per_label,"cases":rows}
def load_cases():
    value=json.loads((ROOT/"evaluations"/"scoring-cases.json").read_text(encoding="utf-8"))
    if not isinstance(value,list) or len(value)<15: raise ValueError("scoring evaluation requires at least 15 cases")
    ids=set(); labels=set()
    for item in value:
        if not isinstance(item,dict) or set(item)!={"id","expected","message"}: raise ValueError("scoring evaluation case has an invalid schema")
        if item["id"] in ids or item["expected"] not in {"Hot","Warm","Cold"}: raise ValueError("scoring evaluation case has a duplicate id or invalid label")
        if not isinstance(item["message"],str) or not item["message"].strip(): raise ValueError("scoring evaluation messages must be non-empty strings")
        ids.add(item["id"]); labels.add(item["expected"])
    if labels!={"Hot","Warm","Cold"}: raise ValueError("scoring evaluation must include every priority label")
    return value
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("deterministic","openai"),default="deterministic"); parser.add_argument("--require-perfect",action="store_true"); args=parser.parse_args(); cases=load_cases(); provider=None
    if args.mode=="openai":
        key=os.environ.get("OPENAI_API_KEY","").strip()
        if not key: raise SystemExit("OPENAI_API_KEY is required for OpenAI evaluation mode")
        provider=OpenAIProvider(key,os.environ.get("OPENAI_MODEL","gpt-4o-mini-2024-07-18"))
    report={"mode":args.mode,**metrics(cases,[analyze_lead(case["message"],provider=provider).priority_label for case in cases])}; print(json.dumps(report,indent=2))
    if args.require_perfect and report["accuracy"]!=1.0: raise SystemExit("scoring regression evaluation did not match all specification labels")
if __name__=="__main__": main()
