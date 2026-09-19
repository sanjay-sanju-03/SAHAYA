"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { addPerson, CasePerson, evaluateGroup, getPeople } from "@/lib/api";
import { Loader2, Plus, Users } from "lucide-react";

function activeCount(person: CasePerson) {
  const p = person.person;
  return [p.wheelchair_required, p.stairs_allowed === false, p.accessible_transport_required, p.caregiver_required, p.visual_communication_required, p.hearing_support_required].filter(Boolean).length;
}

export default function PeoplePage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [people, setPeople] = useState<CasePerson[]>([]);
  const [name, setName] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPeople(id).then((result) => setPeople(result.people)).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, [id]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !text.trim()) return;
    setAdding(true); setError("");
    try { const person = await addPerson(id, name, text); setPeople((items) => [...items, person]); setName(""); setText(""); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to add person."); }
    finally { setAdding(false); }
  };
  const allReviewed = people.length >= 2 && people.every((person) => person.requirements_reviewed);
  if (loading) return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600" /></div>;
  return <div className="page-container max-w-4xl">
    <Link href={`/incident/${id}`} className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to case</Link>
    <div className="mt-5 mb-8"><p className="metric-label mb-2">MULTI-PERSON CASE</p><h1 className="text-display">People</h1><p className="text-gray-600 mt-2">Each person has independently reviewed requirements. Group evaluation uses the same deterministic rules for everyone.</p></div>
    <div className="grid sm:grid-cols-3 gap-3 mb-6"><div className="metric-card"><p className="metric-label">PEOPLE</p><p className="text-2xl font-bold">{people.length}</p></div><div className="metric-card"><p className="metric-label">CONFIRMED</p><p className="text-2xl font-bold">{people.filter((person) => person.requirements_reviewed).length}</p></div><div className="metric-card"><p className="metric-label">GROUP STATUS</p><p className={`text-sm font-bold ${allReviewed ? "text-safe-700" : "text-unknown-700"}`}>{allReviewed ? "READY" : "REVIEW REQUIRED"}</p></div></div>
    <div className="space-y-3 mb-8">{people.map((person) => <div key={person.id} className="card p-5 flex flex-col sm:flex-row justify-between gap-4"><div><p className="metric-label">PERSON</p><h2 className="font-bold text-lg">{person.display_name}</h2><p className="text-sm text-gray-600 mt-1">{activeCount(person)} active requirement{activeCount(person) === 1 ? "" : "s"} · {person.requirements_reviewed ? `Confirmed v${person.requirement_version}` : "Review required"}</p></div><Link className="btn-secondary" href={`/incident/${id}/people/${person.id}/review`}>REVIEW</Link></div>)}</div>
    <form onSubmit={submit} className="card p-5"><div className="flex items-center gap-2 mb-4"><Plus className="w-5 h-5 text-teal-700" /><h2 className="font-bold">Add Person</h2></div><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Name / Identifier" className="w-full rounded-lg border border-gray-300 p-3 text-sm mb-3" /><textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Emergency report for this person..." rows={4} className="w-full rounded-lg border border-gray-300 p-3 text-sm" /><button disabled={adding || !name.trim() || !text.trim()} className="btn-primary mt-4">{adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}START ANALYSIS</button></form>
    {error && <p className="text-sm text-blocked-700 mt-4">{error}</p>}
    <button disabled={!allReviewed} onClick={async () => { await evaluateGroup(id); router.push(`/incident/${id}/group-evaluation`); }} className="btn-primary mt-6 w-full sm:w-auto"><Users className="w-5 h-5" />EVALUATE GROUP</button>
  </div>;
}
