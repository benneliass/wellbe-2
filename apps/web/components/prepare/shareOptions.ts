/**
 * Recipient types for a packet share. The id is sent as the share `purpose`
 * (a C1/C10 purpose code); the label is what the person sees.
 */
export const RECIPIENT_TYPES = [
  { purpose: "clinician_visit", label: "A clinician", hint: "Doctor, nurse, or specialist" },
  { purpose: "caregiver_support", label: "A caregiver", hint: "Family or someone who helps you" },
  { purpose: "personal_share", label: "Someone else", hint: "Anyone else you choose" },
] as const;

export type RecipientPurpose = (typeof RECIPIENT_TYPES)[number]["purpose"];

export const RECIPIENT_LABEL: Record<string, string> = {
  clinician_visit: "Clinician",
  caregiver_support: "Caregiver",
  personal_share: "Someone else",
};

export const EXPIRY_OPTIONS = [
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 168 },
  { label: "30 days", hours: 720 },
] as const;
