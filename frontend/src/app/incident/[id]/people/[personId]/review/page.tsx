"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { confirmPersonRequirements, getPersonRequirements, RequirementReviewItem, RequirementValue, updatePersonRequirement } from "@/lib/api";
import { CheckCircle2, Loader2 } from "lucide-react";
const options: RequirementValue[] = ["required", "not_required", "unknown"];
export default function PersonReviewPage() {
  const { id, personId } = useParams() as { id: string; personId: string }; const router=useRouter();
  const [requirements,setRequirements]=useState<RequirementReviewItem[]>([]); const [reviewed,setReviewed]=useState(false); const [loading,setLoading]=useState(true); const [saving,setSaving]=useState(false);
  useEffect(()=>{getPersonRequirements(id,personId).then(r=>{setRequirements(r.requirements);setReviewed(r.reviewed)}).finally(()=>setLoading(false))},[id,personId]);
  if(loading)return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto"/></div>;
  return <div className="page-container max-w-3xl"><Link href={`/incident/${id}/people`} className="text-sm text-gray-500">← Back to People</Link><h1 className="text-display mt-5 mb-2">Review person requirements</h1><p className="text-gray-600 mb-6">Confirm the requirements for this person before group evaluation.</p><div className="space-y-3">{requirements.map(r=><section key={r.field} className="card p-5 flex flex-col sm:flex-row justify-between gap-3"><div><h2 className="font-bold">{r.label}</h2><p className="text-xs text-gray-500 mt-1">AI proposal: {r.ai_value.replaceAll("_"," ")}</p></div><div className="grid grid-cols-3 gap-2">{options.map(value=><button key={value} onClick={async()=>{setSaving(true);await updatePersonRequirement(id,personId,r.field,value);setRequirements(items=>items.map(i=>i.field===r.field?{...i,final_value:value}:i));setReviewed(false);setSaving(false)}} disabled={saving} className={`rounded-lg border px-3 py-2 text-xs font-semibold ${r.final_value===value?"border-teal-600 bg-teal-50 text-teal-800":"border-gray-200"}`}>{value.replaceAll("_"," ")}</button>)}</div></section>)}</div><button disabled={saving} onClick={async()=>{setSaving(true);await confirmPersonRequirements(id,personId);router.push(`/incident/${id}/people`)}} className="btn-primary mt-6"><CheckCircle2 className="w-5 h-5"/>{reviewed?"Back to People":"Confirm Requirements"}</button></div>;
}
