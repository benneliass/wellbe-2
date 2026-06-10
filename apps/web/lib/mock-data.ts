import type { Thread } from "./types";

/**
 * Sample data — a person's own health threads.
 *
 * THIS IS THE SWAP POINT. When the API is wired (WEL-150), replace the bodies of
 * `getThreads` / `getThread` with @wellbe/api-client calls (and make them async).
 * Screens consume only those functions, never this array directly.
 */
const THREADS: Thread[] = [
  {
    id: "back",
    title: "Lower back pain",
    status: "active",
    question: "What is causing the recurring ache, and is it improving?",
    started: "Started 2 months ago",
    updated: "Updated today",
    risk: "low",
    changed: "Pain down from 6/10 to 3/10 over 3 weeks",
    metrics: [
      { label: "Pain level", value: "3", unit: "/10", delta: "-3", dir: "good" },
      { label: "PT sessions", value: "4", unit: "of 6", delta: null },
    ],
    rail: [
      { label: "Intake", state: "done", meta: "May 12, 9:30 AM" },
      { label: "Assessment", state: "done", meta: "May 13, 10:15 AM" },
      { label: "Physical therapy", state: "current", meta: "In progress" },
      { label: "Re-assessment", state: "upcoming", meta: "Pending" },
    ],
    events: [
      { type: "reported", time: "Today, 8:10 AM", title: "Logged morning stiffness", detail: "Stiff ~15 min, eased after walking.", state: "current" },
      { type: "appointment", time: "May 18, 2:00 PM", title: "PT session 4 of 6", detail: "Focus on hip mobility + core.", state: "done" },
      { type: "note", time: "May 13, 10:15 AM", title: "Assessment note", detail: "No red-flag symptoms. Mechanical pattern.", state: "done", conf: 4, review: "clinician" },
      { type: "lab", time: "May 12, 9:30 AM", title: "Intake & history", detail: "Onset, triggers, and prior episodes recorded.", state: "done" },
    ],
    evidence: [
      { src: "note", title: "Physio assessment", author: "City Physio", date: "May 13", conf: 4 },
      { src: "reported", title: "Symptom log (12 entries)", author: "You", date: "Ongoing", conf: 3 },
      { src: "wearable", title: "Daily step count", author: "Watch", date: "Ongoing", conf: 3 },
    ],
  },
  {
    id: "labs",
    title: "Abnormal lab results",
    status: "attention",
    question: "Why is my CRP elevated, and what should I ask about?",
    started: "Started May 8",
    updated: "Updated 2 days ago",
    risk: "medium",
    changed: "CRP 18 mg/L — above your usual range",
    metrics: [
      { label: "CRP", value: "18", unit: "mg/L", delta: "+11", dir: "bad" },
      { label: "Sources", value: "3", unit: "", delta: null },
    ],
    rail: [
      { label: "Results received", state: "attention", meta: "May 8, 8:45 AM" },
      { label: "Review", state: "current", meta: "Needs attention" },
      { label: "Follow-up", state: "upcoming", meta: "Pending" },
    ],
    events: [
      { type: "lab", time: "May 8, 8:45 AM", title: "CBC, CRP & metabolic panel", detail: "CRP elevated at 18 mg/L.", state: "attention", conf: 5, review: "verified" },
      { type: "note", time: "May 8, 9:00 AM", title: "Auto-summary", detail: "Elevated CRP may indicate inflammation.", state: "done", conf: 3, review: "ai" },
    ],
    evidence: [
      { src: "lab", title: "CBC w/ Differential", author: "City Health Lab", date: "May 8", conf: 5 },
      { src: "note", title: "Progress note", author: "Dr. Jane Smith", date: "May 8", conf: 4 },
      { src: "research", title: "CRP & inflammation markers", author: "PubMed", date: "May 6", conf: 2 },
    ],
  },
  {
    id: "sleep",
    title: "Sleep & energy",
    status: "monitoring",
    question: "Is my sleep pattern affecting daytime energy?",
    started: "Started 3 weeks ago",
    updated: "Updated yesterday",
    risk: "informational",
    changed: "Avg 6h 20m — trending up 25m this week",
    metrics: [
      { label: "Avg sleep", value: "6h 20m", unit: "", delta: "+25m", dir: "good" },
      { label: "Restful nights", value: "4", unit: "of 7", delta: null },
    ],
    rail: [
      { label: "Baseline set", state: "done", meta: "3 weeks ago" },
      { label: "Monitoring", state: "current", meta: "In progress" },
      { label: "Review", state: "upcoming", meta: "Pending" },
    ],
    events: [
      { type: "wearable", time: "Last night", title: "Sleep recorded", detail: "6h 41m · 2 awakenings.", state: "current" },
      { type: "reported", time: "May 16", title: "Logged afternoon slump", detail: "Low energy around 3 PM.", state: "done" },
    ],
    evidence: [
      { src: "wearable", title: "Sleep tracking", author: "Watch", date: "Ongoing", conf: 4 },
      { src: "reported", title: "Energy log", author: "You", date: "Ongoing", conf: 3 },
    ],
  },
  {
    id: "vacc",
    title: "Vaccination record",
    status: "resolved",
    question: "Are my records complete and up to date?",
    started: "Started Apr 28",
    updated: "Resolved Apr 29",
    risk: "low",
    changed: "All records verified and current",
    metrics: [{ label: "Records", value: "12", unit: "", delta: null }],
    rail: [
      { label: "Intake", state: "done", meta: "Apr 28" },
      { label: "Verification", state: "done", meta: "Apr 29" },
      { label: "Resolved", state: "done", meta: "Apr 29" },
    ],
    events: [
      { type: "doc", time: "Apr 29, 10:05 AM", title: "Record updated & verified", detail: "All entries match clinic records.", state: "done", conf: 5, review: "verified" },
    ],
    evidence: [{ src: "doc", title: "Immunization record", author: "County Clinic", date: "Apr 29", conf: 5 }],
  },
];

export function getThreads(): Thread[] {
  return THREADS;
}

export function getThread(id: string): Thread | undefined {
  return THREADS.find((t) => t.id === id);
}
