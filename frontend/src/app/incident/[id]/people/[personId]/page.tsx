"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CasePerson, getPerson } from "@/lib/api";
import { Loader2 } from "lucide-react";
export default function PersonPage(){const {id,personId}=useParams() as {id:string;personId:string};const [person,setPerson]=useState<CasePerson|null>(null);useEffect(()=>{getPerson(id,personId).then(setPerson).catch(console.error)},[id,personId]);if(!person)return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto"/></div>;return <div className="page-container max-w-3xl"><Link href={`/incident/${id}/people`} className="text-sm text-gray-500">← Back to People</Link><p className="metric-label mt-5">PERSON</p><h1 className="text-display">{person.display_name}</h1><p className="text-gray-600 mt-2">Requirement version {person.requirement_version} · {person.requirements_reviewed?"Confirmed":"Review required"}</p><Link href={`/incident/${id}/people/${personId}/review`} className="btn-primary mt-6">REVIEW REQUIREMENTS</Link></div>}
